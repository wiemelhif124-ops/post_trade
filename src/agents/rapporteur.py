"""Agent Rapporteur : génère les rapports PDF/Excel en appelant le module rapports.py."""
import time
import re
from datetime import date, timedelta

from src.core.llm import appeler_llm
import rapports  # On garde l'import de ton ancien fichier pour l'instant

PROMPT_RAPPORTEUR = """Tu es l'Agent Rapporteur d'un système de monitoring post-trade.
À partir des indicateurs et des extraits de données fournis, rédige un rapport écrit en français,
professionnel et concis, en 3 parties :
Résumé : 2 à 3 phrases.
Points d'attention : 2 à 4 phrases (valeurs les plus élevées, anomalies, échecs, risques visibles dans les données).
Conclusion : 1 phrase.
Règles : cite uniquement des chiffres présents dans les données, n'invente rien, n'ajoute aucune recommandation
hors données, n'utilise ni markdown ni astérisques."""


def _resume_donnees(rap):
    """Prépare un résumé textuel pour le LLM."""
    lignes = ["Indicateurs :"] + [f"- {l} : {rapports.fmt(v)}" for l, v in rap["indicateurs"]]
    for s in rap["sections"]:
        lignes.append(f"\n{s['titre']} :")
        lignes.append(s["df"].head(8).to_csv(index=False) if not s["df"].empty else "(aucune donnée)")
    return "\n".join(lignes)


def generer(nom, engine, noter):
    """Construit le rapport, rédige la synthèse et prépare les fichiers PDF et Excel."""
    cfg = rapports.RAPPORTS[nom]
    d1 = d2 = None
    if cfg["debut"] is not None:
        d1 = date.today() + timedelta(days=cfg["debut"])
        d2 = date.today() + timedelta(days=cfg["fin"])
        
    noter(f"Agent Rapporteur : collecte des données « {nom} »")
    rap = rapports.construire_rapport(engine, nom, d1, d2)
    
    noter("Agent Rapporteur : rédaction de la synthèse")
    rap["synthese"] = appeler_llm(PROMPT_RAPPORTEUR, _resume_donnees(rap)).strip()
    
    noter("Agent Rapporteur : génération du PDF et de l'Excel")
    return {
        "id": time.time_ns(), 
        "question": f"Rapport : {nom}", 
        "rapport": rap, 
        "titre": rap["titre"],
        "pdf": rapports.exporter_pdf(rap), 
        "xlsx": rapports.exporter_excel(rap),
        "sql": "-- rapport multi-requêtes (voir rapports.py)", 
        "etapes": []
    }