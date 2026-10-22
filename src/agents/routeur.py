"""Agent Routeur : classifie l'intention de l'utilisateur avec le LLM."""
from src.core.llm import appeler_llm, appeler_llm_json

PROMPT_ROUTEUR = """Tu es l'Agent Routeur d'un assistant post-trade.
Ton rôle est de classer la question de l'utilisateur dans l'une de ces 4 catégories :

1. "salutation" : "bonjour", "merci", "ça va ?", "au revoir", "qui es-tu ?"
2. "meta" : questions sur le post-trade en général ("c'est quoi le règlement-livraison ?", "explique-moi le post-trade")
3. "sql" : questions nécessitant d'interroger la base de données ("combien de clients", "les instructions échouées")
4. "hors_sujet" : tout le reste ("capitale de la France", "écris un poème")

Réponds UNIQUEMENT en JSON avec ce format :
{"type": "salutation|meta|sql|hors_sujet"}

Question de l'utilisateur : {question}
"""

PROMPT_META = """Tu es un expert en post-trade (Custody, Clearing & Settlement, Cash Management).
Réponds de manière claire et professionnelle à la question de l'utilisateur, en 2 ou 3 phrases maximum.
"""

def router(question):
    """Renvoie la catégorie de la question."""
    prompt = PROMPT_ROUTEUR.replace("{question}", question)
    try:
        rep = appeler_llm_json("Tu es un routeur JSON.", prompt)
        return rep.get("type", "sql")
    except Exception:
        return "sql"

def repondre_meta(question):
    """Génère une réponse pour les questions générales sur le post-trade."""
    return appeler_llm(PROMPT_META, question)