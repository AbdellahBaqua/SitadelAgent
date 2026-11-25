"""Étapes 2-3 : règles déterministes, fondées sur les libellés OFFICIELS Insee (config/cj_libelles.csv,
config/naf_rev2_libelles.csv). Chaque règle renvoie famille, confiance, indices (qui citent le libellé officiel).

Principe : la catégorie juridique (CJ) décrit l'entreprise et est stable -> confiance « haute » quand elle tranche.
Le NAF du permis est celui d'un ÉTABLISSEMENT, possiblement fermé/périmé -> il ne donne qu'une confiance
« moyenne » et un drapeau de fragilité. Sans règle applicable : non_determine + needs_llm (l'agent Groq prend la main).
"""
import re
from referentiels import CJ, NAF
from settings import DATASET

# Fichier locaux : une entreprise hors immobilier / construction / finance construit le plus souvent pour sa propre
# activité (entrepôt, usine, magasin). Sections exclues (laissées à l'agent) : 41-43 construction, 64-66 finance et
# holdings, 68 immobilier, 70 sièges sociaux et conseil (NAF souvent périmé, cf. cas SNL-Prologues).
NAF_NON_AUTONOMES = ("41.", "42.", "43.", "64.", "65.", "66.", "68.", "70.", "00.")
CJ_AGRICOLES = ("6532", "6533", "6534", "6535", "6536", "6537", "6538", "6597", "6598")

KW_BAILLEUR = re.compile(r"LOYER MODERE|\bH\.? ?L\.? ?M\b|\bHLM\b|\bOPH\b|ENTREPRISE SOCIALE POUR L.?HABITAT"
                         r"|HABITAT SOCIAL|\bADOMA\b|IMMOBILIERE 3F|\bCDC HABITAT\b")
KW_PROMOTEUR = re.compile(r"\bCOGEDIM\b|\bNEXITY\b|\bBOUYGUES IMMOBILIER\b|\bKAUFMAN\b|\bMARIGNAN\b"
                          r"|\bEIFFAGE IMMOBILIER\b|\bALTAREA\b|\bPROMOTION\b")


def _cj(cj):
    return f"CJ {cj} = {CJ.get(cj, '?')}"


def _naf(ape):
    return f"NAF permis {ape} = {NAF.get(ape, '?')} (établissement du permis, à confirmer)"


def classify(a):
    """a = acteur agrégé (load.aggregate). Retourne dict famille/confiance/indices/fragilites/needs_llm."""
    den = (a["denom"] or "").upper()
    cj, ape = a["cj"] or "", a["ape"] or ""

    def out(fam, conf, *why, frag=()):
        return {"famille": fam, "confiance": conf, "indices": list(why), "fragilites": list(frag),
                "needs_llm": False, "methode": "regle"}

    naf_frag = ["NAF du permis non vérifié (établissement possiblement fermé)"]

    # --- 1. Catégorie juridique qui tranche (haute) ---
    if cj in ("7371",) or cj in ("5546", "5547"):               # OPH ; SA de HLM ; SA coop. de production de HLM
        return out("bailleur_social", "haute", _cj(cj))
    if cj[:2] in ("71", "72", "73", "74") or cj[:2] == "41":     # État, collectivités, établissements publics, EPIC
        return out("collectivite_public", "haute", _cj(cj))
    if cj[:2] in ("92", "93") or cj == "9240":                   # associations, fondations, congrégations
        return out("association_ess", "haute", _cj(cj))
    if cj[:2] == "82":                                           # organismes mutualistes
        return out("association_ess", "moyenne", _cj(cj))
    if cj in ("9110", "9150"):                                   # syndicat de copropriété ; association syndicale libre
        return out("copropriete", "haute", _cj(cj))
    if cj == "6541":                                             # SCI de construction-vente : véhicule de programme
        return out("promoteur", "moyenne", _cj(cj), "véhicule de programme pour la vente")
    if cj in ("6521", "6539"):                                   # SCPI, société civile foncière
        return out("fonciere_investisseur", "haute", _cj(cj))

    # --- 2. Dénomination explicite (moyenne) ---
    if KW_BAILLEUR.search(den):
        return out("bailleur_social", "moyenne", f"dénomination '{den}'", _cj(cj) if cj else "", frag=["famille déduite du nom"])
    if KW_PROMOTEUR.search(den):
        return out("promoteur", "moyenne", f"dénomination '{den}'", frag=["famille déduite du nom"])

    # --- 3. NAF du permis (moyenne, toujours signalé comme à confirmer) ---
    if ape in ("41.10A", "41.10B", "41.10C"):
        return out("promoteur", "moyenne", _naf(ape), _cj(cj) if cj else "", frag=naf_frag)
    if ape == "41.10D":                                          # supports juridiques de programmes = véhicule
        return out("promoteur", "moyenne", _naf(ape), "véhicule juridique de programme", frag=naf_frag)
    if ape.startswith(("86.", "87.", "88.")):                    # santé / hébergement social / action sociale
        return out("exploitant_sante_social", "moyenne", _naf(ape), _cj(cj) if cj else "", frag=naf_frag)
    if ape in ("68.10Z", "68.20A", "68.20B", "68.32B", "64.30Z", "66.19A") or cj == "6540":
        why = [_naf(ape)] if ape in ("68.10Z", "68.20A", "68.20B", "68.32B", "64.30Z", "66.19A") else []
        if cj == "6540":
            why.append(_cj(cj))
        return out("fonciere_investisseur", "moyenne", *why, frag=naf_frag if why and why[0].startswith("NAF") else [])
    if ape in ("41.20A", "41.20B") or ape.startswith(("42.", "43.")):
        return out("entreprise_autre", "moyenne", _naf(ape), "BTP", frag=naf_frag)

    # --- 3 bis. Fichier locaux : entreprises qui construisent pour leur propre activité ---
    if DATASET == "locaux":
        if cj in CJ_AGRICOLES or cj[:2] == "63":                 # GAEC, EARL, SCEA, coopératives agricoles…
            return out("entreprise_autre", "haute", _cj(cj), "exploitation ou coopérative agricole")
        if ape and not ape.startswith(NAF_NON_AUTONOMES) and cj[:2] in ("52", "54", "55", "56", "57", "58", "65"):
            return out("entreprise_autre", "moyenne", _naf(ape), _cj(cj), "construit pour sa propre activité (hypothèse)",
                       frag=naf_frag)

    # --- 4. Rien de fiable : on passe la main à l'agent ---
    return {"famille": "non_determine", "confiance": "n/a", "indices": ["aucune règle applicable"],
            "fragilites": [], "needs_llm": True, "methode": "regle"}
