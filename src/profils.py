r"""Fouille 3 : profils d'acteurs par regroupement automatique (k-means, Python pur, reproductible).

  python -X utf8 src\profils.py

Chaque demandeur (SIREN), logements + locaux réunis, est décrit par 10 indicateurs de COMPORTEMENT. La famille
juridique n'entre pas dans le calcul : on compare ensuite les groupes obtenus aux familles. Le nombre de groupes k
est choisi entre 4 et 8 par le meilleur score de silhouette (calculé sur un échantillon fixe).
Réconciliation : si un SIREN a deux familles différentes selon le fichier, on garde la plus sûre (confiance haute >
moyenne > autre ; une famille déterminée l'emporte sur « non_determine »).

Sorties : out_fouille/profils_acteurs.csv, out_fouille/profils_groupes.json
"""
import json, math, random
from collections import Counter, defaultdict
from fouille_commun import FOUILLE, permis, familles, ecrire_csv, entier

SEED = 42
RES_MEDICO = {"1", "4", "5", "6"}
SP_MEDICO = {"3", "4"}
INDICATEURS = [  # (clé, libellé lisible)
    ("v_permis", "nombre de permis (log)"), ("v_annees", "années actives (log)"), ("v_logements", "logements créés (log)"),
    ("v_surface", "surface de locaux créée (log)"), ("part_locaux", "part de permis de locaux"),
    ("v_taille", "logements par permis (log)"), ("v_communes", "nombre de communes (log)"),
    ("part_medico", "part de projets médico-sociaux"), ("taux_acheve", "taux d'achèvement déclaré"),
    ("taux_annule", "taux d'annulation"),
]
RANG_CONF = {"haute": 3, "moyenne": 2, "faible": 1}


def famille_reconciliee(fl, fc):
    cands = [f for f in (fl, fc) if f]
    if not cands:
        return "non_determine", ""
    if len(cands) == 2 and cands[0]["famille"] != cands[1]["famille"]:
        def score(f):
            return (f["famille"] != "non_determine", RANG_CONF.get(f["confiance"], 0))
        best = max(cands, key=score)
        return best["famille"], "réconciliée (familles différentes selon le fichier)"
    return cands[0]["famille"], ""


def kmeans(X, k, rnd, iters=100):
    # initialisation k-means++
    centres = [X[rnd.randrange(len(X))]]
    while len(centres) < k:
        d2 = [min(sum((a - b) ** 2 for a, b in zip(x, c)) for c in centres) for x in X]
        tot = sum(d2)
        r, acc = rnd.random() * tot, 0.0
        for x, d in zip(X, d2):
            acc += d
            if acc >= r:
                centres.append(x)
                break
    lab = [0] * len(X)
    for _ in range(iters):
        nouv = [min(range(k), key=lambda j: sum((a - b) ** 2 for a, b in zip(x, centres[j]))) for x in X]
        if nouv == lab and _:
            break
        lab = nouv
        for j in range(k):
            membres = [x for x, l in zip(X, lab) if l == j]
            if membres:
                centres[j] = [sum(c) / len(membres) for c in zip(*membres)]
    return lab, centres


def silhouette(X, lab, idx):
    def dist(a, b):
        return math.sqrt(sum((p - q) ** 2 for p, q in zip(a, b)))
    s = []
    for i in idx:
        par = defaultdict(list)
        for j in idx:
            if j != i:
                par[lab[j]].append(dist(X[i], X[j]))
        if not par.get(lab[i]):
            continue
        a = sum(par[lab[i]]) / len(par[lab[i]])
        b = min(sum(v) / len(v) for l, v in par.items() if l != lab[i]) if len(par) > 1 else 0
        s.append((b - a) / max(a, b) if max(a, b) else 0)
    return sum(s) / len(s) if s else 0


def main():
    log, loc = permis("logements"), permis("locaux")
    fam_log, fam_loc = familles("logements"), familles("locaux")
    agg = defaultdict(lambda: {"n_log": 0, "n_loc": 0, "logements": 0, "surface": 0, "annees": set(),
                               "communes": set(), "medico": 0, "acheve": 0, "annule": 0})
    for r in log:
        a = agg[r["SIREN_DEM"]]
        a["n_log"] += 1; a["logements"] += entier(r["NB_LGT_TOT_CREES"]); a["medico"] += r.get("RESIDENCE") in RES_MEDICO
        a["annees"].add(r["AN_DEPOT"]); a["communes"].add(r["COMM"])
        a["acheve"] += r["ETAT_DAU"] == "6"; a["annule"] += r["ETAT_DAU"] == "4"
    for r in loc:
        a = agg[r["SIREN_DEM"]]
        a["n_loc"] += 1; a["surface"] += entier(r["SURF_LOC_CREEE"]); a["medico"] += r.get("TYPE_SERVICE_PUBLIC") in SP_MEDICO
        a["annees"].add(r["AN_DEPOT"]); a["communes"].add(r["COMM"])
        a["acheve"] += r["ETAT_DAU"] == "6"; a["annule"] += r["ETAT_DAU"] == "4"

    lignes = []
    for s, a in agg.items():
        n = a["n_log"] + a["n_loc"]
        fl, fc = fam_log.get(s), fam_loc.get(s)
        fam, note = famille_reconciliee(fl, fc)
        lignes.append({
            "siren": s, "denomination": (fl or fc or {}).get("denomination", ""), "famille": fam, "note_famille": note,
            "permis_logements": a["n_log"], "permis_locaux": a["n_loc"], "logements": a["logements"],
            "surface_m2": a["surface"], "annees_actives": len(a["annees"]), "communes": len(a["communes"]),
            "v_permis": math.log1p(n), "v_annees": math.log1p(len(a["annees"])), "v_logements": math.log1p(a["logements"]),
            "v_surface": math.log1p(a["surface"] / 100), "part_locaux": a["n_loc"] / n,
            "v_taille": math.log1p(a["logements"] / a["n_log"]) if a["n_log"] else 0.0,
            "v_communes": math.log1p(len(a["communes"])), "part_medico": a["medico"] / n,
            "taux_acheve": a["acheve"] / n, "taux_annule": a["annule"] / n,
        })
    cles = [k for k, _ in INDICATEURS]
    moy = {k: sum(l[k] for l in lignes) / len(lignes) for k in cles}
    ect = {k: math.sqrt(sum((l[k] - moy[k]) ** 2 for l in lignes) / len(lignes)) or 1 for k in cles}
    X = [[(l[k] - moy[k]) / ect[k] for k in cles] for l in lignes]

    rnd = random.Random(SEED)
    echant = sorted(rnd.sample(range(len(X)), min(1200, len(X))))
    meilleurs, scores = None, {}
    for k in range(4, 9):
        lab, centres = kmeans(X, k, random.Random(SEED + k))
        scores[k] = round(silhouette(X, lab, echant), 3)
        print(f"k={k} silhouette={scores[k]}", flush=True)
        if meilleurs is None or scores[k] > scores[meilleurs[0]]:
            meilleurs = (k, lab, centres)
    k, lab, centres = meilleurs

    groupes = []
    for j in range(k):
        membres = [l for l, g in zip(lignes, lab) if g == j]
        z = {c: centres[j][i] for i, c in enumerate(cles)}
        traits = sorted(z.items(), key=lambda kv: -abs(kv[1]))[:3]
        libelles = dict(INDICATEURS)
        description = " ; ".join(f"{libelles[c]} {'élevé' if v > 0 else 'faible'} ({v:+.1f} σ)" for c, v in traits)
        fams = Counter(m["famille"] for m in membres)
        groupes.append({
            "groupe": j, "effectif": len(membres), "description_auto": description,
            "familles": dict(fams.most_common()),
            "famille_dominante": fams.most_common(1)[0][0], "part_famille_dominante": round(fams.most_common(1)[0][1] / len(membres), 3),
            "moyennes": {"permis": round(sum(m["permis_logements"] + m["permis_locaux"] for m in membres) / len(membres), 2),
                         "logements": round(sum(m["logements"] for m in membres) / len(membres), 1),
                         "surface_m2": round(sum(m["surface_m2"] for m in membres) / len(membres)),
                         "annees_actives": round(sum(m["annees_actives"] for m in membres) / len(membres), 2),
                         "communes": round(sum(m["communes"] for m in membres) / len(membres), 2),
                         "part_locaux": round(sum(m["part_locaux"] for m in membres) / len(membres), 3),
                         "part_medico": round(sum(m["part_medico"] for m in membres) / len(membres), 3),
                         "taux_acheve": round(sum(m["taux_acheve"] for m in membres) / len(membres), 3),
                         "taux_annule": round(sum(m["taux_annule"] for m in membres) / len(membres), 3)},
            "z_centre": {c: round(v, 2) for c, v in z.items()},
            "exemples": [{"siren": m["siren"], "denomination": m["denomination"], "famille": m["famille"],
                          "permis": m["permis_logements"] + m["permis_locaux"]}
                         for m in sorted(membres, key=lambda m: -(m["permis_logements"] + m["permis_locaux"]))[:6]],
        })
    for l, g in zip(lignes, lab):
        l["groupe"] = g
    sortie = [{k2: (round(v, 4) if isinstance(v, float) else v) for k2, v in l.items()} for l in lignes]
    ecrire_csv("profils_acteurs.csv", sorted(sortie, key=lambda x: (x["groupe"], -(x["permis_logements"] + x["permis_locaux"]))))
    (FOUILLE / "profils_groupes.json").write_text(json.dumps({
        "k": k, "silhouettes": scores, "nb_acteurs": len(lignes), "indicateurs": dict(INDICATEURS),
        "reconciliees": sum(1 for l in lignes if l["note_famille"]), "groupes": groupes}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\nk retenu = {k} ; {len(lignes)} acteurs ; familles réconciliées : {sum(1 for l in lignes if l['note_famille'])}")
    for g in groupes:
        print(f"groupe {g['groupe']} ({g['effectif']}) : {g['description_auto']} | dominante {g['famille_dominante']} "
              f"{g['part_famille_dominante']:.0%} | ex. {', '.join(e['denomination'][:25] for e in g['exemples'][:3])}")


if __name__ == "__main__":
    main()
