# Vérification automatique des chiffres des notes

Règle : chaque nombre > 10 d'une note doit apparaître dans un résultat des requêtes jointes (ou de l'aperçu) ; un pourcentage doit correspondre au rapport de deux nombres de ces résultats (± 0,6 point). Les totaux de colonnes sont acceptés.

| Modèle | Thème | Note | Chiffres non retrouvés |
|---|---|---|---|
| claude-opus-5-5 (session Claude Code) | medico_social | Les résidences médico-sociales et sociales des Yvelines sont portées p | aucun |
| claude-opus-5-5 (session Claude Code) | libre | Reconversion d'équipements publics en logements : beaucoup de petites  | aucun |
| nvidia/nemotron-3.5-lightning-30b-a3b | geographie | Dominance des promoteurs | aucun |
| nvidia/nemotron-3.5-lightning-30b-a3b | transformations | Promoteurs en tête des reconversions bureaux → logements | aucun |
| nvidia/nemotron-3.5-lightning-30b-a3b | dynamique | Répartition des permis par famille de demandeur | aucun |
| nvidia/nemotron-3.5-lightning-30b-a3b | dynamique | Pic des dépôts en 2021 puis recul | aucun |
| nvidia/nemotron-3.5-lightning-30b-a3b | libre | Foncier investisseur : spécialiste du logement individuel | 10 198, 51,8 % (base absente ou fausse dans la phrase), 758 |
| claude-opus-5-5 (session Claude Code) | medico_social | Les associations sont des maîtres d'ouvrage occasionnels, et le champ  | aucun |
| claude-opus-5-5 (session Claude Code) | medico_social | La promotion des Yvelines passe surtout par des sociétés de constructi | aucun |
| nvidia/nemotron-3.5-lightning-30b-a3b | libre | Promoteur dominant et focus sur le collectif | aucun |
