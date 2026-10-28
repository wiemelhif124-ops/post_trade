"""Agent Correcteur : corrige une requête SQL qui a échoué."""
from src.agents import sql_agent

def corriger(question, sql_echoue, erreur):
    """Demande à l'Agent SQL de corriger sa requête en lui donnant l'erreur."""
    return sql_agent.generer(question, erreur=f"La requête '{sql_echoue}' a échoué avec l'erreur : {erreur}")