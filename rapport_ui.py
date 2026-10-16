"""Liaison entre app.py et rapports.py : rapport écrit + téléchargement PDF / Excel."""
import re
import time
from datetime import date, timedelta

import streamlit as st

import rapports

PROMPT_RAPPORTEUR = """Tu es l'Agent Rapporteur d'un système de monitoring post-trade.
À partir des indicateurs et des extraits de données fournis, rédige un rapport écrit en français,
professionnel et concis, en 3 parties :
Résumé : 2 à 3 phrases.
Points d'attention : 2 à 4 phrases (valeurs les plus élevées, anomalies, échecs, risques visibles dans les données).
Conclusion : 1 phrase.
Règles : cite uniquement des chiffres présents dans les données, n'invente rien, n'ajoute aucune recommandation
hors données, n'utilise ni markdown ni astérisques."""

_VUES = {"tableau": "Tableau", "histogramme": "Histogramme", "courbe": "Courbe"}


# ============================================================
# DÉTECTION DU RAPPORT — version corrigée
# ============================================================
def detecter_rapport(question):
    """Renvoie le nom du rapport demandé, ou None si ce n'est pas une demande de rapport."""
    q = question.lower()
    if not re.search(r"rapport|bilan|compte[- ]rendu", q):
        return None

    # 1) Règlements à venir (le plus spécifique)
    if re.search(r"à venir|a venir|prochain|futur", q):
        return "Règlements à venir"

    # 2) Cash / trésorerie
    if re.search(r"cash|tr[ée]sorerie|mouvement", q):
        return "Cash et trésorerie"

    # 3) Clients : uniquement si on ne parle pas de "comptes" ou "soldes"
    if re.search(r"\bclients?\b", q) and not re.search(r"compte|solde", q):
        return "Clients"

    # 4) Comptes / soldes
    if re.search(r"compte|solde", q):
        return "Comptes et soldes"

    # 5) Par défaut
    return "Règlement-livraison"


# ============================================================
# LE RESTE EST INCHANGÉ (fonctionne déjà)
# ============================================================
def _resume_donnees(rap):
    lignes = ["Indicateurs :"] + [f"- {l} : {rapports.fmt(v)}" for l, v in rap["indicateurs"]]
    for s in rap["sections"]:
        lignes.append(f"\n{s['titre']} :")
        lignes.append(s["df"].head(8).to_csv(index=False) if not s["df"].empty else "(aucune donnée)")
    return "\n".join(lignes)


def traiter_rapport(nom, engine, llm, noter):
    """Construit le rapport, rédige la synthèse et prépare les fichiers PDF et Excel."""
    cfg = rapports.RAPPORTS[nom]
    d1 = d2 = None
    if cfg["debut"] is not None:
        d1 = date.today() + timedelta(days=cfg["debut"])
        d2 = date.today() + timedelta(days=cfg["fin"])
    noter(f"Agent Rapporteur : collecte des données « {nom} »")
    rap = rapports.construire_rapport(engine, nom, d1, d2)
    noter("Agent Rapporteur : rédaction de la synthèse")
    rap["synthese"] = llm(PROMPT_RAPPORTEUR, _resume_donnees(rap)).strip()
    noter("Agent Rapporteur : génération du PDF et de l'Excel")
    return {"id": time.time_ns(), "question": f"Rapport : {nom}", "rapport": rap, "titre": rap["titre"],
            "pdf": rapports.exporter_pdf(rap), "xlsx": rapports.exporter_excel(rap),
            "sql": "-- rapport multi-requêtes (voir rapports.py)", "etapes": []}


def afficher(res, rendus):
    rap = res["rapport"]
    st.header(rap["titre"])
    st.caption(f"{rap['periode']}  |  généré le {rap['genere_le']}")

    nom_fichier = re.sub(r"\W+", "_", rap["titre"].lower()).strip("_")
    c1, c2, _ = st.columns([1, 1, 4])
    c1.download_button("Télécharger le PDF", res["pdf"], file_name=f"{nom_fichier}.pdf",
                       mime="application/pdf", type="primary", key=f"pdf_{res['id']}")
    c2.download_button("Télécharger l'Excel", res["xlsx"], file_name=f"{nom_fichier}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key=f"xls_{res['id']}")

    ind = rap["indicateurs"]
    for col, (label, v) in zip(st.columns(len(ind)), ind):
        with col.container(border=True):
            st.metric(label, rapports.fmt(v))

    st.subheader("Synthèse")
    st.write(rap["synthese"])

    for s in rap["sections"]:
        st.subheader(s["titre"])
        df = s["df"]
        if df.empty:
            st.info("Aucune donnée pour cette section.")
            continue
        rendu = rendus[_VUES.get(s["vue"], "Tableau")]
        if rendu(df) is False:
            rendus["Tableau"](df)
        if s["vue"] != "tableau":
            with st.expander("Voir les données"):
                rendus["Tableau"](df)