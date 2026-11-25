r"""Rapport PDF des résultats (périmètre Yvelines) -> rapport\rapport_resultats_yvelines.pdf

  python -X utf8 src\rapport_pdf.py

Lit les sorties déjà produites (aucun recalcul, aucun appel réseau) :
- out\ et out_locaux\ : familles (acteurs_classes.csv), constats des agents (insights_agent.jsonl),
  contrôle automatique des chiffres (verification_chiffres.json) ;
- out_fouille\ : groupes promoteurs, croisement, profils ; relecture.json (verdicts de relecture des constats).
"""
import csv, json
from collections import Counter
from datetime import date
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether)

ROOT = Path(__file__).resolve().parent.parent
FOUILLE = ROOT / "out_fouille"
SORTIE = ROOT / "rapport"
SORTIE.mkdir(exist_ok=True)


def espaces(t):
    """Espaces insécables (fine ou normale) remplacées par une espace simple."""
    return t.replace(" ", " ").replace("\xa0", " ")


def classe(verdict):
    """Verdict de relecture ramené à trois classes : exact / chiffres justes mais lecture à corriger / erroné."""
    v = verdict.lower()
    if v.startswith("erroné"):
        return "erroné"
    if v.startswith("exact") and "," not in v and " mais " not in v or v.startswith("réécrit puis exact"):
        return "exact"
    return "chiffres justes, lecture à corriger" if v else "non relu"

# ---- polices (Segoe UI : accents, flèches, symboles) ; repli Helvetica si absente
try:
    pdfmetrics.registerFont(TTFont("UI", r"C:\Windows\Fonts\segoeui.ttf"))
    pdfmetrics.registerFont(TTFont("UI-B", r"C:\Windows\Fonts\segoeuib.ttf"))
    F, FB = "UI", "UI-B"
except Exception:
    F, FB = "Helvetica", "Helvetica-Bold"

INK, INK2, MUTED, GRID = colors.HexColor("#0b0b0b"), colors.HexColor("#52514e"), colors.HexColor("#898781"), colors.HexColor("#e1e0d9")
S1, S2 = colors.HexColor("#2a78d6"), colors.HexColor("#eb6834")       # palette dataviz (validée)
st = {
    "h1": ParagraphStyle("h1", fontName=FB, fontSize=20, leading=25, textColor=INK, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName=FB, fontSize=14, leading=18, textColor=INK, spaceBefore=14, spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName=FB, fontSize=11, leading=14, textColor=INK, spaceBefore=8, spaceAfter=3),
    "p": ParagraphStyle("p", fontName=F, fontSize=9.5, leading=13.5, textColor=INK, alignment=TA_LEFT, spaceAfter=5),
    "small": ParagraphStyle("small", fontName=F, fontSize=8.5, leading=11.5, textColor=INK2),
    "cell": ParagraphStyle("cell", fontName=F, fontSize=8.2, leading=10.5, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName=FB, fontSize=8.2, leading=10.5, textColor=INK),
    "celln": ParagraphStyle("celln", fontName=F, fontSize=8.2, leading=10.5, textColor=INK, alignment=2),
    "cellbn": ParagraphStyle("cellbn", fontName=FB, fontSize=8.2, leading=10.5, textColor=INK, alignment=2),
}
LIB_FAM = {"promoteur": "Promoteur", "fonciere_investisseur": "Foncière / investisseur", "collectivite_public": "Collectivité / public",
           "bailleur_social": "Bailleur social", "association_ess": "Association / ESS", "entreprise_autre": "Autre entreprise",
           "exploitant_sante_social": "Exploitant santé / social", "copropriete": "Copropriété", "non_determine": "Non déterminé"}


def esc(s):
    return str(s if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt(n):
    return f"{int(n):,}".replace(",", "\u202f")


def lire_csv(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def lire_json(p, d=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else d


def tableau(entetes, lignes, largeurs, num=()):
    data = [[Paragraph(esc(h), st["cellbn" if i in num else "cellb"]) for i, h in enumerate(entetes)]]
    for l in lignes:
        data.append([c if isinstance(c, Paragraph) else Paragraph(esc(c), st["celln" if i in num else "cell"])
                     for i, c in enumerate(l)])
    t = Table(data, colWidths=largeurs, repeatRows=1)
    style = [("LINEBELOW", (0, 0), (-1, 0), 0.8, INK2), ("LINEBELOW", (0, 1), (-1, -1), 0.3, GRID),
             ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    for c in num:
        style.append(("ALIGN", (c, 1), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def barres(lignes, series, largeur=170 * mm, label_w=48 * mm):
    """Barres horizontales fines (1 ou 2 séries), valeur en bout, graduations rondes, légende si 2 séries."""
    bar_h, gap = (5, 1.5) if len(series) > 1 else (7, 0)
    row_h = len(series) * bar_h + gap * (len(series) - 1) + 7
    vmax = max(1, max(l[k] for l in lignes for k, _, _ in series))
    p10 = 10 ** len(str(int(vmax / 6))) / 10 if vmax >= 6 else 1
    pas = next(m * p10 for m in (1, 2, 2.5, 5, 10, 20, 50) if -(-vmax // (m * p10)) <= 6)
    n = int(-(-vmax // pas)); top = pas * n
    leg_h = 14 if len(series) > 1 else 0
    h = leg_h + len(lignes) * row_h + 14
    d = Drawing(largeur, h)
    plot_w = largeur - label_w - 30
    y_top = h - leg_h
    if len(series) > 1:
        x = label_w
        for _, nom, col in series:
            d.add(Rect(x, h - 9, 7, 7, fillColor=col, strokeColor=None)); d.add(String(x + 10, h - 8, nom, fontName=F, fontSize=7.5, fillColor=INK2))
            x += 10 + pdfmetrics.stringWidth(nom, F, 7.5) + 14
    for i in range(n + 1):
        x = label_w + plot_w * i / n
        d.add(Line(x, 12, x, y_top, strokeColor=GRID, strokeWidth=0.4))
        d.add(String(x, 3, fmt(pas * i), fontName=F, fontSize=6.5, fillColor=MUTED, textAnchor="middle"))
    for j, l in enumerate(lignes):
        y0 = y_top - (j + 1) * row_h + 3.5
        d.add(String(label_w - 4, y0 + (row_h - 7) / 2 - 1, l["_label"], fontName=F, fontSize=7.5, fillColor=INK, textAnchor="end"))
        for s, (k, _, col) in enumerate(series):
            v = l[k]; w = plot_w * v / top
            yy = y0 + (len(series) - 1 - s) * (bar_h + gap)
            if v:
                d.add(Rect(label_w, yy, max(w, 1), bar_h, fillColor=col, strokeColor=None, rx=1.5, ry=1.5))
            d.add(String(label_w + w + 3, yy + 1, fmt(v), fontName=F, fontSize=6.5, fillColor=INK2))
    return d


def pied(canvas, doc):
    canvas.saveState()
    canvas.setFont(F, 7.5); canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "Qualification des demandeurs de permis de construire — Yvelines (78) — données publiques Sitadel (SDES) et Annuaire des entreprises")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"page {doc.page}")
    canvas.restoreState()


def modele_lisible(m):
    if m.startswith("claude"):
        return "Claude (Opus 5.5)"
    if m.startswith("nvidia"):
        return "NVIDIA Nemotron"
    if m.startswith("openai/"):
        return "Groq " + m.split("/")[1]
    return m


def main():
    S = []
    fam = {j: lire_csv(ROOT / d / "acteurs_classes.csv") for j, d in (("logements", "out"), ("locaux", "out_locaux"))}
    perm = {j: lire_csv(ROOT / d / "permis_classes.csv") for j, d in (("logements", "out"), ("locaux", "out_locaux"))}
    prof = lire_json(FOUILLE / "profils_groupes.json", {})
    crois = lire_json(FOUILLE / "croisement.json", {})
    grp = lire_csv(FOUILLE / "groupes_synthese.csv")
    soc = lire_csv(FOUILLE / "groupes_societes.csv")
    # titres comparés après normalisation des espaces insécables (les modèles écrivent souvent « type 4 »)
    relecture = {espaces(k): v for k, v in lire_json(FOUILLE / "relecture.json", {}).items()}
    prosp = lire_json(FOUILLE / "prospects_priorises.json", {})
    notes = []
    for jeu, d in (("logements", "out"), ("locaux", "out_locaux")):
        verif = {v["titre"]: v for v in lire_json(ROOT / d / "verification_chiffres.json", [])}
        p = ROOT / d / "insights_agent.jsonl"
        if p.exists():
            for l in p.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    n = json.loads(l); n["jeu"] = jeu
                    n["auto"] = verif.get(n.get("titre"), {}).get("chiffres_non_verifies")
                    notes.append(n)
    # notes jugées erronées à la relecture : retirées des livrables, mais comptées dans le bilan
    retirees = []
    for jeu, d in (("logements", "out"), ("locaux", "out_locaux")):
        p = ROOT / d / "archive_v2" / "notes_erronees_retirees.jsonl"
        if p.exists():
            retirees += [{**json.loads(l), "jeu": jeu} for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

    # bilan de la relecture, par agent et par fichier
    cols = ["exact", "chiffres justes, lecture à corriger", "erroné"]
    bilan = Counter()
    for n in notes + retirees:
        bilan[(modele_lisible(n["modele"]), n["jeu"], classe(relecture.get(espaces(n.get("titre", "")), {}).get("verdict", "")))] += 1
    par_m = Counter()
    for (m, _, c), k in bilan.items():
        par_m[(m.split()[0], c)] += k
    bilan_texte = " ; ".join(
        f"{m} : {par_m[(m, 'exact')]} exacts, {par_m[(m, cols[1])]} à corriger, {par_m[(m, 'erroné')]} erronés"
        for m in sorted({m for m, _ in par_m})) + "."

    # ---- page de garde / synthèse
    S.append(Paragraph("Qui construit dans les Yvelines ?", st["h1"]))
    S.append(Paragraph("Qualification des demandeurs de permis de construire et repérage de patterns — résultats", st["h3"]))
    S.append(Paragraph(f"Rapport généré le {date.today().strftime('%d/%m/%Y')}. Sources publiques : Sitadel (SDES, millésime 2026-10), "
                       "fichiers « logements » et « locaux non résidentiels » ; Annuaire des entreprises (API publique) ; "
                       "FINESS, établissements sanitaires, sociaux et médico-sociaux (ministère, instantané du 04/05/2026). "
                       "Nomenclatures Insee (catégories juridiques, NAF rév. 2).", st["small"]))
    S.append(Spacer(1, 8))
    n_log, n_loc = len(perm["logements"]), len(perm["locaux"])
    S.append(Paragraph("Périmètre", st["h2"]))
    S.append(Paragraph(
        f"Permis de construire (PC) dont <b>le lieu des travaux est dans les Yvelines (78)</b> — contrôlé ligne à ligne : "
        f"code département 78 et commune en 78 —, déposés par une <b>personne morale</b> retrouvée dans Sirène : "
        f"<b>{fmt(n_log)}</b> PC créant des logements et <b>{fmt(n_loc)}</b> PC créant des locaux non résidentiels, "
        f"soit <b>{fmt(prof.get('nb_acteurs', 0))}</b> demandeurs distincts. Le siège du demandeur peut être hors des Yvelines "
        "(Paris, Hauts-de-Seine…) : c'est le lieu des travaux qui définit le périmètre. Aucune prise de contact, aucun nom de "
        "personne physique : les dirigeants personnes physiques sont écartés dès la lecture de l'Annuaire.", st["p"]))
    S.append(Paragraph("Ce qu'il faut retenir", st["h2"]))
    tops = [g for g in grp[:5]]
    tous = fam["logements"] + fam["locaux"]
    par_agent = sum(1 for a in tous if a["methode"].startswith("agent"))
    nd = sum(1 for a in tous if a["famille"] == "non_determine")
    points = [
        f"<b>Familles</b> : la catégorie juridique Sirène tranche l'essentiel ; les {fmt(par_agent)} cas ambigus (logements et locaux) "
        f"passent par un agent LLM outillé (fiche entreprise obligatoire, NAF du permis traité comme indice daté). "
        f"Après l'agent, {fmt(nd)} classements sur {fmt(len(tous))} restent « non déterminé » faute d'indices suffisants.",
        f"<b>Promoteurs masqués</b> : {fmt(len(soc))} sociétés de la famille promoteur, dont {fmt(sum(1 for s in soc if s['methode'] == 'dirigeant personne morale'))} "
        f"rattachées à un gérant personne morale ; premiers groupes : " + ", ".join(esc(g['groupe_nom']) for g in tops) + ".",
        f"<b>Logements × locaux</b> : {fmt(crois.get('permis', {}).get('mixtes', 0))} permis créent les deux ; "
        f"{fmt(crois.get('nb_medico_mixte', 0))} demandeurs construisent logements et équipements de santé ou d'action sociale.",
        f"<b>Profils</b> : {prof.get('k', '?')} profils de comportement (structure modérée, silhouette {prof.get('silhouettes', {}).get(str(prof.get('k')), '?')}), "
        "dont un groupe d'acteurs récurrents multi-communes, liste de comptes clés.",
        "<b>Cœur de cible Buddimm</b> : les associations et fondations construisent rarement (un permis sur toute la période pour la plupart) "
        "mais des équipements de santé de taille significative ; les résidences médico-sociales sont portées par promoteurs et bailleurs.",
        f"<b>Le demandeur n'est pas le client</b> : pour les projets médico-sociaux déposés par des tiers, un agent retrouve l'exploitant "
        f"dans FINESS ({fmt(prosp.get('par_origine', {}).get('exploitant trouvé derrière un permis déposé par un tiers', 0))} exploitants ajoutés "
        f"aux prospects). Avant l'agent, le code écarte {fmt(prosp.get('nb_ecartes_code', 0))} candidats hors cible (culte, écoles, sport, structures cessées) ; "
        f"l'agent ne juge que les cas ambigus. Section 5.",
        f"<b>Agents</b> : {len(notes) + len(retirees)} constats écrits par Claude et NVIDIA, chacun contrôlé par le code (chiffres retrouvés dans les "
        "résultats, pourcentages recalculables dans leur phrase) puis relu, requêtes rejouées. " + bilan_texte +
        f" Les {len(retirees)} constats erronés sont retirés du rapport. Voir la section 6.",
    ]
    for t in points:
        S.append(Paragraph("• " + t, st["p"]))

    # ---- familles
    S.append(PageBreak())
    S.append(Paragraph("1. Familles de demandeurs", st["h2"]))
    S.append(Paragraph("Nombre de demandeurs (SIREN) par famille et par fichier. Règles fondées sur les libellés officiels Insee, "
                       "puis agent LLM pour les cas ambigus. Les familles contradictoires entre fichiers "
                       f"({crois.get('acteurs', {}).get('familles_differentes', '?')} cas) sont réconciliées "
                       "dans les profils.", st["p"]))
    ordre = ["promoteur", "fonciere_investisseur", "collectivite_public", "bailleur_social", "association_ess",
             "entreprise_autre", "exploitant_sante_social", "non_determine", "copropriete"]
    lig = [{"_label": LIB_FAM[f], "log": sum(1 for a in fam["logements"] if a["famille"] == f),
            "loc": sum(1 for a in fam["locaux"] if a["famille"] == f)} for f in ordre]
    S.append(barres(lig, [("log", "Fichier logements", S1), ("loc", "Fichier locaux non résidentiels", S2)]))
    S.append(Spacer(1, 6))
    S.append(tableau(["Famille", "Logements", "Locaux"], [[l["_label"], fmt(l["log"]), fmt(l["loc"])] for l in lig],
                     [80 * mm, 30 * mm, 30 * mm], num=(1, 2)))

    # ---- groupes
    S.append(Paragraph("2. Groupes promoteurs derrière les sociétés de programme", st["h2"]))
    S.append(Paragraph(
        "Les promoteurs déposent souvent via une société par programme (SCI de construction-vente, SNC). Pour chaque demandeur "
        "« promoteur », on lit ses dirigeants <b>personnes morales</b> dans l'Annuaire : le groupe retenu est le gérant ou président, "
        "à défaut l'associé responsable ; les commissaires aux comptes, liquidateurs et cabinets d'audit sont exclus. Un seul niveau : "
        "le gérant peut lui-même appartenir à un groupe plus large (ex. Nexity apparaît sous deux entités, Nexity Régions 10 et Nexity Régions 4).", st["p"]))
    g15 = [{"_label": (g["groupe_nom"][:30] + "…") if len(g["groupe_nom"]) > 31 else g["groupe_nom"],
            "pc": int(g["permis_logements"]) + int(g["permis_locaux"])} for g in grp[:15]]
    if g15:
        S.append(barres(g15, [("pc", "Permis (logements + locaux)", S1)]))
        S.append(Spacer(1, 6))
        S.append(tableau(["Groupe", "Soc.", "PC log.", "Logts", "PC loc.", "Années", "Comm."],
                         [[g["groupe_nom"], g["nb_societes"], g["permis_logements"], fmt(g["logements"]), g["permis_locaux"],
                           f"{g['premiere_annee']}–{g['derniere_annee']}", g["nb_communes"]] for g in grp[:15]],
                         [66 * mm, 13 * mm, 16 * mm, 18 * mm, 16 * mm, 22 * mm, 15 * mm], num=(1, 2, 3, 4, 6)))

    # ---- croisement
    S.append(PageBreak())
    S.append(Paragraph("3. Logements × locaux : les deux fichiers croisés", st["h2"]))
    p, a = crois.get("permis", {}), crois.get("acteurs", {})
    S.append(Paragraph(
        f"<b>{fmt(p.get('mixtes', 0))}</b> permis figurent dans les deux fichiers ({fmt(p.get('mixtes_logements', 0))} logements et "
        f"{fmt(p.get('mixtes_surface_m2', 0))} m² de locaux) ; <b>{fmt(a.get('deux_fichiers', 0))}</b> demandeurs déposent dans les deux ; "
        f"<b>{fmt(crois.get('nb_medico_mixte', 0))}</b> construisent à la fois des logements et des équipements de santé ou d'action sociale. "
        f"{fmt(a.get('familles_differentes', 0))} demandeurs avaient une famille différente selon le fichier (réconciliés).", st["p"]))
    S.append(Paragraph("Demandeurs qui construisent logements et équipements de santé / action sociale (20 premiers)", st["h3"]))
    S.append(tableau(["Demandeur", "Famille", "PC log.", "Logements", "Résid. médico-soc.", "PC locaux", "Équip. santé / social"],
                     [[m["denomination"], LIB_FAM.get(m["famille_logements"], m["famille_logements"]), m["permis_logements"],
                       fmt(m["logements"]), m["residences_medico"], m["permis_locaux"], m["equipements_medico"]]
                      for m in crois.get("medico_mixte", [])[:20]],
                     [55 * mm, 30 * mm, 13 * mm, 17 * mm, 18 * mm, 15 * mm, 20 * mm], num=(2, 3, 4, 5, 6)))

    # ---- profils
    S.append(Paragraph("4. Profils d'acteurs (regroupement automatique)", st["h2"]))
    S.append(Paragraph(
        f"{fmt(prof.get('nb_acteurs', 0))} demandeurs décrits par 10 indicateurs de comportement (volume, régularité, taille des projets, "
        f"part de locaux, dispersion, part médico-sociale, achèvement, annulation), regroupés par k-means (k = {prof.get('k')}, "
        "choisi par le score de silhouette). La famille juridique n'entre pas dans le calcul. Structure modérée : un profil décrit "
        "un comportement moyen, pas chaque acteur.", st["p"]))
    noms = {("v_annees", 1): "Récurrents multi-communes", ("v_permis", 1): "Récurrents multi-communes", ("taux_annule", 1): "Projets annulés",
            ("v_taille", 1): "Programmes de logements de taille", ("v_logements", 1): "Programmes de logements de taille",
            ("part_locaux", 1): "Constructeurs de locaux ponctuels", ("taux_acheve", 1): "Petits projets achevés",
            ("part_locaux", -1): "Petits projets de logements en cours", ("part_medico", 1): "Orientés médico-social"}
    lp = []
    for g in sorted(prof.get("groupes", []), key=lambda g: -g["effectif"]):
        t = max(g["z_centre"].items(), key=lambda kv: abs(kv[1]))
        nom = noms.get((t[0], 1 if t[1] > 0 else -1), f"Profil {g['groupe'] + 1}")
        m = g["moyennes"]
        lp.append([Paragraph(f"<b>{esc(nom)}</b><br/>{esc(', '.join(e['denomination'] for e in g['exemples'][:3]))}", st["cell"]),
                   fmt(g["effectif"]), m["permis"], m["annees_actives"], m["communes"], f"{round(100 * m['part_locaux'])} %",
                   f"{round(100 * m['taux_acheve'])} %", f"{round(100 * m['taux_annule'])} %",
                   f"{LIB_FAM.get(g['famille_dominante'], g['famille_dominante'])} ({round(100 * g['part_famille_dominante'])} %)"])
    S.append(tableau(["Profil (exemples)", "Effectif", "Permis moy.", "Années", "Communes", "Part locaux", "Achevés", "Annulés", "Famille dominante"],
                     lp, [52 * mm, 13 * mm, 13 * mm, 12 * mm, 14 * mm, 14 * mm, 13 * mm, 13 * mm, 30 * mm], num=(1, 2, 3, 4, 5, 6, 7)))

# ---- prospects
    S.append(PageBreak())
    S.append(Paragraph("5. Prospects priorisés pour Buddimm", st["h2"]))
    if prosp.get("prospects"):
        po, pv = prosp.get("par_origine", {}), prosp.get("par_verdict", {})
        n_expl = po.get("exploitant trouvé derrière un permis déposé par un tiers", 0)
        S.append(Paragraph(
            f"<b>{fmt(prosp['nb'])}</b> prospects : {fmt(po.get('demandeur de permis', prosp['nb']))} demandeurs de permis des familles "
            f"clientes de Buddimm, et <b>{fmt(n_expl)} exploitants trouvés derrière des projets médico-sociaux déposés par des tiers</b> "
            "(promoteurs, bailleurs, foncières). Pour ces projets, le demandeur n'est pas le client : un agent rapproche le permis "
            "des établissements FINESS de la commune (même rue, ouverture après l'autorisation) et désigne l'exploitant, qui est le "
            f"vrai prospect. Sur {fmt(prosp.get('nb_candidats', 0))} candidats, <b>le code écarte d'abord {fmt(prosp.get('nb_ecartes_code', 0))} cas "
            "sans jugement à porter</b> (structure cessée, culte, enseignement scolaire, sport, cabinet libéral… lus dans l'activité "
            "actuelle de l'Annuaire, sauf si la structure exploite un établissement FINESS) ; l'agent ne qualifie que les cas qui "
            "demandent un jugement (fiche entreprise, établissements FINESS exploités, permis). Sur l'échantillon qualifié : "
            f"{fmt(pv.get('prospect', 0))} confirmés, {fmt(pv.get('a_verifier', 0))} à vérifier, "
            f"{fmt(prosp.get('nb_ecartes_agent', 0))} faux positifs écartés par l'agent ; les autres restent « non qualifiés ». "
            "La taille est calculée par le code (salariés, établissements) : une très grande structure a probablement sa propre "
            "direction immobilière.", st["p"]))
        cmp_ = lire_json(FOUILLE / "agent_prospects" / "comparaison_nvidia_groq.json", {})
        if cmp_.get("cas"):
            m, dur = cmp_["modeles"], cmp_["duree_mediane_s"]
            S.append(Paragraph(
                f"Deux modèles sur les mêmes prospects tirés au hasard ({cmp_.get('tires', cmp_['cas'])} tirés, {cmp_.get('exclus_par_le_code', 0)} désormais "
                f"écartés par le code, {cmp_['cas']} comparés) : {esc(m['nvidia'])} (NVIDIA) et {esc(m['groq'])} (Groq). "
                f"Accord sur le verdict : {cmp_['accord_verdict']}/{cmp_['cas']} brut, <b>{cmp_.get('accord_verdict_apres_garde_fou', '?')}/{cmp_['cas']} "
                "après le garde-fou du code</b> (un « prospect » sans preuve dure devient « à vérifier ») ; "
                f"accord sur l'adéquation : {cmp_['accord_adequation']}/{cmp_['cas']} "
                f"(l'adéquation n'est donc qu'un départage, pas un critère). Durée médiane par cas : {dur['nvidia']} s contre {dur['groq']} s. "
                "Les désaccords se concentrent sur les associations « grises » (culturelles, communautaires, de formation) sans "
                "établissement FINESS : c'est la définition de la cible qui manque, pas la puissance du modèle. "
                "Détail : out_fouille/agent_prospects/comparaison_nvidia_groq.md.", st["small"]))
        bil = lire_json(FOUILLE / "agent_prospects" / "bilan.json", {})
        if bil.get("permis"):
            pr = bil["par_raison"]
            S.append(Paragraph(
                f"Rapprochement FINESS, sur les {fmt(bil['permis'])} permis traités (échantillon) : {fmt(bil['trouves'])} exploitants trouvés, "
                f"dont {fmt(bil['meme_entite'])} où le demandeur exploite lui-même. Sans exploitant : "
                f"{fmt(pr['résidence seniors privée probable (hors FINESS)'])} résidences seniors privées probables (non médico-sociales, "
                f"absentes de FINESS par nature), {fmt(pr['adresse du permis vide'])} permis sans adresse, "
                f"{fmt(pr['aucun établissement compatible dans la commune'] + pr['aucun établissement compatible dans la rue'])} sans "
                f"établissement compatible dans la commune ou la rue (projet trop récent, ou établissement non répertorié). "
                f"Sur les {fmt(bil['attendus_dans_finess'])} permis où FINESS devrait connaître l'exploitant, l'agent le trouve dans "
                f"<b>{bil['taux_sur_attendus']} %</b> des cas. Détail : out_fouille/agent_prospects/exploitants_bilan.csv.", st["small"]))
        S.append(Paragraph(
            "Barème (hypothèses de travail, à valider avec le métier) : famille cible (association 3, exploitant 2, bailleur 2) ; "
            "projet médico-social +3 ; exploitant d'un projet déposé par un tiers +3 ; dépôt récent +2 (≤ 2 ans) ou +1 (≤ 4 ans) ; "
            "permis autorisé depuis moins de 3 ans et pas encore commencé +2 ; maître d'ouvrage occasionnel +1 ; projet de taille "
            "significative +1 ; annulation récente +1 ; établissements FINESS exploités +2 ; taille moyenne ou grande +1, très grande −2 ; "
            "« à vérifier » −1. Aucune coordonnée : personnes morales et fiches publiques uniquement ; aucune prise de contact. "
            "Listes complètes : out_fouille/prospects_priorises.csv et prospects_ecartes.csv.", st["small"]))
        S.append(tableau(["Rang", "Score", "Prospect", "Qualification", "Dernier permis"],
                         [[p["rang"], p["score"],
                           Paragraph(f"<b>{esc(p['denomination'])}</b><br/>{esc(LIB_FAM.get(p['famille'], p['famille']))}"
                                     + ("<br/><i>exploitant trouvé via FINESS</i>" if p.get("origine", "").startswith("exploitant") else ""), st["cell"]),
                           Paragraph((f"<b>{esc(p['verdict_agent'])}</b> · adéquation {esc(p['adequation'])} · taille {esc(p['taille'])}<br/>"
                                      f"{esc(p['type_structure'])}<br/><i>{esc(p['besoin_immobilier'])}</i>")
                                     if p.get("verdict_agent") not in ("", "non qualifié") else
                                     "<i>non qualifié par l'agent (hors échantillon de test)</i>", st["cell"]),
                           Paragraph(f"{esc(p['dernier_depot'])} · {esc(p['dernier_commune'])}<br/>{esc(p['dernier_type'])} · {esc(p['dernier_etat'])}", st["cell"])]
                          for p in prosp["prospects"][:25]],
                         [13 * mm, 13 * mm, 47 * mm, 71 * mm, 32 * mm], num=(0, 1)))
        if prosp.get("ecartes"):
            S.append(Paragraph("Candidats écartés (extrait : ceux de l'agent, puis ceux du code)", st["h3"]))
            ec = sorted(prosp["ecartes"], key=lambda e: not e.get("ecarte_par", "").startswith("agent"))
            S.append(tableau(["Demandeur", "Écarté par", "Motif"],
                             [[Paragraph(esc(e["denomination"]), st["cell"]), Paragraph(esc(e.get("ecarte_par", "")), st["cell"]),
                               Paragraph(esc(e["motif"]), st["cell"])] for e in ec[:14]], [62 * mm, 34 * mm, 80 * mm]))
    # ---- constats
    S.append(PageBreak())
    S.append(Paragraph("6. Constats des agents (Claude et NVIDIA) et vérification", st["h2"]))
    S.append(Paragraph(
        "Chaque agent interroge les données par des outils en lecture seule, puis écrit ses constats. Le code contrôle "
        "automatiquement chaque note : tout nombre doit se retrouver dans les résultats d'outils (ou en être une somme / un quotient), "
        "tout pourcentage doit être recalculable avec deux nombres de sa phrase. Une relecture vérifie ensuite "
        "l'interprétation, que le code ne voit pas : chaque chiffre est recalculé par une requête rejouée et chaque lecture "
        "confrontée au dictionnaire. Cette relecture a été faite par Claude ; pour ses propres notes, c'est une auto-relecture.", st["p"]))
    agents = sorted({(m, j) for m, j, _ in bilan})
    S.append(tableau(["Agent", "Fichier", "Constats", "Exacts", "À corriger", "Erronés"],
                     [[m, j, sum(bilan[(m, j, c)] for c in cols + ["non relu"])] + [bilan[(m, j, c)] for c in cols]
                      for m, j in agents],
                     [52 * mm, 24 * mm, 20 * mm, 18 * mm, 22 * mm, 18 * mm], num=(2, 3, 4, 5)))
    S.append(Paragraph("« À corriger » : chiffres justes, mais période, titre, limite ou conclusion à reprendre.", st["small"]))
    if retirees:
        S.append(Paragraph(
            f"Les {len(retirees)} constats jugés erronés sont retirés du rapport (archivés dans archive_v2/notes_erronees_retirees.jsonl) : "
            + " ; ".join(f"« {esc(n.get('titre', ''))} » ({esc(relecture.get(espaces(n.get('titre', '')), {}).get('verdict', ''))})"
                         for n in retirees) + ".", st["small"]))
    for jeu in ("logements", "locaux"):
        S.append(Paragraph(f"Fichier {jeu}", st["h3"]))
        for n in [x for x in notes if x["jeu"] == jeu]:
            auto = n.get("auto")
            ctrl = ("chiffres vérifiés par le code" if auto == [] else
                    ("⚠ non vérifiables : " + "; ".join(auto)) if auto else "contrôle non disponible")
            rel = relecture.get(espaces(n.get("titre", "")), {})
            bloc = [Paragraph(f"<b>{esc(n.get('titre', ''))}</b>", st["p"]),
                    Paragraph(f"{esc(modele_lisible(n['modele']))} · thème {esc(n.get('theme', ''))} · fiabilité annoncée : "
                              f"<b>{esc(n.get('fiabilite', ''))}</b> · contrôle automatique : {esc(ctrl)}", st["small"]),
                    Paragraph(esc(n.get("constat", "")), st["p"]),
                    Paragraph("<i>Intérêt pour Buddimm :</i> " + esc(n.get("interet_buddimm", "")), st["small"]),
                    Paragraph("<i>Limites annoncées :</i> " + esc(n.get("limites", "") or "—"), st["small"])]
            if rel:
                bloc.append(Paragraph(f"<b>Relecture :</b> {esc(rel.get('verdict', ''))} — {esc(rel.get('commentaire', ''))}", st["small"]))
            bloc.append(Spacer(1, 7))
            S.append(KeepTogether(bloc))

    # ---- limites
    S.append(Paragraph("7. Limites", st["h2"]))
    for t in [
        "Personnes morales retrouvées dans Sirène uniquement ; PC seulement. Un permis modificatif n'a pas de ligne propre.",
        "Environ 15 % des ouvertures de chantier et un tiers des achèvements ne remontent jamais : taux d'achèvement = minima.",
        "Le NAF et le SIRET d'un permis sont ceux d'un établissement, parfois fermé : la famille s'appuie d'abord sur la catégorie juridique.",
        "Familles et verdicts de prospects : précision à mesurer sur les échantillons de contrôle tirés au hasard "
        "(out_fouille/controle/, à vérifier à la main puis `python src/echantillon.py mesurer`).",
        "Exploitants via FINESS : rapprochement par commune, rue et date d'ouverture ; un projet récent peut ne pas encore figurer "
        "dans FINESS (instantané du 04/05/2026), et un établissement ancien peut correspondre à une extension.",
        "Groupes : un seul niveau de rattachement ; les rôles de l'Annuaire sont parfois mal étiquetés (cabinets d'audit exclus par leur nom, heuristique).",
        "Constats des agents : propositions de modèles. Le contrôle automatique ne voit ni un vrai chiffre pris dans un autre périmètre, "
        "ni un classement ou une interprétation erronés ; d'où la relecture.",
        "Environ 123 lignes de la source (API du SDES) ont des accents abîmés (ex. « ANDRAÃÂSY » pour Andrésy) : réparés à la lecture par un motif régulier.",
        "Prospects : le barème est une hypothèse de travail ; le score classe, il ne prédit pas un besoin.",
        "Huit permis ont un code postal de terrain hors 78 alors que leur commune est dans les Yvelines (probables erreurs de saisie), conservés.",
    ]:
        S.append(Paragraph("• " + esc(t), st["p"]))

    out = SORTIE / "rapport_resultats_yvelines.pdf"
    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                            title="Qui construit dans les Yvelines ? — résultats", author="Prototype Sitadel")
    doc.build(S, onFirstPage=pied, onLaterPages=pied)
    print("écrit", out)


if __name__ == "__main__":
    main()
