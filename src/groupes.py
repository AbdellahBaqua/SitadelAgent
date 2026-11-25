r"""Fouille 1 : rattacher les sociétés de programme (SCCV, SNC…) à leur groupe promoteur.

  python -X utf8 src\groupes.py

Méthode : pour chaque demandeur de la famille « promoteur » (logements et locaux), on lit ses dirigeants dans
l'Annuaire des entreprises (API publique) et on ne garde QUE les dirigeants personnes morales (les personnes physiques
sont écartées dès la lecture, jamais stockées : consigne du brief). Le groupe retenu est le dirigeant personne morale
gérant / président ; à défaut le premier dirigeant personne morale ; à défaut la société elle-même.
Limite : un seul niveau (le gérant peut lui-même être une filiale d'un groupe plus large).

Sorties : out_fouille/groupes_societes.csv (une ligne par société), out_fouille/groupes_synthese.csv (par groupe).
"""
import http.client, json, re, time, urllib.request, urllib.parse, urllib.error
from collections import defaultdict
from fouille_commun import CACHE, permis, familles, ecrire_csv, entier

CACHE_PM = CACHE / "dirigeants_personnes_morales.json"
QUALITES_PRIORITAIRES = ("gérant", "gerant", "président", "president", "directeur général", "co-gérant")


def dirigeants_pm(siren, cache):
    if siren in cache:
        return cache[siren]
    url = "https://recherche-entreprises.api.gouv.fr/search?" + urllib.parse.urlencode({"q": siren, "per_page": 1})
    req = urllib.request.Request(url, headers={"User-Agent": "sitadel-prototype/0.1"})
    for essai in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read()).get("results", [])
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5 * (essai + 1))
                continue
            return None
        except (urllib.error.URLError, OSError, http.client.HTTPException):   # coupure réseau, serveur qui ferme
            time.sleep(3 * (essai + 1))
    else:
        return None
    time.sleep(0.4)                                            # cadence raisonnable
    pm = []
    if res and res[0].get("siren") == siren:
        for d in res[0].get("dirigeants") or []:
            if d.get("type_dirigeant") == "personne morale" and d.get("siren"):   # personnes physiques ignorées
                pm.append({"siren": d["siren"], "denomination": d.get("denomination") or "",
                           "qualite": d.get("qualite") or ""})
    cache[siren] = pm
    return pm


EXCLUS = ("commissaire aux comptes", "liquidateur", "administrateur provisoire")   # contrôle / procédure, pas le groupe


def rang_qualite(q):
    """Plus petit = plus représentatif du groupe. None = à exclure."""
    q = (q or "").lower()
    if any(x in q for x in EXCLUS):
        return None
    if q.startswith(("gérant", "gerant", "président", "president", "directeur général", "directeur general")) or ", gérant" in q:
        return 0                                    # dirige la société
    if q.startswith(("associé", "associe")):
        return 1                                    # associé responsable : souvent la société mère d'une SNC / SCCV
    return 2                                        # « Autre », membre, administrateur… : indice faible


# Le registre étiquette parfois mal les rôles (ex. un cabinet d'audit noté « président du conseil d'administration ») :
# on écarte aussi, par leur nom, les cabinets d'audit / expertise comptable (heuristique documentée).
AUDIT = re.compile(r"AUDIT|MAZARS|KPMG|DELOITTE|ERNST|PRICEWATERHOUSE|\bPWC\b|GRANT THORNTON|\bBDO\b|\bRSM\b|\bEXCO\b"
                   r"|FIDUCIAIRE|EXPERTISE|EXPERT[S]? COMPTABLE|COMMISSARIAT|COMPTAB", re.I)


def groupe_principal(pm):
    cands = [(rang_qualite(d["qualite"]), i, d) for i, d in enumerate(pm)
             if rang_qualite(d["qualite"]) is not None and not AUDIT.search(d["denomination"] or "")]
    return min(cands)[2] if cands else None


def main():
    cache = json.loads(CACHE_PM.read_text(encoding="utf-8")) if CACHE_PM.exists() else {}
    fam = {"logements": familles("logements"), "locaux": familles("locaux")}
    promoteurs = {}
    for jeu, acteurs in fam.items():
        for s, a in acteurs.items():
            if a["famille"] == "promoteur":
                promoteurs.setdefault(s, a)
    print(f"promoteurs (logements + locaux) : {len(promoteurs)}", flush=True)

    vol = defaultdict(lambda: {"permis_log": 0, "logements": 0, "permis_loc": 0, "surface_m2": 0,
                               "annees": set(), "communes": set()})
    for r in permis("logements"):
        v = vol[r["SIREN_DEM"]]
        v["permis_log"] += 1; v["logements"] += entier(r["NB_LGT_TOT_CREES"])
        v["annees"].add(r["AN_DEPOT"]); v["communes"].add(r["COMM"])
    for r in permis("locaux"):
        v = vol[r["SIREN_DEM"]]
        v["permis_loc"] += 1; v["surface_m2"] += entier(r["SURF_LOC_CREEE"])
        v["annees"].add(r["AN_DEPOT"]); v["communes"].add(r["COMM"])

    societes = []
    for i, (s, a) in enumerate(sorted(promoteurs.items())):
        pm = dirigeants_pm(s, cache)
        if i % 50 == 0:
            CACHE_PM.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"  {i}/{len(promoteurs)}", flush=True)
        g = groupe_principal(pm or [])
        societes.append({
            "siren": s, "denomination": a["denomination"], "cj": a["cj"],
            "groupe_siren": g["siren"] if g else s, "groupe_nom": g["denomination"] if g else a["denomination"],
            "qualite_dirigeant": g["qualite"] if g else "",
            "methode": "dirigeant personne morale" if g else ("annuaire indisponible" if pm is None else "aucun dirigeant personne morale retenu : la société elle-même"),
            "autres_dirigeants_pm": " | ".join(d["denomination"] for d in (pm or []) if not g or d["siren"] != g["siren"]),
            "permis_logements": vol[s]["permis_log"], "logements": vol[s]["logements"],
            "permis_locaux": vol[s]["permis_loc"], "surface_m2": vol[s]["surface_m2"],
            "source": f"https://annuaire-entreprises.data.gouv.fr/entreprise/{s}",
        })
    CACHE_PM.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    ecrire_csv("groupes_societes.csv", societes)

    grp = defaultdict(lambda: {"societes": set(), "permis_logements": 0, "logements": 0, "permis_locaux": 0,
                               "surface_m2": 0, "annees": set(), "communes": set(), "nom": ""})
    for x in societes:
        g = grp[x["groupe_siren"]]
        g["nom"] = x["groupe_nom"]; g["societes"].add(x["siren"])
        for k in ("permis_logements", "logements", "permis_locaux", "surface_m2"):
            g[k] += x[k]
        g["annees"] |= vol[x["siren"]]["annees"]; g["communes"] |= vol[x["siren"]]["communes"]
    synth = [{"groupe_siren": k, "groupe_nom": g["nom"], "nb_societes": len(g["societes"]),
              "permis_logements": g["permis_logements"], "logements": g["logements"],
              "permis_locaux": g["permis_locaux"], "surface_m2": g["surface_m2"],
              "annees_actives": len(g["annees"]), "premiere_annee": min(g["annees"]) if g["annees"] else "",
              "derniere_annee": max(g["annees"]) if g["annees"] else "", "nb_communes": len(g["communes"]),
              "source": f"https://annuaire-entreprises.data.gouv.fr/entreprise/{k}"}
             for k, g in grp.items()]
    synth.sort(key=lambda x: (-(x["permis_logements"] + x["permis_locaux"]), -x["logements"]))
    ecrire_csv("groupes_synthese.csv", synth)
    n_rat = sum(1 for x in societes if x["methode"] == "dirigeant personne morale")
    print(f"sociétés : {len(societes)} | rattachées à un dirigeant personne morale : {n_rat} | groupes : {len(synth)}")
    print("top 10 groupes :")
    for x in synth[:10]:
        print(f"  {x['groupe_nom'][:40]:40s} sociétés={x['nb_societes']:3d} PC log={x['permis_logements']:3d} "
              f"logts={x['logements']:5d} PC loc={x['permis_locaux']:3d}")


if __name__ == "__main__":
    main()
