"""Référentiels officiels de l'Insee (chargés depuis config/)."""
import csv
from settings import ROOT


def _load(path):
    d = {}
    if path.exists():
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.reader(f, delimiter=";"):
                if len(row) >= 2:
                    d[row[0].strip()] = row[1].strip()
    return d


NAF = _load(ROOT / "config" / "naf_rev2_libelles.csv")   # NAF rév. 2 (int_courts_naf_rev_2.xls)
CJ = _load(ROOT / "config" / "cj_libelles.csv")          # catégories juridiques (cj_septembre_2022.xls, niveaux I-III)
