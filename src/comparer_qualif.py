r"""Compare deux modèles sur les MÊMES prospects (échantillon tiré par agent_prospects.py --echantillon).

  python -X utf8 src\comparer_qualif.py            # nvidia contre groq -> out_fouille\agent_prospects\comparaison_nvidia_groq.md

Mesure : accord sur le verdict (prospect / faux_positif / a_verifier), accord sur l'adéquation, matrice de confusion,
nombre de fragilités relevées par le code, durée moyenne par cas (écart entre traces successives), et la liste des
désaccords avec la justification de chaque modèle. Aucun modèle n'est la vérité : un désaccord désigne un cas à
trancher à la main (échantillon de contrôle).
"""
import json, os, statistics, sys
from collections import Counter
from fouille_commun import FOUILLE

D = FOUILLE / "agent_prospects"


def charger(nom):
    p = D / f"prospects_{nom}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def durees(nom, cles):
    t = sorted((os.path.getmtime(D / "traces" / f"prospects_{nom}_{k}.json") for k in cles
                if (D / "traces" / f"prospects_{nom}_{k}.json").exists()))
    ecarts = [b - a for a, b in zip(t, t[1:]) if b - a < 600]          # ignore les pauses longues (reprise)
    return round(statistics.median(ecarts)) if ecarts else None


def main(a="nvidia", b="groq"):
    ech = json.loads((D / "echantillon_prospects.json").read_text(encoding="utf-8"))["cles"]
    A, B = charger(a), charger(b)
    import cible, finess
    from agent_prospects import fiche
    cands = {c["siren"]: c for c in json.loads((FOUILLE / "prospects_candidats.json").read_text(encoding="utf-8"))}
    exclus = [k for k in ech if k not in cands]              # désormais écartés par le pré-filtre du code
    communs = [k for k in ech if k in A and k in B and k in cands]
    gf = lambda X, k: cible.garde_fou_prospect(X[k], fiche(k), len(finess.par_siren(k)), cands[k]["famille"],
                                               {p.get("type_projet") for p in cands[k]["permis"]})
    A2, B2 = {k: gf(A, k) for k in communs}, {k: gf(B, k) for k in communs}
    acc_g = sum(A2[k]["verdict"] == B2[k]["verdict"] for k in communs)
    if not communs:
        raise SystemExit("aucun cas commun : lancer les deux modèles sur le même échantillon")
    mod = lambda X: next((v.get("modele") for v in X.values() if v.get("modele")), "?")
    acc_v = sum(A[k]["verdict"] == B[k]["verdict"] for k in communs)
    acc_a = sum(A[k]["adequation"] == B[k]["adequation"] for k in communs)
    conf = Counter((A[k]["verdict"], B[k]["verdict"]) for k in communs)
    verdicts = ["prospect", "a_verifier", "faux_positif"]
    L = [f"# Qualification des prospects : {a} contre {b}", "",
         f"- {a} : `{mod(A)}` ; {b} : `{mod(B)}`",
         f"- Échantillon : {len(ech)} prospects tirés au hasard (graine fixe) parmi ceux qui passent le pré-filtre du code ; "
         f"{len(exclus)} sont désormais écartés par le pré-filtre du code ; comparaison sur les {len(communs)} restants.",
         f"- **Accord sur le verdict : {acc_v}/{len(communs)} ({round(100 * acc_v / len(communs))} %)** ; "
         f"accord sur l'adéquation : {acc_a}/{len(communs)} ({round(100 * acc_a / len(communs))} %).",
         f"- **Après le garde-fou « preuve dure » du code : accord sur le verdict {acc_g}/{len(communs)} "
         f"({round(100 * acc_g / len(communs))} %)** ; verdicts {a} {dict(Counter(A2[k]['verdict'] for k in communs))}, "
         f"{b} {dict(Counter(B2[k]['verdict'] for k in communs))}.",
         f"- Verdicts {a} : {dict(Counter(A[k]['verdict'] for k in communs))} ; {b} : {dict(Counter(B[k]['verdict'] for k in communs))}.",
         f"- Fragilités relevées par le code (indice sans source, mémoire du modèle) : {a} {sum(len(A[k]['fragilites']) for k in communs)}, "
         f"{b} {sum(len(B[k]['fragilites']) for k in communs)}.",
         f"- Garde-fous du code déclenchés (verdict ou adéquation corrigés) : {a} "
         f"{sum('[' in A[k]['limites'] for k in communs)}, {b} {sum('[' in B[k]['limites'] for k in communs)}.",
         f"- Durée médiane par cas : {a} {durees(a, communs)} s, {b} {durees(b, communs)} s (pause entre appels comprise).",
         "", f"## Matrice de confusion (lignes : {a}, colonnes : {b})", "",
         "| | " + " | ".join(verdicts) + " |", "|---|" + "---|" * len(verdicts)]
    for v in verdicts:
        L.append(f"| **{v}** | " + " | ".join(str(conf[(v, w)]) for w in verdicts) + " |")
    L += ["", "## Désaccords sur le verdict", ""]
    for k in communs:
        x, y = A[k], B[k]
        if x["verdict"] != y["verdict"]:
            L += [f"### {x['denomination']} (SIREN {k})",
                  f"- **{a}** : {x['verdict']} / {x['adequation']} — {x['type_structure']}. Limites : {x['limites'][:300]}",
                  f"- **{b}** : {y['verdict']} / {y['adequation']} — {y['type_structure']}. Limites : {y['limites'][:300]}",
                  f"- Source : https://annuaire-entreprises.data.gouv.fr/entreprise/{k}", ""]
    out = D / f"comparaison_{a}_{b}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    (D / f"comparaison_{a}_{b}.json").write_text(json.dumps({
        "modeles": {a: mod(A), b: mod(B)}, "tires": len(ech), "exclus_par_le_code": len(exclus), "cas": len(communs), "accord_verdict": acc_v, "accord_adequation": acc_a, "accord_verdict_apres_garde_fou": acc_g, "verdicts_apres_garde_fou": {a: dict(Counter(A2[k]["verdict"] for k in communs)), b: dict(Counter(B2[k]["verdict"] for k in communs))},
        "duree_mediane_s": {a: durees(a, communs), b: durees(b, communs)},
        "verdicts": {a: dict(Counter(A[k]["verdict"] for k in communs)), b: dict(Counter(B[k]["verdict"] for k in communs))}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(L[:16]))
    print(f"-> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
