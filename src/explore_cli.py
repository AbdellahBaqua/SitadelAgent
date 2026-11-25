r"""Passerelle en ligne de commande vers les outils de l'agent explorateur (src/explore.py).

Permet à un autre « cerveau » (ici Claude, dans une session Claude Code) de jouer l'agent avec EXACTEMENT
les mêmes outils et les mêmes garde-fous que Groq/Gemini : une note est refusée sans requête préalable,
et les requêtes exécutées sont jointes automatiquement à chaque note.

  python -X utf8 src\explore_cli.py start medico_social
  python -X utf8 src\explore_cli.py apercu
  python -X utf8 src\explore_cli.py compter "{\"group_by\": [\"famille\"], \"filtres\": {\"RESIDENCE\": [\"1\"]}}"
  python -X utf8 src\explore_cli.py profil 402987622
  python -X utf8 src\explore_cli.py dico RESIDENCE
  python -X utf8 src\explore_cli.py noter "{\"titre\": ..., \"constat\": ..., ...}"
"""
import json, sys
import explore as E
from settings import OUT

STATE = OUT / "explore_cli_session.json"
MODELE = "claude-opus-5-5 (session Claude Code)"


def _state():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"theme": "libre", "requetes": []}


def _save(s):
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


TABLE = "--table" in sys.argv
if TABLE:
    sys.argv.remove("--table")


def main():
    cmd, args = sys.argv[1], sys.argv[2:]
    if args and args[0] == "-":                     # JSON lu sur l'entrée standard (évite les soucis de guillemets)
        args = [sys.stdin.buffer.read().decode("utf-8-sig")]
    s = _state()
    s.setdefault("sorties", []); s.setdefault("avertis", [])
    if cmd == "start":
        if args[0] not in E.THEMES:
            raise SystemExit(f"thème inconnu ; choix : {list(E.THEMES)}")
        s = {"theme": args[0], "requetes": [], "sorties": [], "avertis": []}
        out = {"theme": args[0], "consigne": E.THEMES[args[0]]}
    elif cmd == "apercu":
        out = E.apercu()
    elif cmd == "compter":
        a = json.loads(args[0])
        out = E.compter(**a)
        if "erreur" not in out:
            s["requetes"].append(f"compter({json.dumps(a, ensure_ascii=False)})")
    elif cmd == "profil":
        out = E.profil_acteur(args[0])
        if "erreur" not in out:
            s["requetes"].append(f"profil_acteur({{\"siren\": \"{args[0]}\"}})")
    elif cmd == "dico":
        out = E.lire_dictionnaire(args[0])
    elif cmd == "fraicheur":
        out = E.fraicheur_donnees()
    elif cmd == "rafraichir":                      # simulation par défaut ; --reel pour remplacer (si millésime plus récent)
        out = E.rafraichir_donnees(args[0] if args and not args[0].startswith("--") else None,
                                   simulation="--reel" not in sys.argv)
    elif cmd == "noter":
        a = json.loads(args[0])
        manquants = E.verifier_chiffres(a, s["sorties"]) if s["requetes"] else []
        if not s["requetes"]:
            out = {"erreur": "Refusé : vérifie d'abord avec compter ou profil_acteur."}
        elif manquants and a.get("titre") not in s["avertis"]:      # même règle que pour Groq/Gemini
            s["avertis"].append(a.get("titre"))
            out = {"erreur": f"Refusé : ces chiffres ne figurent dans aucun résultat d'outil : {', '.join(manquants)}. "
                             "Corrige-les ou fais la requête qui les donne. Chaque pourcentage doit citer son numérateur et son dénominateur dans la même phrase. Puis renote."}
        else:
            if manquants:
                a["chiffres_non_verifies"] = manquants
            E._ecrire_note(s["theme"], a, list(s["requetes"]), MODELE)
            out = {"ok": f"note enregistrée : {a.get('titre', '')}" + (" avec avertissement" if manquants else "")}
    else:
        raise SystemExit("commandes : start, apercu, compter, profil, dico, fraicheur, rafraichir, noter")
    if cmd not in ("start", "noter"):
        s["sorties"].append(out)              # résultats d'outils conservés pour vérifier les chiffres des notes
    _save(s)
    if TABLE and isinstance(out, dict) and "resultats" in out:     # affichage compact
        print(f"permis filtrés : {out['nb_permis_filtres']} | groupes : {out['nb_groupes']}")
        for r in out["resultats"]:
            print(" | ".join(str(v)[:45] for v in r.values()))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
