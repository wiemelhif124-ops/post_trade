"""Appel au LLM Ollama."""
import json

import ollama

from src.core.config import MODEL


def appeler_llm(system, user, json_mode=False):
    """Appelle le LLM avec un prompt système et un prompt utilisateur."""
    kwargs = {"format": "json"} if json_mode else {}
    rep = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        **kwargs,
    )
    return rep["message"]["content"]


def appeler_llm_json(system, user):
    """Appelle le LLM et parse la réponse en JSON."""
    return json.loads(appeler_llm(system, user, json_mode=True))