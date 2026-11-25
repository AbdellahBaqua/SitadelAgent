"""Réparation des accents abîmés dans la source Sitadel (texte encodé plusieurs fois).

La source elle-même (API DiDo) contient environ 123 lignes du fichier logements du 78 avec des libellés comme
« ANDRAÃ\\x82Â\\x89SY » pour « ANDRÉSY ». Le motif est régulier : « A » + « Ã\\x82Â » + l'octet de continuation UTF-8
d'une lettre en C3 xx (É = C3 89, È = C3 88…). On le répare à la lecture ; limite documentée dans le rapport.
"""
import re

_MOTIF = re.compile("AÃ\x82Â([\x80-\xbf])")
CHAMPS = ("DENOM_DEM", "ADR_LOCALITE_TER", "LOCALITE_DEM", "ADR_LIBVOIE_TER", "ADR_LIEUDIT_TER")


def reparer(s):
    if not s or "Ã" not in s:
        return s
    return _MOTIF.sub(lambda m: bytes([0xC3, ord(m.group(1))]).decode("utf-8", "replace"), s)


def reparer_ligne(r):
    for c in CHAMPS:
        if r.get(c):
            r[c] = reparer(r[c])
    return r
