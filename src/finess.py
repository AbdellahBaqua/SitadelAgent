r"""FINESS : établissements sanitaires, sociaux et médico-sociaux (extraction officielle du ministère, géolocalisée).

Fichier : data\finess\etalab-cs1100507-stock-*.csv (data.gouv.fr, jeu « FINESS Extraction du Fichier des
établissements », instantané du 04/05/2026). Séparateur « ; », lignes « structureet » (32 champs, ordre décrit dans
etalab_cs1100507.pdf). Seuls les champs utiles sont gardés : les téléphones et télécopies ne sont jamais chargés
(aucune prise de contact : hors périmètre du brief).

Deux usages :
- par_siren(siren) : établissements exploités par une personne morale (SIREN = 9 premiers chiffres du SIRET de
  l'établissement) -> confirme qu'un prospect est un vrai gestionnaire d'établissements et donne sa taille ;
- candidats(permis) : établissements de la commune d'un permis médico-social, compatibles avec son type, avec
  des indices de rapprochement calculés par le code (même rue, même numéro, ouverture après l'autorisation).
"""
import csv, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOSSIER = ROOT / "data" / "finess"
SOURCE = "https://www.data.gouv.fr/datasets/53699569a3a729239d2046eb"

# Agrégats hors périmètre « établissement à exploiter » : commerce de biens médicaux (pharmacies, opticiens),
# laboratoires, exercice libéral, transfusion, santé au travail, formation, centres de ressources.
AGREGATS_EXCLUS = {"3201", "3101", "2103", "3401", "3409", "6101", "6201", "3408"}

# Type de permis -> préfixes d'agrégats FINESS compatibles
COMPATIBLES = {
    "résidence personnes âgées": ("4401", "4402", "1109"),
    "résidence hôtelière sociale": ("4601", "4602", "4605", "4607"),
    "résidence sociale": ("4601", "4602", "4605", "4607"),
    "résidence handicapés": ("41", "43"),
    "équipement de santé": ("11", "12", "22"),
    "équipement d'action sociale": ("4",),
}
MOTS_VIDES = {"RUE", "AVENUE", "AV", "CHEMIN", "ROUTE", "PLACE", "BOULEVARD", "BD", "ALLEE", "IMPASSE", "SENTE",
              "QUAI", "COURS", "SQUARE", "CHAUSSEE", "VOIE", "DES", "DU", "DE", "LA", "LE", "LES", "AUX", "SAINT"}

_ETABS = None


def _fichier():
    f = sorted(DOSSIER.glob("etalab-cs1100507-stock-*.csv"))
    if not f:
        raise SystemExit(f"FINESS absent : télécharger l'extraction géolocalisée dans {DOSSIER} (voir README).")
    return f[-1]


def etablissements():
    """Liste de dicts, un par établissement (France entière), champs utiles seulement."""
    global _ETABS
    if _ETABS is None:
        _ETABS = []
        with open(_fichier(), encoding="utf-8", newline="") as fh:
            for r in csv.reader(fh, delimiter=";"):
                if r[0] != "structureet":
                    continue
                _ETABS.append({
                    "finess": r[1], "finess_ej": r[2], "nom": r[4] or r[3], "num": r[7], "voie": f"{r[8]} {r[9]}".strip(),
                    "commune": r[13] + r[12] if len(r[13]) == 2 else "", "departement": r[13],
                    "ville": r[15][6:] if len(r[15]) > 6 else r[15],
                    "categorie": r[19], "agregat": r[20], "agregat_libelle": r[21], "siret": r[22],
                    "statut": r[27], "ouverture": r[28], "autorisation": r[29],
                    "fiche": f"{SOURCE} (FINESS {r[1]})",   # le site finess.esante.gouv.fr n'a pas d'adresse stable par fiche
                })
    return _ETABS


_PAR_SIREN = None


def par_siren(siren):
    global _PAR_SIREN
    if _PAR_SIREN is None:
        _PAR_SIREN = defaultdict(list)
        for e in etablissements():
            if e["siret"] and e["agregat"] not in AGREGATS_EXCLUS:
                _PAR_SIREN[e["siret"][:9]].append(e)
    return _PAR_SIREN.get(siren, [])


def resume_siren(siren):
    """Ce qu'un outil d'agent renvoie : comptages et 10 établissements des Yvelines au plus."""
    es = par_siren(siren)
    cats = defaultdict(int)
    for e in es:
        cats[e["agregat_libelle"]] += 1
    y = [e for e in es if e["departement"] == "78"]
    return {"nb_etablissements_finess_france": len(es), "nb_etablissements_finess_yvelines": len(y),
            "nb_departements": len({e["departement"] for e in es}),
            "par_type": dict(sorted(cats.items(), key=lambda kv: -kv[1])[:8]),
            "exemples_yvelines": [{k: e[k] for k in ("finess", "nom", "ville", "categorie", "ouverture")} for e in y[:10]],
            "source": SOURCE,
            "aide": "Établissements dont le SIRET commence par ce SIREN. 0 ne prouve pas l'absence d'activité "
                    "médico-sociale (SIRET non renseigné dans FINESS, autre entité juridique du même groupe)."}


def _mots(voie):
    return {w for w in re.sub(r"[^A-Z0-9 ]", " ", (voie or "").upper()).split() if len(w) > 2 and w not in MOTS_VIDES}


def candidats(r, type_projet, n=8):
    """Établissements de la commune du permis r (ligne Sitadel) compatibles avec type_projet, classés par indices."""
    prefixes = COMPATIBLES.get(type_projet, ("1", "2", "4"))
    date_ref = (r.get("DATE_REELLE_AUTORISATION") or "")[:10] or f"{r.get('AN_DEPOT', '')}-01-01"
    mots_permis, num_permis = _mots(r.get("ADR_LIBVOIE_TER")), (r.get("ADR_NUM_TER") or "").lstrip("0")
    out = []
    for e in etablissements():
        if e["commune"] != r["COMM"] or e["agregat"] in AGREGATS_EXCLUS or not e["agregat"].startswith(prefixes):
            continue
        meme_rue = bool(mots_permis & _mots(e["voie"]))
        meme_num = meme_rue and num_permis and e["num"].lstrip("0") == num_permis
        apres = (e["ouverture"] or "") >= date_ref[:4]          # ouvert l'année de l'autorisation ou après
        score = 3 * meme_rue + 2 * bool(meme_num) + 2 * apres
        out.append({"finess": e["finess"], "nom": e["nom"], "adresse": f"{e['num']} {e['voie']}".strip(),
                    "categorie": e["categorie"], "ouverture": e["ouverture"], "siren_exploitant": e["siret"][:9],
                    "meme_rue": meme_rue, "meme_numero": bool(meme_num), "ouvert_apres_autorisation": apres,
                    "score_code": score, "fiche": e["fiche"]})
    out.sort(key=lambda c: c["ouverture"] or "", reverse=True)      # à score égal : le plus récent d'abord
    out.sort(key=lambda c: -c["score_code"])
    return out[:n]
