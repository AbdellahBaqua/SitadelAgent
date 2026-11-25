r"""Vérifie après coup les chiffres de toutes les notes de l'agent explorateur.

  python -X utf8 src\verifier_notes.py

Pour chaque note de out/insights_agent.jsonl, rejoue les requêtes jointes (compter / profil_acteur)
plus l'aperçu, puis cherche chaque nombre de la note dans ces résultats (même règle que le garde-fou en direct).
Écrit out/verification_chiffres.md.
"""
import json, re
import explore as E
from settings import OUT

SRC = OUT / "insights_agent.jsonl"
REQ = re.compile(r"^(compter|profil_acteur)\((.*)\)$", re.S)


def rejouer(requete):
    m = REQ.match(requete.strip())
    if not m:
        return {"erreur": "requête illisible"}
    try:
        a = json.loads(m.group(2))
        return E.compter(**a) if m.group(1) == "compter" else E.profil_acteur(**a)
    except (json.JSONDecodeError, TypeError) as e:
        return {"erreur": str(e)}


def main():
    notes = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
    apercu = E.apercu()
    lignes = ["# Vérification automatique des chiffres des notes\n",
              "Règle : chaque nombre > 10 d'une note doit apparaître dans un résultat des requêtes jointes (ou de l'aperçu) ; "
              "un pourcentage doit correspondre au rapport de deux nombres de ces résultats (± 0,6 point). "
              "Les totaux de colonnes sont acceptés.\n",
              "| Modèle | Thème | Note | Chiffres non retrouvés |", "|---|---|---|---|"]
    resultats = []
    for n in notes:
        sorties = [apercu] + [rejouer(q) for q in n.get("requetes_justificatives", [])]
        manquants = E.verifier_chiffres(n, sorties)
        resultats.append({"modele": n.get("modele", ""), "theme": n.get("theme", ""), "titre": n.get("titre", ""),
                          "fiabilite": n.get("fiabilite", ""), "constat": n.get("constat", ""),
                          "interet_buddimm": n.get("interet_buddimm", ""), "chiffres_non_verifies": manquants})
        lignes.append(f"| {n.get('modele', '')} | {n.get('theme', '')} | {n.get('titre', '')[:70]} | "
                      f"{', '.join(manquants) if manquants else 'aucun'} |")
        print(f"{n.get('modele', '')[:22]:22s} {n.get('titre', '')[:60]:60s} -> {', '.join(manquants) or 'OK'}")
    (OUT / "verification_chiffres.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    (OUT / "verification_chiffres.json").write_text(json.dumps(resultats, ensure_ascii=False, indent=1), encoding="utf-8")
    print("écrit", OUT / "verification_chiffres.md")


if __name__ == "__main__":
    main()
