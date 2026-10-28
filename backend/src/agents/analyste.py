"""Agent Analyste : rédige un commentaire chiffré à partir du résultat."""
from src.core.llm import appeler_llm

PROMPT_ANALYSTE = """Tu es l'Agent Analyste post-trade. À partir de la question et du résultat,
écris un commentaire de 1 à 2 phrases en français. Cite uniquement des faits chiffrés présents dans le résultat
(valeur la plus grande, la plus petite, total). N'interprète pas, n'invente rien."""


def commenter(question, df, nb_lignes, langue_instruction):
    """Renvoie un commentaire (str) à partir d'une question et d'un DataFrame."""
    if df.empty:
        return ""
    
    prompt_modifie = f"""{PROMPT_ANALYSTE}
    
    IMPORTANT : Le résultat contient exactement {nb_lignes} lignes. Ne compte pas toi-même.
    {langue_instruction}"""
    
    return appeler_llm(
        prompt_modifie,
        f"Question : {question}\nRésultat (5 premières lignes) :\n{df.head(5).to_csv(index=False)}",
    )