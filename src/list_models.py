r"""Liste les modèles disponibles chez le fournisseur choisi (LLM_PROVIDER dans .env), et teste l'appel d'outils.

  python -X utf8 src\list_models.py            # liste
  python -X utf8 src\list_models.py --test     # + un petit appel avec un outil, sur le modèle configuré
"""
import argparse, json, urllib.request, urllib.error
from llm_classify import config


def _req(url, key, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "sitadel-prototype/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    c = config()
    print(f"fournisseur : {c['provider']} | modèle configuré : {c['model'] or '(vide)'} | clé présente : {bool(c['key'])}")
    if not c["key"]:
        raise SystemExit(f"Renseignez {c['key_name']} dans .env.")
    try:
        models = sorted(m["id"] for m in _req(c["models_url"], c["key"])["data"])
    except urllib.error.HTTPError as e:
        raise SystemExit(f"erreur {e.code} : {e.read().decode(errors='replace')[:300]}")
    print("\n".join(models))
    if a.test:
        if not c["model"]:
            raise SystemExit(f"Renseignez {c['model_name']} dans .env avec un des modèles ci-dessus.")
        tool = {"type": "function", "function": {"name": "addition", "description": "Additionne deux nombres.",
                "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                               "required": ["a", "b"]}}}
        try:
            r = _req(c["url"], c["key"], {"model": c["model"], "tools": [tool], "tool_choice": "auto",
                     "messages": [{"role": "user", "content": "Combien font 17 + 25 ? Utilise l'outil."}]})
            m = r["choices"][0]["message"]
            print("\ntest appel d'outil :", "OK" if m.get("tool_calls") else "AUCUN appel d'outil",
                  json.dumps(m.get("tool_calls"), ensure_ascii=False)[:300])
        except urllib.error.HTTPError as e:
            print(f"\ntest échoué {e.code} : {e.read().decode(errors='replace')[:400]}")


if __name__ == "__main__":
    main()
