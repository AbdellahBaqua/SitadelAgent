# Constats de l'agent explorateur — claude

Modèle(s) : claude-opus-5-5 (session Claude Code) · 4 note(s). Requêtes jointes automatiquement par le code. À relire : le modèle peut se tromper.

## [libre] Transformations de locaux : surtout des réhabilitations sans changement de destination

- **Constat** : 469 PC transforment des locaux non résidentiels (TYPE_TRANSFO_PRINCIPAL 4). Le premier flux en surface reste dans le service public : 56 permis pour 37 567 m², soit 12 % des permis (56 sur 469). Vient ensuite commerce vers commerce, 44 permis pour 24 593 m². Les vrais changements de destination sont plus petits : bureaux vers entrepôt, 10 permis pour 12 339 m², et industrie vers entrepôt, 6 permis pour 9 661 m².
- **Intérêt pour Buddimm** : Dans les Yvelines, la transformation de locaux est d'abord de la remise à niveau d'équipements publics et de commerces, pas de la reconversion massive de bureaux. Pour un acteur médico-social qui cherche des locaux, les reconversions de bureaux restent rares et ponctuelles.
- **Fiabilité** : fragile
- **Limites** : Destination d'origine et destination d'arrivée sont recodées (la seconde par le code, d'après la plus grande surface créée). Petits effectifs pour les changements de destination.
- **À creuser** : Localiser les reconversions bureaux vers entrepôt et commerce vers hébergement.
- *Requêtes (claude-opus-5-5 (session Claude Code), 2026-11-22T01:19:03)* :
  - `compter({"group_by": ["DENOM_DEM", "famille"], "mesure": "permis", "top": 6})`
  - `compter({"group_by": ["DEST_SURF_MAX"], "filtres": {"famille": "collectivite_public"}, "mesure": "permis", "top": 4})`
  - `compter({"group_by": ["TYPE_PRINCIP_LOCAUX_TRANSFORMES", "DEST_SURF_MAX"], "filtres": {"TYPE_TRANSFO_PRINCIPAL": "4"}, "mesure": "surface_m2", "top": 5})`

## [medico_social] Équipements de santé : les associations créent le plus de surface, mais un seul projet en pèse près de la moitié

- **Constat** : 176 PC créent des équipements de santé (TYPE_SERVICE_PUBLIC 3) pour 236 413 m². Les associations en créent 79 217 m², soit 33,5 % (79 217 sur 236 413), sur 32 permis portés par 21 demandeurs, devant les foncières (50 132 m²) et les collectivités (45 083 m², mais 67 permis). Un seul projet, MGEN UNION à La Verrière, compte 36 628 m², soit 46 % (36 628 sur 79 217) de la surface associative. Suivent FONDATION DES AMIS DE L'ATELIER aux Mureaux (9 587 m²), CHEMINS D'ESPERANCE à Vélizy-Villacoublay (6 591 m²) et FONDATION LEOPOLD BELLAN à Magnanville (5 787 m²).
- **Intérêt pour Buddimm** : Les associations et fondations de santé des Yvelines construisent des équipements de taille significative, en général une seule fois : c'est le cœur de cible de Buddimm. La liste des 21 demandeurs associatifs en santé est une liste de prospects directement exploitable.
- **Fiabilité** : établi
- **Limites** : TYPE_SERVICE_PUBLIC vient du formulaire et est souvent non rempli : d'autres équipements de santé existent sans être repérés. La surface créée ne dit rien de la surface totale du bâtiment.
- **À creuser** : Croiser ces 21 associations avec le fichier logements (résidences, foyers) pour repérer celles qui portent plusieurs types de projets.
- *Requêtes (claude-opus-5-5 (session Claude Code), 2026-11-22T16:16:18)* :
  - `compter({"group_by": ["TYPE_SERVICE_PUBLIC"], "filtres": {"TYPE_SERVICE_PUBLIC": ["3", "4"]}, "mesure": "surface_m2", "top": 5})`
  - `compter({"group_by": ["famille"], "filtres": {"TYPE_SERVICE_PUBLIC": "3"}, "mesure": "surface_m2", "top": 9})`
  - `compter({"group_by": ["famille"], "filtres": {"TYPE_SERVICE_PUBLIC": "4"}, "mesure": "surface_m2", "top": 9})`
  - `compter({"group_by": ["DENOM_DEM", "ADR_LOCALITE_TER"], "filtres": {"TYPE_SERVICE_PUBLIC": "3", "famille": "association_ess"}, "mesure": "surface_m2", "top": 6})`
  - `compter({"group_by": ["DENOM_DEM", "famille"], "mesure": "permis", "top": 8})`
  - `compter({"group_by": ["DEST_SURF_MAX"], "filtres": {"famille": "collectivite_public"}, "mesure": "permis", "top": 4})`

## [medico_social] Action sociale : beaucoup de petits équipements de collectivités, peu de surface associative

- **Constat** : 231 PC créent des équipements d'action sociale (TYPE_SERVICE_PUBLIC 4) pour 85 879 m². Les collectivités en déposent 93, soit 40 % (93 sur 231), pour 30 311 m². Les promoteurs en déposent 25 pour 25 730 m². Les associations en déposent aussi 25, mais pour seulement 5 568 m². Les exploitants privés de santé et de social en déposent 38, pour 1 023 m² au total : de très petites créations de surface.
- **Intérêt pour Buddimm** : L'action sociale (crèches, centres sociaux, accueils de jour) est surtout une affaire de collectivités et de petits projets. Les associations y sont présentes mais sur de petites surfaces : besoins d'accompagnement plus légers, ou projets portés par d'autres pour leur compte.
- **Fiabilité** : fragile
- **Limites** : Même limite de remplissage de TYPE_SERVICE_PUBLIC. Les exploitants privés sont repérés par leur activité (NAF) et par l'agent de classification, moins fiable que la catégorie juridique.
- **À creuser** : Identifier les promoteurs qui construisent des équipements d'action sociale (souvent en rez-de-chaussée de programmes de logements), et la nature des 38 petits permis d'exploitants privés.
- *Requêtes (claude-opus-5-5 (session Claude Code), 2026-11-22T16:16:19)* :
  - `compter({"group_by": ["TYPE_SERVICE_PUBLIC"], "filtres": {"TYPE_SERVICE_PUBLIC": ["3", "4"]}, "mesure": "surface_m2", "top": 5})`
  - `compter({"group_by": ["famille"], "filtres": {"TYPE_SERVICE_PUBLIC": "3"}, "mesure": "surface_m2", "top": 9})`
  - `compter({"group_by": ["famille"], "filtres": {"TYPE_SERVICE_PUBLIC": "4"}, "mesure": "surface_m2", "top": 9})`
  - `compter({"group_by": ["DENOM_DEM", "ADR_LOCALITE_TER"], "filtres": {"TYPE_SERVICE_PUBLIC": "3", "famille": "association_ess"}, "mesure": "surface_m2", "top": 6})`
  - `compter({"group_by": ["DENOM_DEM", "famille"], "mesure": "permis", "top": 8})`
  - `compter({"group_by": ["DEST_SURF_MAX"], "filtres": {"famille": "collectivite_public"}, "mesure": "permis", "top": 4})`

## [medico_social] Les grands déposants de locaux sont des collectivités, avec une exception associative : la Fondation Mallet

- **Constat** : Parmi les 6 premiers déposants de PC de locaux non résidentiels des Yvelines, 5 sont des collectivités : DEPARTEMENT DES YVELINES (54 permis, 115 560 m²), GRAND PARIS SEINE ET OISE (29), REGION ILE DE FRANCE (26), COMMUNE DE MANTES LA VILLE (26) et COMMUNE DE POISSY (19). La sixième est une fondation, FONDATION MALLET (28 permis, 13 268 m²). Les collectivités déposent 1 132 permis, dont 940 en service public ou d'intérêt collectif, soit 83 % (940 sur 1 132).
- **Intérêt pour Buddimm** : La Fondation Mallet est un maître d'ouvrage associatif récurrent, ce qui est rare : un compte à suivre de près. Les collectivités sont les premiers donneurs d'ordre d'équipements ; elles sont aussi des propriétaires de foncier et de bâtiments avec qui les associations clientes de Buddimm montent leurs projets.
- **Fiabilité** : établi
- **Limites** : Compte par SIREN : les services et établissements publics rattachés à une même collectivité ne sont pas regroupés.
- **À creuser** : Détailler les 28 permis de la Fondation Mallet (communes, années, destinations).
- *Requêtes (claude-opus-5-5 (session Claude Code), 2026-11-22T16:16:21)* :
  - `compter({"group_by": ["TYPE_SERVICE_PUBLIC"], "filtres": {"TYPE_SERVICE_PUBLIC": ["3", "4"]}, "mesure": "surface_m2", "top": 5})`
  - `compter({"group_by": ["famille"], "filtres": {"TYPE_SERVICE_PUBLIC": "3"}, "mesure": "surface_m2", "top": 9})`
  - `compter({"group_by": ["famille"], "filtres": {"TYPE_SERVICE_PUBLIC": "4"}, "mesure": "surface_m2", "top": 9})`
  - `compter({"group_by": ["DENOM_DEM", "ADR_LOCALITE_TER"], "filtres": {"TYPE_SERVICE_PUBLIC": "3", "famille": "association_ess"}, "mesure": "surface_m2", "top": 6})`
  - `compter({"group_by": ["DENOM_DEM", "famille"], "mesure": "permis", "top": 8})`
  - `compter({"group_by": ["DEST_SURF_MAX"], "filtres": {"famille": "collectivite_public"}, "mesure": "permis", "top": 4})`
