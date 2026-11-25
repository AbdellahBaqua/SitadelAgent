import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPARTEMENT = "78"      # périmètre du brief : permis dont le LIEU DES TRAVAUX est dans les Yvelines

# Jeu de données traité : DATASET=logements (défaut) ou DATASET=locaux (variable d'environnement)
DATASET = os.environ.get("DATASET", "logements").strip().lower()
_DATASETS = {
    "logements": {"csv": "data/sortie.csv", "out": "out", "dico": "dictionnaire_variables.txt",
                  "rid": "8b35affb-55fc-4c1f-915b-7750f974446a"},
    "locaux": {"csv": "data/sortie_locaux.csv", "out": "out_locaux", "dico": "dictionnaire_variables_locaux.txt",
               "rid": "f8f0700f-806c-40a7-83b1-f21cf507e7c4"},
}
if DATASET not in _DATASETS:
    raise SystemExit(f"DATASET inconnu : {DATASET} (choix : {', '.join(_DATASETS)})")
CSV_IN = ROOT / _DATASETS[DATASET]["csv"]      # extraction DiDo/SDES, département 78 (data/ : hors dépôt git)
OUT = ROOT / _DATASETS[DATASET]["out"]         # sorties séparées par jeu de données
OUT.mkdir(exist_ok=True)
DICO = ROOT / "config" / _DATASETS[DATASET]["dico"]

FAMILLES = [
    "bailleur_social", "promoteur", "fonciere_investisseur",
    "association_ess", "exploitant_sante_social", "collectivite_public",
    "copropriete", "entreprise_autre", "non_determine",
]

# Sources publiques citées pour chaque résultat
SRC_DATASET = ("https://www.statistiques.developpement-durable.gouv.fr/catalogue?page=datafile"
               f"&datafileRid={_DATASETS[DATASET]['rid']}")
def src_entreprise(siren: str) -> str:
    return f"https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}"
