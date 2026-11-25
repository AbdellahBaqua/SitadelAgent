r"""Liste de prospects priorisée pour Buddimm (Yvelines) -> out_fouille\prospects_priorises.csv / .json

  python -X utf8 src\prospects.py [--qualif nvidia|groq]

Étapes :
1. Candidats = familles clientes de Buddimm parmi les demandeurs de permis (association_ess, exploitant_sante_social,
   bailleur_social ; famille finale règles + agent, réconciliée entre fichiers comme dans profils.py)
   + EXPLOITANTS trouvés derrière les projets médico-sociaux déposés par des tiers (agent_prospects.py exploitants).
   Écrit prospects_candidats.json, lu par l'agent de qualification (agent_prospects.py prospects).
   Avant l'agent, un PRÉ-FILTRE déterministe (cible.py) écarte les cas sans jugement à porter : structure cessée,
   activité actuelle hors cible (culte, enseignement scolaire, sport, cabinet libéral…) sans établissement FINESS.
2. Score additif et explicable : chaque point a une raison écrite. Si l'agent de qualification est passé :
   faux positifs écartés (prospects_ecartes.csv, avec le motif) ; « à vérifier » -1 ; taille calculée par le code
   (moyenne ou grande +1, très grande -2) ; établissements FINESS exploités +2 (fait vérifiable, pas avis du modèle).
Les poids sont des HYPOTHÈSES de travail, à valider avec l'équipe métier. Aucune coordonnée, aucune personne
physique : personnes morales et liens vers sources publiques.
"""
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from fouille_commun import FOUILLE, permis, familles, ecrire_csv, entier
from profils import famille_reconciliee

CIBLES = {"association_ess": 3, "exploitant_sante_social": 2, "bailleur_social": 2}   # points de base par famille
RES_MEDICO = {"1": "résidence personnes âgées", "4": "résidence hôtelière sociale", "5": "résidence sociale",
              "6": "résidence handicapés"}
SP_MEDICO = {"3": "équipement de santé", "4": "équipement d'action sociale"}
ETATS = {"2": "autorisé", "4": "annulé", "5": "commencé", "6": "terminé"}
AUJ = date.today()
SEUIL_ATTENTE = (AUJ - timedelta(days=3 * 365)).isoformat()      # autorisé il y a moins de 3 ans
AGENT = FOUILLE / "agent_prospects"


def lire(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def type_med(jeu, r):
    return RES_MEDICO.get(r.get("RESIDENCE") or "") if jeu == "logements" else SP_MEDICO.get(r.get("TYPE_SERVICE_PUBLIC") or "")


def resume(jeu, r, depose_par=None):
    d = {"num_dau": r["NUM_DAU"], "fichier": jeu, "annee_depot": r["AN_DEPOT"], "commune": r.get("ADR_LOCALITE_TER", ""),
         "etat": ETATS.get(r["ETAT_DAU"], r["ETAT_DAU"]), "type_projet": type_med(jeu, r) or "",
         "logements_crees": entier(r.get("NB_LGT_TOT_CREES")) if jeu == "logements" else None,
         "surface_locaux_creee_m2": entier(r.get("SURF_LOC_CREEE")) if jeu == "locaux" else None}
    if depose_par:
        d["depose_par"] = depose_par
    return d


def bonus_temps(prs, score, raisons):
    derniere = max(entier(r["AN_DEPOT"]) for _, r in prs)
    if derniere >= AUJ.year - 2:
        score += 2; raisons.append(f"dépôt récent ({derniere}) +2")
    elif derniere >= AUJ.year - 4:
        score += 1; raisons.append(f"dépôt assez récent ({derniere}) +1")
    attente = [r for _, r in prs if r["ETAT_DAU"] == "2" and (r.get("DATE_REELLE_AUTORISATION") or "") >= SEUIL_ATTENTE]
    if attente:
        score += 2; raisons.append(f"{len(attente)} permis autorisé(s) depuis moins de 3 ans, pas encore commencé(s) +2")
    return score, attente


def famille_exploitant(exp):
    """Famille d'un exploitant FINESS, par sa forme juridique (règles de rules.py)."""
    import rules
    fam = rules.classify({"denom": exp.get("nom") or "", "cj": exp.get("nature_juridique") or "",
                          "ape": ""})["famille"]
    return "exploitant_sante_social" if fam in ("non_determine", "entreprise_autre", "fonciere_investisseur",
                                                 "promoteur") else fam


def candidats():
    fl, fc = familles("logements"), familles("locaux")
    acteurs = defaultdict(list)
    for jeu in ("logements", "locaux"):
        for r in permis(jeu):
            acteurs[r["SIREN_DEM"]].append((jeu, r))
    index = {(jeu, r["NUM_DAU"]): r for s, prs in acteurs.items() for jeu, r in prs}

    out = {}
    for s, prs in acteurs.items():
        fam, _ = famille_reconciliee(fl.get(s), fc.get(s))
        if fam not in CIBLES:
            continue
        score, raisons = CIBLES[fam], [f"famille cible ({fam}) +{CIBLES[fam]}"]
        medico = sorted({type_med(j, r) for j, r in prs if type_med(j, r)})
        if medico:
            score += 3; raisons.append(f"projet médico-social ({', '.join(medico)}) +3")
        score, attente = bonus_temps(prs, score, raisons)
        if fam != "bailleur_social" and len(prs) <= 2:
            score += 1; raisons.append("maître d'ouvrage occasionnel (1 ou 2 permis) +1")
        if any((j == "logements" and entier(r.get("NB_LGT_TOT_CREES")) >= 20) or
               (j == "locaux" and entier(r.get("SURF_LOC_CREEE")) >= 1000) for j, r in prs):
            score += 1; raisons.append("projet de taille significative (≥ 20 logements ou ≥ 1 000 m²) +1")
        if any(r["ETAT_DAU"] == "4" and entier(r["AN_DEPOT"]) >= AUJ.year - 4 for _, r in prs):
            score += 1; raisons.append("projet annulé récemment (besoin possible de sécurisation) +1")
        out[s] = {"siren": s, "famille": fam, "score": score, "raisons": raisons, "prs": prs, "attente": attente,
                  "origine": "demandeur de permis",
                  "denomination": (fl.get(s) or fc.get(s) or {}).get("denomination", "") or prs[0][1].get("DENOM_DEM", "")}

    # Exploitants trouvés derrière les projets déposés par des tiers
    for num, e in lire(AGENT / "exploitants.json").items():
        if e.get("finess") in (None, "aucun") or e.get("confiance") not in ("haute", "moyenne") or not e.get("siren_exploitant"):
            continue
        exp = e.get("exploitant") or {}
        if (exp.get("etat") or "A") in ("C", "F"):
            continue
        fam = famille_exploitant(exp)
        if fam not in CIBLES:
            continue
        s, r = e["siren_exploitant"], index.get((e["fichier"], num))
        if r is None:
            continue
        lien = (f"exploitant probable ({e['confiance']}) de « {e['etablissement']['nom']} », projet {e['type_projet']} "
                f"déposé par {e['demandeur']} (permis {num}) +3")
        if s not in out:
            out[s] = {"siren": s, "famille": fam, "score": CIBLES[fam], "raisons": [f"famille cible ({fam}) +{CIBLES[fam]}"],
                      "prs": [], "attente": [], "origine": "exploitant trouvé derrière un permis déposé par un tiers",
                      "denomination": exp.get("nom") or e["etablissement"]["nom"]}
        c = out[s]
        if not any(x.startswith("exploitant probable") for x in c["raisons"]):
            c["score"] += 3
        c["raisons"].append(lien)
        c.setdefault("prs_tiers", []).append((e["fichier"], r, e["demandeur"]))

    for c in out.values():                                 # bonus de calendrier pour les seuls exploitants trouvés
        if not c["prs"] and c.get("prs_tiers"):
            c["score"], c["attente"] = bonus_temps([(j, r) for j, r, _ in c["prs_tiers"]], c["score"], c["raisons"])
    return out


def main():
    import argparse, cible, finess
    from agent_prospects import fiche
    ap = argparse.ArgumentParser()
    ap.add_argument("--qualif", default="nvidia", help="verdicts de l'agent à appliquer : nvidia ou groq")
    qualif = ap.parse_args().qualif
    cands = candidats()

    # 1. Pré-filtre déterministe (code) : les cas sans jugement à porter ne vont pas à l'agent
    exclus = {}
    for s, c in cands.items():
        e = cible.filtrer(fiche(s), len(finess.par_siren(s)), c["famille"])
        if e:
            exclus[s] = e
    (FOUILLE / "prospects_candidats.json").write_text(json.dumps([{
        "siren": c["siren"], "denomination": c["denomination"], "famille": c["famille"], "origine": c["origine"],
        "raisons": " ; ".join(c["raisons"]),
        "permis": sorted([resume(j, r) for j, r in c["prs"]] + [resume(j, r, d) for j, r, d in c.get("prs_tiers", [])],
                         key=lambda x: x["annee_depot"], reverse=True)} for s, c in cands.items() if s not in exclus],
        ensure_ascii=False, indent=1), encoding="utf-8")

    # 2. Verdicts de l'agent (cas qui demandent un jugement)
    verdicts = lire(AGENT / f"prospects_{qualif}.json")
    prospects, ecartes = [], []
    for s, c in cands.items():
        score, raisons, v = c["score"], list(c["raisons"]), verdicts.get(s)
        types = {type_med(j, r) for j, r in c["prs"]} | {type_med(j, r) for j, r, _ in c.get("prs_tiers", [])}
        preuves = [] if s in exclus else cible.preuves_dures(fiche(s), len(finess.par_siren(s)), c["famille"], types)
        if v:                                              # garde-fou du code, aussi appliqué aux verdicts déjà en cache
            v = cible.garde_fou_prospect(v, fiche(s), len(finess.par_siren(s)), c["famille"], types)
        src = f"https://annuaire-entreprises.data.gouv.fr/entreprise/{s}"
        if s in exclus:
            ecartes.append({"denomination": c["denomination"], "famille": c["famille"], "score_initial": score,
                            "ecarte_par": "code (règle)", "motif": exclus[s]["motif"], "indices": exclus[s]["regle"],
                            "limites": "", "siren": s, "source_entreprise": src})
            continue
        if v:
            if v["verdict"] == "faux_positif":
                ecartes.append({"denomination": c["denomination"], "famille": c["famille"], "score_initial": score,
                                "ecarte_par": f"agent ({v.get('modele', qualif)})", "motif": v["type_structure"],
                                "indices": " ; ".join(v["indices"]), "limites": v["limites"], "siren": s, "source_entreprise": src})
                continue
            if v["verdict"] == "a_verifier":
                score -= 1; raisons.append("agent : à vérifier -1")
            if v["taille"] in ("moyenne", "grande"):
                score += 1; raisons.append(f"taille {v['taille']} (cœur de cible) +1")
            elif v["taille"] == "très grande":
                score -= 2; raisons.append("très grande structure, direction immobilière interne probable -2")
            if v["finess_france"] > 0:
                score += 2; raisons.append(f"exploite {v['finess_france']} établissement(s) FINESS +2")
        jd, rd = max(c["prs"] or [(j, r) for j, r, _ in c["prs_tiers"]],
                     key=lambda x: (x[1]["AN_DEPOT"], x[1].get("DATE_REELLE_AUTORISATION") or ""))
        prospects.append({
            "siren": s, "denomination": c["denomination"], "famille": c["famille"], "origine": c["origine"],
            "score": score, "raisons": " ; ".join(raisons),
            "verdict_agent": v["verdict"] if v else "non qualifié", "adequation": v["adequation"] if v else "",
            "taille": v["taille"] if v else "", "type_structure": v["type_structure"] if v else "",
            "besoin_immobilier": v["besoin_immobilier"] if v else "",
            "preuves_dures": " ; ".join(preuves) or "aucune (à vérifier)",
            "indices_agent": " ; ".join(v["indices"]) if v else "",
            "permis_logements": sum(1 for j, _ in c["prs"] if j == "logements"),
            "permis_locaux": sum(1 for j, _ in c["prs"] if j == "locaux"),
            "dernier_permis": rd["NUM_DAU"], "dernier_depot": rd["AN_DEPOT"], "dernier_commune": rd.get("ADR_LOCALITE_TER", ""),
            "dernier_etat": ETATS.get(rd["ETAT_DAU"], rd["ETAT_DAU"]),
            "dernier_type": ("logements" if jd == "logements" else "locaux") + (f" ({type_med(jd, rd)})" if type_med(jd, rd) else ""),
            "permis_en_attente": ", ".join(r["NUM_DAU"] for r in c["attente"][:3]),
            "source_entreprise": f"https://annuaire-entreprises.data.gouv.fr/entreprise/{s}",
        })
    ordre_adeq = {"forte": 0, "moyenne": 1, "faible": 2, "": 3}
    prospects.sort(key=lambda p: (-p["score"], ordre_adeq.get(p["adequation"], 3), -int(p["dernier_depot"] or 0), p["denomination"]))
    for i, p in enumerate(prospects, 1):
        p["rang"] = i
    cols = ["rang", "score", "denomination", "famille", "origine", "verdict_agent", "adequation", "taille", "type_structure",
            "besoin_immobilier", "preuves_dures", "raisons", "indices_agent", "permis_logements", "permis_locaux", "dernier_depot", "dernier_commune",
            "dernier_type", "dernier_etat", "dernier_permis", "permis_en_attente", "siren", "source_entreprise"]
    ecrire_csv("prospects_priorises.csv", [{k: p[k] for k in cols} for p in prospects])
    ecrire_csv("prospects_ecartes.csv", ecartes)
    nb = lambda k, val: sum(1 for p in prospects if p[k] == val)
    (FOUILLE / "prospects_priorises.json").write_text(json.dumps({
        "genere_le": AUJ.isoformat(), "qualification": qualif, "nb_candidats": len(cands), "nb": len(prospects), "nb_ecartes": len(ecartes),
        "nb_ecartes_code": sum(1 for e in ecartes if e["ecarte_par"].startswith("code")),
        "nb_ecartes_agent": sum(1 for e in ecartes if e["ecarte_par"].startswith("agent")),
        "motifs_code": dict(Counter(e["motif"] for e in ecartes if e["ecarte_par"].startswith("code")).most_common()),
        "par_famille": {f: nb("famille", f) for f in CIBLES},
        "par_origine": {o: nb("origine", o) for o in ("demandeur de permis", "exploitant trouvé derrière un permis déposé par un tiers")},
        "par_verdict": {v: nb("verdict_agent", v) for v in ("prospect", "a_verifier", "non qualifié")},
        "bareme": {"famille cible": CIBLES, "projet médico-social": 3, "dépôt récent (≤ 2 ans) / assez récent (≤ 4 ans)": "2 / 1",
                   "permis autorisé < 3 ans non commencé": 2, "maître d'ouvrage occasionnel (hors bailleurs)": 1,
                   "projet de taille significative": 1, "annulation récente": 1,
                   "exploitant probable d'un projet déposé par un tiers": 3, "exploite des établissements FINESS": 2,
                   "taille moyenne ou grande / très grande": "+1 / -2", "agent : à vérifier": -1, "agent : faux positif": "écarté",
                   "pré-filtre du code (cessée, culte, enseignement, sport, cabinet libéral…)": "écarté"},
        "ecartes": ecartes,
        "prospects": [{k: p[k] for k in cols} for p in prospects]}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"candidats : {len(cands)} | écartés par le code : {len(exclus)} | à qualifier par l'agent : {len(cands) - len(exclus)} | "
          f"verdicts {qualif} : {sum(1 for s in verdicts if s in cands)}")
    print(f"prospects : {len(prospects)} | écartés : {len(ecartes)} | "
          f"qualifiés par l'agent : {sum(1 for p in prospects if p['verdict_agent'] != 'non qualifié') + sum(1 for e in ecartes if e['ecarte_par'].startswith('agent'))}")
    for p in prospects[:20]:
        print(f"{p['rang']:3d}. [{p['score']:2d}] {p['denomination'][:38]:38s} {p['famille'][:12]:12s} "
              f"{p['verdict_agent'][:10]:10s} {p['adequation']:7s} {p['taille']:11s} {p['dernier_type'][:30]}")


if __name__ == "__main__":
    main()
