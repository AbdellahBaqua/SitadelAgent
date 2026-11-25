r"""Échantillons de contrôle à vérifier À LA MAIN, puis mesure de la précision.

  python -X utf8 src\echantillon.py tirer      # écrit out_fouille\controle\echantillon_familles.csv et echantillon_prospects.csv
  python -X utf8 src\echantillon.py mesurer    # lit les colonnes remplies -> out_fouille\controle\precision.md

Familles : 50 demandeurs tirés au hasard (graine fixe) par strates, pour mesurer séparément la précision des
règles sur les familles cibles de Buddimm, des règles sur les autres familles et de l'agent :
  15 règles / familles cibles, 10 règles / autres familles, 20 agent, 5 non_determine.
Prospects : 20 verdicts de l'agent de qualification (prospect, à vérifier, faux positif).

Comment remplir : ouvrir le lien source_entreprise (et FINESS si utile), puis écrire dans
- famille_verifiee : la famille juste (même liste fermée), ou « ? » si impossible à trancher ;
- verdict_verifie (prospects) : prospect, faux_positif ou a_verifier.
Une ligne laissée vide n'est pas comptée. Ne rien ajouter sur des personnes physiques.
"""
import csv, json, math, random, sys
from collections import Counter, defaultdict
from fouille_commun import ROOT, FOUILLE

DOSSIER = FOUILLE / "controle"
DOSSIER.mkdir(exist_ok=True)
F_FAM, F_PROS = DOSSIER / "echantillon_familles.csv", DOSSIER / "echantillon_prospects.csv"
CIBLES = {"association_ess", "exploitant_sante_social", "bailleur_social"}
STRATES = [("règles, familles cibles", 15), ("règles, autres familles", 10), ("agent", 20), ("non_determine", 5)]


def acteurs():
    vus = {}
    for jeu, d in (("logements", "out"), ("locaux", "out_locaux")):
        with open(ROOT / d / "acteurs_classes.csv", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f, delimiter=";"):
                vus.setdefault(r["siren"], {**r, "fichier": jeu})        # un SIREN présent dans les deux fichiers : une ligne
    return list(vus.values())


def strate(r):
    if r["famille"] == "non_determine":
        return "non_determine"
    if r["methode"].startswith("agent"):
        return "agent"
    return "règles, familles cibles" if r["famille"] in CIBLES else "règles, autres familles"


def tirer():
    rnd = random.Random(78)
    par = defaultdict(list)
    for r in acteurs():
        par[strate(r)].append(r)
    lignes = []
    for s, n in STRATES:
        pool = sorted(par[s], key=lambda r: r["siren"])
        if s == "agent":                                     # répartir l'agent entre ses familles
            fams = defaultdict(list)
            for r in pool:
                fams[r["famille"]].append(r)
            choix = []
            while len(choix) < n and any(fams.values()):
                for f in sorted(fams):
                    if fams[f] and len(choix) < n:
                        choix.append(fams[f].pop(rnd.randrange(len(fams[f]))))
        else:
            choix = rnd.sample(pool, min(n, len(pool)))
        for r in choix:
            lignes.append({"strate": s, "siren": r["siren"], "denomination": r["denomination"], "fichier": r["fichier"],
                           "famille_proposee": r["famille"], "methode": r["methode"], "confiance": r["confiance"],
                           "indices": r["indices"][:400], "source_entreprise": r["source"],
                           "famille_verifiee": "", "commentaire": ""})
    ecrire(F_FAM, lignes)
    print(f"{len(lignes)} demandeurs -> {F_FAM}")

    p = FOUILLE / "agent_prospects" / "prospects_nvidia.json"
    if p.exists():
        v = json.loads(p.read_text(encoding="utf-8"))
        pp = FOUILLE / "prospects_priorises.json"            # cas désormais écartés par le code : hors de l'agent
        code = {e["siren"] for e in json.loads(pp.read_text(encoding="utf-8")).get("ecartes", [])
                if e.get("ecarte_par", "").startswith("code")} if pp.exists() else set()
        v = {s: x for s, x in v.items() if s not in code}
        par_v = defaultdict(list)
        for s, x in sorted(v.items()):
            par_v[x["verdict"]].append(x)
        quota = {"prospect": 10, "a_verifier": 5, "faux_positif": 5}
        lp = []
        for verdict, n in quota.items():
            for x in rnd.sample(par_v[verdict], min(n, len(par_v[verdict]))):
                lp.append({"siren": x["siren"], "denomination": x["denomination"], "verdict_agent": x["verdict"],
                           "adequation": x["adequation"], "taille": x["taille"], "type_structure": x["type_structure"],
                           "indices": " ; ".join(x["indices"])[:500],
                           "source_entreprise": f"https://annuaire-entreprises.data.gouv.fr/entreprise/{x['siren']}",
                           "verdict_verifie": "", "commentaire": ""})
        ecrire(F_PROS, lp)
        print(f"{len(lp)} verdicts de prospects -> {F_PROS}")


def ecrire(path, lignes):
    if path.exists() and any(r.get("famille_verifiee") or r.get("verdict_verifie") for r in lire(path)):
        raise SystemExit(f"{path.name} contient déjà des vérifications : renommez-le avant de retirer un échantillon.")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]), delimiter=";")
        w.writeheader()
        w.writerows(lignes)


def lire(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0, c - m), min(1, c + m))


def ligne(nom, k, n):
    if n == 0:
        return f"| {nom} | 0 | – | – |"
    a, b = wilson(k, n)
    return f"| {nom} | {n} | {k}/{n} = {100 * k / n:.0f} % | {100 * a:.0f}–{100 * b:.0f} % |"


def mesurer():
    out = ["# Précision mesurée sur les échantillons de contrôle", "",
           "Intervalle de confiance à 95 % (Wilson). Petits échantillons : l'intervalle est large, c'est normal.", ""]
    if F_FAM.exists():
        rows = [r for r in lire(F_FAM) if r["famille_verifiee"].strip() not in ("", "?")]
        out += ["## Familles", "", "| Strate | Vérifiés | Justes | IC 95 % |", "|---|---|---|---|"]
        for s, _ in STRATES:
            sub = [r for r in rows if r["strate"] == s]
            out.append(ligne(s, sum(r["famille_verifiee"].strip() == r["famille_proposee"] for r in sub), len(sub)))
        out.append(ligne("**total**", sum(r["famille_verifiee"].strip() == r["famille_proposee"] for r in rows), len(rows)))
        err = Counter((r["famille_proposee"], r["famille_verifiee"].strip()) for r in rows if r["famille_verifiee"].strip() != r["famille_proposee"])
        if err:
            out += ["", "Erreurs (proposée → vérifiée) : " + " ; ".join(f"{a} → {b} ×{k}" for (a, b), k in err.most_common())]
    if F_PROS.exists():
        rows = [r for r in lire(F_PROS) if r["verdict_verifie"].strip()]
        out += ["", "## Verdicts de l'agent de qualification", "", "| Verdict de l'agent | Vérifiés | Justes | IC 95 % |", "|---|---|---|---|"]
        for v in ("prospect", "a_verifier", "faux_positif"):
            sub = [r for r in rows if r["verdict_agent"] == v]
            out.append(ligne(v, sum(r["verdict_verifie"].strip() == v for r in sub), len(sub)))
        out.append(ligne("**total**", sum(r["verdict_verifie"].strip() == r["verdict_agent"] for r in rows), len(rows)))
    (DOSSIER / "precision.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    {"tirer": tirer, "mesurer": mesurer}[sys.argv[1] if len(sys.argv) > 1 else "mesurer"]()
