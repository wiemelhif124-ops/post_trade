"""Agent Sécurité : filtre les salutations et les questions hors domaine post-trade."""
import re
import unicodedata

EXEMPLES = ("« donner tous les clients », « comptes en TND », « nombre d'instructions échouées par motif », "
            "« combien d'instructions sont en attente ? », « rapport clients »")

MESSAGE_SALUT = "Bonjour ! "

MESSAGE_AIDE = ("Je n'ai pas compris cette demande, ou elle ne concerne pas les données post-trade "
                "(clients, comptes, titres, instructions de règlement-livraison, mouvements de cash). "
                f"Pouvez-vous la reformuler ? Exemples : {EXEMPLES}.")

_SALUTATIONS = {"bonjour", "bonsoir", "salut", "salam", "hello", "hi", "hey", "coucou", "merci", "ok",
                "d'accord", "daccord", "au", "revoir", "ca", "va", "comment", "allez", "vous", "tu", "cc"}

_MOTS_DOMAINE = re.compile(
    r"\b(client|compte|solde|titre|isin|instruction|reglement|livraison|echec|echou|regle|cash|tresorerie|"
    r"mouvement|devise|tnd|eur|usd|montant|achat|vente|vendre|acheter|statut|attente|apparie|rapport|bilan|"
    r"action|obligation|emetteur|pays|banque|assurance|fonds|entreprise|motif|quantite|date|jour|semaine|mois|"
    r"portefeuille|custody|trade|total|nombre|combien|liste|tableau|histogramme|courbe|kpi|evolution|"
    r"repartition|moyenne|somme|maximum|minimum|volume|flux|entrant|sortant|prevu|execute)"
)


def _normaliser(texte):
    texte = unicodedata.normalize("NFD", texte.lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def est_salutation(question):
    mots = re.findall(r"[a-z']+", _normaliser(question))
    return bool(mots) and all(m in _SALUTATIONS for m in mots)


def est_dans_le_domaine(question):
    return bool(_MOTS_DOMAINE.search(_normaliser(question)))


def reponse_garde(question):
    """Renvoie un message si la question ne doit pas aller à l'Agent SQL, sinon None."""
    if est_salutation(question):
        return MESSAGE_SALUT
    if not est_dans_le_domaine(question):
        return MESSAGE_AIDE
    return None