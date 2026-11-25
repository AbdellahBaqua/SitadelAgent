r"""Compare deux modèles de classification sur les mêmes acteurs (sans modifier le cache).

  python -X utf8 src\comparer_modeles.py            # MODEL_CLASSIFICATION contre les résultats déjà en cache

Reclasse avec le modèle MODEL_CLASSIFICATION les acteurs déjà classés dans out*/agent_cache.json par un autre modèle,
puis affiche l'accord sur la famille. Écrit out*/comparaison_classification.csv.
"""
import csv, json, time
import load, agent
from llm_classify import _env
from settings import OUT


def main():
    cache = json.loads(agent.CACHE.read_text(encoding="utf-8")) if agent.CACHE.exists() else {}
    key, model = _env("classification")
    scope = [r for r in load.read_permis() if load.in_scope(r)]
    acteurs = load.aggregate(scope)
    a_comparer = [s for s, c in cache.items() if c.get("modele") != model and s in acteurs]
    print(f"{len(a_comparer)} acteurs déjà classés par un autre modèle ; reclassement avec {model}", flush=True)
    lignes, accord = [], 0
    for s in a_comparer:
        t = time.time()
        res, _ = agent.analyser(acteurs[s], acteurs, key, model)
        ok = res["famille"] == cache[s]["famille"]
        accord += ok
        lignes.append({"siren": s, "denomination": acteurs[s]["denom"], "modele_ref": cache[s].get("modele"),
                       "famille_ref": cache[s]["famille"], "confiance_ref": cache[s].get("confiance"),
                       "modele_test": model, "famille_test": res["famille"], "confiance_test": res["confiance"],
                       "accord": int(ok), "secondes": round(time.time() - t, 1)})
        print(f"  {acteurs[s]['denom'][:38]:38s} ref={cache[s]['famille']:22s} test={res['famille']:22s} "
              f"{'OK' if ok else 'DIFF'} ({lignes[-1]['secondes']} s)", flush=True)
        time.sleep(1)
    if lignes:
        with open(OUT / "comparaison_classification.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(lignes[0]), delimiter=";")
            w.writeheader(); w.writerows(lignes)
        print(f"accord : {accord}/{len(lignes)} = {100 * accord / len(lignes):.0f} % ; "
              f"temps moyen {sum(l['secondes'] for l in lignes) / len(lignes):.1f} s par acteur")


if __name__ == "__main__":
    main()
