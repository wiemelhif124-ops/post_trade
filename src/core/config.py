"""Configuration centrale du projet post-trade multi-agents."""
import os

# =====================  MODÈLE LLM  =====================
MODEL = "qwen2.5-coder:3b"
VOICE_LANG = "fr"
WHISPER_SIZE = "tiny"

# =====================  BASE DE DONNÉES  =====================
DB_URL = "postgresql+psycopg2://agent_ro:agent_ro_pwd@localhost:5432/posttrade"
# DB_URL = "sqlite:///file:post_trade.db?mode=ro&uri=true"
# DB_URL = "oracle+oracledb://user:motdepasse@localhost:1521/?service_name=XE"

# =====================  CHEMINS  =====================
RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOSSIER_DATA = os.path.join(RACINE, "data")
FICHIER_DISCUSSIONS = os.path.join(RACINE, "discussions.pkl")

# =====================  SCHÉMA DE LA BASE  =====================
SCHEMA = """
clients(id_client, nom, pays, type_client)            -- type_client: banque|assurance|fonds|entreprise
comptes_clients(id_compte, id_client, type_compte, devise, solde)  -- type_compte: titres|cash ; devise: TND|EUR|USD
titres(isin, nom, type_titre, emetteur)               -- type_titre: action|obligation
instructions(id_instruction, id_compte, isin, sens, quantite, montant, devise,
             date_negociation, date_reglement, statut, motif_echec)
   -- sens: achat|vente ; statut: en_attente|apparie|regle|echoue
mouvements_cash(id_mouvement, id_compte, sens, montant, devise, date_valeur, statut)
   -- sens: entrant|sortant ; statut: prevu|execute
Jointures : comptes_clients.id_client = clients.id_client ;
instructions.id_compte = comptes_clients.id_compte ; instructions.isin = titres.isin ;
mouvements_cash.id_compte = comptes_clients.id_compte
"""