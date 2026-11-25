r"""Extrait un département du fichier national « locaux non résidentiels » (SDES/Sitadel).

  python -X utf8 src\extract_locaux.py "C:\...\Liste-des-autorisations-durbanisme-creant-des-locaux-non-residentiels.2026-10.csv" 78

Écrit data\sortie_locaux.csv (séparateur ;), lu ensuite par le pipeline avec DATASET=locaux.
"""
import csv, sys
from settings import ROOT


def main():
    src, dep = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "78")
    out = ROOT / "data" / "sortie_locaux.csv"
    n_in = n_out = 0
    with open(src, encoding="utf-8-sig", newline="") as fi, open(out, "w", encoding="utf-8", newline="") as fo:
        r = csv.reader(fi, delimiter=";")
        w = csv.writer(fo, delimiter=";")
        head = next(r)
        w.writerow(head)
        i_dep = head.index("DEP_CODE")
        for row in r:
            n_in += 1
            if row[i_dep] == dep:
                w.writerow(row)
                n_out += 1
    print(f"lignes lues : {n_in} | gardées (département {dep}) : {n_out} -> {out}")


if __name__ == "__main__":
    main()
