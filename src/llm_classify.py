"""Étape 4 : LLM (Groq, API gratuite compatible OpenAI) pour les acteurs que les règles ne tranchent pas.

Clé lue dans l'environnement (GROQ_API_KEY) ou dans .env ; jamais écrite dans le code.
Résultats mis en cache par SIREN (out/llm_cache.json) pour respecter les limites gratuites.
"""
import json, os, time, urllib.request, urllib.error
from settings import ROOT, OUT, FAMILLES

CACHE = OUT / "llm_cache.json"

SYSTEM = (
    "Tu classes des demandeurs de permis de construire (personnes morales, Yvelines) à partir de données "
    "publiques Sitadel/Sirène. Réponds UNIQUEMENT par un objet JSON : "
    '{"famille": <une de ' + ", ".join(FAMILLES) + '>, "confiance": "haute|moyenne|faible", '
    '"indices": [<courtes raisons tirées des champs fournis>]}. '
    'Si les indices ne suffisent pas, réponds famille="non_determine". N\'invente rien : '
    "n'utilise que les champs fournis, ne cherche aucune information sur des personnes physiques.\n"
    "Glossaire (dictionnaire officiel SDES des variables) :\n"
    "- categorie_juridique_CJ / naf_APE : codes Sirène bruts. Tu n'as PAS leur libellé. N'interprète un code "
    "que si tu es certain de son sens ; sinon ne t'en sers pas et dis-le dans indices.\n"
    "- types_residence_declares : déjà décodés en clair ; vide = non renseigné (champ rare, absent avant mai 2022).\n"
    "- logements_locatifs_sociaux_declares : champ « insuffisamment renseigné », rarement corrigé : un 0 ne prouve "
    "pas l'absence de logement social ; un nombre > 0 est un indice mais pas une preuve.\n"
    "- nb_permis_collectif / nb_permis_individuel : type principal des logements créés par permis.\n"
    "- logements_crees_total : somme des logements créés ; des logements individuels groupés peuvent coexister "
    "avec du collectif.\n"
    "Le nom (denomination) est souvent le meilleur indice (ex. mots comme HABITAT, ASSOCIATION, SOLIDAIRE, SOCIAL) "
    "mais un nom peut tromper : indique la confiance « faible » si l'indice est seul."
)

RESIDENCE_LABELS = {
    "1": "résidence pour personnes âgées", "2": "résidence étudiante", "3": "résidence de tourisme",
    "4": "résidence hôtelière à vocation sociale", "5": "résidence sociale",
    "6": "résidence pour handicapés", "7": "autre résidence", "8": "projet mixte",
}


def _read_env():
    """Variables de .env, surchargées par l'environnement du système."""
    vals = {}
    envf = ROOT / ".env"
    if envf.exists():
        for line in envf.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
    for k in [p[c] for p in PROVIDERS.values() for c in ("key", "model")] + ["LLM_PROVIDER"]:
        if os.environ.get(k):
            vals[k] = os.environ[k]
    return vals


# Fournisseurs compatibles avec le format OpenAI (chat/completions + tools)
PROVIDERS = {
    "groq": {"url": "https://api.groq.com/openai/v1/chat/completions",
             "models_url": "https://api.groq.com/openai/v1/models",
             "key": "GROQ_API_KEY", "model": "GROQ_MODEL", "default_model": "openai/gpt-oss-120b"},
    "gemini": {"url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
               "models_url": "https://generativelanguage.googleapis.com/v1beta/openai/models",
               "key": "GEMINI_API_KEY", "model": "GEMINI_MODEL", "default_model": ""},
    "nvidia": {"url": "https://integrate.api.nvidia.com/v1/chat/completions",
               "models_url": "https://integrate.api.nvidia.com/v1/models",
               "key": "NVIDIA_API_KEY", "model": "NVIDIA_MODEL", "default_model": ""},
}


def config():
    vals = _read_env()
    name = (vals.get("LLM_PROVIDER") or "groq").lower()
    if name not in PROVIDERS:
        raise SystemExit(f"LLM_PROVIDER inconnu : {name} (choix : {', '.join(PROVIDERS)})")
    p = PROVIDERS[name]
    return {"provider": name, "url": p["url"], "models_url": p["models_url"],
            "key": vals.get(p["key"], ""), "key_name": p["key"],
            "model": vals.get(p["model"]) or p["default_model"], "model_name": p["model"]}


URL = config()["url"]           # fournisseur choisi dans .env (LLM_PROVIDER)


def _env(role=None):
    """Clé et modèle. role = "classification" ou "exploration" : MODEL_CLASSIFICATION / MODEL_EXPLORATION dans .env
    (ou l'environnement) donnent à chaque agent son propre modèle, chez le même fournisseur."""
    c = config()
    model = c["model"]
    if role:
        cle = f"MODEL_{role.upper()}"
        model = os.environ.get(cle) or _read_env().get(cle) or model
    if c["key"] and not model:
        raise SystemExit(f"{c['model_name']} vide dans .env : lancez `python -X utf8 src\\list_models.py` "
                         f"pour voir les modèles disponibles, puis renseignez-en un.")
    return c["key"], model


def _dossier(a):
    return {
        "denomination": a["denom"], "categorie_juridique_CJ": a["cj"], "naf_APE": a["ape"],
        "nb_permis": a["n_permis"], "annees_depot": sorted(a["annees"]),
        "nb_communes": len(a["communes"]), "logements_crees_total": a["logements"],
        "nb_permis_collectif": a["n_collectif"], "nb_permis_individuel": a["n_individuel"],
        "types_residence_declares": [RESIDENCE_LABELS.get(x, x) for x in sorted(a["residence"])],
        "logements_locatifs_sociaux_declares": a["lgt_social"],
    }


def _call(key, model, dossier):
    body = json.dumps({
        "model": model, "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": json.dumps(dossier, ensure_ascii=False)}],
    }).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "User-Agent": "sitadel-prototype/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(json.loads(r.read())["choices"][0]["message"]["content"])


def classify_ambiguous(acteurs_a_traiter, limit=None, pause=2.5):
    """acteurs_a_traiter : liste d'acteurs agrégés. Retourne {siren: résultat}."""
    key, model = _env()
    if not key:
        raise SystemExit("Clé API manquante : copiez .env.example en .env et collez votre clé.")
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    done = 0
    for a in acteurs_a_traiter:
        s = a["siren"]
        if s in cache:
            continue
        if limit is not None and done >= limit:
            break
        try:
            res = _call(key, model, _dossier(a))
            if res.get("famille") not in FAMILLES:       # liste fermée : sinon non déterminé
                res = {"famille": "non_determine", "confiance": "faible", "indices": ["réponse hors liste"]}
            res["modele"] = model
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
            # Ne pas mettre l'échec en cache : on réessaiera au prochain lancement.
            print(f"  {s}: échec ({e}) -> laissé non_determine")
            time.sleep(pause)
            continue
        cache[s] = res
        done += 1
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(pause)
    return cache
