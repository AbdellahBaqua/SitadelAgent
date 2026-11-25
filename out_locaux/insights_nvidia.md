# Constats de l'agent explorateur — nvidia

Modèle(s) : nvidia/nemotron-3.5-lightning-30b-a3b · 10 note(s). Requêtes jointes automatiquement par le code. À relire : le modèle peut se tromper.

## [geographie] Dominance du service public / intérêt collectif

- **Constat** : Les surfaces de destination 9 (service public / intérêt collectif) représentent 1 202 328 m², soit 23,7 % du total des surfaces créées (5 080 108 m²) sur l'ensemble des permis yvelinois 2005‑2025.
- **Intérêt pour Buddimm** : Identifier les territoires et acteurs liés aux équipements collectifs pour du conseil en programmation ou de la veille.
- **Fiabilité** : établi
- **Limites** : Données SDES/Sitadel, périmètre Yvelines, années 2005‑2025, 2026 partiel.
- **À creuser** : Creuser la part des collectivités publiques vs promoteurs sur ce type de destination.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:16:34)* :
  - `compter({"group_by": ["DESTINATION_PRINCIPALE"], "mesure": "surface_m2", "top": 10})`
  - `compter({"group_by": ["famille", "DESTINATION_PRINCIPALE"], "mesure": "surface_m2", "top": 20})`
  - `compter({"group_by": ["COMM", "DESTINATION_PRINCIPALE"], "mesure": "surface_m2", "top": 10})`

## [geographie] Dominance du service public / intérêt collectif

- **Constat** : Les surfaces de destination 9 (service public / intérêt collectif) représentent 1 202 328 m² sur un total de 5 080 108 m² créé par les 4 245 permis yvelinois 2005‑2025, soit 23,7 % (1 202 328 / 5 080 108).
- **Intérêt pour Buddimm** : Identifier les territoires et acteurs liés aux équipements collectifs pour du conseil en programmation ou de la veille.
- **Fiabilité** : établi
- **Limites** : Données SDES/Sitadel, périmètre Yvelines, années 2005‑2025, total des surfaces calculé sur l'ensemble des destinations.
- **À creuser** : Creuser la part des collectivités publiques vs promoteurs sur ce type de destination.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:17:06)* :
  - `compter({"group_by": ["DESTINATION_PRINCIPALE"], "mesure": "surface_m2", "top": 10})`
  - `compter({"group_by": ["famille", "DESTINATION_PRINCIPALE"], "mesure": "surface_m2", "top": 20})`
  - `compter({"group_by": ["COMM", "DESTINATION_PRINCIPALE"], "mesure": "surface_m2", "top": 10})`
  - `compter({"group_by": [], "mesure": "surface_m2"})`
  - `compter({"group_by": ["DESTINATION_PRINCIPALE"], "mesure": "surface_m2", "top": 100})`

## [medico_social] Dominance des collectivités et surface moyenne par permis pour TYPE_SERVICE_PUBLIC 3

- **Constat** : Sur les 176 permis TYPE_SERVICE_PUBLIC 3, les collectivités publiques obtiennent 67 permis (38,1 %), les associations ESS 32 permis (18,2 %) et les foncières investisseuses 31 permis (17,6 %). La surface moyenne par permis s'établit à 45083 m² / 67 ≈ 673 m² pour les collectivités, 79217 m² / 32 ≈ 2 476 m² pour les associations ESS et 50132 m² / 31 ≈ 1 617 m² pour les foncières investisseuses.
- **Intérêt pour Buddimm** : Identifie les acteurs qui portent les plus grands projets d'équipements de santé/action sociale, utile pour cibler les promoteurs ou foncières dans la prospection.
- **Fiabilité** : établi
- **Limites** : Basé sur l'extraction SDES/Sitadel des Yvelines ; ne couvre pas les permis résidentiels ni les extensions.
- **À creuser** : Analyser les projets d'associations ESS pour comprendre leurs besoins en surface et éventuellement les conseiller sur des regroupements de projets.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:17:51)* :
  - `compter({"group_by": ["famille"], "filtres": {"TYPE_SERVICE_PUBLIC": "3"}, "mesure": "permis", "top": 20})`
  - `compter({"group_by": ["famille"], "filtres": {"TYPE_SERVICE_PUBLIC": "4"}, "mesure": "permis", "top": 20})`
  - `compter({"group_by": ["COMM"], "filtres": {"TYPE_SERVICE_PUBLIC": "3"}, "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["AN_DEPOT"], "filtres": {"TYPE_SERVICE_PUBLIC": "3"}, "mesure": "permis", "top": 30})`
  - `compter({"group_by": ["AN_DEPOT"], "filtres": {"TYPE_SERVICE_PUBLIC": "4"}, "mesure": "permis", "top": 30})`

## [medico_social] Collectivités dominantes pour TYPE_SERVICE_PUBLIC 3

- **Constat** : Sur les 176 permis TYPE_SERVICE_PUBLIC 3, les collectivités publiques obtiennent 67 permis (38,1 % sur 176), soit la part la plus importante. La surface moyenne par permis s'établit à 45 083 m² / 67 ≈ 673 m².
- **Intérêt pour Buddimm** : Cibler les projets portés par les collectivités pour des opérations de conseil ou de prospection immobilière sur des équipements de santé/action sociale.
- **Fiabilité** : établi
- **Limites** : Extraction SDES/Sitadel des Yvelines ; ne concerne que les permis créant des locaux non résidentiels.
- **À creuser** : Analyser les projets municipaux pour identifier des opportunités de regroupement ou de partenariat avec des bailleurs.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:17:56)* :
  - `compter({"group_by": ["famille"], "filtres": {"TYPE_SERVICE_PUBLIC": "3"}, "mesure": "permis", "top": 20})`
  - `compter({"group_by": ["famille"], "filtres": {"TYPE_SERVICE_PUBLIC": "4"}, "mesure": "permis", "top": 20})`
  - `compter({"group_by": ["COMM"], "filtres": {"TYPE_SERVICE_PUBLIC": "3"}, "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["AN_DEPOT"], "filtres": {"TYPE_SERVICE_PUBLIC": "3"}, "mesure": "permis", "top": 30})`
  - `compter({"group_by": ["AN_DEPOT"], "filtres": {"TYPE_SERVICE_PUBLIC": "4"}, "mesure": "permis", "top": 30})`

## [transformations] Distribution des types de transformation de locaux

- **Constat** : Sur les 4245 permis de construire de locaux non résidentiels dans les Yvelines, 3487 (3487 sur 4245, soit 82,2 %) concernent une création de locaux sans transformation (TYPE_TRANSFO_PRINCIPAL vide). Les 469 permis de transformation de locaux (type 4) représentent 469 sur 4245, soit 11,1 % : ils sont principalement déposés par enterprise_autre (141), fonciere_investisseur (133) et collectivite_public (98). Les 224 permis de transformation logements → locaux (type 3) représentent 224 sur 4245, soit 5,3 % : fonciere_investisseur en dépose 73, collectivite_public 62. Les 52 permis de transformation locaux → logements (type 1) représentent 52 sur 4245, soit 1,2 %. Les 13 permis de transformation logements (type 2) représentent 13 sur 4245, soit 0,3 %.
- **Intérêt pour Buddimm** : Identifier les acteurs (bailleurs, promoteurs, foncières) les plus actifs sur les opérations de transformation, afin d’affiner la prospection et le conseil en matière de changement de destination ou de réhabilitation de locaux.
- **Fiabilité** : établi
- **Limites** : Les données ne distinguent pas les sous‑types de transformation (ex : changement de destination commerciale vs équipement social) et les périmètres de surface peuvent varier selon la lecture des formulaires.
- **À creuser** : Analyser les destinations d’origine et d’arrivée (DESTINATION_PRINCIPALE, DEST_SURF_MAX) pour chaque famille d’acteur afin de préciser les tendances de changement de destination.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:18:12)* :
  - `compter({"group_by": ["famille", "TYPE_TRANSFO_PRINCIPAL"], "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["TYPE_TRANSFO_PRINCIPAL"], "mesure": "permis", "top": 20})`

## [transformations] Création de locaux sans transformation dominante

- **Constat** : Sur les 4245 permis de construire de locaux non résidentiels dans les Yvelines, 3487 (3487 sur 4245, soit 82,2 %) concernent une création de locaux sans transformation (TYPE_TRANSFO_PRINCIPAL vide). Parmi ceux‑ci, les destinations principales sont : service public / intérêt collectif (1225 permis), commerce (574), bureaux (397), entrepôt (348), industrie (342), habitation (321) et agriculture (235).
- **Intérêt pour Buddimm** : Mettre en évidence les usages dominants des nouveaux locaux (logements, commerce, bureaux, équipements publics) pour orienter la prospection de terrains ou de biens en vue de nouvelles opérations de création.
- **Fiabilité** : établi
- **Limites** : Le dictionnaire indique que DESTINATION_PRINCIPALE a été introduit en mai 2022 ; les périmètres antérieurs ne comportent pas cette variable.
- **À creuser** : Analyser l’évolution dans le temps de ces destinations selon les familles d’acteurs (bailleur_social, promoteur, etc.).
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:18:24)* :
  - `compter({"group_by": ["famille", "TYPE_TRANSFO_PRINCIPAL"], "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["TYPE_TRANSFO_PRINCIPAL"], "mesure": "permis", "top": 20})`
  - `compter({"group_by": ["TYPE_TRANSFO_PRINCIPAL", "DESTINATION_PRINCIPALE"], "mesure": "permis", "top": 50})`

## [transformations] Transformation de locaux (type 4) par acteur et destination

- **Constat** : Sur les 4245 permis de locaux non résidentiels dans les Yvelines, 469 (469 sur 4245, soit 11,1 %) sont des transformations de locaux (TYPE_TRANSFO_PRINCIPAL = 4). Les trois familles d’acteurs les plus actives sont enterprise_autre (141 permis), fonciere_investisseur (133) et collectivite_public (98). Les destinations principales issues de DESTINATION_PRINCIPALE sont le commerce (126 permis, 42 892 m²), les bureaux (106 permis, 24 193 m²) et les équipements de service public / intérêt collectif (90 permis, 63 699 m²).
- **Intérêt pour Buddimm** : Identifier les acteurs majeurs et les usages dominants (commerce, bureaux, équipements publics) pour cibler les opérations de réhabilitation ou de changement de destination de locaux existants.
- **Fiabilité** : établi
- **Limites** : Le comptage des destinations repose sur la variable DESTINATION_PRINCIPALE introduite en mai 2022 ; les périmètres antérieurs ne la comportent pas.
- **À creuser** : Analyser l’évolution temporelle de ces transformations et confronter aux projets de réhabilitation en cours.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:18:32)* :
  - `compter({"group_by": ["famille", "TYPE_TRANSFO_PRINCIPAL"], "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["TYPE_TRANSFO_PRINCIPAL"], "mesure": "permis", "top": 20})`
  - `compter({"group_by": ["TYPE_TRANSFO_PRINCIPAL", "DESTINATION_PRINCIPALE"], "mesure": "permis", "top": 50})`

## [dynamique] Répartition des permis par état d'avancement

- **Constat** : Sur les 4245 permis étudiés, on observe les répartitions suivantes : autorisés (ETAT_DAU=2) = 1644 soit 38,7 % (1644/4245) ; terminés (6) = 1241 soit 29,2 % (1241/4245) ; commencés (5) = 1146 soit 27,0 % (1146/4245) ; annulés (4) = 214 soit 5,0 % (214/4245).
- **Intérêt pour Buddimm** : Permet d'évaluer la capacité d'accueil des nouveaux projets et de cibler les actions de veille sur les projets en souffrance ou abandonnés.
- **Fiabilité** : établi
- **Limites** : Le statut ETAT_DAU reflète l'état connu à la date d'extraction ; il n'est pas possible de retracer l'historique complet de chaque permis pour distinguer « autorisés jamais commencés ».
- **À creuser** : Analyser le parcours des permis autorisés pour identifier ceux qui n'ont jamais été déclarés commencés.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:19:14)* :
  - `compter({"group_by": ["AN_DEPOT", "ETAT_DAU"], "mesure": "permis", "top": 20})`
  - `compter({"group_by": ["AN_DEPOT", "DESTINATION_PRINCIPALE", "ETAT_DAU"], "mesure": "permis", "top": 200})`
  - `compter({"group_by": ["famille", "ETAT_DAU"], "mesure": "permis", "top": 50})`
  - `compter({"group_by": ["ETAT_DAU"], "mesure": "permis", "top": 100})`

## [libre] Promoteurs : surface moyenne par permis très élevée

- **Constat** : Les 374 permis déposés par des promoteurs créent en moyenne 2 518 m² de surface (941 613 m² / 374), soit près du double de la moyenne globale du fichier (≈1 197 m² par permis). Cette famille représente 8,8 % des permis (374 sur 4 245) mais 18,5 % de la surface totale créée (941 613 m² sur 5 080 108 m²).
- **Intérêt pour Buddimm** : Identifier les promoteurs pour des opérations de grande envergure, cibler des projets de bureaux ou d’équipements lourds.
- **Fiabilité** : établi
- **Limites** : La moyenne est influencée par quelques très gros projets ; à affiner par type de local ou par commune.
- **À creuser** : Analyser les promoteurs par commune ou par année pour affiner la prospection.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:19:52)* :
  - `compter({"group_by": ["famille"], "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["famille", "AN_DEPOT"], "mesure": "permis", "top": 20})`
  - `compter({"group_by": ["COMM"], "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["AN_DEPOT", "famille"], "mesure": "permis", "top": 30})`
  - `compter({"group_by": ["famille"], "mesure": "surface_m2", "top": 30})`

## [libre] Fonciers investisseurs : part dominante de la surface créée

- **Constat** : Les 1 194 permis déposés par des fonciers investisseurs représentent 28,1 % des permis (1 194 sur 4 245) et 39,0 % de la surface totale créée (1 979 625 m² sur 5 080 108 m²). Ils sont ainsi le premier contributeur de surface malgré une moyenne de 1 658 m² par permis, supérieure à la moyenne globale (~1 197 m²).
- **Intérêt pour Buddimm** : Cibler les opérations de fonciers investisseurs pour des opérations de plus grande envergure, identifier des terrains ou des projets de développement commercial ou logistique.
- **Fiabilité** : établi
- **Limites** : La moyenne de surface par permis peut être faussée par quelques très gros projets ; à affiner par type de local.
- **À creuser** : Segmenter les fonciers investisseurs par commune ou par année pour affiner la prospection commerciale.
- *Requêtes (nvidia/nemotron-3.5-lightning-30b-a3b, 2026-11-22T16:20:02)* :
  - `compter({"group_by": ["famille"], "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["famille", "AN_DEPOT"], "mesure": "permis", "top": 20})`
  - `compter({"group_by": ["COMM"], "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["AN_DEPOT", "famille"], "mesure": "permis", "top": 30})`
  - `compter({"group_by": ["famille"], "mesure": "surface_m2", "top": 30})`
