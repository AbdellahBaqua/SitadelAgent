"""Étape 1 : filtrer le périmètre et agréger par demandeur (SIREN)."""
import csv
from collections import defaultdict
from settings import CSV_IN, DEPARTEMENT
from texte import reparer_ligne


def read_permis():
    with open(CSV_IN, encoding="utf-8-sig", newline="") as f:
        return [reparer_ligne(r) for r in csv.DictReader(f, delimiter=";")]   # accents abîmés de la source réparés


def in_scope(r):
    # Brief : permis de construire (PC) dont le demandeur est une personne morale (SIREN connu).
    return (r["TYPE_DAU"] == "PC" and bool(r["SIREN_DEM"])
            and r["DEP_CODE"] == DEPARTEMENT and r["COMM"].startswith(DEPARTEMENT))   # Yvelines uniquement


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def aggregate(permis):
    """Une ligne par SIREN : identité + profil de ses permis."""
    acteurs = {}
    for r in permis:
        s = r["SIREN_DEM"]
        a = acteurs.setdefault(s, {
            "siren": s, "denom": r["DENOM_DEM"], "cj": r["CJ_DEM"], "ape": r["APE_DEM"],
            "n_permis": 0, "annees": set(), "communes": set(), "logements": 0,
            "residence": set(), "lgt_social": 0, "n_collectif": 0, "n_individuel": 0,
            "n_non_commence": 0, "surface": 0,
            "etabs": {},     # SIRET du permis -> {naf, n, annees} : l'APE_DEM est celui de CET établissement
        })
        e = a["etabs"].setdefault(r["SIRET_DEM"] or "?", {"naf": r["APE_DEM"], "n": 0, "annees": set()})
        e["n"] += 1
        if r["AN_DEPOT"]:
            e["annees"].add(r["AN_DEPOT"])
        a["n_permis"] += 1
        if r["AN_DEPOT"]:
            a["annees"].add(r["AN_DEPOT"])
        a["communes"].add(r["COMM"])
        a["logements"] += _int(r.get("NB_LGT_TOT_CREES", ""))
        a["surface"] += _int(r.get("SURF_LOC_CREEE", ""))     # fichier locaux : surface non résidentielle créée (m²)
        a["lgt_social"] += _int(r.get("NB_LGT_PRET_LOC_SOCIAL", ""))
        if r.get("RESIDENCE", "") not in ("", "9"):          # 9 = non rempli
            a["residence"].add(r.get("RESIDENCE", ""))
        t = r.get("TYPE_PRINCIP_LOGTS_CREES", "")
        if t in ("3", "4"):
            a["n_collectif"] += 1
        elif t in ("1", "2"):
            a["n_individuel"] += 1
        if r["ETAT_DAU"] == "2":                      # autorisé, pas (encore) remonté comme commencé
            a["n_non_commence"] += 1
    return acteurs
