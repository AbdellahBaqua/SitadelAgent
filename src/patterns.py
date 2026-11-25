"""Détection de patterns exploitables pour Buddimm -> out/patterns.md

Chaque pattern indique : ce qu'il montre, pourquoi c'est utile (métier), les champs sources et sa fiabilité.
Familles : règles (rules.py) puis, pour les ambigus, conclusions de l'agent (out/agent_cache.json) si présentes.
"""
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import load, rules
from llm_classify import RESIDENCE_LABELS
from settings import OUT, SRC_DATASET, src_entreprise

AUJOURDHUI = datetime.now().date()
TRANSFO_LOCAUX = {"3": "bureaux", "4": "commerce", "6": "industrie", "8": "entrepôt", "9": "service public / intérêt collectif"}


def familles(acteurs):
    cache_f = OUT / "agent_cache.json"
    cache = json.loads(cache_f.read_text(encoding="utf-8")) if cache_f.exists() else {}
    res = {}
    for s, a in acteurs.items():
        r = rules.classify(a)
        if r["needs_llm"] and s in cache:
            res[s] = (cache[s]["famille"], "agent")
        else:
            res[s] = (r["famille"], "regle" if not r["needs_llm"] else "aucune")
    return res


def tab(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def link(s, label=None):
    return f"[{label or s}]({src_entreprise(s)})"


def main():
    permis = [r for r in load.read_permis() if load.in_scope(r)]
    acteurs = load.aggregate(permis)
    fam = familles(acteurs)
    by = defaultdict(list)
    for r in permis:
        by[r["SIREN_DEM"]].append(r)
    md = [f"# Patterns — permis de construire, Yvelines (personnes morales)\n",
          f"Généré le {AUJOURDHUI} · {len(permis)} PC · {len(acteurs)} demandeurs · source : [fichier SDES]({SRC_DATASET}) "
          "+ [Annuaire des entreprises](https://annuaire-entreprises.data.gouv.fr/).\n",
          f"Familles : {dict(Counter(f for f, _ in fam.values()).most_common())}. "
          f"« non_determine » = {sum(1 for f, _ in fam.values() if f == 'non_determine')} demandeurs non classés (honnêtement laissés tels quels).\n"]

    # 1. Récurrents
    rec = [(s, a) for s, a in acteurs.items() if a["n_permis"] >= 4 and len(a["annees"]) >= 3]
    rec.sort(key=lambda x: -x[1]["n_permis"])
    md.append("## 1. Constructeurs récurrents\n"
              "**Critère** : au moins 4 PC sur au moins 3 années de dépôt différentes. **Utilité** : acteurs qui ont une "
              "filière de projets continue, donc des besoins répétés (maîtrise d'ouvrage, pilotage). "
              "**Champs** : `SIREN_DEM`, `AN_DEPOT`, `NB_LGT_TOT_CREES`. **Fiabilité** : bonne (comptage direct), "
              "un permis modificatif n'a pas de ligne propre, donc les volumes sont plutôt sous-estimés.\n")
    md.append(f"{len(rec)} acteurs. Répartition par famille : {dict(Counter(fam[s][0] for s, _ in rec).most_common())}\n")
    md.append(tab(["Demandeur", "Famille", "PC", "Années", "Logements", "Communes"],
                  [[link(s, a["denom"][:38]), fam[s][0], a["n_permis"], f"{min(a['annees'])}-{max(a['annees'])}",
                    a["logements"], len(a["communes"])] for s, a in rec[:15]]))

    # 2. Montée en charge
    def vol(s, y0, y1):
        return sum(int(r["NB_LGT_TOT_CREES"] or 0) for r in by[s] if y0 <= int(r["AN_DEPOT"] or 0) <= y1)
    mont = [(s, vol(s, 2021, 2023), vol(s, 2024, 2026)) for s in acteurs]
    mont = [(s, a, b) for s, a, b in mont if b >= 30 and b >= 2 * max(a, 1)]
    mont.sort(key=lambda x: -x[2])
    md.append("\n## 2. Montée en charge récente\n"
              "**Critère** : logements créés par les permis déposés en 2024-2026 ≥ 30 et ≥ 2× ceux de 2021-2023. "
              "**Utilité** : acteurs en croissance, à repérer tôt. **Champs** : `AN_DEPOT`, `NB_LGT_TOT_CREES`. "
              "**Fiabilité** : moyenne (2026 est une année partielle ; des dépôts récents ne sont pas encore tous remontés).\n")
    md.append(tab(["Demandeur", "Famille", "Logts 2021-23", "Logts 2024-26"],
                  [[link(s, acteurs[s]["denom"][:38]), fam[s][0], a, b] for s, a, b in mont[:12]]))

    # 3. Signaux médico-sociaux
    ms = [r for r in permis if r["RESIDENCE"] in ("1", "4", "5", "6", "7", "8")]
    md.append("\n## 3. Projets de résidences à vocation médico-sociale / sociale\n"
              "**Critère** : champ `RESIDENCE` renseigné (personnes âgées, hôtelière sociale, sociale, handicapés, autre, mixte). "
              "**Utilité** : c'est le cœur de cible de Buddimm. **Fiabilité** : **fragile** : champ rempli sur moins de 3 % des "
              "permis seulement et introduit en mai 2022 pour les `RES_*` ; l'absence ne prouve rien.\n")
    md.append(f"{len(ms)} permis. Par type : {dict(Counter(RESIDENCE_LABELS[r['RESIDENCE']] for r in ms).most_common())}\n")
    ms_sorted = sorted(ms, key=lambda r: -int(r["AN_DEPOT"] or 0))[:12]
    md.append(tab(["Demandeur", "Famille", "Type", "Année", "Logements", "État"],
                  [[link(r["SIREN_DEM"], r["DENOM_DEM"][:34]), fam[r["SIREN_DEM"]][0], RESIDENCE_LABELS[r["RESIDENCE"]],
                    r["AN_DEPOT"], r["NB_LGT_TOT_CREES"], {"2": "autorisé", "4": "annulé", "5": "commencé", "6": "terminé"}.get(r["ETAT_DAU"], "")]
                   for r in ms_sorted]))

    # 4. Associations / ESS / exploitants
    cibles = [(s, a) for s, a in acteurs.items() if fam[s][0] in ("association_ess", "exploitant_sante_social")]
    cibles.sort(key=lambda x: -x[1]["n_permis"])
    md.append("\n## 4. Associations, ESS et exploitants santé/social qui construisent\n"
              "**Critère** : famille `association_ess` ou `exploitant_sante_social`. **Utilité** : prospects naturels "
              "(maîtres d'ouvrage non professionnels de l'immobilier). **Fiabilité** : bonne pour les associations "
              "(catégorie juridique Sirène), moyenne pour les exploitants (déduits du NAF de l'établissement).\n")
    md.append(f"{len(cibles)} acteurs.\n")
    md.append(tab(["Demandeur", "Famille", "PC", "Années", "Logements"],
                  [[link(s, a["denom"][:38]), fam[s][0], a["n_permis"], f"{min(a['annees'])}-{max(a['annees'])}", a["logements"]]
                   for s, a in cibles[:15]]))

    # 5. Reconversions de locaux
    rec_loc = [r for r in permis if r["TYPE_TRANSFO_PRINCIPAL"] == "1" and r["TYPE_PRINCIP_LOCAUX_TRANSFORMES"] in TRANSFO_LOCAUX]
    md.append("\n## 5. Reconversions de locaux en logements\n"
              "**Critère** : `TYPE_TRANSFO_PRINCIPAL` = 1 (locaux transformés en logements) avec le type d'origine renseigné. "
              "**Utilité** : montages complexes (changement de destination) où un appui MOA a de la valeur ; l'origine "
              "« service public / intérêt collectif » ou « bureaux » signale de la reconversion d'équipements. "
              "**Fiabilité** : moyenne (champs recodés par le SDES à partir des surfaces ; dits introduits en mai 2022 mais "
              "renseignés dès 2012 dans le fichier).\n")
    md.append(f"{len(rec_loc)} permis. Origine : {dict(Counter(TRANSFO_LOCAUX[r['TYPE_PRINCIP_LOCAUX_TRANSFORMES']] for r in rec_loc).most_common())}. "
              f"Par famille de demandeur : {dict(Counter(fam[r['SIREN_DEM']][0] for r in rec_loc).most_common())}\n")

    # 6. Dormants
    seuil = (AUJOURDHUI - timedelta(days=3 * 365)).isoformat()
    dorm = [r for r in permis if r["ETAT_DAU"] == "2" and r["DATE_REELLE_AUTORISATION"] and r["DATE_REELLE_AUTORISATION"] < seuil
            and int(r["AN_DEPOT"] or 0) >= 2018]
    dorm_a = Counter(r["SIREN_DEM"] for r in dorm)
    md.append("\n## 6. Permis autorisés depuis plus de 3 ans et jamais remontés comme commencés\n"
              "**Critère** : `ETAT_DAU` = 2 (autorisé), autorisation datant de plus de 3 ans, déposé depuis 2018. "
              "**Utilité** : projets potentiellement bloqués ou abandonnés, où un acteur pourrait chercher de l'aide ou un repreneur. "
              "**Fiabilité** : **faible** : environ 15 % des ouvertures de chantier ne remontent jamais dans la base ; un "
              "permis « dormant » est peut-être simplement un chantier non déclaré. À traiter comme hypothèse à vérifier.\n")
    md.append(f"{len(dorm)} permis, {len(dorm_a)} acteurs. Par famille : {dict(Counter(fam[r['SIREN_DEM']][0] for r in dorm).most_common())}\n")
    md.append(tab(["Demandeur", "Famille", "Permis dormants"],
                  [[link(s, acteurs[s]["denom"][:38]), fam[s][0], n] for s, n in dorm_a.most_common(10)]))

    # 7. Annulations
    ann = [(s, sum(1 for r in by[s] if r["ETAT_DAU"] == "4"), a["n_permis"]) for s, a in acteurs.items() if a["n_permis"] >= 5]
    ann = [(s, k, n) for s, k, n in ann if k / n >= 0.3]
    ann.sort(key=lambda x: -x[1] / x[2])
    md.append("\n## 7. Acteurs à taux d'annulation élevé\n"
              "**Critère** : au moins 5 PC dont ≥ 30 % annulés (`ETAT_DAU` = 4). **Utilité** : acteurs dont les projets "
              "n'aboutissent pas (foncier, financement, recours) : besoin potentiel de sécurisation. **Fiabilité** : "
              "moyenne (l'état « annulé » n'est connu que si l'information est remontée).\n")
    md.append(tab(["Demandeur", "Famille", "Annulés", "PC"],
                  [[link(s, acteurs[s]["denom"][:38]), fam[s][0], k, n] for s, k, n in ann[:10]]))

    md.append("\n## Limites générales\n"
              "- Fichier « logements » uniquement : les locaux non résidentiels purs n'y figurent pas.\n"
              "- Un permis modificatif n'a pas de ligne propre ; une ligne = dernier état connu.\n"
              "- ~15 % des ouvertures de chantier et ~1/3 des achèvements ne remontent jamais.\n"
              "- NAF/SIRET des permis : établissement possiblement fermé ; la famille s'appuie d'abord sur la catégorie juridique.\n"
              "- Personnes morales uniquement ; aucun nom de personne physique n'est utilisé ni recherché.\n")
    (OUT / "patterns.md").write_text("\n".join(md), encoding="utf-8")
    print("écrit", OUT / "patterns.md")


if __name__ == "__main__":
    main()
