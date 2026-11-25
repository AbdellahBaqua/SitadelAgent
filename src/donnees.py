r"""Outil de données : fraîcheur et rafraîchissement des extractions Sitadel (API DiDo du SDES), Yvelines.

Version Python de fetch_yvelines.ps1, utilisable par les agents (outils `fraicheur_donnees` et `rafraichir_donnees`
de src/explore.py) et en ligne de commande :

  python -X utf8 src\donnees.py fraicheur
  python -X utf8 src\donnees.py simuler tous             # télécharge, contrôle et compare, sans rien remplacer
  python -X utf8 src\donnees.py rafraichir tous          # ou : logements / locaux

Méthode : export CSV filtré `DEP_CODE=eq:78` (une requête, quelques secondes) ; en secours, pagination /rows par
pages de 100 (comme fetch_yvelines.ps1). Avant de remplacer le fichier local : contrôle des colonnes, du département et
du nombre de lignes (= décompte de l'API). L'ancien fichier est archivé dans raw\archive\, et une fiche de provenance
est écrite à côté (<fichier>.meta.json).
"""
import csv, io, json, shutil, sys, time, urllib.error, urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datafiles"
UA = {"User-Agent": "sitadel-prototype/0.1"}
JEUX = {"logements": {"rid": "8b35affb-55fc-4c1f-915b-7750f974446a", "fichier": ROOT / "data" / "sortie.csv"},
        "locaux": {"rid": "f8f0700f-806c-40a7-83b1-f21cf507e7c4", "fichier": ROOT / "data" / "sortie_locaux.csv"}}
COLONNES_REQUISES = {"DEP_CODE", "COMM", "TYPE_DAU", "NUM_DAU", "ETAT_DAU", "AN_DEPOT", "CJ_DEM", "APE_DEM", "SIREN_DEM"}
MILLESIME_INITIAL = "2026-10"   # fichiers fournis au départ du projet (extraction faite hors de cet outil)


def _get(url, timeout=120, essais=4):
    for i in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or i == essais - 1:
                raise
        except (urllib.error.URLError, OSError):
            if i == essais - 1:
                raise
        time.sleep(3 * (i + 1))


def _meta_local(jeu):
    p = JEUX[jeu]["fichier"].with_suffix(".meta.json")
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    f = JEUX[jeu]["fichier"]
    return {"millesime": MILLESIME_INITIAL, "lignes": None, "recupere_le": None,
            "note": "fiche absente : fichier fourni au départ, millésime supposé " + MILLESIME_INITIAL,
            "modifie_le": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds") if f.exists() else None}


def fraicheur():
    """Compare, pour chaque fichier, le millésime local au dernier millésime publié par le SDES."""
    out = {}
    for jeu, j in JEUX.items():
        loc = _meta_local(jeu)
        try:
            m = json.loads(_get(f"{API}/{j['rid']}", timeout=60))
            dist = {"millesime": m.get("millesime"), "publie_le": m.get("published"), "titre": m.get("title")}
        except Exception as e:                                   # réseau indisponible : on le dit, sans planter
            dist = {"erreur": str(e)}
        out[jeu] = {"local": loc, "distant": dist,
                    "a_jour": dist.get("millesime") == loc.get("millesime") if "millesime" in dist else None}
    return out


def _compte(rid, millesime, dep):
    d = json.loads(_get(f"{API}/{rid}/rows?millesime={millesime}&pageSize=10&page=1&DEP_CODE=eq:{dep}", timeout=60))
    return int(d["total"])


def _pagination(rid, millesime, dep, total):
    """Secours : même logique que fetch_yvelines.ps1 (pages de 100, l'une après l'autre)."""
    lignes, page = [], 1
    while len(lignes) < total:
        d = json.loads(_get(f"{API}/{rid}/rows?millesime={millesime}&pageSize=100&page={page}&DEP_CODE=eq:{dep}"))
        if not d.get("data"):
            break
        lignes += d["data"]
        page += 1
        time.sleep(0.3)
    if not lignes:
        return ""
    cols = list(lignes[0])
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(cols)
    for r in lignes:
        w.writerow(["" if r.get(c) is None else (str(r[c]).lower() if isinstance(r[c], bool) else r[c]) for c in cols])
    return buf.getvalue()


def _comparer(f, lignes):
    """Différences entre le fichier local et l'extraction reçue (sans rien écrire)."""
    if not f.exists():
        return {"local": "absent"}
    with open(f, encoding="utf-8-sig", newline="") as fh:
        loc = list(csv.DictReader(fh, delimiter=";"))
    a, b = {r["NUM_DAU"]: r for r in loc}, {r["NUM_DAU"]: r for r in lignes}
    communs = a.keys() & b.keys()
    changes = sum(1 for k in communs if any((a[k].get(c) or "") != (b[k].get(c) or "") for c in ("ETAT_DAU", "SIREN_DEM", "CJ_DEM")))
    return {"lignes_locales": len(loc), "lignes_recues": len(lignes), "permis_nouveaux": len(b.keys() - a.keys()),
            "permis_disparus": len(a.keys() - b.keys()), "permis_modifies_etat_ou_demandeur": changes}


def rafraichir(jeu, departement="78", millesime=None, simulation=False):
    """Télécharge l'extraction du département, la contrôle, puis remplace le fichier local (ancien archivé).
    simulation=True : télécharge et contrôle, compare au fichier local, mais ne remplace rien."""
    if jeu == "tous":
        return {j: rafraichir(j, departement, millesime, simulation) for j in JEUX}
    if jeu not in JEUX:
        return {"erreur": f"jeu inconnu : {jeu} (logements, locaux ou tous)"}
    j = JEUX[jeu]
    meta = json.loads(_get(f"{API}/{j['rid']}", timeout=60))
    millesime = millesime or meta["millesime"]
    attendu = _compte(j["rid"], millesime, departement)
    url = f"{API}/{j['rid']}/csv?millesime={millesime}&DEP_CODE=eq:{departement}"
    t0, methode = time.time(), "export CSV filtré"
    try:
        texte = _get(url, timeout=300).decode("utf-8-sig")
    except Exception:
        texte, methode = _pagination(j["rid"], millesime, departement, attendu), "pagination /rows (secours)"
    lignes = list(csv.DictReader(io.StringIO(texte), delimiter=";"))
    # ---- contrôles avant remplacement
    probs = []
    if not lignes:
        probs.append("aucune ligne reçue")
    else:
        manq = COLONNES_REQUISES - set(lignes[0])
        if manq:
            probs.append(f"colonnes manquantes : {sorted(manq)}")
        hors = sum(1 for r in lignes if r.get("DEP_CODE") != departement)
        if hors:
            probs.append(f"{hors} lignes hors département {departement}")
    if len(lignes) != attendu:
        probs.append(f"{len(lignes)} lignes reçues pour {attendu} attendues")
    if probs:
        return {"jeu": jeu, "ok": False, "fichier_local_inchange": True, "problemes": probs}
    if simulation:
        return {"jeu": jeu, "ok": True, "simulation": True, "fichier_local_inchange": True, "millesime": millesime,
                "methode": methode, "duree_s": round(time.time() - t0, 1), "comparaison": _comparer(j["fichier"], lignes)}
    # ---- remplacement (ancien fichier archivé)
    f = j["fichier"]
    if f.exists():
        arch = ROOT / "data" / "archive"
        arch.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, arch / f"{f.stem}_{datetime.now():%Y%m%d_%H%M%S}{f.suffix}")
    tmp = f.with_suffix(".tmp")
    tmp.write_text(texte, encoding="utf-8")
    tmp.replace(f)
    fiche = {"jeu": jeu, "millesime": millesime, "publie_le": meta.get("published"), "departement": departement,
             "lignes": len(lignes), "methode": methode, "duree_s": round(time.time() - t0, 1),
             "recupere_le": datetime.now().isoformat(timespec="seconds"), "source": url}
    f.with_suffix(".meta.json").write_text(json.dumps(fiche, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, **fiche}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "fraicheur"
    jeu = sys.argv[2] if len(sys.argv) > 2 else "tous"
    res = (fraicheur() if cmd == "fraicheur" else
           rafraichir(jeu, simulation=True) if cmd == "simuler" else rafraichir(jeu))
    print(json.dumps(res, ensure_ascii=False, indent=1))
