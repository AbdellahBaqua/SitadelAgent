# Qualification des demandeurs de permis (Sitadel, Yvelines)

Prototype pour le test Buddimm : pour chaque permis de construire (PC) des Yvelines dont le demandeur est une
personne morale, dire à quelle **famille** appartient le demandeur, puis repérer des patterns exploitables.
Un demandeur non classable reste `non_determine`. Chaque résultat renvoie à sa source publique
(fichier Sitadel du SDES, fiche de l'Annuaire des entreprises).

**À lire d'abord :** `rapport\rapport_resultats_yvelines.pdf` (résultats), `out_fouille\dashboard.html`
(tableau de bord), `out_fouille\prospects_priorises.csv` (prospects qualifiés).

## 1. Installation

Prérequis : Python 3 (aucune dépendance externe, bibliothèque standard uniquement).

1. Copier `.env.example` en `.env` puis renseigner le fournisseur et la clé, par exemple :
   ```
   LLM_PROVIDER=nvidia
   NVIDIA_API_KEY=<votre clé>
   MODEL_CLASSIFICATION=nvidia/nemotron-3-ultra-550b-a55b
   MODEL_EXPLORATION=nvidia/nemotron-3.5-lightning-30b-a3b
   ```
   `.env` est ignoré par git. Ne jamais coller la clé dans le code ni dans un chat.
2. Données brutes, dans `data\` (ignoré par git : fichiers volumineux, re-téléchargeables) :
   - `data\sortie.csv` : PC logements du département 78, millésime 2026-10 (API DiDo du SDES).
     `python -X utf8 src\donnees.py rafraichir logements` le télécharge ou le met à jour.
   - `data\sortie_locaux.csv` : locaux non résidentiels du 78, extraits du fichier national par
     `python -X utf8 src\extract_locaux.py <fichier national.csv> 78` (ou `src\donnees.py rafraichir locaux`).
   - `data\finess\etalab-cs1100507-stock-*.csv` : FINESS, établissements sanitaires, sociaux et médico-sociaux géolocalisés
     (ministère, jeu « FINESS Extraction du Fichier des établissements » sur data.gouv.fr, instantané du 04/05/2026, 46 Mo).
3. Référentiels officiels, déjà versionnés : `config\naf_rev2_libelles.csv` et `config\cj_libelles.csv` (Insee),
   `config\dictionnaire_variables*.txt` (SDES). Les fichiers d'origine sont dans `raw\`.

## Arborescence

| Dossier | Contenu |
|---|---|
| `src\` | tout le code (classification, agents, fouille, rapport) |
| `config\` | référentiels Insee / SDES utilisés par le code |
| `raw\` | fichiers officiels d'origine des référentiels (xls) |
| `scripts\` | scripts d'acquisition du début du projet (`fetch_yvelines.ps1`, `filter_sitadel.py`), remplacés par `src\donnees.py` |
| `out\`, `out_locaux\` | résultats par fichier : classification, traces de l'agent, notes des agents explorateurs |
| `out_fouille\` | fouille croisée : groupes, profils, prospects priorisés et écartés, relecture des notes, tableau de bord |
| `out_fouille\agent_prospects\` | agent de qualification : exploitants trouvés via FINESS, verdicts sur les prospects, traces |
| `out_fouille\controle\` | échantillons de contrôle à vérifier à la main, et précision mesurée |
| `cache\` | cache des dirigeants **personnes morales** (aucune personne physique) |
| `rapport\` | rapport PDF des résultats et documents explicatifs |
| `data\` | données brutes (non versionné) |

## 2. Lancer

Depuis la racine du projet (le flag `-X utf8` évite les erreurs d'accents sous Windows) ;
`$env:DATASET='locaux'` pour traiter le fichier des locaux au lieu des logements :

| Commande | Effet |
|---|---|
| `python -X utf8 src\run.py --llm` | Filtre + règles, puis agent sur les acteurs ambigus (174 logements, 184 locaux). Les acteurs déjà en cache ne sont pas renvoyés au modèle. |
| `python -X utf8 src\run.py --llm --llm-limit 5` | Agent limité à 5 nouveaux acteurs (test). |
| `python -X utf8 src\run.py --llm --nom "SNL"` | Force l'agent sur les acteurs dont la dénomination contient `SNL`, même s'ils sont déjà classés par règle. |
| `python -X utf8 src\run.py` | Règles seules, **sans** les conclusions de l'agent : réécrit les CSV avec les ambigus en `non_determine`. |

Les conclusions sont en cache (`out\agent_cache.json`) : relancer ne repaie pas les mêmes acteurs.
Pour rejouer un acteur, supprimer son SIREN du cache.

## 3. Comment ça marche

```
data\sortie.csv ─► load.py   : garde PC + SIREN, agrège par demandeur (SIREN)
                ─► rules.py  : règles sur la catégorie juridique, la dénomination, le NAF (92 % des acteurs)
                ─► agent.py  : agent LLM à outils pour les cas ambigus (8 %)
                ─► run.py    : écrit out\acteurs_classes.csv et out\permis_classes.csv
```

### Boucle de l'agent (`src/agent.py`)
Le code appelle d'abord les quatre outils de lecture et donne leurs résultats au modèle, qui peut en rappeler
(8 étapes maximum) puis conclut.

| Outil | Rôle |
|---|---|
| `permis_du_demandeur(siren)` | Profil de ses permis dans les Yvelines (nombre, années, communes, logements, m² de locaux, collectif/individuel, résidences, logements sociaux déclarés). |
| `fiche_entreprise(siren)` | Fiche publique (API Recherche d'entreprises) : activité **actuelle**, forme, taille, état de chaque établissement cité dans les permis, alertes (établissement fermé, NAF divergent). **Dirigeants et finances exclus.** |
| `libelle_naf(code)` / `libelle_cj(code)` | Libellés officiels Insee. |
| `conclure(...)` | Réponse finale : `famille` (liste fermée), `confiance`, `indices` (chacun cite son outil), `limites`. |

Garde-fous appliqués par le code : conclusion refusée sans fiche entreprise ; famille hors liste → `non_determine` ;
pas de conclusion en 8 étapes → `non_determine` ; confiance « haute » plafonnée à « moyenne » dès qu'une fragilité
est détectée ; trace complète par acteur ; erreurs 429 ou réseau → attente puis réessai, sinon l'acteur est
retenté au lancement suivant (rien n'est mis en cache).

### Familles (liste fermée)
`bailleur_social`, `promoteur`, `fonciere_investisseur`, `association_ess`, `exploitant_sante_social`,
`collectivite_public`, `copropriete`, `entreprise_autre`, `non_determine`.

## 4. Lire les résultats

- `out\acteurs_classes.csv` : une ligne par SIREN (famille, confiance, méthode `regle` ou `agent:<modèle>`, indices, lien source).
- `out\permis_classes.csv` : une ligne par permis (`NUM_DAU`, famille, liens vers la source des données et la fiche du demandeur).
- `out\traces\<siren>.json` : le raisonnement de l'agent, étape par étape (appels d'outils et résultats).
  À ouvrir pour comprendre ou contester un classement.
- `out\agent_cache.json` : conclusions mémorisées.

Voir une trace en PowerShell :
```powershell
Get-Content out\traces\402987622.json -Raw -Encoding utf8 | ConvertFrom-Json | % { $_.appels; $_.resultats }
```

## 4 bis. Agent explorateur : le LLM propose des patterns (`src/explore.py`)

L'agent explorateur (modèle `MODEL_EXPLORATION`, distinct de celui de la classification) interroge lui-même les données (outils en lecture seule, aucune exécution de code), vérifie ses hypothèses
puis écrit ses constats.

| Commande | Effet |
|---|---|
| `python -X utf8 src\explore.py --theme medico_social --steps 10` | Un seul thème, 10 étapes maximum |
| `python -X utf8 src\explore.py` | Tous les thèmes : `acteurs`, `geographie`, `medico_social`, `transformations`, `dynamique`, `libre` |

Outils donnés au modèle : `apercu` (volumes, familles, limites des données), `compter` (agrégation par 1 à 3 colonnes,
filtres, tri par permis / logements / acteurs), `profil_acteur(siren)`, `lire_dictionnaire(variable)`,
`noter(...)`, `terminer`.

Sorties :
- `out\insights_nvidia.md` et `out\insights_claude.md` (un fichier par modèle, produits par
  `src\split_insights.py` à partir du `.jsonl`) : les constats lisibles (constat chiffré, intérêt pour Buddimm, fiabilité
  établi / fragile / hypothèse, limites, à creuser). **Sous chaque note, le code joint les requêtes réellement
  exécutées avant** : on peut refaire le calcul.
- `out\insights_agent.jsonl` : les mêmes notes en JSON (une par ligne).
- `out\explore_traces\<thème>_<date>.json` : tout le raisonnement (appels et résultats).

Garde-fous : une note est refusée si aucune requête n'a été faite avant ; un appel d'outil mal formé est
signalé au modèle au lieu d'arrêter le thème ; les anciens résultats sont raccourcis pour rester sous le quota
du fournisseur. Ne pas lancer l'explorateur en même temps que l'évaluation ou l'agent de
classification : ils partagent ce quota.

**Garde-fou sur les chiffres** (`verifier_chiffres` dans `src/explore.py`) :
- chaque nombre > 10 d'une note doit apparaître dans un résultat d'outil de la session, ou être une somme (2 à 6
  termes) ou un quotient de nombres de la note eux-mêmes retrouvés (ex. « 3 251 » = somme de 5 communes citées,
  « 13,6 » = 1 458 / 107) ;
- **chaque pourcentage doit être recalculable avec deux nombres vérifiés de la même phrase** : part (a / b) ou
  évolution ((a - b) / b), à 0,6 point près. Exemple accepté : « 3 251 sur 11 785, soit 27,6 % ». Un pourcentage
  sans base dans sa phrase est refusé, même s'il est juste : le modèle doit citer sa base ;
- les pourcentages de « À creuser » (seuils, pistes) ne sont pas contrôlés ; les libellés contenant des chiffres
  (noms de sociétés) sont retirés avant l'extraction.
Si des chiffres ne sont pas vérifiables, la note est refusée une fois avec la liste ; si le modèle insiste, elle est
enregistrée avec un avertissement « ⚠️ Chiffres non retrouvés ». La même règle s'applique à la passerelle
`src/explore_cli.py` (quand Claude joue l'agent).

Vérifier après coup toutes les notes (rejoue les requêtes jointes ; ajouter `$env:DATASET='locaux'` pour les locaux) :
```
python -X utf8 src\verifier_notes.py        # -> out\verification_chiffres.md
python -X utf8 src\split_insights.py        # -> out\insights_claude.md, out\insights_nvidia.md (un fichier par modèle)
python -X utf8 src\rapport_pdf.py           # -> rapport\rapport_resultats_yvelines.pdf
```
Le garde-fou accepte aussi un pourcentage cité tel quel par un outil (ex. « ~15 % des ouvertures de chantier »,
réserve du dictionnaire). L'interprétation, que le code ne voit pas, est relue à part : `out_fouille/relecture.json`
donne pour chaque note (clé = titre) un `verdict` et un `commentaire`, repris sous la note dans le PDF avec un bilan
par agent. Relecture du 2026-11-22 (requêtes rejouées par Claude) : NVIDIA 8 exacts, 8 à corriger (période, titre ou
limite faux), 3 erronés (lecture inversée de ETAT_DAU, DESTINATION_PRINCIPALE prise pour la destination des locaux).
Sur les 20 notes existantes, la règle attrape les 7 pourcentages faux connus et le total inventé, sans fausse
alerte sur les sommes et quotients justes ; elle signale aussi 9 pourcentages justes mais sans base citée.
Limites : un nombre vrai pris dans un autre périmètre passe (ex. « 78 permis / 1 679 logements », vrai pour tous les
types de transformation, rapporté au total d'un seul type) ; un classement ou une interprétation erronés à partir de
vrais chiffres passent ; les nombres de 0 à 10 ne sont pas contrôlés ; une somme de nombres cités peut tomber juste
par coïncidence.

Les notes de l'agent sont des **propositions à relire**, pas des faits.

## 4 ter. Fouille de données et tableau de bord (`out_fouille\`)

Le code calcule, le LLM n'interprète que des résultats vérifiables. À lancer après `run.py` sur les deux fichiers :

```powershell
python -X utf8 src\groupes.py       # rattache les sociétés de programme à leur groupe (Annuaire, ~10 min)
python -X utf8 src\croisement.py    # croise logements × locaux
python -X utf8 src\profils.py       # profils d'acteurs par k-means
python -X utf8 src\dashboard.py     # -> out_fouille\dashboard.html
```

| Analyse | Méthode | Sorties |
|---|---|---|
| Groupes promoteurs | Pour chaque demandeur « promoteur », dirigeants **personnes morales** lus dans l'Annuaire (les personnes physiques sont écartées dès la lecture, jamais stockées). Groupe = gérant / président personne morale. Un seul niveau. Cache : `cache\dirigeants_personnes_morales.json` | `groupes_societes.csv`, `groupes_synthese.csv` |
| Croisement logements × locaux | Jointure sur `NUM_DAU` (permis mixtes) et sur le SIREN (acteurs présents dans les deux) ; zoom sur les équipements de santé / action sociale | `croisement.json`, `acteurs_deux_fichiers.csv` |
| Profils d'acteurs | 10 indicateurs de comportement standardisés, k-means (k-means++, graine fixe) avec k choisi entre 4 et 8 par la silhouette ; la famille juridique n'entre pas dans le calcul. Familles contradictoires entre fichiers réconciliées (la plus sûre l'emporte) | `profils_acteurs.csv`, `profils_groupes.json` |
| Tableau de bord | HTML autonome (aucune bibliothèque externe), modes clair et sombre, infobulles, tableau sous chaque graphique, palette validée par `validate_palette.js` (dataviz) | `dashboard.html` |

Ouvrir le tableau de bord : double-cliquer sur `out_fouille\dashboard.html`, ou le servir localement
(`python -m http.server 8765 --directory out_fouille`, puis http://localhost:8765/dashboard.html).

## 4 quater. Agent de qualification commerciale (`src/agent_prospects.py`)

L'agent de classification ne sert qu'aux cas ambigus, surtout de petites sociétés sans intérêt pour Buddimm. Celui-ci
travaille là où se joue la valeur commerciale, avec les mêmes garde-fous (outils, sources citées, plafonds imposés par
le code, traces).

```powershell
python -X utf8 src\agent_prospects.py exploitants   # 1. futur exploitant des projets médico-sociaux déposés par des tiers
                                                    #    (--echantillon 50 : 50 permis tirés au hasard, pour tester vite)
python -X utf8 src\agent_prospects.py bilan         #    pourquoi pas d'exploitant (résidence seniors privée, adresse vide…)
python -X utf8 src\prospects.py                     # 2. candidats (demandeurs + exploitants trouvés) -> prospects_candidats.json
python -X utf8 src\agent_prospects.py prospects     # 3. vrai prospect / faux positif / à vérifier (cas ambigus seulement)
                                                    #    --echantillon 25 --fournisseur groq --modele openai/gpt-oss-120b
python -X utf8 src\comparer_qualif.py               #    accord entre deux modèles sur les mêmes cas
python -X utf8 src\prospects.py                     # 4. score final -> prospects_priorises.csv, prospects_ecartes.csv
python -X utf8 src\echantillon.py tirer             # 5. échantillons de contrôle à vérifier à la main
python -X utf8 src\echantillon.py mesurer           #    puis précision mesurée -> out_fouille\controle\precision.md
```

1. **Le demandeur n'est pas le client.** Pour chaque permis de résidence médico-sociale ou d'équipement de santé /
   d'action sociale déposé par un promoteur, un bailleur, une foncière ou une entreprise, le code liste les
   établissements FINESS de la commune compatibles avec le type de projet et calcule des indices (même rue, même
   numéro, ouverture après l'autorisation). L'agent choisit l'établissement correspondant ou « aucun » ; le code refuse
   un numéro hors liste et n'accorde « haute » qu'avec même rue ET ouverture après l'autorisation. L'exploitant trouvé
   (souvent une association) entre dans la liste de prospects.
2. **Pré-filtre déterministe** (`src/cible.py`) : le code écarte d'abord les candidats sans jugement à porter, lus dans
   l'activité actuelle de l'Annuaire : structure cessée, culte, enseignement scolaire, sport, cabinet libéral de santé,
   pharmacie… sauf si la structure exploite un établissement FINESS. Chaque exclusion garde sa règle (`prospects_ecartes.csv`).
   Un bailleur cessé est signalé comme « fusion probable » : son successeur reste une cible. La famille ne change pas
   (une association de culte reste une association) : le filtre répond à une autre question, « est-ce une cible ? ».
3. **Vrai prospect ?** Pour chaque prospect restant, le code fournit ses permis, sa fiche entreprise (activité actuelle, état,
   effectif) et ses établissements FINESS, et calcule sa taille. L'agent rend `prospect` / `faux_positif` / `a_verifier`,
   l'adéquation, le type de structure et le besoin immobilier visible. Garde-fous du code : faux positif refusé s'il ne
   repose que sur le nom ; structure cessée jamais « prospect » ; adéquation « forte » refusée pour une très grande
   structure ou sans preuve d'activité sociale / médico-sociale.
4. **Score final** (`prospects.py`) : faux positifs écartés avec leur motif ; « à vérifier » −1 ; établissements FINESS
   exploités +2 ; taille moyenne ou grande +1, très grande −2 (direction immobilière interne probable).
## 5. Limites connues

- **Précision non mesurée** : aucun échantillon d'acteurs n'a encore été vérifié à la main. La confiance affichée
  est celle du modèle, corrigée par les garde-fous ; ce n'est pas une précision mesurée.
- **Cas ambigus vraiment ambigus** : sur 25 acteurs difficiles, deux modèles différents donnent la même famille
  dans 14 cas (56 %) (`src\comparer_modeles.py` -> `out\comparaison_classification.csv`).
- **`entreprise_autre` est une catégorie fourre-tout**, et la frontière promoteur / foncière / marchand de biens
  reste floue.
- **NAF des permis périmés** : le NAF de Sitadel est celui d'un établissement au moment du dépôt, souvent fermé
  depuis ; l'agent le recoupe avec l'activité actuelle (Annuaire), les règles non.
- **Faux positifs du scoring des prospects** : ex. un OGEC (gestionnaire d'école) bien classé parce que son
  permis est codé « action sociale ».
- **Notes des agents explorateurs** : des chiffres vérifiés n'empêchent pas une mauvaise lecture
  (voir `out_fouille\relecture.json` et la section 6 du rapport PDF).
- **Champs mal renseignés** : logements sociaux, résidence (rare, depuis mai 2022), dates de chantier/achèvement.
- Personnes morales uniquement ; aucune prise de contact ; aucun enrichissement avec des noms de personnes physiques ;
  appels aux API en cache et espacés.

## 6. Pistes d'amélioration

1. Étiqueter à la main 50 à 100 acteurs pour mesurer la précision des règles et de l'agent.
2. Ajouter FINESS (établissements sanitaires et sociaux) comme source pour confirmer les familles santé-social et ESS.
3. Découper `entreprise_autre` en sous-familles ; remonter au promoteur réel derrière chaque SCCV (plusieurs niveaux).
4. Corriger le scoring des prospects avec un filtre sur l'activité réelle (écoles, cultes…).
5. Ajouter la soustraction au garde-fou des chiffres.