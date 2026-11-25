# Constats de l'agent explorateur — claude

Modèle(s) : claude-opus-5-5 (session Claude Code) · 4 note(s). Requêtes jointes automatiquement par le code. À relire : le modèle peut se tromper.

## [medico_social] Les résidences médico-sociales et sociales des Yvelines sont portées par les promoteurs et les bailleurs, presque jamais par les associations

- **Constat** : 64 PC déclarent une résidence pour personnes âgées, hôtelière sociale, sociale ou pour handicapés (RESIDENCE 1, 4, 5 ou 6). Les promoteurs en déposent 26 (2 698 logements) et les bailleurs sociaux 23 (2 229 logements), soit 49 permis sur 64, environ 77 %. Les associations n'en déposent que 4 (56 logements). Les résidences pour personnes âgées, 33 PC, suivent un rythme de 3 à 5 permis par an de 2017 à 2021, puis 2 en 2022, 2 en 2023 et 1 en 2024.
- **Intérêt pour Buddimm** : Dans les Yvelines, les gestionnaires médico-sociaux ne construisent pas eux-mêmes leurs résidences : un promoteur ou un bailleur porte le permis. Pour Buddimm, l'enjeu est d'accompagner l'association dans ce montage (choix du porteur, programme, VEFA ou bail), pas seulement de la repérer comme demandeur.
- **Fiabilité** : fragile
- **Limites** : Le champ RESIDENCE n'est rempli que sur une minorité de permis ; l'absence de résidence déclarée ne prouve rien. Le recul après 2021 peut venir en partie du délai de remontée des dépôts récents.
- **À creuser** : Croiser ces 64 permis avec le fichier locaux pour repérer les associations gestionnaires présentes comme exploitants d'équipements.
- *Requêtes (claude-opus-5-5 (session Claude Code), 2026-11-22T01:16:58)* :
  - `compter({"group_by": ["famille"], "filtres": {"RESIDENCE": ["1", "4", "5", "6"]}, "mesure": "logements", "top": 10})`
  - `compter({"group_by": ["AN_DEPOT"], "filtres": {"RESIDENCE": "1"}, "mesure": "permis", "top": 20})`
  - `compter({"group_by": ["RESIDENCE"], "filtres": {"famille": ["association_ess", "exploitant_sante_social"]}, "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["SIREN_DEM"], "filtres": {"famille": ["association_ess", "exploitant_sante_social"]}, "mesure": "permis", "top": 8})`

## [libre] Reconversion d'équipements publics en logements : beaucoup de petites opérations de collectivités, quelques grosses de promoteurs

- **Constat** : 38 PC transforment principalement des locaux de service public ou d'intérêt collectif en logements. Les collectivités en portent 11, soit 29 % (11 sur 38), mais seulement 69 logements. Les promoteurs en portent 7 pour 261 logements, les foncières 9 pour 183, les bailleurs sociaux 5 pour 55 et les associations 3 pour 34.
- **Intérêt pour Buddimm** : Ces reconversions (bâtiments communaux, anciens équipements) sont des montages complexes. Les petites opérations de collectivités signalent des communes des Yvelines qui valorisent leur patrimoine bâti : des bâtiments publics potentiellement mobilisables pour un projet associatif ou de logement social.
- **Fiabilité** : fragile
- **Limites** : Petits effectifs (38 permis). Le type de transformation est recodé par le SDES à partir des surfaces.
- **À creuser** : Lister les communes concernées et la surface publique transformée.
- *Requêtes (claude-opus-5-5 (session Claude Code), 2026-11-22T01:17:21)* :
  - `compter({"group_by": ["CJ_DEM"], "filtres": {"famille": "promoteur"}, "mesure": "acteurs", "top": 6})`
  - `compter({"group_by": ["famille"], "filtres": {"TYPE_TRANSFO_PRINCIPAL": "1", "TYPE_PRINCIP_LOCAUX_TRANSFORMES": "9"}, "mesure": "logements", "top": 8})`

## [medico_social] Les associations sont des maîtres d'ouvrage occasionnels, et le champ RESIDENCE ne les voit presque pas

- **Constat** : 30 demandeurs des familles association_ess ou exploitant_sante_social déposent 47 PC. Seuls 6 en déposent plus d'un (6, 6, 3, 3, 3 et 2 permis) : les autres n'ont qu'un permis sur toute la période. Sur ces 47 permis, 41 ont RESIDENCE non rempli, soit 87 % (41 sur 47), alors que ces structures portent souvent de l'hébergement spécifique.
- **Intérêt pour Buddimm** : C'est le profil d'un client de direction immobilière externalisée : une structure qui construit rarement et sans équipe immobilière. Pour les repérer, il faut partir de la forme juridique du demandeur (association, fondation) et non du champ RESIDENCE.
- **Fiabilité** : établi
- **Limites** : Seuls les permis déposés au nom de l'association sont comptés ; un projet associatif porté par un bailleur ou une SCI n'apparaît pas sous l'association.
- **À creuser** : Suivre les 6 associations qui déposent plusieurs permis, et les permis associatifs autorisés mais pas commencés.
- *Requêtes (claude-opus-5-5 (session Claude Code), 2026-11-22T16:15:25)* :
  - `compter({"group_by": ["famille"], "filtres": {"RESIDENCE": ["1", "4", "5", "6"]}, "mesure": "logements", "top": 10})`
  - `compter({"group_by": ["RESIDENCE"], "filtres": {"famille": ["association_ess", "exploitant_sante_social"]}, "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["SIREN_DEM"], "filtres": {"famille": ["association_ess", "exploitant_sante_social"]}, "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["famille"], "filtres": {"famille": ["association_ess", "exploitant_sante_social"]}, "mesure": "permis", "top": 5})`
  - `compter({"group_by": ["CJ_DEM"], "filtres": {"famille": "promoteur"}, "mesure": "logements", "top": 6})`
  - `compter({"group_by": ["famille"], "mesure": "permis", "top": 10})`

## [medico_social] La promotion des Yvelines passe surtout par des sociétés de construction-vente à usage unique : le vrai promoteur est masqué

- **Constat** : La famille promoteur dépose 1 146 PC. Les SCI de construction-vente (CJ 6541) en déposent 484, soit 42,2 % (484 sur 1 146), pour 27 254 logements, mais ce sont 426 sociétés différentes : à peine plus d'un permis chacune. À l'inverse, les SAS déposent 299 permis pour 123 demandeurs et les SNC 140 permis pour 52 demandeurs.
- **Intérêt pour Buddimm** : Compter les permis par SIREN sous-estime fortement la récurrence des grands promoteurs. Pour savoir qui construit régulièrement (partenaires possibles en VEFA pour un bailleur ou une association), il faut rattacher chaque société de programme à son groupe.
- **Fiabilité** : établi
- **Limites** : La famille promoteur des SCI de construction-vente vient de leur catégorie juridique, sans vérification individuelle.
- **À creuser** : Rattacher les sociétés de programme à leur gérant personne morale (fait dans out_fouille/groupes_synthese.csv) et recalculer la récurrence par groupe.
- *Requêtes (claude-opus-5-5 (session Claude Code), 2026-11-22T16:15:28)* :
  - `compter({"group_by": ["famille"], "filtres": {"RESIDENCE": ["1", "4", "5", "6"]}, "mesure": "logements", "top": 10})`
  - `compter({"group_by": ["RESIDENCE"], "filtres": {"famille": ["association_ess", "exploitant_sante_social"]}, "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["SIREN_DEM"], "filtres": {"famille": ["association_ess", "exploitant_sante_social"]}, "mesure": "permis", "top": 10})`
  - `compter({"group_by": ["famille"], "filtres": {"famille": ["association_ess", "exploitant_sante_social"]}, "mesure": "permis", "top": 5})`
  - `compter({"group_by": ["CJ_DEM"], "filtres": {"famille": "promoteur"}, "mesure": "logements", "top": 6})`
  - `compter({"group_by": ["famille"], "mesure": "permis", "top": 10})`
