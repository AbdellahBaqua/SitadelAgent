#!/usr/bin/env python3
"""Filtre un fichier CSV Sitadel (plusieurs centaines de milliers de lignes)
et ecrit une copie ne contenant que les lignes dont une colonne vaut une valeur donnee.

Par defaut : colonne DEP_CODE = 78 (Yvelines).

Usage :
    python filter_sitadel.py entree.csv sortie.csv
    python filter_sitadel.py entree.csv sortie.csv --column REG_CODE --value 78
    python filter_sitadel.py entree.csv sortie.csv --column DEP_CODE --value 78 --delimiter ";"

Bibliotheque standard uniquement. Le fichier est lu ligne par ligne :
la memoire reste faible meme pour des fichiers tres volumineux.
"""

import argparse
import csv
import sys

csv.field_size_limit(sys.maxsize)

ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


def detect_encoding(path):
    """Teste les encodages courants sur le fichier entier (lecture en flux)."""
    for enc in ENCODINGS:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                for _ in f:
                    pass
            return enc
        except UnicodeDecodeError:
            continue
    raise SystemExit("Encodage du fichier non reconnu.")


def detect_delimiter(path, encoding):
    with open(path, "r", encoding=encoding, newline="") as f:
        header = f.readline()
    candidates = [";", ",", "\t", "|"]
    return max(candidates, key=header.count)


def normalize(value):
    """Compare '78', ' 78 ', '078' comme equivalents (codes numeriques)."""
    v = value.strip().strip('"')
    return v.lstrip("0") or "0" if v.isdigit() else v.upper()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="fichier CSV Sitadel en entree")
    p.add_argument("output", help="fichier CSV filtre en sortie")
    p.add_argument("--column", default="DEP_CODE", help="colonne a tester (defaut : DEP_CODE)")
    p.add_argument("--value", default="78", help="valeur recherchee (defaut : 78)")
    p.add_argument("--delimiter", default=None, help="separateur (detecte automatiquement par defaut)")
    p.add_argument("--encoding", default=None, help="encodage (detecte automatiquement par defaut)")
    args = p.parse_args()

    encoding = args.encoding or detect_encoding(args.input)
    delimiter = args.delimiter or detect_delimiter(args.input, encoding)
    target = normalize(args.value)

    total = kept = 0
    with open(args.input, "r", encoding=encoding, newline="") as fin, \
         open(args.output, "w", encoding="utf-8-sig", newline="") as fout:
        reader = csv.reader(fin, delimiter=delimiter)
        writer = csv.writer(fout, delimiter=delimiter, lineterminator="\n")

        try:
            header = next(reader)
        except StopIteration:
            raise SystemExit("Fichier vide.")
        header = [h.strip().lstrip("﻿") for h in header]

        if args.column not in header:
            raise SystemExit(
                f"Colonne '{args.column}' introuvable.\nColonnes disponibles : {', '.join(header)}"
            )
        idx = header.index(args.column)
        writer.writerow(header)

        for row in reader:
            total += 1
            if len(row) > idx and normalize(row[idx]) == target:
                writer.writerow(row)
                kept += 1

    print(f"Encodage : {encoding} | separateur : {delimiter!r}")
    print(f"{total} lignes lues, {kept} lignes gardees ({args.column} = {args.value}) -> {args.output}")
    if kept == 0:
        print("Attention : aucune ligne gardee. Verifie le nom de la colonne et la valeur.")


if __name__ == "__main__":
    main()
