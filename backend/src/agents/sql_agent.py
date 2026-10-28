"""Agent SQL : transforme une question en requête SELECT."""
from datetime import date

from src.core.config import SCHEMA
from src.core.db import DIALECT, DIALECT_HINTS
from src.core.llm import appeler_llm_json

PROMPT_SQL = """Tu es l'Agent SQL d'un système de monitoring post-trade (règlement-livraison, custody, cash).
Date du jour : {today}. {dialect_hint}
Tu réponds UNIQUEMENT en JSON : {{"sql": "...", "affichage": "courbe|histogramme|tableau|kpi", "titre": "..."}}

Règles :
- Uniquement une requête SELECT, sur les tables ci-dessous, sans point-virgule final.
- "semaine prochaine" = du lundi prochain au dimanche suivant (7 jours).
- "échoué" = statut 'echoue'. "en TND" = devise 'TND'.
- affichage : kpi = un seul chiffre ; courbe = évolution dans le temps ;
  histogramme = comparaison entre catégories ; tableau = liste de lignes.
- Si l'utilisateur demande une liste (clients, comptes...), utilise "tableau".
- Si la question n'a aucun rapport avec les données post-trade, réponds
  {{"sql": "", "affichage": "tableau", "titre": "", "hors_sujet": true}}.

Schéma :
{schema}

Exemples :
Q: donner tous les clients
R: {{"sql": "SELECT * FROM clients", "affichage": "tableau", "titre": "Tous les clients"}}
Q: nombre d'instructions échouées par motif
R: {{"sql": "SELECT motif_echec, COUNT(*) AS nb FROM instructions WHERE statut='echoue' GROUP BY motif_echec", "affichage": "histogramme", "titre": "Échecs par motif"}}
Q: combien d'instructions sont en attente ?
R: {{"sql": "SELECT COUNT(*) AS nb FROM instructions WHERE statut='en_attente'", "affichage": "kpi", "titre": "Instructions en attente"}}
Q: bonjour
R: {{"sql": "", "affichage": "tableau", "titre": "", "hors_sujet": true}}
"""


def generer(question, erreur=None):
    """Génère une requête SQL à partir d'une question."""
    prompt = (PROMPT_SQL
              .replace("{today}", date.today().isoformat())
              .replace("{dialect_hint}", DIALECT_HINTS[DIALECT])
              .replace("{schema}", SCHEMA))
    user = question if not erreur else f"{question}\n\nTa requête précédente a échoué : {erreur}. Corrige-la."
    return appeler_llm_json(prompt, user)