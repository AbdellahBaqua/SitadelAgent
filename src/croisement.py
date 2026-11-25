r"""Fouille 2 : croiser les fichiers logements et locaux non résidentiels.

  python -X utf8 src\croisement.py

- Permis mixtes : même NUM_DAU dans les deux fichiers (un permis qui crée à la fois des logements et des locaux).
- Acteurs présents dans les deux fichiers (même SIREN), par famille.
- Zoom médico-social : demandeurs qui construisent des équipements de santé / action sociale (locaux,
  TYPE_SERVICE_PUBLIC 3 ou 4) ET des logements, ou des résidences (logements, RESIDENCE 1/4/5/6).
Sortie : out_fouille/croisement.json + out_fouille/acteurs_deux_fichiers.csv
"""
import json
from collections import Counter, defaultdict
from fouille_commun import FOUILLE, permis, familles, ecrire_csv, entier

RES_MEDICO = {"1": "personnes âgées", "4": "hôtelière sociale", "5": "sociale", "6": "handicapés"}
SP_MEDICO = {"3": "santé", "4": "action sociale"}


def main():
    log, loc = permis("logements"), permis("locaux")
    fam_log, fam_loc = familles("logements"), familles("locaux")

    # 1. permis mixtes
    loc_par_num = {r["NUM_DAU"]: r for r in loc}
    mixtes = [(r, loc_par_num[r["NUM_DAU"]]) for r in log if r["NUM_DAU"] in loc_par_num]
    fam_mixtes = Counter(fam_log.get(r["SIREN_DEM"], {}).get("famille", "?") for r, _ in mixtes)
    dest_mixtes = Counter()
    for _, l in mixtes:
        sp = l.get("TYPE_SERVICE_PUBLIC", "")
        dest_mixtes[SP_MEDICO.get(sp, "autre")] += 1

    # 2. acteurs dans les deux fichiers
    agg = defaultdict(lambda: {"permis_logements": 0, "logements": 0, "permis_locaux": 0, "surface_m2": 0,
                               "residences_medico": 0, "equipements_medico": 0})
    for r in log:
        a = agg[r["SIREN_DEM"]]
        a["permis_logements"] += 1; a["logements"] += entier(r["NB_LGT_TOT_CREES"])
        if r.get("RESIDENCE") in RES_MEDICO:
            a["residences_medico"] += 1
    for r in loc:
        a = agg[r["SIREN_DEM"]]
        a["permis_locaux"] += 1; a["surface_m2"] += entier(r["SURF_LOC_CREEE"])
        if r.get("TYPE_SERVICE_PUBLIC") in SP_MEDICO:
            a["equipements_medico"] += 1
    deux = [s for s, a in agg.items() if a["permis_logements"] and a["permis_locaux"]]
    lignes = []
    for s in deux:
        fl, fc = fam_log.get(s, {}), fam_loc.get(s, {})
        lignes.append({"siren": s, "denomination": fl.get("denomination") or fc.get("denomination", ""),
                       "famille_logements": fl.get("famille", ""), "famille_locaux": fc.get("famille", ""),
                       **agg[s], "source": f"https://annuaire-entreprises.data.gouv.fr/entreprise/{s}"})
    lignes.sort(key=lambda x: -(x["permis_logements"] + x["permis_locaux"]))
    ecrire_csv("acteurs_deux_fichiers.csv", lignes)

    # 3. zoom médico-social : équipements santé/action sociale ET logements
    medico_mixte = [x for x in lignes if x["equipements_medico"] > 0]
    desaccords = [x for x in lignes if x["famille_logements"] and x["famille_locaux"]
                  and x["famille_logements"] != x["famille_locaux"]]

    out = {
        "permis": {"logements": len(log), "locaux": len(loc), "mixtes": len(mixtes),
                   "mixtes_par_famille": dict(fam_mixtes.most_common()),
                   "mixtes_avec_equipement": dict(dest_mixtes.most_common()),
                   "mixtes_logements": sum(entier(r["NB_LGT_TOT_CREES"]) for r, _ in mixtes),
                   "mixtes_surface_m2": sum(entier(l["SURF_LOC_CREEE"]) for _, l in mixtes)},
        "acteurs": {"logements": len(fam_log), "locaux": len(fam_loc), "deux_fichiers": len(deux),
                    "deux_fichiers_par_famille": dict(Counter(x["famille_logements"] for x in lignes).most_common()),
                    "familles_differentes": len(desaccords)},
        "medico_mixte": [{k: x[k] for k in ("siren", "denomination", "famille_logements", "permis_logements",
                                              "logements", "residences_medico", "permis_locaux",
                                              "equipements_medico", "surface_m2", "source")}
                         for x in medico_mixte[:30]],
        "nb_medico_mixte": len(medico_mixte),
        "desaccords_exemples": [{k: x[k] for k in ("siren", "denomination", "famille_logements", "famille_locaux")}
                                for x in desaccords[:15]],
    }
    (FOUILLE / "croisement.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    p, a = out["permis"], out["acteurs"]
    print(f"permis mixtes : {p['mixtes']} ({p['mixtes_logements']} logements, {p['mixtes_surface_m2']} m²) ; par famille {p['mixtes_par_famille']}")
    print(f"acteurs dans les deux fichiers : {a['deux_fichiers']} ; par famille {a['deux_fichiers_par_famille']}")
    print(f"acteurs avec équipements santé/action sociale ET logements : {len(medico_mixte)}")
    print(f"familles différentes selon le fichier : {a['familles_differentes']}")


if __name__ == "__main__":
    main()
