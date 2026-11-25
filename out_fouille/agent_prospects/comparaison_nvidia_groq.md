# Qualification des prospects : nvidia contre groq

- nvidia : `nvidia/nemotron-3-ultra-550b-a55b` ; groq : `openai/gpt-oss-120b`
- Échantillon : 25 prospects tirés au hasard (graine fixe) parmi ceux qui passent le pré-filtre du code ; 3 sont désormais écartés par le pré-filtre du code ; comparaison sur les 22 restants.
- **Accord sur le verdict : 17/22 (77 %)** ; accord sur l'adéquation : 10/22 (45 %).
- **Après le garde-fou « preuve dure » du code : accord sur le verdict 20/22 (91 %)** ; verdicts nvidia {'a_verifier': 5, 'prospect': 17}, groq {'faux_positif': 1, 'prospect': 16, 'a_verifier': 5}.
- Verdicts nvidia : {'prospect': 20, 'a_verifier': 2} ; groq : {'faux_positif': 1, 'prospect': 19, 'a_verifier': 2}.
- Fragilités relevées par le code (indice sans source, mémoire du modèle) : nvidia 1, groq 1.
- Garde-fous du code déclenchés (verdict ou adéquation corrigés) : nvidia 0, groq 0.
- Durée médiane par cas : nvidia 73 s, groq 17 s (pause entre appels comprise).

## Matrice de confusion (lignes : nvidia, colonnes : groq)

| | prospect | a_verifier | faux_positif |
|---|---|---|---|
| **prospect** | 17 | 2 | 1 |
| **a_verifier** | 2 | 0 | 0 |
| **faux_positif** | 0 | 0 | 0 |

## Désaccords sur le verdict

### ARAM ATELIERS RECH ARTIS ARTIST MAULDRE (SIREN 309206134)
- **nvidia** : prospect / moyenne — Association artistique/artisanale (ESS) – ateliers de recherche et création. Limites : Taille exacte inconnue (effectif NN) ; activité culturelle/artisanale et non sociale ou médico-sociale cœur de cible ; un seul permis récent, projet de faible envergure (surface créée 0 m²).
- **groq** : faux_positif / faible — Association culturelle/artistique (ESS) sans activité médico‑sociale apparente.. Limites : L'activité de l'association (artisanal/artistique) n'est pas clairement liée au secteur social, médico‑social ou à l'ESS à forte dimension d'action sociale. Absence d'établissements FINESS et de projet immobilier clairement orienté vers des besoins d'action sociale.
- Source : https://annuaire-entreprises.data.gouv.fr/entreprise/309206134

### ESPERANCE BANLIEUES POISSY (SIREN 843651753)
- **nvidia** : a_verifier / faible — Association déclarée (ESS) « Autres organisations fonctionnant par adhésion volontaire » (NAF 94.99Z), petite taille (6‑9 salariés). Limites : NAF 94.99Z large, ne permet pas de confirmer ni d'exclure une activité d'enseignement scolaire (cas évident écarté par le code) ; taille petite (effectif 03) hors cœur de cible Buddimm (structures moyennes/grandes) ; permis unique et terminé, besoin immobilier actuel peu visible.
- **groq** : prospect / faible — Association déclarée d'intérêt général (ESS). Limites : Structure très petite (effectif 3, un seul établissement), aucune activité médico‑sociale identifiée, le projet de permis est de petite envergure et son statut « terminé » ne confirme pas la mise en œuvre.
- Source : https://annuaire-entreprises.data.gouv.fr/entreprise/843651753

### CPO FC CENTRE DE FORMATION PROFESIONNELLE CONTINUE (SIREN 785104563)
- **nvidia** : prospect / moyenne — Association déclarée de formation continue d'adultes (ESS). Limites : Permis unique et ancien (2014), annulé ; activité de formation continue non directement sanitaire/sociale ; effectif non connu (NN) ; pas de projet récent visible.
- **groq** : a_verifier / moyenne — Association de formation continue d'adultes. Limites : Pas de projet immobilier actif ou récent ; l'activité principale est la formation, pas directement liée au secteur social/medical ciblé.
- Source : https://annuaire-entreprises.data.gouv.fr/entreprise/785104563

### ASSOCIATION AMICALE FRANCO TURQUE (SIREN 393964010)
- **nvidia** : a_verifier / faible — Association culturelle/amicale (ESS) de très petite taille. Limites : Activité réelle non confirmée comme relevant du social, médico-social ou ESS à fort besoin immobilier (NAF 94.99Z large, dénomination culturelle). Très petite structure (effectif 01) qui a peu de projets selon l'hypothèse Buddimm, mais les permis montrent un besoin ponctuel significatif. À vérifier 
- **groq** : prospect / moyenne — Association de l'ESS, petite taille, activité non médico‑sociale clairement identifiée.. Limites : Absence de précision sur la finalité exacte du projet (culturel, social, administratif). Aucun établissement FINESS pour confirmer une activité médico‑sociale.
- Source : https://annuaire-entreprises.data.gouv.fr/entreprise/393964010

### FERME ECOLE GRAINES D'AVENIR (SIREN 884298035)
- **nvidia** : prospect / moyenne — Association ESS gérant un Lieu de Vie et d'Accueil (FINESS) et une ferme école (enseignement professionnel). Limites : Le permis indique une surface créée de 0 m² (possible rénovation ou changement de destination sans extension). L'activité principale (NAF) est l'enseignement, mais l'établissement FINESS confirme une activité médico-sociale (Lieu de Vie). La structure est petite (10-19 salariés), ce qui peut limiter
- **groq** : a_verifier / faible — Association de l'ESS à vocation éducative et sociale (ferme école).. Limites : L'activité principale est éducative (exclue) alors que l'établissement FINESS suggère une dimension sociale ; les informations sur le besoin immobilier sont insuffisantes.
- Source : https://annuaire-entreprises.data.gouv.fr/entreprise/884298035

