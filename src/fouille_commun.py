"""Chargement commun aux analyses de fouille (logements + locaux), indépendant de DATASET."""
import csv
from texte import reparer, reparer_ligne
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOUILLE = ROOT / "out_fouille"
FOUILLE.mkdir(exist_ok=True)
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)

JEUX = {"logements": (ROOT / "data" / "sortie.csv", ROOT / "out" / "acteurs_classes.csv"),
        "locaux": (ROOT / "data" / "sortie_locaux.csv", ROOT / "out_locaux" / "acteurs_classes.csv")}


def entier(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def permis(jeu):
    """PC de personnes morales (même périmètre que le pipeline)."""
    src, _ = JEUX[jeu]
    with open(src, encoding="utf-8-sig", newline="") as f:
        return [reparer_ligne(r) for r in csv.DictReader(f, delimiter=";") if r["TYPE_DAU"] == "PC" and r["SIREN_DEM"]
                and r["DEP_CODE"] == "78" and r["COMM"].startswith("78")]          # Yvelines uniquement


def familles(jeu):
    """{siren: ligne de acteurs_classes.csv} (famille finale : règles + agent)."""
    _, src = JEUX[jeu]
    with open(src, encoding="utf-8-sig", newline="") as f:
        return {r["siren"]: {**r, "denomination": reparer(r.get("denomination", ""))} for r in csv.DictReader(f, delimiter=";")}


def ecrire_csv(nom, lignes):
    if not lignes:
        return
    with open(FOUILLE / nom, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]), delimiter=";")
        w.writeheader()
        w.writerows(lignes)
