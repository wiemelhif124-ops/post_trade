"""Agent Contrôle : vérifie que le SQL est un SELECT sans mot interdit."""
import re

_MOTS_INTERDITS = (
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|"
    r"replace|vacuum|truncate|grant|merge|exec|execute)\b"
)


def verifier(sql):
    """Retourne (ok, message) : True si le SQL est valide et sûr."""
    s = sql.strip().rstrip(";").lower()
    if not (s.startswith("select") or s.startswith("with")):
        return False, "Seules les requêtes SELECT sont autorisées."
    if re.search(_MOTS_INTERDITS, s):
        return False, "Mot-clé interdit détecté."
    if ";" in s:
        return False, "Une seule requête est autorisée."
    return True, "OK"