# Constats de l'agent explorateur — nvidia

Modèle(s) : nvidia/nemotron-3.5-lightning-30b-a3b · 6 note(s). Requêtes jointes automatiquement par le code. À relire : le modèle peut se tromper.

## [geographie] Dominance des promoteurs

- **Constat** : Sur les 3363 permis analysés, les promoteurs ont déposé 1146 permis (34,1 % du total), générant 62 906 logements, soit la part la plus élevée parmi les familles de demandeurs.
- **Intérêt pour Buddimm** : Prospection ciblée vers les promoteurs pour les opérations de conseil en développement immobilier et identification de territoires à fort potentiel promoteur.
- **Fiabilité** : établi
- **Limites** : Pourcentage calculé sur l'ensemble des permis (3363) ; le nombre total de logements dans l'ensemble de la base n'est pas fourni, donc le pourcentage de logements sur le total global ne peut être précisé.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:12:32)* :
  - `compter({"group_by": ["famille"], "mesure": "logements", "top": 10})`
  - `compter({"group_by": ["COMM", "famille"], "mesure": "logements", "top": 30, "filtres": {"famille": "bailleur_social"}})`
  - `compter({"group_by": ["COMM", "famille"], "mesure": "logements", "top": 50, "filtres": {"famille": "association_ess"}})`
  - `compter({"group_by": ["COMM", "famille"], "mesure": "logements", "top": 50, "filtres": {"famille": "collectivite_public"}})`
  - `compter({"group_by": ["COMM"], "mesure": "logements", "top": 100})`
  - `compter({"group_by": [], "mesure": "logements", "top": 1, "filtres": {"famille": "association_ess"}})`

## [transformations] Promoteurs en tête des reconversions bureaux → logements

- **Constat** : Sur les 360 permis de transformation de locaux en logements (type 1), 50 sont déposés par des promoteurs, représentant 1 % des 3 363 permis totaux et 13,9 % des permis de type 1 (50/360). Ces 50 permis génèrent 1 998 logements, soit 51,1 % des logements issus de type 1 (1 998/3 908).
- **Intérêt pour Buddimm** : Identifier les promoteurs actifs sur les reconversions permet cibler des opérations de conseil ou de partenariat pour Buddimm, notamment auprès de ceux qui réalisent le plus de logements par permis.
- **Fiabilité** : établi
- **Limites** : Les données ne couvrent que les Yvelines et les promoteurs « non déterminés » sont exclus du décompte.
- **À creuser** : Analyser le portefeuille immobilier des promoteurs identifiés pour proposer des scénarios de reconversion.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:14:11)* :
  - `compter({"group_by": ["TYPE_TRANSFO_PRINCIPAL"], "mesure": "logements", "top": 20})`
  - `compter({"group_by": ["famille", "TYPE_TRANSFO_PRINCIPAL"], "mesure": "logements", "top": 50})`
  - `compter({"group_by": ["AN_DEPOT", "TYPE_TRANSFO_PRINCIPAL"], "mesure": "logements", "top": 10})`
  - `compter({"group_by": ["COMM", "TYPE_TRANSFO_PRINCIPAL"], "mesure": "logements", "top": 20})`

## [dynamique] Répartition des permis par famille de demandeur

- **Constat** : Sur 3363 permis analysés (période 2011-2023), la famille « fonciere_investisseur » dépose 1462 permis (43,5 %), « promoteur » 1146 permis (34,1 %), « bailleur_social » 300 permis (8,9 %), « entreprise_autre » 204 permis (6,1 %), « collectivite_public » 166 permis (4,9 %), « association_ess » 41 permis (1,2 %), « non_determine » 34 permis (1,0 %), « exploitant_sante_social » 6 permis (0,2 %) et « copropriete » 4 permis (0,1 %).
- **Intérêt pour Buddimm** : Identifier les familles d’acteurs dominantes pour orienter la prospection et le conseil immobilier (ex: prioriser les promoteurs et foncières investisseuses).
- **Fiabilité** : établi
- **Limites** : Pourcentages calculés sur l’ensemble de la période 2011-2023 ; évolution dans le temps non détaillée ici.
- **À creuser** : Analyser l’évolution annuelle de chaque famille pour détecter les tendances de croissance ou de décroissance.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:14:46)* :
  - `compter({"group_by": ["AN_DEPOT", "famille"], "mesure": "permis", "top": 50})`
  - `compter({"group_by": ["AN_DEPOT", "famille", "ETAT_DAU"], "mesure": "permis", "top": 200})`
  - `compter({"group_by": ["ETAT_DAU"], "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["AN_DEPOT", "ETAT_DAU"], "mesure": "permis", "top": 50})`
  - `compter({"group_by": ["famille"], "mesure": "permis", "top": 20})`

## [dynamique] Pic des dépôts en 2021 puis recul

- **Constat** : Le nombre de permis déposés par an atteint son pic en 2021 avec 356 permis, soit 10,6 % des 3363 permis totaux (356 / 3363). Après 2021, on observe un recul régulier : 247 permis en 2022, 221 en 2023 et 185 en 2024 (5,5 % soit 185 / 3363).
- **Intérêt pour Buddimm** : Identifier les années de forte activité pour ajuster les cycles de prospection et anticiper les périodes de baisse.
- **Fiabilité** : établi
- **Limites** : Les données disponibles s'arrêtent à 2024 ; les années 2025‑2026 montrent une baisse continue (168 puis 77 permis).
- **À creuser** : Analyser les facteurs externes (conjoncture économique, évolutions réglementaires) ayant pu provoquer le pic 2021 et le recul subséquent.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:14:54)* :
  - `compter({"group_by": ["AN_DEPOT", "famille"], "mesure": "permis", "top": 50})`
  - `compter({"group_by": ["AN_DEPOT", "famille", "ETAT_DAU"], "mesure": "permis", "top": 200})`
  - `compter({"group_by": ["ETAT_DAU"], "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["AN_DEPOT", "ETAT_DAU"], "mesure": "permis", "top": 50})`
  - `compter({"group_by": ["famille"], "mesure": "permis", "top": 20})`

## [libre] Foncier investisseur : spécialiste du logement individuel

- **Constat** : Sur les 1462 permis fonciers investisseurs répertoriés dans les Yvelines, 704 (48,2 % soit 704 sur 1462) concernent un seul logement individuel (TYPE_PRINCIP_LOGTS_CREES = 1), représentant 704 logements. Les 758 autres permis (51,8 % soit 758 sur 1462) produisent principalement des logements collectifs (type 3) ou plusieurs individuels, soit 10 198 logements au total (10 902 − 704).
- **Intérêt pour Buddimm** : Identifier des opportunités de prospection pour des projets de petits lots ou de rénovation individuelle, et cibler les promoteurs fonciers pour des opérations de division foncière.
- **Fiabilité** : établi
- **Limites** : Périmètre limité aux Yvelines (78) ; les pourcentages sont calculés sur l'ensemble des permis logements de la base (1462 permis fonciers investisseurs).
- **À creuser** : Analyser le profil des 758 autres permis fonciers investisseurs pour distinguer ceux qui réalisent des collectifs de ceux qui font de l'habitat groupé.
- ⚠️ **Chiffres non retrouvés dans les résultats d'outils** : 10 198, 51,8 % (base absente ou fausse dans la phrase), 758
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:15:21)* :
  - `compter({"group_by": ["famille"], "mesure": "logements", "top": 10})`
  - `compter({"group_by": ["famille", "AN_DEPOT"], "mesure": "logements", "top": 20})`
  - `compter({"group_by": ["famille", "TYPE_PRINCIP_LOGTS_CREES"], "mesure": "logements", "top": 30})`

## [libre] Promoteur dominant et focus sur le collectif

- **Constat** : Sur les 3363 permis déposés dans les Yvelines, les promoteurs déposent 1146 permis (34,1 % soit 1146 / 3363) et produisent 62 906 logements (69,8 % soit 62 906 / 90 115). Ces projets sont majoritairement des logements collectifs (type 3 : collectif hors résidence) représentant 53 467 logements sur les 62 906 soit 84,9 % de leurs productions.
- **Intérêt pour Buddimm** : Prospection ciblée auprès des promoteurs pour des opérations de densification, regroupement ou transformation de projets existants.
- **Fiabilité** : établi
- **Limites** : Périmètre limité aux Yvelines (78) ; les pourcentages sont calculés sur l'ensemble des permis logements de la base (3363 permis, 90 115 logements).
- **À creuser** : Analyser la répartition géographique des projets promoteurs pour identifier les zones à fort potentiel de regroupement ou de renouvellement urbain.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:15:32)* :
  - `compter({"group_by": ["famille"], "mesure": "logements", "top": 10})`
  - `compter({"group_by": ["famille", "AN_DEPOT"], "mesure": "logements", "top": 20})`
  - `compter({"group_by": ["famille", "TYPE_PRINCIP_LOGTS_CREES"], "mesure": "logements", "top": 30})`
  - `compter({"group_by": ["famille", "AN_DEPOT_min"], "mesure": "logements", "top": 30})`
