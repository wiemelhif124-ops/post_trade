"""Agent Analyste : rédige un commentaire chiffré à partir du résultat."""
from src.core.llm import appeler_llm

PROMPT_ANALYSTE = """Tu es l'Agent Analyste post-trade. À partir de la question et du résultat,
écris un commentaire de 1 à 2 phrases en français. Cite uniquement des faits chiffrés présents dans le résultat
(valeur la plus grande, la plus petite, total). N'interprète pas, n'invente rien."""


def commenter(question, df):
    """Renvoie un commentaire (str) à partir d'une question et d'un DataFrame."""
    if df.empty:
        return ""
    return appeler_llm(
        PROMPT_ANALYSTE,
        f"Question : {question}\nRésultat (20 premières lignes) :\n{df.head(20).to_csv(index=False)}",
    )