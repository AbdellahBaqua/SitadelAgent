"""Pipeline : python src/run.py [--llm] [--llm-limit N]"""
import argparse, csv, json
from datetime import datetime
from collections import Counter
import load, rules, agent
from settings import OUT, src_entreprise, SRC_DATASET


def safe_open(path):
    """Ouvre un CSV en écriture ; s'il est verrouillé (ouvert dans Excel), écrit une copie horodatée."""
    try:
        return open(path, "w", encoding="utf-8-sig", newline="")
    except PermissionError:
        alt = path.with_name(f"{path.stem}_{datetime.now():%H%M%S}{path.suffix}")
        print(f"  ! {path.name} est ouvert ailleurs : écriture dans {alt.name}")
        return open(alt, "w", encoding="utf-8-sig", newline="")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="lancer l'agent Groq sur les cas ambigus")
    ap.add_argument("--llm-limit", type=int, default=None, help="max d'acteurs traités par l'agent (test)")
    ap.add_argument("--nom", default=None, help="forcer l'agent sur les acteurs dont la dénomination contient ce texte")
    args = ap.parse_args()

    # Étape 1
    permis = load.read_permis()
    scope = [r for r in permis if load.in_scope(r)]
    acteurs = load.aggregate(scope)
    print(f"lignes: {len(permis)} | PC personnes morales: {len(scope)} | acteurs (SIREN): {len(acteurs)}")

    # Étapes 2-3
    res = {s: rules.classify(a) for s, a in acteurs.items()}
    ambigus = [acteurs[s] for s, r in res.items() if r["needs_llm"]]
    print("par règles:", Counter(r["famille"] for r in res.values()).most_common())
    print(f"acteurs ambigus (à envoyer au LLM): {len(ambigus)} / {len(acteurs)}")

    # Étape 4
    if args.llm:
        cible = ambigus
        if args.nom:
            cible = [a for a in acteurs.values() if args.nom.upper() in (a["denom"] or "").upper()]
        cache = agent.run_batch(cible, acteurs, limit=args.llm_limit)
        for s, c in cache.items():
            if s in res and (res[s]["needs_llm"] or args.nom):
                res[s] = {"famille": c["famille"], "confiance": c.get("confiance", "faible"),
                          "indices": c.get("indices", []) + ([f"limites: {c['limites']}"] if c.get("limites") else []),
                          "fragilites": c.get("fragilites", []),
                          "needs_llm": False, "methode": f"agent:{c.get('modele','')}"}

    # Sorties
    with safe_open(OUT / "acteurs_classes.csv") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["siren", "denomination", "cj", "naf", "nb_permis", "logements", "famille", "confiance",
                    "methode", "indices", "fragilites", "source"])
        for s, a in sorted(acteurs.items(), key=lambda kv: -kv[1]["n_permis"]):
            r = res[s]
            w.writerow([s, a["denom"], a["cj"], a["ape"], a["n_permis"], a["logements"], r["famille"],
                        r["confiance"], r["methode"], " ; ".join(r["indices"]),
                        " ; ".join(r.get("fragilites", [])), src_entreprise(s)])
    with safe_open(OUT / "permis_classes.csv") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["NUM_DAU", "COMM", "AN_DEPOT", "SIREN_DEM", "DENOM_DEM", "famille", "confiance", "source_donnees", "source_demandeur"])
        for r in scope:
            x = res[r["SIREN_DEM"]]
            w.writerow([r["NUM_DAU"], r["COMM"], r["AN_DEPOT"], r["SIREN_DEM"], r["DENOM_DEM"],
                        x["famille"], x["confiance"], SRC_DATASET, src_entreprise(r["SIREN_DEM"])])
    print(f"écrit: {OUT / 'acteurs_classes.csv'} et permis_classes.csv")


if __name__ == "__main__":
    main()
