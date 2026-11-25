"""Agent Groq : le LLM décide lui-même quels outils appeler pour qualifier un demandeur.

Boucle : modèle -> appel(s) d'outil -> résultat -> modèle ... -> outil `conclure` (réponse finale).

Garde-fous (appliqués par le code, pas seulement demandés au modèle) :
- `conclure` est refusé tant que `fiche_entreprise` n'a pas été consultée ;
- nb d'étapes borné ; famille dans une liste fermée ;
- la fiche entreprise est filtrée (aucune personne physique : dirigeants et finances exclus) ;
- la confiance « haute » est plafonnée à « moyenne » si une fragilité est détectée
  (catégorie juridique non vérifiable, NAF du permis venant d'un établissement fermé, divergence de NAF) ;
- trace complète et fragilités sauvegardées pour chaque acteur.
"""
import csv, http.client, json, time, urllib.request, urllib.error, urllib.parse
from settings import ROOT, OUT, FAMILLES, src_entreprise
from llm_classify import URL, _env

TRACES = OUT / "traces"
TRACES.mkdir(exist_ok=True)
CACHE = OUT / "agent_cache.json"
ANNUAIRE_CACHE = OUT / "annuaire_cache.json"
MAX_STEPS = 8


# ---------- référentiels ----------
from referentiels import NAF, CJ   # libellés officiels Insee


# ---------- Annuaire des entreprises (API publique, avec cache) ----------
_ann = json.loads(ANNUAIRE_CACHE.read_text(encoding="utf-8")) if ANNUAIRE_CACHE.exists() else {}


def _annuaire(q):
    """Premier résultat de recherche pour un SIREN ou un SIRET, réduit aux champs d'entreprise."""
    if q in _ann:
        return _ann[q]
    url = "https://recherche-entreprises.api.gouv.fr/search?" + urllib.parse.urlencode({"q": q, "per_page": 1})
    req = urllib.request.Request(url, headers={"User-Agent": "sitadel-prototype/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read()).get("results", [])
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        return {"erreur": str(e)}                        # pas mis en cache : on réessaiera
    time.sleep(0.4)                                      # cadence raisonnable
    if not res:
        out = {"erreur": "introuvable"}
    else:
        x = res[0]
        sg = x.get("siege") or {}
        out = {
            "siren": x.get("siren"), "nom": x.get("nom_complet"), "nature_juridique": x.get("nature_juridique"),
            "naf_actuel": x.get("activite_principale"), "etat": x.get("etat_administratif"),
            "date_creation": x.get("date_creation"), "categorie": x.get("categorie_entreprise"),
            "effectif": x.get("tranche_effectif_salarie"),
            "nb_etablissements": x.get("nombre_etablissements"),
            "nb_etablissements_ouverts": x.get("nombre_etablissements_ouverts"),
            "siege_actuel": {"siret": sg.get("siret"), "naf": sg.get("activite_principale"),
                             "etat": sg.get("etat_administratif")},
            "etabs_trouves": [{k: e.get(k) for k in ("siret", "activite_principale", "etat_administratif",
                                                     "date_creation", "date_fermeture", "est_siege")}
                              for e in (x.get("matching_etablissements") or [])],
        }   # dirigeants, finances, complements : volontairement ignorés
    _ann[q] = out
    ANNUAIRE_CACHE.write_text(json.dumps(_ann, ensure_ascii=False), encoding="utf-8")
    return out


# ---------- outils ----------
def libelle_naf(code):
    code = (code or "").strip()
    return {"code": code, "libelle": NAF.get(code)} if code in NAF else \
        {"code": code, "libelle": None, "note": "code NAF rév. 2 inconnu du référentiel"}


def libelle_cj(code):
    code = (code or "").strip()
    if not CJ:
        return {"code": code, "libelle": None,
                "note": "référentiel des catégories juridiques non fourni : ne pas interpréter ce code de mémoire"}
    return {"code": code, "libelle": CJ.get(code)} if code in CJ else {"code": code, "libelle": None, "note": "code inconnu"}


def _tool_permis(acteurs):
    def permis_du_demandeur(siren):
        a = acteurs.get(siren)
        if not a:
            return {"erreur": "SIREN hors périmètre"}
        return {
            "denomination": a["denom"], "nb_permis_PC": a["n_permis"], "annees_depot": sorted(a["annees"]),
            "nb_communes": len(a["communes"]), "logements_crees_total": a["logements"],
            "surface_locaux_non_residentiels_creee_m2": a.get("surface", 0),
            "nb_permis_collectif": a["n_collectif"], "nb_permis_individuel": a["n_individuel"],
            "types_residence_declares": sorted(a["residence"]),
            "logements_locatifs_sociaux_declares": a["lgt_social"],
            "permis_autorises_pas_remontes_comme_commences": a["n_non_commence"],
        }
    return permis_du_demandeur


def _tool_fiche(acteurs):
    def fiche_entreprise(siren):
        """Entreprise (activité ACTUELLE) + état actuel de chaque établissement cité dans les permis."""
        e = _annuaire(siren)
        if "erreur" in e:
            return {"erreur": e["erreur"]}
        a = acteurs.get(siren, {"etabs": {}})
        etabs, alertes = [], []
        for siret, info in sorted(a["etabs"].items()):
            d = _annuaire(siret) if siret != "?" else {"erreur": "SIRET absent du permis"}
            m = next((x for x in d.get("etabs_trouves", []) if x.get("siret") == siret), None)
            row = {"siret": siret, "naf_dans_permis": info["naf"], "nb_permis": info["n"],
                   "annees_depot": sorted(info["annees"])}
            if m:
                row.update({"etat_actuel": "fermé" if m["etat_administratif"] == "F" else "ouvert",
                            "date_creation": m["date_creation"], "date_fermeture": m["date_fermeture"]})
                if m["etat_administratif"] == "F":
                    alertes.append(f"SIRET {siret} (permis {','.join(sorted(info['annees']))}) fermé"
                                   f"{' le ' + m['date_fermeture'] if m['date_fermeture'] else ''} : "
                                   f"le NAF {info['naf']} du permis vient d'un établissement fermé")
            etabs.append(row)
        nafs = {x["naf_dans_permis"] for x in etabs if x["naf_dans_permis"]}
        if e.get("naf_actuel") and nafs and e["naf_actuel"] not in nafs:
            alertes.append(f"NAF du permis {sorted(nafs)} différent du NAF actuel de l'entreprise {e['naf_actuel']}")
        return {"entreprise": e, "etablissements_des_permis": etabs, "alertes": alertes,
                "aide": "Le NAF du permis est celui d'un ÉTABLISSEMENT (possiblement fermé) ; "
                        "naf_actuel est celui de l'ENTREPRISE aujourd'hui.",
                "source": src_entreprise(siren)}
    return fiche_entreprise


TOOLS = [
    {"type": "function", "function": {"name": "libelle_naf", "description": "Libellé officiel d'un code NAF rév. 2 (ex. 68.20A).",
        "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}},
    {"type": "function", "function": {"name": "libelle_cj", "description": "Libellé officiel d'une catégorie juridique Sirène (4 chiffres).",
        "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}},
    {"type": "function", "function": {"name": "permis_du_demandeur", "description": "Profil agrégé des permis de construire déposés par ce SIREN dans les Yvelines.",
        "parameters": {"type": "object", "properties": {"siren": {"type": "string"}}, "required": ["siren"]}}},
    {"type": "function", "function": {"name": "fiche_entreprise", "description": "OBLIGATOIRE avant de conclure. Fiche publique : activité ACTUELLE de l'entreprise, forme juridique, taille, et état (ouvert/fermé) des établissements cités dans les permis, avec alertes.",
        "parameters": {"type": "object", "properties": {"siren": {"type": "string"}}, "required": ["siren"]}}},
    {"type": "function", "function": {"name": "conclure", "description": "Réponse finale, à appeler une seule fois, après fiche_entreprise.",
        "parameters": {"type": "object", "properties": {
            "famille": {"type": "string", "enum": FAMILLES},
            "confiance": {"type": "string", "enum": ["haute", "moyenne", "faible"]},
            "indices": {"type": "array", "items": {"type": "string"},
                        "description": "Preuves : chacune cite l'outil ou le champ dont elle vient."},
            "limites": {"type": "string", "description": "Ce qui reste incertain ou manquant."}},
            "required": ["famille", "confiance", "indices", "limites"]}}},
]

SYSTEM = (
    "Tu es un agent d'analyse pour Buddimm (direction immobilière externalisée, clients : associations médico-sociales, "
    "ESS, bailleurs sociaux). Tâche : dire à quelle famille appartient un demandeur de permis de construire "
    "(personne morale, Yvelines), parmi : " + ", ".join(FAMILLES) + ". "
    "Familles : bailleur_social (OPH, SA de HLM, coopérative HLM, SEM de logement social), promoteur (construit "
    "pour vendre, y compris SCI de construction-vente et supports juridiques de programmes), "
    "fonciere_investisseur (détient/loue du patrimoine : foncière, SCI, marchand de biens, SCPI), association_ess "
    "(association, fondation, mutuelle, ESS, structure à vocation solidaire), exploitant_sante_social (opérateur "
    "privé hors association : santé, médico-social, hébergement social, petite enfance), collectivite_public, "
    "copropriete (syndicat de copropriétaires), entreprise_autre, non_determine.\n"
    "Méthode : 1) permis_du_demandeur ; 2) fiche_entreprise (OBLIGATOIRE, le système refuse sinon de conclure) ; "
    "3) libelle_naf / libelle_cj pour les codes qui comptent ; 4) conclure.\n"
    "RÈGLES SUR LES SOURCES :\n"
    "- Le NAF et le SIRET des permis viennent de Sirène pour un ÉTABLISSEMENT, qui peut être FERMÉ depuis des années : "
    "ce n'est PAS l'activité actuelle de la structure. Donne la priorité au naf_actuel de l'entreprise (fiche_entreprise) "
    "et traite le NAF du permis comme un indice historique, d'autant plus faible que l'établissement est fermé.\n"
    "- Ne te fie JAMAIS à ta mémoire pour le sens d'un code : utilise les outils. Si un référentiel est "
    "indisponible, dis-le dans `limites`.\n"
    "- Une dénomination seule est un indice faible. Les champs de logements sociaux et de résidence sont mal "
    "renseignés : un 0 ne prouve rien.\n"
    "- Ne cherche aucune information sur des personnes physiques.\n"
    "- Chaque indice commence par sa source : le nom d'un outil, ou « dénomination » pour le seul nom fourni. "
    "Si tu utilises une connaissance générale qui ne vient d'aucun outil, l'indice DOIT commencer par "
    "« connaissance du modèle (non vérifiée) : ».\n"
    "- Si les preuves ne suffisent pas, conclus non_determine : c'est acceptable. N'écris « haute » que si plusieurs "
    "sources indépendantes concordent."
)


def _chat(key, model, messages, tools=None, url=None):
    body = json.dumps({"model": model, "temperature": 0, "messages": messages,
                       "tools": tools or TOOLS, "tool_choice": "auto"}).encode()
    req = urllib.request.Request(url or URL, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "sitadel-prototype/0.1"})
    for attempt in range(5):                       # limites gratuites Groq : on attend et on réessaie
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read())["choices"][0]["message"]
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504) or attempt == 4:
                raise
            wait = float(e.headers.get("retry-after") or 10 * (attempt + 1))
            print(f"    {e.code} (limite ou indisponibilité du fournisseur), attente {wait:.0f}s", flush=True)
            time.sleep(min(wait, 90))
        except (TimeoutError, OSError, http.client.HTTPException) as e:   # délai dépassé, connexion coupée
            if attempt == 4:
                raise
            print(f"    {type(e).__name__} (réseau), nouvel essai dans {15 * (attempt + 1)}s", flush=True)
            time.sleep(15 * (attempt + 1))


def _fragilites(trace, fiche_ok):
    """Fragilités détectées par le CODE (pas par le modèle), à partir des sorties d'outils."""
    f = []
    if not CJ:
        f.append("catégorie juridique non vérifiable (référentiel absent)")
    if not fiche_ok:
        f.append("fiche entreprise non consultée")
    for t in trace:
        for r in t.get("resultats", []):
            if r["outil"] == "fiche_entreprise":
                f.extend(r["sortie"].get("alertes", []))
    return f


def fragilites_indices(indices):
    """Chaque indice doit citer sa source (outil ou dénomination) ; sinon c'est une fragilité."""
    sources = ("libelle_naf", "libelle_cj", "permis_du_demandeur", "fiche_entreprise", "dénomination", "denomination")
    f = []
    for ind in indices:
        low = ind.strip().lower()
        if low.startswith("connaissance du modèle"):
            f.append(f"indice issu de la mémoire du modèle, non vérifié : {ind[:120]}")
        elif not low.startswith(sources):
            f.append(f"indice sans source d'outil : {ind[:120]}")
    return f


def conclusion(final, trace, fiche_ok, model, etapes):
    """Applique les garde-fous du code à une conclusion, quel que soit le modèle qui l'a produite."""
    fam, lim = final.get("famille"), final.get("limites", "")
    if fam not in FAMILLES:
        fam, lim = "non_determine", lim + " [famille hors liste -> non_determine]"
    conf = final.get("confiance", "faible")
    frag = _fragilites(trace, fiche_ok) + fragilites_indices(final.get("indices", []))
    if frag and conf == "haute":
        conf = "moyenne"
        lim += " [confiance plafonnée à moyenne : fragilités détectées]"
    return {"famille": fam, "confiance": conf, "indices": final.get("indices", []),
            "limites": lim, "fragilites": frag, "etapes": etapes, "modele": model}


def analyser(acteur, acteurs, key, model):
    """Fait tourner l'agent sur un acteur. Retourne (résultat, trace)."""
    handlers = {"libelle_naf": libelle_naf, "libelle_cj": libelle_cj,
                "permis_du_demandeur": _tool_permis(acteurs), "fiche_entreprise": _tool_fiche(acteurs)}
    s = acteur["siren"]
    # Pré-appels faits par le CODE (toujours les mêmes, inutile de les faire demander au modèle) : économise 3 à 4
    # échanges par acteur, donc du quota. Ils sont tracés comme des appels d'outils ordinaires.
    pre = {"permis_du_demandeur": handlers["permis_du_demandeur"](s), "fiche_entreprise": handlers["fiche_entreprise"](s)}
    codes_naf = {acteur["ape"]} | {(pre["fiche_entreprise"].get("entreprise") or {}).get("naf_actuel")}
    pre["libelle_naf"] = [libelle_naf(c) for c in sorted(x for x in codes_naf if x)]
    pre["libelle_cj"] = libelle_cj(acteur["cj"])
    trace = [{"etape": "pre", "texte": "appels faits par le code avant le modèle",
              "appels": [{"outil": k, "args": s} for k in pre],
              "resultats": [{"outil": k, "sortie": v} for k, v in pre.items()]}]
    fiche_ok = "erreur" not in pre["fiche_entreprise"]
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": json.dumps({
                    "siren": s, "denomination": acteur["denom"], "cj": acteur["cj"],
                    "naf_dans_permis": acteur["ape"],
                    "etablissements_dans_permis": [{"siret": k, "naf": v["naf"], "nb_permis": v["n"]}
                                                   for k, v in acteur["etabs"].items()],
                    "resultats_outils_deja_obtenus": pre,
                    "consigne": "Ces résultats viennent des outils permis_du_demandeur, fiche_entreprise, libelle_naf et "
                                "libelle_cj : cite-les comme tels. Appelle un autre outil seulement si nécessaire, puis conclus."},
                    ensure_ascii=False)[:9000]}]
    for step in range(MAX_STEPS):
        msg = _chat(key, model, messages)
        calls = msg.get("tool_calls") or []
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls") and v})
        trace.append({"etape": step, "texte": msg.get("content"), "appels": [
            {"outil": c["function"]["name"], "args": c["function"]["arguments"]} for c in calls]})
        if not calls:
            messages.append({"role": "user", "content": "Conclus maintenant avec l'outil `conclure`."})
            continue
        final = None
        for c in sorted(calls, key=lambda c: c["function"]["name"] == "conclure"):   # conclure en dernier
            name = c["function"]["name"]
            try:
                args = json.loads(c["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            if name == "conclure":
                if not fiche_ok:                                   # garde-fou : fiche obligatoire
                    out = {"erreur": "Refusé : appelle d'abord fiche_entreprise, puis conclus."}
                    trace[-1].setdefault("resultats", []).append({"outil": name, "sortie": out})
                    messages.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(out, ensure_ascii=False)})
                    continue
                final = args
                continue
            fn = handlers.get(name)
            out = fn(**args) if fn else {"erreur": f"outil inconnu {name}"}
            if name == "fiche_entreprise" and "erreur" not in out:
                fiche_ok = True
            trace[-1].setdefault("resultats", []).append({"outil": name, "sortie": out})
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(out, ensure_ascii=False)})
        if final is not None:
            fam = final.get("famille")
            lim = final.get("limites", "")
            if fam not in FAMILLES:
                fam, lim = "non_determine", lim + " [famille hors liste -> non_determine]"
            conf = final.get("confiance", "faible")
            frag = _fragilites(trace, fiche_ok) + fragilites_indices(final.get("indices", []))
            if frag and conf == "haute":                           # plafond de confiance imposé par le code
                conf = "moyenne"
                lim += " [confiance plafonnée à moyenne : fragilités détectées]"
            return {"famille": fam, "confiance": conf, "indices": final.get("indices", []),
                    "limites": lim, "fragilites": frag, "etapes": step + 1, "modele": model}, trace
    return {"famille": "non_determine", "confiance": "faible", "indices": [],
            "limites": f"pas de conclusion en {MAX_STEPS} étapes", "fragilites": _fragilites(trace, fiche_ok),
            "etapes": MAX_STEPS, "modele": model}, trace


def run_batch(a_traiter, acteurs, limit=None, pause=3.0):
    key, model = _env("classification")
    if not key:
        raise SystemExit("Clé API manquante dans .env (GROQ_API_KEY ou GEMINI_API_KEY selon LLM_PROVIDER).")
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    done = 0
    for a in a_traiter:
        s = a["siren"]
        if s in cache:
            continue
        if limit is not None and done >= limit:
            break
        try:
            res, trace = analyser(a, acteurs, key, model)
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, KeyError,
                TimeoutError, OSError, http.client.HTTPException) as e:
            print(f"  {s} {a['denom']}: échec ({type(e).__name__}: {e}), sera retenté au prochain lancement", flush=True)
            time.sleep(pause)
            continue
        cache[s] = res
        (TRACES / f"{s}.json").write_text(json.dumps(trace, ensure_ascii=False, indent=1), encoding="utf-8")
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {s} {a['denom'][:40]:40s} -> {res['famille']} ({res['confiance']}, {res['etapes']} étapes)", flush=True)
        done += 1
        time.sleep(pause)
    return cache
