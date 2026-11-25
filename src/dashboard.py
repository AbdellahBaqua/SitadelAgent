r"""Tableau de bord HTML autonome des résultats (aucune bibliothèque externe, s'ouvre dans un navigateur).

  python -X utf8 src\dashboard.py        # -> out_fouille\dashboard.html

Lit : out/ et out_locaux/ (familles, constats vérifiés), out_fouille/ (groupes, croisement, profils).
Palette : 7 teintes catégorielles du skill dataviz, validées (validate_palette.js) en clair et en sombre.
"""
import csv, json
from collections import Counter
from datetime import date
from fouille_commun import ROOT, FOUILLE, permis, familles

FAMILLES_ORDRE = ["promoteur", "fonciere_investisseur", "collectivite_public", "bailleur_social",
                  "association_ess", "entreprise_autre", "exploitant_sante_social"]     # 7 couleurs fixes
LIB_FAM = {"promoteur": "Promoteur", "fonciere_investisseur": "Foncière / investisseur",
           "collectivite_public": "Collectivité / public", "bailleur_social": "Bailleur social",
           "association_ess": "Association / ESS", "entreprise_autre": "Autre entreprise",
           "exploitant_sante_social": "Exploitant santé / social", "copropriete": "Copropriété",
           "non_determine": "Non déterminé", "autres": "Autres (non déterminé, copropriété)"}
NOMS_PROFILS = {  # trait principal du centre (signe) -> nom lisible, calculé, stable d'une exécution à l'autre
    ("v_annees", 1): "Récurrents multi-communes", ("v_permis", 1): "Récurrents multi-communes",
    ("taux_annule", 1): "Projets annulés", ("v_taille", 1): "Programmes de logements de taille",
    ("v_logements", 1): "Programmes de logements de taille", ("part_locaux", 1): "Constructeurs de locaux ponctuels",
    ("taux_acheve", 1): "Petits projets achevés", ("part_locaux", -1): "Petits projets de logements en cours",
    ("part_medico", 1): "Orientés médico-social",
}


def lire_csv(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def lire_json(p, defaut=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else defaut


def donnees():
    fl, fc = familles("logements"), familles("locaux")
    profils = lire_json(FOUILLE / "profils_groupes.json", {})
    for g in profils.get("groupes", []):
        trait = max(g["z_centre"].items(), key=lambda kv: abs(kv[1]))
        g["nom"] = NOMS_PROFILS.get((trait[0], 1 if trait[1] > 0 else -1), f"Profil {g['groupe'] + 1}")
        fams = Counter()
        for f, n in g["familles"].items():
            fams[f if f in FAMILLES_ORDRE else "autres"] += n
        g["familles_pliees"] = [[f, fams[f]] for f in FAMILLES_ORDRE + ["autres"] if fams[f]]
    groupes = lire_csv(FOUILLE / "groupes_synthese.csv")
    societes = lire_csv(FOUILLE / "groupes_societes.csv")
    for g in groupes:
        for k in ("nb_societes", "permis_logements", "logements", "permis_locaux", "surface_m2", "annees_actives", "nb_communes"):
            g[k] = int(g[k] or 0)
    constats = []
    for jeu, dossier in (("logements", "out"), ("locaux", "out_locaux")):
        for n in lire_json(ROOT / dossier / "verification_chiffres.json", []):
            constats.append({**n, "jeu": jeu})
    return {
        "genere_le": date.today().isoformat(),
        "tuiles": {"permis_logements": len(permis("logements")), "permis_locaux": len(permis("locaux")),
                   "acteurs": profils.get("nb_acteurs", 0)},
        "familles": [{"famille": f, "libelle": LIB_FAM[f],
                      "logements": sum(1 for a in fl.values() if a["famille"] == f),
                      "locaux": sum(1 for a in fc.values() if a["famille"] == f)}
                     for f in FAMILLES_ORDRE + ["non_determine", "copropriete"]],
        "groupes": groupes[:15],
        "groupes_stats": {"societes": len(societes),
                          "rattachees": sum(1 for s in societes if s["methode"] == "dirigeant personne morale"),
                          "groupes": len(groupes),
                          "groupes_multi": sum(1 for g in groupes if g["nb_societes"] > 1)},
        "croisement": lire_json(FOUILLE / "croisement.json", {}),
        "profils": profils,
        "constats": constats,
        "prospects": lire_json(FOUILLE / "prospects_priorises.json", {}),
        "lib_fam": LIB_FAM, "familles_ordre": FAMILLES_ORDRE + ["autres"],
    }


HTML = r"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Permis de construire des Yvelines — qualification des demandeurs</title>
<style>
.viz-root{color-scheme:light;--surface-1:#fcfcfb;--page:#f9f9f7;--text-primary:#0b0b0b;--text-secondary:#52514e;
 --muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);
 --s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#6250d6;--other:#c3c2b7;--warn:#fab219;--good:#0ca30c}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])) .viz-root{color-scheme:dark;--surface-1:#1a1a19;--page:#0d0d0d;
 --text-primary:#f0efec;--text-secondary:#c3c2b7;--grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);
 --s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#0ca30c;--s7:#9085e9;--other:#52514e}}
:root[data-theme="dark"] .viz-root{color-scheme:dark;--surface-1:#1a1a19;--page:#0d0d0d;--text-primary:#f0efec;--text-secondary:#c3c2b7;
 --grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#0ca30c;--s7:#9085e9;--other:#52514e}
*{box-sizing:border-box}
body{margin:0}
.viz-root{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--page);color:var(--text-primary);min-height:100vh;line-height:1.45}
header{padding:28px 32px 8px;max-width:1180px;margin:0 auto;display:flex;justify-content:space-between;gap:16px;align-items:flex-start}
header h1{font-size:22px;margin:0 0 4px;font-weight:600}
header p{margin:0;color:var(--text-secondary);font-size:14px}
nav{max-width:1180px;margin:0 auto;padding:6px 32px 0;display:flex;gap:18px;flex-wrap:wrap;font-size:14px}
nav a{color:var(--text-secondary);text-decoration:none}nav a:hover{color:var(--text-primary);text-decoration:underline}
main{max-width:1180px;margin:0 auto;padding:16px 32px 48px;display:grid;gap:20px}
.card{background:var(--surface-1);border:1px solid var(--border);border-radius:12px;padding:20px 22px;overflow-x:auto}
.card h2{font-size:17px;margin:0 0 4px;font-weight:600}
.card .sub{color:var(--text-secondary);font-size:13.5px;margin:0 0 14px}
.tiles{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:16px}
.tile .label{color:var(--text-secondary);font-size:13px}.tile .value{font-size:30px;font-weight:600}.tile.hero .value{font-size:52px}
.tile .note{color:var(--muted);font-size:12.5px}
svg text{font-family:inherit}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--text-secondary);margin:0 0 10px}
.legend span{display:inline-flex;align-items:center;gap:6px}.legend i{width:10px;height:10px;border-radius:3px;display:inline-block}
details{margin-top:10px;font-size:13px}summary{cursor:pointer;color:var(--text-secondary)}
table{border-collapse:collapse;width:100%;margin-top:8px;font-size:13px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--grid);vertical-align:top}
th{color:var(--text-secondary);font-weight:600}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
a{color:var(--s1)}
.tip{position:fixed;pointer-events:none;background:var(--surface-1);color:var(--text-primary);border:1px solid var(--border);
 border-radius:8px;padding:8px 10px;font-size:12.5px;box-shadow:0 4px 16px rgba(0,0,0,.12);max-width:320px;display:none;z-index:9}
.profils{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}
.profil{border:1px solid var(--border);border-radius:10px;padding:14px}
.profil h3{margin:0 0 2px;font-size:15px}.profil .eff{color:var(--text-secondary);font-size:13px}
.profil p{font-size:13px;color:var(--text-secondary);margin:6px 0}
.seg{display:flex;gap:2px;height:28px;margin:8px 0}
.seg div{border-radius:4px;min-width:2px;display:flex;align-items:center;padding-left:6px;font-size:12px;color:#fff;white-space:nowrap;overflow:visible}
.pill{display:inline-block;font-size:12px;padding:1px 8px;border-radius:10px;border:1px solid var(--border);color:var(--text-secondary)}
.ok{color:var(--good)}.ko{color:var(--text-primary)}
.ko::before{content:"⚠ ";color:var(--warn)}
.ok::before{content:"✓ "}
button.theme{background:var(--surface-1);color:var(--text-primary);border:1px solid var(--border);border-radius:8px;padding:6px 10px;cursor:pointer;font:inherit;font-size:13px}
.limites li{margin:4px 0;font-size:13.5px;color:var(--text-secondary)}
@media (max-width:820px){.tiles{grid-template-columns:1fr 1fr}header,nav,main{padding-left:16px;padding-right:16px}}
</style></head>
<body><div class="viz-root">
<header><div><h1>Qui construit dans les Yvelines ?</h1>
<p>Permis de construire déposés par des personnes morales — logements et locaux non résidentiels (Sitadel, SDES, millésime 2026-10). Généré le <span id="date"></span>.</p></div>
<button class="theme" id="theme" type="button">Mode sombre / clair</button></header>
<nav><a href="#vue">Vue d'ensemble</a><a href="#familles">Familles</a><a href="#groupes">Groupes promoteurs</a>
<a href="#prospects">Prospects</a><a href="#croisement">Logements × locaux</a><a href="#profils">Profils d'acteurs</a><a href="#constats">Constats des agents</a><a href="#limites">Limites</a></nav>
<main>
<section id="vue" class="tiles"></section>
<section id="familles" class="card"><h2>Familles de demandeurs</h2>
<p class="sub">Nombre de demandeurs (SIREN) par famille, selon le fichier. Famille issue des règles (catégorie juridique, NAF, dénomination) puis de l'agent pour les cas ambigus.</p>
<div class="legend"><span><i style="background:var(--s1)"></i>Fichier logements</span><span><i style="background:var(--s2)"></i>Fichier locaux non résidentiels</span></div>
<div id="c-familles"></div><details><summary>Voir le tableau</summary><div id="t-familles"></div></details></section>
<section id="groupes" class="card"><h2>Groupes promoteurs derrière les sociétés de programme</h2>
<p class="sub" id="groupes-sub"></p><div id="c-groupes"></div><details><summary>Voir le tableau</summary><div id="t-groupes"></div></details></section>
<section id="prospects" class="card"><h2>Prospects priorisés pour Buddimm</h2>
<p class="sub" id="prosp-sub"></p><div id="c-prosp"></div><div id="t-prosp"></div><details><summary>Candidats écartés, par le code (règle) ou par l'agent (jugement)</summary><div id="t-ecartes"></div></details></section>
<section id="croisement" class="card"><h2>Logements × locaux : les deux fichiers croisés</h2>
<p class="sub" id="crois-sub"></p><div id="c-crois"></div>
<details open><summary>Demandeurs qui construisent à la fois des logements et des équipements de santé ou d'action sociale</summary><div id="t-medico"></div></details></section>
<section id="profils" class="card"><h2>Profils d'acteurs (regroupement automatique)</h2>
<p class="sub" id="profils-sub"></p>
<div class="legend" id="leg-fam"></div><div class="profils" id="c-profils"></div>
<details><summary>Voir le tableau des moyennes par profil</summary><div id="t-profils"></div></details></section>
<section id="constats" class="card"><h2>Constats des agents (Claude, NVIDIA) et vérification des chiffres</h2>
<p class="sub">Chaque constat a été écrit par un modèle à partir de requêtes sur les données, puis contrôlé par le code : tout chiffre doit se retrouver dans les résultats d'outils, tout pourcentage doit être recalculable dans sa phrase. ✓ = chiffres vérifiés ; ⚠ = chiffres non vérifiables. Les relectures humaines détaillées sont dans <code>out/verification_*.md</code> et <code>out_locaux/verification_*.md</code>.</p>
<div id="t-constats"></div></section>
<section id="limites" class="card"><h2>Limites à garder en tête</h2><ul class="limites" id="l-limites"></ul></section>
</main><div class="tip" id="tip" role="tooltip"></div></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const $ = s => document.querySelector(s);
const fmt = n => new Intl.NumberFormat("fr-FR").format(n);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const SLOT = {}; D.familles_ordre.forEach((f, i) => SLOT[f] = i < 7 ? `var(--s${i + 1})` : "var(--other)");
const INK_BLANC = {promoteur:1, fonciere_investisseur:1, collectivite_public:1, bailleur_social:0, association_ess:1, entreprise_autre:1, exploitant_sante_social:1, autres:0};
$("#date").textContent = D.genere_le;
document.getElementById("theme").onclick = () => { const r = document.documentElement;
  const sombre = r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  r.dataset.theme = sombre ? "light" : "dark"; };

// ---- infobulle (survol + focus clavier)
const tip = $("#tip");
function bindTip(el, html) {
  const show = e => { tip.innerHTML = html; tip.style.display = "block";
    const r = el.getBoundingClientRect(); const x = e && e.clientX ? e.clientX : r.right; const y = e && e.clientY ? e.clientY : r.top;
    tip.style.left = Math.min(x + 14, innerWidth - 340) + "px"; tip.style.top = (y + 14) + "px"; };
  el.addEventListener("mousemove", show); el.addEventListener("focus", () => show());
  el.addEventListener("mouseleave", () => tip.style.display = "none"); el.addEventListener("blur", () => tip.style.display = "none");
  el.setAttribute("tabindex", "0");
}
function table(cols, rows) {
  return `<table><thead><tr>${cols.map(c => `<th class="${c.n ? "n" : ""}">${c.t}</th>`).join("")}</tr></thead><tbody>` +
    rows.map(r => `<tr>${cols.map(c => `<td class="${c.n ? "n" : ""}">${c.f ? c.f(r) : esc(r[c.k])}</td>`).join("")}</tr>`).join("") + "</tbody></table>";
}

// ---- barres horizontales (1 ou 2 séries), barres <= 24px, extrémité arrondie, valeur en bout
function hbars(target, rows, series, opts = {}) {
  const NS = "http://www.w3.org/2000/svg", labelW = opts.labelW || 230, barH = series.length > 1 ? 11 : 16, gap = 2;
  const rowH = series.length * barH + (series.length - 1) * gap + 14, W = target.clientWidth || 900, plotW = W - labelW - 70;
  // axe : graduations sur des nombres ronds (pas de 1, 2, 2,5 ou 5 × 10^n), le plus fin tenant en 6 graduations
  const vmax = Math.max(1, ...rows.flatMap(r => series.map(s => r[s.k]))), p10 = 10 ** Math.floor(Math.log10(vmax / 6));
  const pas = [1, 2, 2.5, 5, 10, 20].map(m => m * p10).find(v => Math.ceil(vmax / v) <= 6);
  const nTicks = Math.ceil(vmax / pas), max = pas * nTicks;
  const svg = document.createElementNS(NS, "svg"); svg.setAttribute("width", W); svg.setAttribute("height", rows.length * rowH + 24);
  svg.setAttribute("role", "img"); svg.setAttribute("aria-label", opts.aria || "graphique en barres");
  const mk = (t, a) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); return e; };
  for (let i = 0; i <= nTicks; i++) { const x = labelW + plotW * i / nTicks;
    svg.append(mk("line", {x1:x, x2:x, y1:0, y2:rows.length * rowH, stroke:"var(--grid)", "stroke-width":1}));
    const t = mk("text", {x, y:rows.length * rowH + 16, "text-anchor":"middle", "font-size":11, fill:"var(--muted)"}); t.textContent = fmt(Math.round(pas * i)); svg.append(t); }
  svg.append(mk("line", {x1:labelW, x2:labelW, y1:0, y2:rows.length * rowH, stroke:"var(--axis)", "stroke-width":1}));
  rows.forEach((r, i) => {
    const y0 = i * rowH + 7; const lab = mk("text", {x:labelW - 10, y:y0 + (rowH - 14) / 2 + 4, "text-anchor":"end", "font-size":12.5, fill:"var(--text-primary)"});
    lab.textContent = r._label; svg.append(lab);
    series.forEach((s, j) => { const v = r[s.k], w = Math.max(v > 0 ? 2 : 0, plotW * v / max), y = y0 + j * (barH + gap), rr = Math.min(4, w / 2);
      const p = mk("path", {d:`M${labelW},${y} h${w - rr} a${rr},${rr} 0 0 1 ${rr},${rr} v${barH - 2 * rr} a${rr},${rr} 0 0 1 ${-rr},${rr} h${-(w - rr)} z`, fill:s.color});
      bindTip(p, opts.tip ? opts.tip(r, s) : `<b>${esc(r._label)}</b><br>${esc(s.label)} : ${fmt(v)}`); svg.append(p);
      const t = mk("text", {x:labelW + w + 6, y:y + barH - 2, "font-size":11.5, fill:"var(--text-secondary)"}); t.textContent = fmt(v); svg.append(t); });
  });
  target.innerHTML = ""; target.append(svg);
}

// ---- vue d'ensemble
const T = D.tuiles, C = D.croisement || {}, P = D.profils || {};
$("#vue").innerHTML = `
 <div class="card tile hero"><div class="label">Demandeurs analysés (personnes morales)</div><div class="value">${fmt(T.acteurs)}</div><div class="note">SIREN distincts, logements et locaux réunis</div></div>
 <div class="card tile"><div class="label">Permis — logements</div><div class="value">${fmt(T.permis_logements)}</div><div class="note">PC créant des logements</div></div>
 <div class="card tile"><div class="label">Permis — locaux</div><div class="value">${fmt(T.permis_locaux)}</div><div class="note">PC créant des locaux non résidentiels</div></div>
 <div class="card tile"><div class="label">Permis mixtes</div><div class="value">${fmt((C.permis || {}).mixtes || 0)}</div><div class="note">présents dans les deux fichiers</div></div>`;

// ---- familles
const fam = D.familles.map(f => ({...f, _label: f.libelle}));
const drawFam = () => hbars($("#c-familles"), fam, [{k:"logements", label:"Fichier logements", color:"var(--s1)"}, {k:"locaux", label:"Fichier locaux", color:"var(--s2)"}], {aria:"Demandeurs par famille et par fichier"});
$("#t-familles").innerHTML = table([{t:"Famille", k:"libelle"}, {t:"Logements", k:"logements", n:1, f:r => fmt(r.logements)}, {t:"Locaux", k:"locaux", n:1, f:r => fmt(r.locaux)}], fam);

// ---- groupes promoteurs
const G = D.groupes.map(g => ({...g, _label: g.groupe_nom.length > 34 ? g.groupe_nom.slice(0, 33) + "…" : g.groupe_nom, permis_total: g.permis_logements + g.permis_locaux}));
const GS = D.groupes_stats;
$("#groupes-sub").innerHTML = G.length ? `Les promoteurs passent souvent par une société par programme (SCCV, SNC). En lisant leurs dirigeants <b>personnes morales</b> dans l'Annuaire des entreprises (jamais les personnes physiques), ${fmt(GS.rattachees)} des ${fmt(GS.societes)} sociétés de la famille « promoteur » ont été rattachées à un gérant ; ${fmt(GS.groupes_multi)} groupes réunissent plusieurs sociétés. Classement des 15 groupes par nombre de permis (logements + locaux). Un seul niveau de rattachement : un gérant peut lui-même appartenir à un groupe plus large.` : "Rattachement en cours de calcul : relancer le tableau de bord quand <code>src/groupes.py</code> a terminé.";
const drawGroupes = () => G.length && hbars($("#c-groupes"), G, [{k:"permis_total", label:"Permis", color:"var(--s1)"}], {labelW:260, aria:"Permis par groupe promoteur",
  tip:r => `<b>${esc(r.groupe_nom)}</b><br>${fmt(r.nb_societes)} société(s) · ${fmt(r.permis_logements)} PC logements (${fmt(r.logements)} logts) · ${fmt(r.permis_locaux)} PC locaux<br>${r.premiere_annee}–${r.derniere_annee} · ${fmt(r.nb_communes)} communes`});
$("#t-groupes").innerHTML = table([{t:"Groupe", f:r => `<a href="${esc(r.source)}" target="_blank" rel="noopener">${esc(r.groupe_nom)}</a>`}, {t:"Sociétés", n:1, f:r => fmt(r.nb_societes)},
  {t:"PC logements", n:1, f:r => fmt(r.permis_logements)}, {t:"Logements", n:1, f:r => fmt(r.logements)}, {t:"PC locaux", n:1, f:r => fmt(r.permis_locaux)},
  {t:"Années", f:r => `${r.premiere_annee}–${r.derniere_annee}`}, {t:"Communes", n:1, f:r => fmt(r.nb_communes)}], G);

// ---- croisement
if (C.permis) {
  $("#crois-sub").innerHTML = `${fmt(C.permis.mixtes)} permis figurent dans les deux fichiers (${fmt(C.permis.mixtes_logements)} logements et ${fmt(C.permis.mixtes_surface_m2)} m² de locaux) ; ${fmt(C.acteurs.deux_fichiers)} demandeurs déposent dans les deux ; ${fmt(C.nb_medico_mixte)} construisent à la fois des logements et des équipements de santé ou d'action sociale. ${fmt(C.acteurs.familles_differentes)} demandeurs avaient une famille différente selon le fichier : réconciliés dans les profils. Graphique : permis mixtes par famille du demandeur.`;
  const M = Object.entries(C.permis.mixtes_par_famille).map(([f, n]) => ({_label: D.lib_fam[f] || f, n}));
  window.drawCrois = () => hbars($("#c-crois"), M, [{k:"n", label:"Permis mixtes", color:"var(--s1)"}], {aria:"Permis mixtes par famille"});
  $("#t-medico").innerHTML = table([{t:"Demandeur", f:r => `<a href="${esc(r.source)}" target="_blank" rel="noopener">${esc(r.denomination)}</a>`}, {t:"Famille", f:r => esc(D.lib_fam[r.famille_logements] || r.famille_logements)},
    {t:"PC logements", n:1, f:r => fmt(r.permis_logements)}, {t:"Logements", n:1, f:r => fmt(r.logements)}, {t:"Résidences médico-sociales", n:1, f:r => fmt(r.residences_medico)},
    {t:"PC locaux", n:1, f:r => fmt(r.permis_locaux)}, {t:"Équipements santé / action sociale", n:1, f:r => fmt(r.equipements_medico)}], C.medico_mixte.slice(0, 20));
}

// ---- prospects
const PR = D.prospects || {};
if (PR.prospects) {
  const bar = Object.entries(PR.bareme).map(([k, v]) => `${esc(k)} : ${esc(typeof v === "object" ? Object.entries(v).map(([a, b]) => `${D.lib_fam[a] || a} ${b}`).join(", ") : v)}`).join(" · ");
  const pv = PR.par_verdict || {}, po = PR.par_origine || {};
  $("#prosp-sub").innerHTML = `${fmt(PR.nb_candidats || PR.nb)} candidats : ${fmt(po["demandeur de permis"] || 0)} demandeurs de permis des familles clientes de Buddimm et <b>${fmt(po["exploitant trouvé derrière un permis déposé par un tiers"] || 0)} exploitants trouvés derrière des projets médico-sociaux déposés par des promoteurs, bailleurs ou foncières</b> (rapprochement FINESS par l'agent). <b>Le code écarte d'abord ${fmt(PR.nb_ecartes_code || 0)} candidats sans jugement à porter</b> (structure cessée, culte, enseignement scolaire, sport, cabinet libéral, lus dans l'activité actuelle de l'Annuaire) ; l'agent qualifie ensuite les cas ambigus : ${fmt(pv.prospect || 0)} confirmés, ${fmt(pv.a_verifier || 0)} à vérifier, ${fmt(PR.nb_ecartes_agent || 0)} faux positifs écartés, les autres restent « non qualifiés » (échantillon). Score additif dont chaque point est justifié. <b>Barème (hypothèses à valider avec le métier)</b> : ${bar}. Aucune coordonnée : personnes morales et fiches publiques uniquement ; aucune prise de contact. 30 premiers ci-dessous.`;
  $("#t-prosp").innerHTML = table([{t:"Rang", n:1, k:"rang"}, {t:"Score", n:1, k:"score"},
    {t:"Prospect", f:r => `<a href="${esc(r.source_entreprise)}" target="_blank" rel="noopener">${esc(r.denomination)}</a><br><span style="color:var(--text-secondary)">${esc(D.lib_fam[r.famille] || r.famille)}${r.origine !== "demandeur de permis" ? " · exploitant trouvé via FINESS" : ""}</span>`},
    {t:"Qualification (agent)", f:r => `${esc(r.verdict_agent)}${r.adequation ? " · adéquation " + esc(r.adequation) : ""}${r.taille ? " · taille " + esc(r.taille) : ""}<br><span style="color:var(--text-secondary)">${esc(r.type_structure)}${r.besoin_immobilier ? " — " + esc(r.besoin_immobilier) : ""}</span>`},
    {t:"Pourquoi ce score", f:r => `<span style="color:var(--text-secondary)">${esc(r.raisons)}</span>`},
    {t:"Dernier permis", f:r => `${esc(r.dernier_depot)} · ${esc(r.dernier_commune)}<br><span style="color:var(--text-secondary)">${esc(r.dernier_type)} · ${esc(r.dernier_etat)}</span>`}], PR.prospects.slice(0, 30));
  $("#t-ecartes").innerHTML = (PR.ecartes || []).length ? table([{t:"Demandeur", f:r => `<a href="${esc(r.source_entreprise)}" target="_blank" rel="noopener">${esc(r.denomination)}</a>`},
    {t:"Famille", f:r => esc(D.lib_fam[r.famille] || r.famille)}, {t:"Écarté par", f:r => esc(r.ecarte_par || "")}, {t:"Score initial", n:1, k:"score_initial"},
    {t:"Motif", f:r => `${esc(r.motif)}<br><span style="color:var(--text-secondary)">${esc(r.indices)}</span>`}], PR.ecartes) : "Aucun.";
}

// ---- profils
if (P.groupes) {
  $("#profils-sub").innerHTML = `${fmt(P.nb_acteurs)} demandeurs décrits par 10 indicateurs de comportement (volume, régularité, taille des projets, part de locaux, dispersion, part médico-sociale, achèvement, annulation), regroupés par k-means (k = ${P.k}, choisi par le score de silhouette : ${P.silhouettes[P.k]}). <b>Structure modérée</b> : les profils se recouvrent en partie. La famille juridique n'entre pas dans le calcul ; la barre montre ensuite comment les familles se répartissent dans chaque profil. Noms de profils déduits automatiquement du trait le plus marqué.`;
  $("#leg-fam").innerHTML = D.familles_ordre.map(f => `<span><i style="background:${SLOT[f]}"></i>${esc(D.lib_fam[f])}</span>`).join("");
  const grp = [...P.groupes].sort((a, b) => b.effectif - a.effectif);
  $("#c-profils").innerHTML = grp.map(g => {
    const tot = g.familles_pliees.reduce((s, [, n]) => s + n, 0);
    const seg = g.familles_pliees.map(([f, n]) => { const pct = Math.round(100 * n / tot);
      return `<div class="segp" data-t="${esc(D.lib_fam[f])} : ${fmt(n)} (${pct} %)" style="flex:${n};background:${SLOT[f]};color:${INK_BLANC[f] ? "#fff" : "#0b0b0b"}">${pct >= 12 ? pct + " %" : ""}</div>`; }).join("");
    return `<div class="profil"><h3>${esc(g.nom)}</h3><div class="eff">${fmt(g.effectif)} demandeurs · moyenne ${g.moyennes.permis} permis, ${g.moyennes.annees_actives} années actives</div>
      <div class="seg" role="img" aria-label="Répartition des familles du profil ${esc(g.nom)}">${seg}</div>
      <p>${esc(g.description_auto)}</p><p>Exemples : ${g.exemples.slice(0, 4).map(e => esc(e.denomination)).join(", ")}</p></div>`; }).join("");
  document.querySelectorAll(".segp").forEach(el => bindTip(el, el.dataset.t));
  $("#t-profils").innerHTML = table([{t:"Profil", k:"nom"}, {t:"Effectif", n:1, f:r => fmt(r.effectif)}, {t:"Permis", n:1, f:r => r.moyennes.permis},
    {t:"Logements", n:1, f:r => fmt(r.moyennes.logements)}, {t:"Surface locaux (m²)", n:1, f:r => fmt(r.moyennes.surface_m2)}, {t:"Années actives", n:1, f:r => r.moyennes.annees_actives},
    {t:"Communes", n:1, f:r => r.moyennes.communes}, {t:"Part locaux", n:1, f:r => Math.round(100 * r.moyennes.part_locaux) + " %"},
    {t:"Part médico-sociale", n:1, f:r => Math.round(100 * r.moyennes.part_medico) + " %"}, {t:"Achevés", n:1, f:r => Math.round(100 * r.moyennes.taux_acheve) + " %"},
    {t:"Annulés", n:1, f:r => Math.round(100 * r.moyennes.taux_annule) + " %"}, {t:"Famille dominante", f:r => `${esc(D.lib_fam[r.famille_dominante] || r.famille_dominante)} (${Math.round(100 * r.part_famille_dominante)} %)`}], grp);
}

// ---- constats
const modele = m => m.startsWith("claude") ? "Claude (Opus 5.5)" : m.startsWith("nvidia") ? "NVIDIA Nemotron" : m.startsWith("openai/") ? "Groq " + m.split("/")[1] : m;
$("#t-constats").innerHTML = table([{t:"Fichier", k:"jeu"}, {t:"Modèle", f:r => esc(modele(r.modele))}, {t:"Thème", k:"theme"},
  {t:"Constat", f:r => `<b>${esc(r.titre)}</b><br><span style="color:var(--text-secondary)">${esc(r.constat)}</span>`},
  {t:"Fiabilité annoncée", f:r => `<span class="pill">${esc(r.fiabilite)}</span>`},
  {t:"Contrôle des chiffres", f:r => r.chiffres_non_verifies.length ? `<span class="ko">${esc(r.chiffres_non_verifies.join(" · "))}</span>` : `<span class="ok">vérifiés</span>`}], D.constats);

// ---- limites
$("#l-limites").innerHTML = [
 "Personnes morales retrouvées dans Sirène uniquement ; PC seulement (DP et PA exclus).",
 "Un permis modificatif n'a pas de ligne propre ; environ 15 % des ouvertures de chantier et un tiers des achèvements ne remontent jamais : les taux d'achèvement sont des minima.",
 "Le NAF et le SIRET d'un permis sont ceux d'un établissement, parfois fermé : la famille s'appuie d'abord sur la catégorie juridique, puis sur la fiche entreprise actuelle.",
 "Familles et verdicts de prospects : précision à mesurer sur les échantillons de contrôle (out_fouille/controle/, à vérifier à la main).",
 "Exploitants trouvés via FINESS : rapprochement par commune, rue et date d'ouverture ; FINESS ne liste que les établissements autorisés, un projet récent peut ne pas y figurer encore.",
 "Taille des structures et poids du barème : hypothèses de travail (une très grande structure a probablement sa propre direction immobilière), à valider avec Buddimm.",
 "Rattachement des sociétés de programme : un seul niveau (le gérant personne morale) ; les co-promotions sont rattachées au premier gérant.",
 "Profils : structure modérée (silhouette ≈ 0,35) ; un profil décrit un comportement moyen, pas chaque acteur.",
 "Constats des agents : propositions de modèles, contrôlées automatiquement sur les chiffres mais pas sur l'interprétation (voir les relectures détaillées)."
].map(t => `<li>${esc(t)}</li>`).join("");

const drawAll = () => { drawFam(); drawGroupes(); window.drawCrois && drawCrois(); };
drawAll(); let rt; addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(drawAll, 150); });
</script></body></html>
"""


def main():
    data = json.dumps(donnees(), ensure_ascii=False).replace("</", "<\\/")
    out = FOUILLE / "dashboard.html"
    out.write_text(HTML.replace("__DATA__", data), encoding="utf-8")
    print("écrit", out)


if __name__ == "__main__":
    main()
