r"""Agent de qualification commerciale pour Buddimm : deux missions, mêmes garde-fous que l'agent de classification.

  python -X utf8 src\agent_prospects.py exploitants [--limit N]   # futur exploitant des projets déposés par des tiers
  python -X utf8 src\agent_prospects.py prospects   [--limit N]   # vrai prospect ou faux positif ?
  python -X utf8 src\agent_prospects.py bilan                     # raisons des « aucun » + taux sur les permis attendus
  --fournisseur groq --modele openai/gpt-oss-120b : autre fournisseur ; les verdicts vont dans prospects_<fournisseur>.json
  (les prospects reçus sont ceux qui ont passé le pré-filtre déterministe de cible.py, appliqué par prospects.py).
  --echantillon 50 : ne traiter que 50 éléments tirés au hasard (graine fixe, --graine) pour les tests ;
  « bilan --echantillon 50 » mesure alors sur ce seul échantillon. Les résultats déjà en cache sont réutilisés.

1. exploitants : pour chaque permis médico-social ou social déposé par un NON-exploitant (promoteur, bailleur,
   foncière, entreprise, non déterminé), le code liste les établissements FINESS de la commune compatibles avec le
   type de projet, avec des indices (même rue, même numéro, ouverture après l'autorisation). Le modèle choisit
   l'établissement qui correspond au permis, ou « aucun ». L'exploitant trouvé est le vrai client potentiel.
2. prospects : pour chaque candidat de la liste de prospects (out_fouille\prospects_candidats.json, écrit par
   prospects.py), le code fournit ses permis, sa fiche entreprise et ses établissements FINESS ; le modèle dit
   prospect / faux_positif / a_verifier, avec l'adéquation et le besoin immobilier visible.

Garde-fous appliqués par le CODE : listes fermées ; numéro FINESS choisi obligatoirement dans la liste fournie ;
confiance « haute » seulement si même rue ET ouverture après l'autorisation ; taille calculée par le code, pas par
le modèle ; adéquation « forte » impossible pour une très grande structure ou sans aucune preuve d'activité
médico-sociale ou sociale ; faux positif refusé s'il ne repose que sur le nom ; chaque indice doit citer son outil ;
trace complète sauvegardée ; cache par identifiant. Aucune donnée sur des personnes physiques, aucun téléphone.
"""
import argparse, csv, http.client, json, random, sys, time, urllib.error
from collections import Counter, defaultdict
from fouille_commun import FOUILLE, permis, familles, entier
from profils import famille_reconciliee
import llm_classify
import agent, cible, finess
from referentiels import NAF, CJ

DOSSIER = FOUILLE / "agent_prospects"
TRACES = DOSSIER / "traces"
TRACES.mkdir(parents=True, exist_ok=True)
CACHE_EXPL = DOSSIER / "exploitants.json"
def cache_prospects(fournisseur):
    return DOSSIER / f"prospects_{fournisseur}.json"
MAX_STEPS = 6

RES_MEDICO = {"1": "résidence personnes âgées", "4": "résidence hôtelière sociale", "5": "résidence sociale",
              "6": "résidence handicapés"}
SP_MEDICO = {"3": "équipement de santé", "4": "équipement d'action sociale"}
ETATS = {"2": "autorisé, pas encore commencé", "4": "annulé", "5": "commencé", "6": "terminé"}
NON_EXPLOITANTS = {"promoteur", "bailleur_social", "fonciere_investisseur", "entreprise_autre", "non_determine"}
TRANCHES = {"00": 0, "01": 1, "02": 3, "03": 6, "11": 10, "12": 20, "21": 50, "22": 100, "31": 200, "32": 250,
            "41": 500, "42": 1000, "51": 2000, "52": 5000, "53": 10000}


def type_projet(jeu, r):
    if jeu == "logements":
        return RES_MEDICO.get(r.get("RESIDENCE") or "")
    return SP_MEDICO.get(r.get("TYPE_SERVICE_PUBLIC") or "")


def resume_permis(jeu, r):
    return {"num_dau": r["NUM_DAU"], "fichier": jeu, "annee_depot": r["AN_DEPOT"],
            "date_autorisation": (r.get("DATE_REELLE_AUTORISATION") or "")[:10], "commune": r.get("ADR_LOCALITE_TER", ""),
            "etat": ETATS.get(r["ETAT_DAU"], r["ETAT_DAU"]), "type_projet": type_projet(jeu, r) or "",
            "logements_crees": entier(r.get("NB_LGT_TOT_CREES")) if jeu == "logements" else None,
            "surface_locaux_creee_m2": entier(r.get("SURF_LOC_CREEE")) if jeu == "locaux" else None}


# ---------- fiche entreprise (Annuaire, cache partagé avec l'agent de classification) ----------
def fiche(siren):
    e = agent._annuaire(siren)
    if "erreur" in e:
        return {"erreur": e["erreur"]}
    if e.get("siren") != siren:
        return {"erreur": "SIREN introuvable dans l'Annuaire (premier résultat différent)"}
    out = {k: e.get(k) for k in ("nom", "nature_juridique", "naf_actuel", "etat", "date_creation", "categorie",
                                 "effectif", "nb_etablissements", "nb_etablissements_ouverts")}
    out["libelle_naf_actuel"] = NAF.get(e.get("naf_actuel") or "")
    out["libelle_nature_juridique"] = CJ.get(e.get("nature_juridique") or "")
    out["aide"] = ("etat A = active, C ou F = cessée. effectif = tranche Insee de salariés (ex. 21 = 50 à 99, "
                   "41 = 500 à 999, 51 = 2 000 à 4 999). Dirigeants et finances volontairement exclus.")
    out["source"] = f"https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}"
    return out


def taille(f, fin):
    """Classe de taille calculée par le CODE (hypothèse de travail, à valider avec Buddimm)."""
    if "erreur" in f:
        return "inconnue", "fiche entreprise indisponible"
    sal = TRANCHES.get(f.get("effectif") or "")
    nfin, nouv = fin["nb_etablissements_finess_france"], f.get("nb_etablissements_ouverts") or 0
    if (sal or 0) >= 2000 or nfin >= 100 or nouv >= 200:
        cl = "très grande"
    elif (sal or 0) >= 500 or nfin >= 30 or nouv >= 50:
        cl = "grande"
    elif (sal or 0) >= 50 or nfin >= 3 or nouv >= 5:
        cl = "moyenne"
    elif sal is not None:
        cl = "petite"
    else:
        cl = "inconnue"
    return cl, f"salariés ≥ {sal if sal is not None else '?'}, établissements ouverts {nouv}, établissements FINESS {nfin}"


# ---------- boucle commune ----------
def boucle(key, model, system, entree, tools, handlers, nom_conclure, url=None):
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": json.dumps(entree, ensure_ascii=False)[:12000]}]
    trace = [{"etape": "pre", "texte": "résultats calculés par le code avant le modèle", "entree": entree}]
    for step in range(MAX_STEPS):
        msg = agent._chat(key, model, messages, tools, url)
        calls = msg.get("tool_calls") or []
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls") and v})
        trace.append({"etape": step, "texte": msg.get("content"), "appels": [
            {"outil": c["function"]["name"], "args": c["function"]["arguments"]} for c in calls]})
        if not calls:
            messages.append({"role": "user", "content": f"Conclus maintenant avec l'outil `{nom_conclure}`."})
            continue
        final = None
        for c in calls:
            name = c["function"]["name"]
            try:
                args = json.loads(c["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            if name == nom_conclure:
                final = args
                continue
            fn = handlers.get(name)
            try:
                out = fn(**args) if fn else {"erreur": f"outil inconnu {name}"}
            except TypeError as e:
                out = {"erreur": f"arguments invalides : {e}"}
            trace[-1].setdefault("resultats", []).append({"outil": name, "sortie": out})
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(out, ensure_ascii=False)[:6000]})
        if final is not None:
            return final, trace, step + 1
    return None, trace, MAX_STEPS


def sources_indices(indices, outils):
    """Fragilités : indice sans outil cité, ou venant de la mémoire du modèle."""
    f = []
    for ind in indices:
        low = ind.strip().lower()
        if low.startswith("connaissance du modèle"):
            f.append(f"indice issu de la mémoire du modèle, non vérifié : {ind[:100]}")
        elif not low.startswith(tuple(outils) + ("dénomination", "denomination")):
            f.append(f"indice sans source d'outil : {ind[:100]}")
    return f


def _fiche_tool():
    return {"type": "function", "function": {"name": "fiche_entreprise",
            "description": "Fiche publique d'une personne morale (Annuaire des entreprises) : activité actuelle, forme juridique, état, taille.",
            "parameters": {"type": "object", "properties": {"siren": {"type": "string"}}, "required": ["siren"]}}}


def _enregistrer(cache_path, cache, cle, res, trace):
    cache[cle] = res
    (TRACES / f"{cache_path.stem}_{cle}.json").write_text(json.dumps(trace, ensure_ascii=False, indent=1), encoding="utf-8")
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def connexion(fournisseur=None, modele=None):
    """Fournisseur et modèle de l'agent. Par défaut : LLM_PROVIDER et MODEL_CLASSIFICATION de .env.
    --fournisseur groq --modele openai/gpt-oss-120b permet de comparer deux modèles sur les mêmes cas."""
    vals = llm_classify._read_env()
    defaut = (vals.get("LLM_PROVIDER") or "nvidia").lower()
    nom = (fournisseur or defaut).lower()
    if nom not in llm_classify.PROVIDERS:
        raise SystemExit(f"fournisseur inconnu : {nom} (choix : {', '.join(llm_classify.PROVIDERS)})")
    p = llm_classify.PROVIDERS[nom]
    model = modele or (vals.get("MODEL_CLASSIFICATION") if nom == defaut else None) or vals.get(p["model"]) or p["default_model"]
    key = vals.get(p["key"], "")
    if not key or not model:
        raise SystemExit(f"Clé ({p['key']}) ou modèle manquant dans .env pour {nom}.")
    return {"nom": nom, "url": p["url"], "key": key, "model": model}


def _lancer(items, cache_path, analyser, limit, pause, conn):
    key, model = conn["key"], conn["model"]
    print(f"fournisseur : {conn['nom']} | modèle : {model}", flush=True)
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    fait = 0
    for cle, item in items:
        if cle in cache:
            continue
        if limit is not None and fait >= limit:
            break
        try:
            res, trace = analyser(item, key, model, conn["url"])
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, KeyError,
                TimeoutError, OSError, http.client.HTTPException) as e:
            print(f"  {cle}: échec ({type(e).__name__}: {e}), retenté au prochain lancement", flush=True)
            time.sleep(pause)
            continue
        _enregistrer(cache_path, cache, cle, res, trace)
        fait += 1
        print(f"  {cle} -> {res.get('verdict') or res.get('finess')} ({res.get('confiance') or res.get('adequation')})", flush=True)
        if res.get("modele"):
            time.sleep(pause)
    print(f"{fait} nouveaux résultats, {len(cache)} en cache -> {cache_path}")
    return cache


# ======================= 1. futur exploitant =======================
SYSTEM_EXPL = (
    "Tu aides Buddimm (direction immobilière externalisée pour associations, gestionnaires d'établissements "
    "médico-sociaux et bailleurs sociaux) à trouver le FUTUR EXPLOITANT d'un bâtiment médico-social ou social dont le "
    "permis de construire a été déposé par un tiers (promoteur, bailleur, foncière…). Le code te donne le permis, puis "
    "les établissements FINESS de la même commune compatibles avec le type de projet, avec des indices calculés : "
    "meme_rue, meme_numero, ouvert_apres_autorisation, et la fiche entreprise de leurs exploitants.\n"
    "Choisis le numéro FINESS de l'établissement qui correspond le plus probablement à ce permis, ou « aucun ».\n"
    "RÈGLES :\n"
    "- Ne choisis QUE dans la liste candidats_finess ; n'invente aucun numéro.\n"
    "- « haute » seulement si même rue ET ouverture l'année de l'autorisation ou après. Un établissement ouvert bien "
    "avant l'autorisation peut correspondre à une extension ou une reconstruction : dis-le dans limites.\n"
    "- Plusieurs candidats aussi plausibles, ou aucun dans la même rue : « aucun » ou confiance « faible ».\n"
    "- Chaque indice commence par sa source : permis, candidats_finess ou fiche_entreprise.\n"
    "- Ne cherche aucune information sur des personnes physiques."
)
TOOLS_EXPL = [_fiche_tool(), {"type": "function", "function": {"name": "conclure_exploitant",
    "description": "Réponse finale.", "parameters": {"type": "object", "properties": {
        "finess": {"type": "string", "description": "numéro FINESS choisi dans candidats_finess, ou « aucun »"},
        "confiance": {"type": "string", "enum": ["haute", "moyenne", "faible"]},
        "indices": {"type": "array", "items": {"type": "string"}},
        "limites": {"type": "string"}}, "required": ["finess", "confiance", "indices", "limites"]}}}]


def permis_tiers():
    """Permis médico-sociaux ou sociaux déposés par un non-exploitant, avec leur demandeur."""
    fl, fc = familles("logements"), familles("locaux")
    out = []
    for jeu in ("logements", "locaux"):
        for r in permis(jeu):
            tp = type_projet(jeu, r)
            if not tp:
                continue
            fam, _ = famille_reconciliee(fl.get(r["SIREN_DEM"]), fc.get(r["SIREN_DEM"]))
            if fam in NON_EXPLOITANTS:
                den = (fl.get(r["SIREN_DEM"]) or fc.get(r["SIREN_DEM"]) or {}).get("denomination") or r.get("DENOM_DEM", "")
                out.append((jeu, r, tp, fam, den))
    return out


SENIORS_PRIVES = ("RSS", "SENIOR", "SENIORIALES", "TEMPORELLES", "DOMITYS", "OVELIA", "ARCADIE", "AQUARELIA",
                  "HESPERIDES", "VILLAGES D'OR", "COGEDIM CLUB", "ESPACE ET VIE")
RAISONS = ["exploitant trouvé", "bâtiment pas encore ouvert (autorisé non commencé ou annulé)", "adresse du permis vide",
           "résidence seniors privée probable (hors FINESS)",
           "aucun établissement compatible dans la commune", "aucun établissement compatible dans la rue",
           "candidat dans la rue écarté par l'agent"]
ATTENDUS = {"exploitant trouvé", "aucun établissement compatible dans la commune",
            "aucun établissement compatible dans la rue", "candidat dans la rue écarté par l'agent"}


def raison(res, cands, adresse):
    """Pourquoi un exploitant a (ou n'a pas) été trouvé : calculé par le CODE, pas par le modèle.
    Les résidences services seniors privées sont classées « résidence personnes âgées » dans Sitadel, comme les Ehpad,
    mais ne sont pas des établissements médico-sociaux : elles ne figurent pas dans FINESS (exploitant commercial)."""
    if res["finess"] != "aucun":
        return "exploitant trouvé"
    if res.get("etat", "").startswith(("autorisé", "annulé")):     # rien n'a été construit : rien à trouver dans FINESS
        return "bâtiment pas encore ouvert (autorisé non commencé ou annulé)"
    if not (adresse or "").strip():
        return "adresse du permis vide"
    rue = any(c["meme_rue"] for c in cands)
    nom = (res.get("demandeur") or "").upper()
    if res["type_projet"] == "résidence personnes âgées" and not rue and (
            any(k in nom.split() or k in nom for k in SENIORS_PRIVES if len(k) > 3) or " RSS " in f" {nom} "
            or res["famille_demandeur"] in ("promoteur", "fonciere_investisseur", "entreprise_autre", "non_determine")):
        return "résidence seniors privée probable (hors FINESS)"
    if not cands:
        return "aucun établissement compatible dans la commune"
    return "candidat dans la rue écarté par l'agent" if rue else "aucun établissement compatible dans la rue"


def analyser_permis(item, key, model, url=None):
    res, trace = _analyser_permis(item, key, model, url)
    _, r, tp, _, _ = item
    res["raison"] = raison(res, finess.candidats(r, tp), r.get("ADR_LIBVOIE_TER"))
    return res, trace


def _analyser_permis(item, key, model, url=None):
    jeu, r, tp, fam, den = item
    cands = finess.candidats(r, tp)
    p = {**resume_permis(jeu, r), "adresse_travaux": f"{(r.get('ADR_NUM_TER') or '').lstrip('0')} {r.get('ADR_LIBVOIE_TER') or ''}".strip(),
         "demandeur": den, "siren_demandeur": r["SIREN_DEM"], "famille_demandeur": fam}
    base = {"num_dau": r["NUM_DAU"], "fichier": jeu, "type_projet": tp, "demandeur": den, "siren_demandeur": r["SIREN_DEM"],
            "famille_demandeur": fam, "commune": p["commune"], "annee_depot": r["AN_DEPOT"], "etat": p["etat"]}
    if not cands:                                          # rien à départager : pas d'appel au modèle
        return {**base, "finess": "aucun", "confiance": "faible", "indices": ["candidats_finess : aucun établissement compatible dans la commune"],
                "limites": "FINESS ne liste que les établissements autorisés ; un projet récent peut ne pas y être encore.",
                "fragilites": [], "etapes": 0, "modele": None}, [{"etape": "pre", "candidats": []}]
    fiches = {}
    for c in cands[:4]:
        s = c["siren_exploitant"]
        if s and s not in fiches:
            fiches[s] = fiche(s)
    entree = {"permis": p, "candidats_finess": cands, "fiches_exploitants": fiches,
              "consigne": "Ces résultats viennent des outils permis, candidats_finess et fiche_entreprise : cite-les. "
                          "Appelle fiche_entreprise seulement pour un exploitant absent de fiches_exploitants, puis conclus."}
    final, trace, etapes = boucle(key, model, SYSTEM_EXPL, entree, TOOLS_EXPL, {"fiche_entreprise": fiche}, "conclure_exploitant", url)
    if final is None:
        return {**base, "finess": "aucun", "confiance": "faible", "indices": [], "limites": f"pas de conclusion en {MAX_STEPS} étapes",
                "fragilites": [], "etapes": etapes, "modele": model}, trace
    num, conf, lim = (final.get("finess") or "aucun").strip(), final.get("confiance", "faible"), final.get("limites", "")
    frag = sources_indices(final.get("indices", []), ("permis", "candidats_finess", "fiche_entreprise"))
    choix = next((c for c in cands if c["finess"] == num), None)
    if num != "aucun" and choix is None:                   # garde-fou : pas de numéro inventé
        num, conf, lim = "aucun", "faible", lim + " [numéro hors liste -> aucun]"
    if conf not in ("haute", "moyenne", "faible"):
        conf = "faible"
    if choix:
        if conf == "haute" and not (choix["meme_rue"] and choix["ouvert_apres_autorisation"]):
            conf, lim = "moyenne", lim + " [haute refusée : il faut même rue et ouverture après l'autorisation]"
        if not choix["meme_rue"] and not choix["ouvert_apres_autorisation"]:
            conf = "faible"
        if frag and conf == "haute":
            conf, lim = "moyenne", lim + " [confiance plafonnée : fragilités détectées]"
    exp = fiches.get(choix["siren_exploitant"]) if choix else None
    if choix and exp is None and choix["siren_exploitant"]:
        exp = fiche(choix["siren_exploitant"])
    return {**base, "finess": num, "confiance": conf, "indices": final.get("indices", []), "limites": lim, "fragilites": frag,
            "etablissement": choix and {k: choix[k] for k in ("nom", "adresse", "categorie", "ouverture", "fiche")},
            "siren_exploitant": choix and choix["siren_exploitant"],
            "exploitant": exp and {k: exp.get(k) for k in ("nom", "nature_juridique", "libelle_nature_juridique", "naf_actuel", "etat")},
            "etapes": etapes, "modele": model}, trace


# ======================= 2. vrai prospect ? =======================
SYSTEM_PROS = (
    "Tu es analyste commercial pour Buddimm, direction immobilière externalisée : Buddimm pilote les projets "
    "immobiliers (recherche de locaux, construction, réhabilitation, montage d'opération) d'associations et structures "
    "de l'ESS, de gestionnaires d'établissements sanitaires, sociaux et médico-sociaux, et de bailleurs sociaux qui "
    "n'ont pas de direction immobilière interne suffisante.\n"
    "Tâche : pour une personne morale retenue dans la liste de prospects (Yvelines), dire si c'est un VRAI prospect. "
    "Les cas évidents (structure cessée, culte, enseignement scolaire, sport, cabinet libéral de santé) ont déjà été "
    "écartés par le code : il te reste ceux qui demandent un jugement.\n"
    "verdict : prospect (cible plausible avec un besoin immobilier visible) ; faux_positif (pas une cible : école, "
    "culte, activité sans lien avec le social, le médico-social ou l'ESS, structure cessée…) ; a_verifier (preuves "
    "insuffisantes ou contradictoires). adequation : forte, moyenne ou faible.\n"
    "RÈGLES :\n"
    "- Les résultats des outils sont fournis : cite-les. Chaque indice commence par sa source : permis_du_prospect, "
    "fiche_entreprise, finess_du_prospect ou dénomination.\n"
    "- taille_calculee vient du code : ne la recalcule pas. Hypothèse de travail de Buddimm : une très grande structure "
    "(milliers de salariés, centaines d'établissements) a sa propre direction immobilière, donc adéquation au mieux "
    "moyenne ; les structures moyennes et grandes sont le cœur de cible ; une très petite structure a peu de projets.\n"
    "- FINESS confirme qu'une structure exploite des établissements sanitaires ou médico-sociaux ; 0 établissement "
    "FINESS ne prouve rien à lui seul.\n"
    "- Le type d'équipement du permis est une case cochée au dépôt : un « équipement d'action sociale » peut être une "
    "école ou un lieu de culte. Vérifie avec l'activité réelle (libelle_naf_actuel, nature juridique).\n"
    "- Une structure cessée (etat C ou F) n'est pas un prospect.\n"
    "- Petite enfance (crèches) : cible si association ou structure de l'ESS ; une crèche commerciale privée est au mieux "
    "une adéquation faible (hypothèse de travail). Un bailleur social est une cible : ne l'écarte pas pour son activité "
    "« location de logements ».\n"
    "- Ne te fie jamais à ta mémoire pour le sens d'un code. Aucune information sur des personnes physiques.\n"
    "- besoin_immobilier : ce que montrent les permis (projet autorisé non commencé, projets récurrents…), une phrase.\n"
    "- Dans le doute : a_verifier."
)
TOOLS_PROS = [_fiche_tool(), {"type": "function", "function": {"name": "conclure_prospect",
    "description": "Réponse finale.", "parameters": {"type": "object", "properties": {
        "verdict": {"type": "string", "enum": ["prospect", "faux_positif", "a_verifier"]},
        "adequation": {"type": "string", "enum": ["forte", "moyenne", "faible"]},
        "type_structure": {"type": "string", "description": "ce qu'est la structure, en quelques mots"},
        "besoin_immobilier": {"type": "string"},
        "indices": {"type": "array", "items": {"type": "string"}},
        "limites": {"type": "string"}},
        "required": ["verdict", "adequation", "type_structure", "besoin_immobilier", "indices", "limites"]}}}]


def analyser_prospect(cand, key, model, url=None):
    s = cand["siren"]
    f, fin = fiche(s), finess.resume_siren(s)
    cl, pourquoi = taille(f, fin)
    entree = {"siren": s, "denomination": cand["denomination"], "famille_classification": cand["famille"],
              "raisons_du_score": cand["raisons"], "taille_calculee": cl, "taille_calcul": pourquoi,
              "permis_du_prospect": cand["permis"][:15], "fiche_entreprise": f, "finess_du_prospect": fin,
              "origine": cand.get("origine", "demandeur de permis"),
              "consigne": "Ces résultats viennent des outils permis_du_prospect, fiche_entreprise et finess_du_prospect : "
                          "cite-les. Conclus avec conclure_prospect."}
    final, trace, etapes = boucle(key, model, SYSTEM_PROS, entree, TOOLS_PROS, {"fiche_entreprise": fiche}, "conclure_prospect", url)
    base = {"siren": s, "denomination": cand["denomination"], "taille": cl, "taille_calcul": pourquoi,
            "finess_france": fin["nb_etablissements_finess_france"], "finess_yvelines": fin["nb_etablissements_finess_yvelines"]}
    if final is None:
        return {**base, "verdict": "a_verifier", "adequation": "faible", "type_structure": "", "besoin_immobilier": "",
                "indices": [], "limites": f"pas de conclusion en {MAX_STEPS} étapes", "fragilites": [], "etapes": etapes,
                "modele": model}, trace
    v, a, lim = final.get("verdict"), final.get("adequation"), final.get("limites", "")
    ind = final.get("indices", [])
    frag = sources_indices(ind, ("permis_du_prospect", "fiche_entreprise", "finess_du_prospect", "libelle", "taille_calcul"))
    if v not in ("prospect", "faux_positif", "a_verifier"):
        v, lim = "a_verifier", lim + " [verdict hors liste]"
    if a not in ("forte", "moyenne", "faible"):
        a = "faible"
    if "erreur" in f and v != "a_verifier":
        v, lim = "a_verifier", lim + " [fiche entreprise indisponible -> a_verifier]"
    if v == "faux_positif" and not any(i.strip().lower().startswith(("fiche_entreprise", "finess_du_prospect", "permis_du_prospect"))
                                       for i in ind):
        v, lim = "a_verifier", lim + " [faux positif fondé sur le seul nom -> a_verifier]"
    if (f.get("etat") or "A") in ("C", "F") and v == "prospect":
        v, lim = "a_verifier", lim + " [structure cessée selon l'Annuaire]"
    preuve_social = (fin["nb_etablissements_finess_france"] > 0 or (f.get("naf_actuel") or "")[:2] in ("86", "87", "88")
                     or (f.get("nature_juridique") or "")[:2] in ("92", "93") or cand["famille"] == "bailleur_social")
    if a == "forte" and cl == "très grande":
        a, lim = "moyenne", lim + " [forte refusée : très grande structure, direction immobilière interne probable]"
    if a == "forte" and not preuve_social:
        a, lim = "moyenne", lim + " [forte refusée : aucune preuve d'activité sociale ou médico-sociale]"
    res = {**base, "verdict": v, "adequation": a, "type_structure": final.get("type_structure", ""),
           "besoin_immobilier": final.get("besoin_immobilier", ""), "indices": ind, "limites": lim, "fragilites": frag,
           "etapes": etapes, "modele": model}
    res = cible.garde_fou_prospect(res, f, fin["nb_etablissements_finess_france"], cand["famille"],
                                   {p.get("type_projet") for p in cand["permis"]})
    return res, trace


def echantillonner(items, n, graine, mission):
    """Tirage aléatoire reproductible de n éléments (graine fixe) ; la liste tirée est enregistrée."""
    if not n or n >= len(items):
        return items
    tires = random.Random(graine).sample(items, n)
    (DOSSIER / f"echantillon_{mission}.json").write_text(json.dumps(
        {"graine": graine, "n": n, "sur": len(items), "cles": [k for k, _ in tires]}, ensure_ascii=False, indent=1), encoding="utf-8")
    return tires


def bilan_exploitants(echantillon=False):
    """Étiquette chaque résultat en cache (raison calculée par le code) et mesure le taux de rapprochement sur les
    permis où FINESS DEVRAIT trouver un exploitant. Écrit exploitants_bilan.csv."""
    cache = json.loads(CACHE_EXPL.read_text(encoding="utf-8")) if CACHE_EXPL.exists() else {}
    if echantillon and (DOSSIER / "echantillon_exploitants.json").exists():
        cles = set(json.loads((DOSSIER / "echantillon_exploitants.json").read_text(encoding="utf-8"))["cles"])
        cache = {k: v for k, v in cache.items() if k in cles}
    items = {r["NUM_DAU"]: (jeu, r, tp) for jeu, r, tp, _, _ in permis_tiers()}
    lignes = []
    for k, res in cache.items():
        if k not in items:
            continue
        jeu, r, tp = items[k]
        res["raison"] = raison(res, finess.candidats(r, tp), r.get("ADR_LIBVOIE_TER"))
        e = res.get("etablissement") or {}
        lignes.append({"num_dau": k, "type_projet": tp, "annee_depot": res["annee_depot"], "etat": res["etat"],
                       "demandeur": res["demandeur"], "famille_demandeur": res["famille_demandeur"], "raison": res["raison"],
                       "finess": res["finess"], "confiance": res["confiance"], "etablissement": e.get("nom", ""),
                       "categorie": e.get("categorie", ""), "ouverture": e.get("ouverture", ""),
                       "exploitant": (res.get("exploitant") or {}).get("nom", ""), "siren_exploitant": res.get("siren_exploitant") or "",
                       "meme_entite": bool(res.get("siren_exploitant")) and res.get("siren_exploitant") == res["siren_demandeur"]})
    if not echantillon:
        CACHE_EXPL.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    if lignes:
        nom = "exploitants_bilan_echantillon.csv" if echantillon else "exploitants_bilan.csv"
        with open(DOSSIER / nom, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(lignes[0]), delimiter=";")
            w.writeheader()
            w.writerows(lignes)
    c = Counter(l["raison"] for l in lignes)
    att = [l for l in lignes if l["raison"] in ATTENDUS]
    trouves = [l for l in lignes if l["raison"] == "exploitant trouvé"]
    bil = {"permis": len(lignes), "par_raison": {r: c[r] for r in RAISONS},
           "attendus_dans_finess": len(att), "trouves": len(trouves),
           "taux_sur_attendus": round(100 * len(trouves) / len(att)) if att else None,
           "par_confiance": dict(Counter(l["confiance"] for l in trouves)),
           "meme_entite": sum(l["meme_entite"] for l in trouves),
           "nouveaux_exploitants": len({l["siren_exploitant"] for l in trouves
                                        if l["siren_exploitant"] and not l["meme_entite"] and l["confiance"] in ("haute", "moyenne")})}
    (DOSSIER / ("bilan_echantillon.json" if echantillon else "bilan.json")).write_text(json.dumps(bil, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(bil, ensure_ascii=False, indent=1))
    return bil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mission", choices=["exploitants", "prospects", "bilan"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--echantillon", type=int, default=None, help="ne traiter que N éléments tirés au hasard (tests)")
    ap.add_argument("--graine", type=int, default=78)
    ap.add_argument("--pause", type=float, default=3.0)
    ap.add_argument("--fournisseur", default=None, help="nvidia, groq ou gemini (défaut : LLM_PROVIDER de .env)")
    ap.add_argument("--modele", default=None, help="modèle (défaut : MODEL_CLASSIFICATION ou modèle du fournisseur)")
    a = ap.parse_args()
    if a.mission == "bilan":
        bilan_exploitants(echantillon=bool(a.echantillon))
    elif a.mission == "exploitants":
        items = [(r["NUM_DAU"], (jeu, r, tp, fam, den)) for jeu, r, tp, fam, den in permis_tiers()]
        items = list({k: v for k, v in items}.items())               # un permis présent dans les deux fichiers : une fois
        print(f"permis médico-sociaux ou sociaux déposés par un tiers : {len(items)}")
        items = echantillonner(items, a.echantillon, a.graine, "exploitants")
        _lancer(items, CACHE_EXPL, analyser_permis, a.limit, a.pause, connexion(a.fournisseur, a.modele))
    else:
        p = FOUILLE / "prospects_candidats.json"
        if not p.exists():
            raise SystemExit("Lancer d'abord : python -X utf8 src\\prospects.py (écrit prospects_candidats.json)")
        cands = json.loads(p.read_text(encoding="utf-8"))
        conn = connexion(a.fournisseur, a.modele)
        print(f"candidats à qualifier (après le pré-filtre du code) : {len(cands)}")
        items = echantillonner([(c["siren"], c) for c in cands], a.echantillon, a.graine, "prospects")
        _lancer(items, cache_prospects(conn["nom"]), analyser_prospect, a.limit, a.pause, conn)


if __name__ == "__main__":
    main()
