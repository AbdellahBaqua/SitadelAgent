r"""Sépare les constats de l'agent explorateur par modèle, à partir de out/insights_agent.jsonl.

  python -X utf8 src\split_insights.py

Écrit out/insights_groq.md (modèles Groq), out/insights_gemini.md, out/insights_claude.md.
Relançable à tout moment : les fichiers sont régénérés depuis le journal JSON (source de vérité).
"""
import json
from collections import defaultdict
from settings import OUT

SRC = OUT / "insights_agent.jsonl"


def famille_modele(m):
    m = (m or "").lower()
    if "claude" in m:
        return "claude"
    if "gemini" in m:
        return "gemini"
    if m.startswith(("nvidia/", "mistralai/", "moonshotai/", "z-ai/")):
        return "nvidia"      # modèles servis par NVIDIA NIM
    return "groq"            # openai/gpt-oss-*, qwen… servis par Groq


def rendu(n):
    lignes = [f"## [{n.get('theme', '')}] {n.get('titre', '')}\n",
              f"- **Constat** : {n.get('constat', '')}",
              f"- **Intérêt pour Buddimm** : {n.get('interet_buddimm', '')}",
              f"- **Fiabilité** : {n.get('fiabilite', '')}",
              f"- **Limites** : {n.get('limites', '')}"]
    if n.get("a_creuser"):
        lignes.append(f"- **À creuser** : {n['a_creuser']}")
    if n.get("chiffres_non_verifies"):
        lignes.append(f"- ⚠️ **Chiffres non retrouvés dans les résultats d'outils** : {', '.join(n['chiffres_non_verifies'])}")
    lignes.append(f"- *Requêtes ({n.get('modele', '')}, {n.get('date', '')})* :")
    lignes += [f"  - `{q}`" for q in n.get("requetes_justificatives", [])[-6:]]
    return "\n".join(lignes) + "\n"


def main():
    notes = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
    par = defaultdict(list)
    for n in notes:
        par[famille_modele(n.get("modele"))].append(n)
    for fam, ns in par.items():
        modeles = sorted({n.get("modele", "") for n in ns})
        entete = (f"# Constats de l'agent explorateur — {fam}\n\n"
                  f"Modèle(s) : {', '.join(modeles)} · {len(ns)} note(s). Requêtes jointes automatiquement par le code. "
                  "À relire : le modèle peut se tromper.\n\n")
        (OUT / f"insights_{fam}.md").write_text(entete + "\n".join(rendu(n) for n in ns), encoding="utf-8")
        print(f"insights_{fam}.md : {len(ns)} note(s)")


if __name__ == "__main__":
    main()
