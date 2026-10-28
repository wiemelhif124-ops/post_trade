"""Agent Routeur : classifie l'intention de l'utilisateur avec le LLM."""
from src.core.llm import appeler_llm, appeler_llm_json

PROMPT_ROUTEUR = """Tu es l'Agent Routeur d'un assistant post-trade.
Ton rôle est de classer la question de l'utilisateur dans l'une de ces 4 catégories :

1. "salutation" : "bonjour", "merci", "ça va ?", "au revoir", "qui es-tu ?"
2. "meta" : questions sur le post-trade en général ("c'est quoi le règlement-livraison ?", "explique-moi le post-trade")
3. "sql" : TOUTE question qui demande d'AGIR sur les données (générer, lister, afficher, montrer, combien, quels sont, donne-moi, etc.). 
   Exemples : "génère-moi toutes les instructions", "affiche les clients", "combien de comptes", "montre-moi les échecs".
4. "hors_sujet" : tout le reste ("capitale de la France", "écris un poème", "météo").

RÈGLE ABSOLUE : Si la question contient un VERBE D'ACTION (générer, lister, afficher, montrer, donner, combien, quels sont) ET qu'elle parle de données post-trade (instructions, clients, comptes, titres, cash), c'est TOUJOURS "sql".
Ne réponds JAMAIS par "meta" si l'utilisateur demande de générer ou lister des données.

Réponds UNIQUEMENT en JSON avec ce format :
{"type": "salutation|meta|sql|hors_sujet"}

Question de l'utilisateur : {question}
"""

PROMPT_META = """Tu es un expert en post-trade (Custody, Clearing & Settlement, Cash Management).
Réponds de manière claire et professionnelle à la question de l'utilisateur, en 2 ou 3 phrases maximum.
"""

def router(question):
    prompt = PROMPT_ROUTEUR.replace("{question}", question)
    try:
        rep = appeler_llm_json("Tu es un routeur JSON.", prompt)
        return rep.get("type", "sql")
    except Exception:
        return "sql"

def repondre_meta(question):
    return appeler_llm(PROMPT_META, question)