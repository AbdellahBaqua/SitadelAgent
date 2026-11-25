r"""Agent explorateur Groq : il interroge lui-même les données, propose des patterns et les note.

  python -X utf8 src\explore.py                     # tous les thèmes
  python -X utf8 src\explore.py --theme medico_social --steps 12

Groq dispose d'outils de requête en lecture seule (pas d'exécution de code). Il note ses constats dans
out/insights_agent.md (lisible) et out/insights_agent.jsonl (machine). Garde-fou : une note n'est acceptée que
si au moins une requête a été faite avant, et le code joint automatiquement les requêtes qui la précèdent.
"""
import argparse, itertools, json, re, time, urllib.request, urllib.error
from collections import Counter, defaultdict
from datetime import datetime
import load, donnees
from patterns import familles
from referentiels import CJ, NAF
from settings import ROOT, OUT, FAMILLES, src_entreprise, DATASET, DICO
from llm_classify import URL, _env

LOCAUX = DATASET == "locaux"
VOL = "surface_m2" if LOCAUX else "logements"      # mesure de volume : m² de locaux créés, ou logements créés

NOTES_MD = OUT / "insights_agent.md"
NOTES_JL = OUT / "insights_agent.jsonl"
TRACES = OUT / "explore_traces"
TRACES.mkdir(exist_ok=True)

# Libellés des modalités (dictionnaire SDES des variables)
LABELS = {
    "ETAT_DAU": {"2": "autorisé", "4": "annulé", "5": "commencé", "6": "terminé"},
    "RESIDENCE": {"1": "personnes âgées", "2": "étudiants", "3": "tourisme", "4": "hôtelière sociale", "5": "sociale",
                  "6": "handicapés", "7": "autre", "8": "mixte", "9": "non rempli"},
    "TYPE_PRINCIP_LOGTS_CREES": {"1": "1 logement individuel", "2": "plusieurs individuels", "3": "collectif hors résidence", "4": "résidence"},
    "NATURE_PROJET_COMPLETEE": {"1": "nouvelle construction", "2": "transformation sans extension", "3": "transformation avec extension",
                                "4": "transformation avec diminution", "5": "extension sans transformation", "6": "diminution sans transformation"},
    "TYPE_TRANSFO_PRINCIPAL": {"1": "locaux -> logements", "2": "transformation de logements", "3": "logements -> locaux", "4": "transformation de locaux"},
    "TYPE_PRINCIP_LOCAUX_TRANSFORMES": {"1": "logements", "3": "bureaux", "4": "commerce", "6": "industrie", "7": "agriculture",
                                        "8": "entrepôt", "9": "service public / intérêt collectif"},
    "UTILISATION": {"1": "occupation personnelle", "2": "vente", "3": "location", "4": "vente-location", "5": "non rempli"},
    "DESTINATION_PRINCIPALE": {"1": "logements", "2": "non résidentiel"},
    "ZONE_OP": {"1": "lotissement", "2": "ZAC", "3": "AFU", "4": "hors zone / ne sait pas"},
}
COLS = ["famille", "AN_DEPOT", "COMM", "ADR_LOCALITE_TER", "ETAT_DAU", "RESIDENCE", "TYPE_PRINCIP_LOGTS_CREES",
        "NATURE_PROJET_COMPLETEE", "TYPE_TRANSFO_PRINCIPAL", "TYPE_PRINCIP_LOCAUX_TRANSFORMES", "UTILISATION",
        "DESTINATION_PRINCIPALE", "ZONE_OP", "CJ_DEM", "APE_DEM", "SIREN_DEM", "DENOM_DEM"]

# Fichier « locaux non résidentiels » : codes propres (dictionnaire SDES des permis de construire des locaux)
DEST_LOCAUX = {"1": "habitation", "2": "hôtels", "3": "bureaux", "4": "commerce", "6": "industrie", "7": "agriculture",
               "8": "entrepôt", "9": "service public / intérêt collectif"}
SURF_DEST = {"HEB": "hôtels / hébergement", "BUR": "bureaux", "COM": "commerce", "IND": "industrie",
             "AGR": "agriculture", "ENT": "entrepôt", "PUB": "service public / intérêt collectif"}
if LOCAUX:
    LABELS["DESTINATION_PRINCIPALE"] = DEST_LOCAUX
    LABELS["TYPE_PRINCIP_LOCAUX_TRANSFORMES"] = DEST_LOCAUX
    LABELS["TYPE_SERVICE_PUBLIC"] = {"1": "transport", "2": "enseignement et recherche", "3": "santé", "4": "action sociale",
                                     "5": "ouvrage spécial", "6": "culture et loisir", "7": "non rempli", "8": "plusieurs types"}
    COLS = ["famille", "AN_DEPOT", "COMM", "ADR_LOCALITE_TER", "ETAT_DAU", "DESTINATION_PRINCIPALE", "DEST_SURF_MAX",
            "TYPE_SERVICE_PUBLIC", "NATURE_PROJET_COMPLETEE", "TYPE_TRANSFO_PRINCIPAL", "TYPE_PRINCIP_LOCAUX_TRANSFORMES",
            "ZONE_OP", "CJ_DEM", "APE_DEM", "SIREN_DEM", "DENOM_DEM"]

THEMES_LOCAUX = {
    "acteurs": "Qui construit régulièrement des locaux ? Profils par famille (surfaces, destinations, nombre de communes, régularité).",
    "geographie": "Où se concentrent les surfaces créées selon les destinations (entrepôts, bureaux, commerce, équipements) et les familles ?",
    "medico_social": "Équipements de santé et d'action sociale (TYPE_SERVICE_PUBLIC 3 et 4), hébergement : qui les porte (associations, collectivités, exploitants privés, bailleurs), où, quand, quelle taille.",
    "transformations": "Transformations et changements de destination de locaux : qui, quelles destinations d'origine et d'arrivée, tendance.",
    "dynamique": "Tendances dans le temps par destination et par famille ; permis annulés ; autorisés jamais commencés.",
    "libre": "Explore librement et propose ce qui te semble le plus utile pour Buddimm, en dehors des thèmes évidents.",
}

THEMES = {
    "acteurs": "Qui construit régulièrement ? Quels profils par famille (taille des projets, nombre de communes, régularité dans le temps) ?",
    "geographie": "Où se concentrent les projets selon les familles ? Communes où bailleurs sociaux, associations ou collectivités sont actifs ; communes dominées par un seul acteur.",
    "medico_social": "Résidences (personnes âgées, handicapés, sociales…), associations, ESS et exploitants santé/social : qui, où, quand, quelle taille.",
    "transformations": "Reconversions de locaux (bureaux, équipements publics, entrepôts…) en logements : qui les porte, où, tendance.",
    "dynamique": "Tendances dans le temps : dépôts par famille et par année, permis annulés, permis autorisés jamais commencés, acteurs en montée.",
    "libre": "Explore librement et propose ce qui te semble le plus utile pour Buddimm, en dehors des thèmes évidents.",
}


# ---------- données ----------
def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


if LOCAUX:
    THEMES = THEMES_LOCAUX


def _dest_surf_max(r):
    """Destination qui reçoit le plus de surface (créée + issue de transformation) ; 'aucune' si tout est à 0."""
    best, val = "aucune", 0
    for k, lib in SURF_DEST.items():
        v = _int(r.get(f"SURF_{k}_CREEE")) + _int(r.get(f"SURF_{k}_ISSUE_TRANSFO"))
        if v > val:
            best, val = lib, v
    return best


def _charger():
    """(Re)charge les permis du fichier courant ; appelé au démarrage et après un rafraîchissement des données."""
    global PERMIS, ACTEURS, FAM, ROWS
    PERMIS = [r for r in load.read_permis() if load.in_scope(r)]
    ACTEURS = load.aggregate(PERMIS)
    FAM = {s: f for s, (f, _) in familles(ACTEURS).items()}
    ROWS = [{**{c: r.get(c, "") for c in COLS if c not in ("famille", "DEST_SURF_MAX")}, "famille": FAM[r["SIREN_DEM"]],
             **({"DEST_SURF_MAX": _dest_surf_max(r)} if LOCAUX else {}),
             "_vol": _int(r.get("SURF_LOC_CREEE") if LOCAUX else r.get("NB_LGT_TOT_CREES")),
             "_chambres": _int(r.get("NB_CHAMBRES")),
             "_aut": r["DATE_REELLE_AUTORISATION"], "_num": r["NUM_DAU"]}
            for r in PERMIS]


_charger()


# ---------- outils de données (fetch_yvelines.ps1 porté en Python : src/donnees.py) ----------
def fraicheur_donnees():
    return donnees.fraicheur()


def rafraichir_donnees(jeu=None, simulation=True):
    """Simulation par défaut. Remplacement réel seulement si un millésime plus récent est publié."""
    jeu = jeu or DATASET
    if jeu not in ("logements", "locaux", "tous"):
        return {"erreur": "jeu : logements, locaux ou tous"}
    if not simulation:
        fr = donnees.fraicheur()
        concernes = list(donnees.JEUX) if jeu == "tous" else [jeu]
        if all(fr[j].get("a_jour") for j in concernes):
            return {"refus": "les données locales sont déjà au dernier millésime publié : remplacement inutile",
                    "fraicheur": {j: fr[j]["distant"].get("millesime") for j in concernes}}
    res = donnees.rafraichir(jeu, simulation=simulation)
    ok = res.get("ok") if jeu != "tous" else all(r.get("ok") for r in res.values())
    if ok and not simulation and jeu in (DATASET, "tous"):
        _charger()
        res = {"resultat": res, "note": "données rechargées ; familles recalculées par les règles (l'agent de "
                                        "classification n'est pas relancé automatiquement)"}
    return res


def _label(col, v):
    if col in LABELS and v in LABELS[col]:
        return f"{v} ({LABELS[col][v]})"
    if col == "CJ_DEM" and v in CJ:
        return f"{v} ({CJ[v]})"
    if col == "APE_DEM" and v in NAF:
        return f"{v} ({NAF[v]})"
    return v or "(vide)"


def _filtrer(filtres):
    filtres = dict(filtres or {})
    amin, amax = _int(filtres.pop("AN_DEPOT_min", 0)), _int(filtres.pop("AN_DEPOT_max", 9999)) or 9999
    bad = [k for k in filtres if k not in COLS]
    if bad:
        return None, {"erreur": f"colonnes inconnues {bad}", "colonnes_autorisees": COLS + ["AN_DEPOT_min", "AN_DEPOT_max"]}
    out = []
    for r in ROWS:
        if not (amin <= _int(r["AN_DEPOT"]) <= amax):
            continue
        ok = True
        for k, v in filtres.items():
            vals = v if isinstance(v, list) else [v]
            # accepte « 3 » comme « 3 (santé) » : le modèle recopie souvent la valeur affichée avec son libellé
            if str(r[k]) not in [str(x).split(" (")[0].strip() for x in vals]:
                ok = False
                break
        if ok:
            out.append(r)
    return out, None


# ---------- outils ----------
def apercu():
    communes = ["2026 est une année partielle", "un permis modificatif n'a pas de ligne propre",
                "~15 % des ouvertures de chantier et ~1/3 des achèvements ne remontent jamais",
                "APE_DEM = NAF de l'établissement du permis, possiblement fermé"]
    if LOCAUX:
        propres = ["surface_m2 = SURF_LOC_CREEE, surface de plancher de locaux non résidentiels créée",
                   "DEST_SURF_MAX = destination qui reçoit le plus de surface (calculée par le code à partir des SURF_*)",
                   "DESTINATION_PRINCIPALE est codée par le SDES (introduite en mai 2022) ; TYPE_SERVICE_PUBLIC vient du formulaire et est souvent 'non rempli'",
                   "un même permis peut aussi créer des logements : il figure alors aussi dans le fichier logements"]
        perim = "PC des Yvelines (78) créant des locaux non résidentiels, déposés par des personnes morales, extraction SDES/Sitadel"
    else:
        propres = ["RESIDENCE est rempli sur une petite minorité de permis (souvent 'non rempli') ; les drapeaux RES_* n'existent que depuis mai 2022",
                   "NATURE_PROJET_COMPLETEE et TYPE_TRANSFO_* sont dits 'introduits en mai 2022' mais sont renseignés dès 2012 dans le fichier (recodage SDES probable)"]
        perim = "PC des Yvelines (78) créant des logements, déposés par des personnes morales, extraction SDES/Sitadel"
    return {
        "perimetre": perim,
        "nb_permis": len(ROWS), "nb_demandeurs": len(ACTEURS),
        "annees_depot": dict(sorted(Counter(r["AN_DEPOT"] for r in ROWS).items())),
        "familles_demandeurs": dict(Counter(FAM.values()).most_common()),
        "colonnes_interrogeables": COLS,
        "mesures": ["permis", VOL, "acteurs"],
        "remarques": communes + propres,
    }


def compter(group_by, filtres=None, mesure="permis", top=15):
    group_by = group_by if isinstance(group_by, list) else [group_by]
    if not group_by or len(group_by) > 3 or any(c not in COLS for c in group_by):
        return {"erreur": "group_by : 1 à 3 colonnes parmi la liste", "colonnes_autorisees": COLS}
    rows, err = _filtrer(filtres)
    if err:
        return err
    agg = defaultdict(lambda: {"permis": 0, VOL: 0, "acteurs": set()})
    for r in rows:
        k = tuple(_label(c, r[c]) for c in group_by)
        agg[k]["permis"] += 1
        agg[k][VOL] += r["_vol"]
        agg[k]["acteurs"].add(r["SIREN_DEM"])
    mesure = mesure if mesure in ("permis", VOL, "acteurs") else "permis"
    key = (lambda kv: len(kv[1]["acteurs"])) if mesure == "acteurs" else (lambda kv: kv[1][mesure])
    items = sorted(agg.items(), key=key, reverse=True)
    top = max(1, min(_int(top) or 15, 25))
    return {"filtres": filtres or {}, "nb_permis_filtres": len(rows), "nb_groupes": len(items),
            "resultats": [{**dict(zip(group_by, k)), "permis": v["permis"], VOL: v[VOL],
                           "acteurs": len(v["acteurs"])} for k, v in items[:top]]}


def profil_acteur(siren):
    a = ACTEURS.get(str(siren))
    if not a:
        return {"erreur": "SIREN hors périmètre"}
    rs = sorted((r for r in ROWS if r["SIREN_DEM"] == a["siren"]), key=lambda r: r["AN_DEPOT"])

    def detail(r):
        d = {"num": r["_num"], "annee": r["AN_DEPOT"], "commune": r["ADR_LOCALITE_TER"], VOL: r["_vol"],
             "etat": _label("ETAT_DAU", r["ETAT_DAU"])}
        if LOCAUX:
            d.update({"destination": r["DEST_SURF_MAX"], "service_public": _label("TYPE_SERVICE_PUBLIC", r["TYPE_SERVICE_PUBLIC"]),
                      "chambres": r["_chambres"]})
        else:
            d.update({"type": _label("TYPE_PRINCIP_LOGTS_CREES", r["TYPE_PRINCIP_LOGTS_CREES"]),
                      "residence": _label("RESIDENCE", r["RESIDENCE"])})
        return d
    return {"denomination": a["denom"], "famille": FAM[a["siren"]], "cj": _label("CJ_DEM", a["cj"]),
            "nb_permis": a["n_permis"], VOL: sum(r["_vol"] for r in rs), "source": src_entreprise(a["siren"]),
            "permis": [detail(r) for r in rs[:20]], "tronque": len(rs) > 20}


_DICO = None
def lire_dictionnaire(variable):
    global _DICO
    if _DICO is None:
        _DICO, cur = {}, None
        p = DICO
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"^([A-Z][A-Z0-9_]+) \| ", line)
            if m:
                cur = m.group(1)
                _DICO[cur] = line
            elif cur:
                _DICO[cur] += "\n" + line
    v = (variable or "").strip().upper()
    return {"variable": v, "definition": _DICO.get(v, "variable inconnue du dictionnaire")[:1200]}


TOOLS = [
    {"type": "function", "function": {"name": "apercu", "description": "Vue d'ensemble : volumes, années, familles, colonnes interrogeables, limites des données.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "compter", "description": f"Agrège les permis : group_by (1 à 3 colonnes), filtres (colonne -> valeur ou liste ; AN_DEPOT_min / AN_DEPOT_max), mesure de tri (permis, {VOL}, acteurs). Renvoie les plus gros groupes avec les trois mesures.",
        "parameters": {"type": "object", "properties": {
            "group_by": {"type": "array", "items": {"type": "string"}},
            "filtres": {"type": "object", "additionalProperties": True,
                        "description": "ex. {\"famille\": \"bailleur_social\", \"AN_DEPOT_min\": 2022}"},
            "mesure": {"type": "string", "enum": ["permis", VOL, "acteurs"]},
            "top": {"type": "integer"}}, "required": ["group_by"]}}},
    {"type": "function", "function": {"name": "profil_acteur", "description": "Liste des permis d'un demandeur (SIREN) : années, communes, logements, état, type.",
        "parameters": {"type": "object", "properties": {"siren": {"type": "string"}}, "required": ["siren"]}}},
    {"type": "function", "function": {"name": "lire_dictionnaire", "description": "Définition officielle d'une variable et de ses modalités (dictionnaire SDES).",
        "parameters": {"type": "object", "properties": {"variable": {"type": "string"}}, "required": ["variable"]}}},
    {"type": "function", "function": {"name": "fraicheur_donnees", "description": "Compare le millésime des fichiers locaux au dernier millésime publié par le SDES (logements et locaux).",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "rafraichir_donnees", "description": "Télécharge l'extraction Yvelines depuis l'API du SDES et la contrôle. Par défaut simulation=true : compare au fichier local sans rien remplacer. simulation=false ne remplace le fichier que si un millésime plus récent est publié.",
        "parameters": {"type": "object", "properties": {"jeu": {"type": "string", "enum": ["logements", "locaux", "tous"]},
                                                         "simulation": {"type": "boolean"}}}}},
    {"type": "function", "function": {"name": "noter", "description": "Enregistre un constat. Uniquement après avoir vérifié avec compter/profil_acteur.",
        "parameters": {"type": "object", "properties": {
            "titre": {"type": "string"},
            "constat": {"type": "string", "description": "Ce que montrent les chiffres, avec les chiffres."},
            "interet_buddimm": {"type": "string", "description": "Pourquoi c'est utile pour Buddimm (prospection, conseil, veille)."},
            "fiabilite": {"type": "string", "enum": ["établi", "fragile", "hypothèse"]},
            "limites": {"type": "string"},
            "a_creuser": {"type": "string"}},
            "required": ["titre", "constat", "interet_buddimm", "fiabilite", "limites"]}}},
    {"type": "function", "function": {"name": "terminer", "description": "Termine l'exploration du thème.",
        "parameters": {"type": "object", "properties": {"resume": {"type": "string"}}, "required": ["resume"]}}},
]

SYSTEM = (
    "Tu es un analyste pour Buddimm, direction immobilière externalisée qui accompagne associations médico-sociales, "
    "structures de l'ESS et bailleurs sociaux dans leurs projets immobiliers. Tu explores la base des permis de "
    "construire (Sitadel) des Yvelines déposés par des personnes morales, pour trouver des patterns exploitables "
    "(prospection, conseil, veille). "
    + ("Fichier étudié : permis créant des LOCAUX NON RÉSIDENTIELS (bureaux, commerces, entrepôts, équipements de "
       "santé et d'action sociale…) ; la mesure de volume est la surface créée en m² (surface_m2). "
       if LOCAUX else "Fichier étudié : permis créant des LOGEMENTS ; la mesure de volume est le nombre de logements. ")
    + "Familles de demandeurs : " + ", ".join(FAMILLES) + ".\n"
    "Données : tu peux vérifier leur fraîcheur (fraicheur_donnees) ; ne demande un rafraîchissement réel que si un millésime plus récent est publié. "
    "Méthode : formule une hypothèse, VÉRIFIE-LA avec compter / profil_acteur, puis note-la avec `noter` "
    "(2 à 4 notes par thème, des chiffres précis dans chaque constat). Termine avec `terminer`.\n"
    "Périmètre : uniquement les permis dont les travaux sont situés dans les Yvelines (78) ; ne tire aucune conclusion sur d'autres territoires et n'apporte pas de connaissance extérieure présentée comme un fait (si tu en mentionnes une, signale-la comme hypothèse). "
    "Règles : n'invente aucun chiffre (seulement ceux renvoyés par les outils) ; chaque pourcentage cite dans la même phrase son numérateur et son dénominateur ; distingue établi / fragile / hypothèse ; "
    "tiens compte des limites données par apercu ; n'utilise ni ne recherche aucune information sur des personnes "
    "physiques ; ne propose aucune prise de contact avec les demandeurs. Préfère les constats surprenants ou "
    "actionnables aux évidences."
)


TOOLS_FIN = [t for t in TOOLS if t["function"]["name"] in ("noter", "terminer")]


class AppelInvalide(Exception):
    """Groq a rejeté l'appel d'outil généré par le modèle (400 tool_use_failed)."""


def _compact(messages, garder=4, taille=400):
    """Quota gratuit = 8 000 jetons/minute : on raccourcit les anciens résultats d'outils déjà lus."""
    tools_idx = [i for i, m in enumerate(messages) if m.get("role") == "tool"]
    out = [dict(m) for m in messages]
    for i in tools_idx[:-garder]:
        if len(out[i]["content"]) > taille:
            out[i]["content"] = out[i]["content"][:taille] + "…[résultat ancien tronqué]"
    return out


def _chat(key, model, messages, tools=None):
    body = json.dumps({"model": model, "temperature": 0.3, "messages": _compact(messages),
                       "tools": tools or TOOLS, "tool_choice": "auto"}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "sitadel-prototype/0.1"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())["choices"][0]["message"]
        except urllib.error.HTTPError as e:
            txt = e.read().decode(errors="replace")
            if e.code == 400 and "tool_use_failed" in txt:
                raise AppelInvalide(txt[:300])
            if e.code not in (429, 502, 503, 504) or attempt == 5:
                print(f"    erreur API {e.code} : {txt[:300]}", flush=True)
                raise
            wait = float(e.headers.get("retry-after") or 10 * (attempt + 1))
            print(f"    {e.code} (limite ou indisponibilité du fournisseur), attente {wait:.0f}s", flush=True)
            time.sleep(min(wait, 120))
        except (TimeoutError, OSError) as e:                       # délai dépassé, connexion coupée
            if attempt == 5:
                raise
            print(f"    {type(e).__name__} (réseau), nouvel essai dans {15 * (attempt + 1)}s", flush=True)
            time.sleep(15 * (attempt + 1))


# ---------- garde-fou : chaque chiffre d'une note doit venir d'un résultat d'outil ----------
NUM_RE = re.compile(r"\d{1,3}(?:[   ]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?")
CHAMPS_NOTE = ("titre", "constat", "interet_buddimm", "limites", "a_creuser")
SEUIL_PETITS = 10          # 0..10 ignorés (« 2 étapes », « 3 permis »… trop de fausses alertes)


def _nombres(texte):
    """[(valeur, est_pourcentage, texte_brut)] trouvés dans un texte (« 61 394 », « 10,6 % »…)."""
    out = []
    for m in NUM_RE.finditer(texte or ""):
        brut = m.group()
        try:
            val = float(re.sub(r"[   ]", "", brut).replace(",", "."))
        except ValueError:
            continue
        pct = (texte[m.end():].lstrip("   ")[:1] == "%")
        out.append((val, pct, brut))
    return out


def _totaux(sorties):
    """Dénominateurs plausibles d'un pourcentage : totaux de colonnes et volumes filtrés."""
    t = set()
    for s in sorties:
        if isinstance(s, dict) and isinstance(s.get("resultats"), list):
            for col in ("permis", VOL, "acteurs"):
                t.add(float(sum(r.get(col, 0) for r in s["resultats"] if isinstance(r, dict))))
            for k in ("nb_permis_filtres", "nb_groupes"):
                if isinstance(s.get(k), (int, float)):
                    t.add(float(s[k]))
        if isinstance(s, dict):
            for k in ("nb_permis", "nb_demandeurs"):
                if isinstance(s.get(k), (int, float)):
                    t.add(float(s[k]))
    return {v for v in t if v > 0}


def _pool(sorties):
    """Tous les nombres présents dans les sorties d'outils, + totaux de colonnes."""
    pool = set()

    def walk(x):
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            pool.add(float(x))
        elif isinstance(x, str):
            pool.update(v for v, _, _ in _nombres(x))
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(k)               # les clés comptent aussi (ex. années de « annees_depot »)
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    for s in sorties:
        walk(s)
        if isinstance(s, dict) and isinstance(s.get("resultats"), list):
            for col in ("permis", VOL, "acteurs"):
                pool.add(float(sum(r.get(col, 0) for r in s["resultats"] if isinstance(r, dict))))
    return pool


def verifier_chiffres(args, sorties):
    """Liste des nombres de la note introuvables dans les sorties d'outils (vide = tout est retrouvé)."""
    pool = _pool(sorties)
    vals = sorted(v for v in pool if v > 0)
    totaux = _totaux(sorties)
    # Libellés contenant des chiffres (« SCCV RSS AUBERGENVILLE 78 ») : retirés du texte avant extraction,
    # sinon « … 78 211 logements » serait lu comme le nombre 78 211.
    libelles = set()
    pcts_sources = set()     # pourcentages écrits tels quels dans une sortie (ex. réserve du dictionnaire « ~15 % »)

    def walk(x):
        if isinstance(x, str):
            pcts_sources.update(v for v, p, _ in _nombres(x) if p)
        if isinstance(x, str) and len(x) >= 6 and re.search(r"\d", x) and re.search(r"[A-Za-zÀ-ÿ]", x):
            libelles.add(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(sorties)
    manquants = []
    for champ in CHAMPS_NOTE:
        texte = args.get(champ, "") or ""
        for lib in sorted(libelles, key=len, reverse=True):
            if lib in texte:
                texte = texte.replace(lib, " ")
        # nombres du champ retrouvés tels quels dans les résultats : base des calculs dérivés admis
        base = sorted({v for v, p, _ in _nombres(texte) if not p and v > 0 and v in pool})

        # 1. Nombres (hors pourcentages) : présents dans les résultats, ou somme / quotient de nombres retrouvés
        for val, pct, brut in _nombres(texte):
            if pct or val in pool or val <= SEUIL_PETITS or _derive_ok(val, base):
                continue
            manquants.append(brut)

        # 2. Pourcentages : recalculables avec deux nombres vérifiés de la MÊME phrase (part a/b ou évolution (a-b)/b).
        #    « À creuser » contient des pistes et des seuils (« dépasse 50 % »), pas des constats : non contrôlé.
        if champ == "a_creuser":
            continue
        for phrase in _phrases(texte):
            nums = _nombres(phrase)
            cand = [v for v, p, _ in nums if not p and v > 0 and (v in pool or _derive_ok(v, base))]
            for val, pct, brut in nums:
                if not pct or val in pcts_sources:
                    continue
                if any(abs(100 * a / b - val) <= 0.6 or abs(100 * (a - b) / b - val) <= 0.6
                       for a in cand for b in cand if b):
                    continue
                manquants.append(f"{brut} % (base absente ou fausse dans la phrase)")
    return sorted(set(manquants))


def _phrases(texte):
    """Découpe en phrases (le séparateur décimal est la virgule, donc le point termine bien une phrase)."""
    return [p for p in re.split(r"(?<=[.;!?])\s+|\n", texte or "") if p.strip()]


def _derive_ok(val, base):
    """val est-il une somme (2 à 6 termes) ou un quotient de nombres déjà retrouvés dans la note ?"""
    termes = [b for b in base if SEUIL_PETITS < b < val]     # une somme n'utilise que des termes plus petits
    if val > SEUIL_PETITS and len(termes) <= 22:
        for k in range(2, min(6, len(termes)) + 1):
            for c in itertools.combinations(termes, k):
                if abs(sum(c) - val) < 0.01:
                    return True
    tol = 0.5 if float(val).is_integer() else 0.05     # moyennes, ratios (« 13,6 logts/permis », « 4 874 m² »)
    for a in base:
        for b in base:
            if b and abs(a / b - val) <= tol:
                return True
    return False


def _ecrire_note(theme, args, requetes, model):
    note = {"date": datetime.now().isoformat(timespec="seconds"), "theme": theme, "modele": model, **args,
            "requetes_justificatives": requetes}
    with open(NOTES_JL, "a", encoding="utf-8") as f:
        f.write(json.dumps(note, ensure_ascii=False) + "\n")
    new = not NOTES_MD.exists()
    with open(NOTES_MD, "a", encoding="utf-8") as f:
        if new:
            f.write("# Constats proposés par l'agent explorateur\n\n"
                    "Notes écrites par le modèle après vérification par requêtes. Les requêtes listées sous chaque note "
                    "sont jointes automatiquement par le code (traçabilité). À relire : le modèle peut se tromper.\n\n")
        f.write(f"## [{theme}] {args.get('titre', '')}\n\n"
                f"- **Constat** : {args.get('constat', '')}\n"
                f"- **Intérêt pour Buddimm** : {args.get('interet_buddimm', '')}\n"
                f"- **Fiabilité** : {args.get('fiabilite', '')}\n"
                f"- **Limites** : {args.get('limites', '')}\n"
                + (f"- **À creuser** : {args['a_creuser']}\n" if args.get("a_creuser") else "")
                + (f"- ⚠️ **Chiffres non retrouvés dans les résultats d'outils** : {', '.join(args['chiffres_non_verifies'])}\n"
                   if args.get("chiffres_non_verifies") else "")
                + f"- *Requêtes ({model}, {note['date']})* :\n"
                + "".join(f"  - `{q}`\n" for q in requetes[-6:]) + "\n")


def explorer(theme, steps, key, model):
    handlers = {"apercu": apercu, "compter": compter, "profil_acteur": profil_acteur, "lire_dictionnaire": lire_dictionnaire,
                "fraicheur_donnees": fraicheur_donnees, "rafraichir_donnees": rafraichir_donnees}
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Thème : {theme} — {THEMES[theme]}\nCommence par apercu."}]
    trace, requetes, n_notes = [], [], 0
    sorties, avertis = [], set()      # résultats d'outils (pour vérifier les chiffres), notes déjà refusées
    for step in range(steps):
        if step == steps - 2:
            messages.append({"role": "user", "content": "Il te reste 2 étapes : seuls noter et terminer sont encore disponibles. Note maintenant tes 2 à 4 meilleurs constats vérifiés (chiffres issus des résultats déjà obtenus), puis termine."})
        try:
            fin_proche = step >= steps - 2       # garde-fou : forcer la conclusion en fin de budget
            msg = _chat(key, model, messages, TOOLS_FIN if fin_proche else None)
        except AppelInvalide as e:
            print(f"    appel d'outil invalide, le modèle est prévenu", flush=True)
            trace.append({"etape": step, "appel_invalide": str(e)})
            messages.append({"role": "user", "content": "Ton dernier appel d'outil était mal formé (arguments hors "
                             "schéma). Réessaie avec des arguments valides : group_by = liste de colonnes, filtres = "
                             "objet {colonne: valeur ou liste}, top = entier."})
            continue
        calls = msg.get("tool_calls") or []
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls") and v})
        trace.append({"etape": step, "texte": msg.get("content"), "appels": []})
        if not calls:
            messages.append({"role": "user", "content": "Utilise un outil : vérifie, note, ou termine."})
            continue
        fin = False
        for c in calls:
            name = c["function"]["name"]
            try:
                args = json.loads(c["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            if name == "noter":
                manquants = verifier_chiffres(args, sorties) if requetes else []
                if not requetes:
                    out = {"erreur": "Refusé : vérifie d'abord avec compter ou profil_acteur."}
                elif manquants and args.get("titre") not in avertis:
                    avertis.add(args.get("titre"))             # refus une fois : le modèle peut corriger
                    out = {"erreur": "Refusé : chiffres non vérifiables : "
                                     f"{', '.join(manquants)}. Corrige-les avec des chiffres issus des requêtes, "
                                     "ou fais la requête qui les donne. Chaque pourcentage doit citer, dans la même "
                                     "phrase, son numérateur et son dénominateur (ex. « 3 251 sur 11 785, soit 27,6 % »). "
                                     "Puis renote."}
                    print(f"    note refusée (chiffres non retrouvés : {', '.join(manquants)})", flush=True)
                else:
                    if manquants:
                        args["chiffres_non_verifies"] = manquants
                    _ecrire_note(theme, args, list(requetes), model)
                    n_notes += 1
                    out = {"ok": f"note {n_notes} enregistrée" + (" avec avertissement" if manquants else "")}
                    print(f"  note : {args.get('titre', '')} ({args.get('fiabilite', '')})"
                          + (f" ⚠ non retrouvés : {', '.join(manquants)}" if manquants else ""), flush=True)
            elif name == "terminer":
                out, fin = {"ok": "fin"}, True
            else:
                fn = handlers.get(name)
                try:
                    out = fn(**args) if fn else {"erreur": f"outil inconnu {name}"}
                except TypeError as e:
                    out = {"erreur": f"arguments invalides : {e}"}
                if name in ("compter", "profil_acteur"):
                    requetes.append(f"{name}({json.dumps(args, ensure_ascii=False)})")
                sorties.append(out)
            trace[-1]["appels"].append({"outil": name, "args": args, "sortie": out})
            messages.append({"role": "tool", "tool_call_id": c["id"],
                             "content": json.dumps(out, ensure_ascii=False)[:3000]})
        if fin:
            break
    (TRACES / f"{theme}_{datetime.now():%Y%m%d_%H%M%S}.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=1), encoding="utf-8")
    return n_notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", choices=list(THEMES), default=None, help="un seul thème (défaut : tous)")
    ap.add_argument("--steps", type=int, default=10, help="étapes max par thème")
    args = ap.parse_args()
    key, model = _env("exploration")
    if not key:
        raise SystemExit("Clé API manquante dans .env (GROQ_API_KEY ou GEMINI_API_KEY selon LLM_PROVIDER).")
    for theme in ([args.theme] if args.theme else list(THEMES)):
        print(f"== thème {theme}", flush=True)
        try:
            n = explorer(theme, args.steps, key, model)
            print(f"  {n} note(s)", flush=True)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"  échec du thème {theme} : {type(e).__name__}: {e}", flush=True)
    print(f"notes : {NOTES_MD}")


if __name__ == "__main__":
    main()
