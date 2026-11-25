r"""Pré-filtre déterministe des prospects : écarte, AVANT l'agent, les cas qui ne demandent aucun jugement.

Principe (règles + agent) : le code tranche quand la décision est une lecture d'un champ fiable ; l'agent ne reçoit que
les cas qui demandent de peser des indices. La FAMILLE d'un demandeur (ce qu'il est : une association de culte est bien
une association) reste inchangée ; ce filtre répond à une autre question : est-ce une cible de Buddimm ?

Écarté par le code si :
- la structure est cessée dans l'Annuaire des entreprises (état C ou F) ;
- son activité ACTUELLE (NAF de l'entreprise, pas celui du permis) est sans lien avec le médico-social, le social,
  l'ESS ou le logement social (culte, enseignement scolaire, sport, cabinet libéral de santé, pharmacie…),
  SAUF si elle exploite au moins un établissement FINESS (ex. une association « enseignement » qui gère un IME) :
  ce cas part à l'agent.
Tout ce qui n'est pas clairement exclu part à l'agent. Chaque exclusion est écrite avec sa règle et sa source.
"""
import re

# NAF rév. 2 de l'entreprise -> motif d'exclusion (préfixes ; libellés Insee)
EXCLUSIONS_NAF = {
    "94.91": "organisation religieuse (culte)",
    "94.92": "organisation politique",
    "94.11": "organisation patronale ou consulaire",
    "94.12": "organisation professionnelle",
    "94.20": "syndicat de salariés",
    "93.": "sport, loisirs ou activités récréatives",
    "85.1": "enseignement pré-primaire",
    "85.2": "enseignement primaire",
    "85.3": "enseignement secondaire",
    "85.4": "enseignement supérieur",
    "85.60": "soutien à l'enseignement",
    "86.21": "cabinet libéral de médecine générale",
    "86.22": "cabinet libéral de médecine spécialisée ou d'imagerie",
    "86.23": "cabinet dentaire",
    "47.73": "pharmacie",
    "90.0": "spectacle vivant",
    "01.": "agriculture, chasse",
}


def motif_naf(naf):
    naf = naf or ""
    for prefixe, motif in EXCLUSIONS_NAF.items():
        if naf.startswith(prefixe):
            return prefixe, motif
    return None, None


def filtrer(fiche, nb_finess, famille=None):
    """Retourne None (à qualifier par l'agent) ou {"regle", "motif"} (écarté par le code)."""
    if "erreur" in fiche:
        return None                                      # pas de fiche : l'agent tranchera (et devra dire « à vérifier »)
    if (fiche.get("etat") or "A") in ("C", "F"):
        if famille == "bailleur_social":                 # les bailleurs cessent surtout par fusion : le client continue
            return {"regle": f"état {fiche['etat']} (Annuaire)",
                    "motif": "bailleur social cessé (fusion ou absorption probable : rechercher le successeur)"}
        return {"regle": f"état {fiche['etat']} (Annuaire)", "motif": "structure cessée"}
    prefixe, motif = motif_naf(fiche.get("naf_actuel"))
    if motif and nb_finess == 0:
        return {"regle": f"NAF actuel {fiche.get('naf_actuel')} ({fiche.get('libelle_naf_actuel') or '?'}), aucun établissement FINESS",
                "motif": motif}
    # Lieux de culte déclarés sous le code générique 94.99Z (« autres organisations ») : le nom seul est un indice faible,
    # mais combiné au NAF générique et à l'absence d'établissement FINESS, il suffit.
    mots = set(re.sub(r"[^A-Z ]", " ", (fiche.get("nom") or "").upper()).split())
    if (fiche.get("naf_actuel") or "").startswith("94.99") and nb_finess == 0 and mots & MOTS_CULTE:
        return {"regle": f"NAF actuel 94.99Z (organisation générique) + nom ({', '.join(sorted(mots & MOTS_CULTE))}), "
                         "aucun établissement FINESS", "motif": "organisation religieuse (culte)"}
    return None


TYPES_PREUVE = {"résidence personnes âgées", "résidence hôtelière sociale", "résidence sociale", "résidence handicapés",
                "équipement de santé"}       # « équipement d'action sociale » seul est trop bruité (cases cochées au dépôt)


def preuves_dures(fiche, nb_finess, famille, types_projet):
    """Faits vérifiables (pas des avis du modèle) qui rattachent une structure au cœur de cible de Buddimm."""
    p = []
    if nb_finess > 0:
        p.append(f"{nb_finess} établissement(s) FINESS")
    if (fiche.get("naf_actuel") or "")[:2] in ("86", "87", "88"):
        p.append(f"activité actuelle {fiche.get('naf_actuel')} (santé, hébergement médico-social, action sociale)")
    if famille == "bailleur_social":
        p.append("bailleur social")
    t = sorted(set(types_projet) & TYPES_PREUVE)
    if t:
        p.append("permis : " + ", ".join(t))
    return p


def garde_fou_prospect(v, fiche, nb_finess, famille, types_projet):
    """Un « prospect » sans aucune preuve dure devient « à vérifier » : appliqué par le code, quel que soit le modèle."""
    if v.get("verdict") != "prospect" or preuves_dures(fiche, nb_finess, famille, types_projet):
        return v
    return {**v, "verdict": "a_verifier",
            "limites": (v.get("limites") or "") + " [prospect sans preuve dure (FINESS, activité santé/social, bailleur, "
                                                  "permis médico-social) -> a_verifier]"}


MOTS_CULTE = {"EGLISE", "EGLISES", "PAROISSE", "PAROISSES", "PAROISSIALE", "MOSQUEE", "MOSQUEES", "MUSULMAN", "MUSULMANS", "MUSULMANE",
              "MUSULMANES", "CULTUELLE", "CULTUELLES", "CULTUEL", "CULTUELS",
              "EVANGELIQUE", "PENTECOTE", "PENTECOTISTE", "PROTESTANTE", "SYNAGOGUE", "ISRAELITE", "TEMPLE", "DIOCESE",
              "DIOCESAINE", "BOUDDHISTE", "PAGODE", "CHRETIENS", "CHRETIENNE", "ADVENTISTE", "ORTHODOXE"}
