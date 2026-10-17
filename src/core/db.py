"""Connexion à la base de données PostgreSQL / SQLite / Oracle."""
from decimal import Decimal

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from src.core.config import DB_URL

engine = create_engine(DB_URL)
DIALECT = make_url(DB_URL).get_backend_name()

DIALECT_HINTS = {
    "sqlite": "Base SQLite. Dates: date('now'), date('now','+7 days'). Limiter: LIMIT n. "
              "Prochain lundi: date('now','weekday 1','+1 day','weekday 1').",
    "postgresql": "Base PostgreSQL. Dates: CURRENT_DATE, CURRENT_DATE + INTERVAL '7 days'. "
                  "Limiter: LIMIT n. Prochain lundi: "
                  "(date_trunc('week', CURRENT_DATE) + INTERVAL '7 days')::date. "
                  "Les colonnes de date sont de type DATE.",
    "oracle": "Base Oracle. Dates: TRUNC(SYSDATE), TRUNC(SYSDATE) + 7. "
              "Limiter: FETCH FIRST n ROWS ONLY (jamais LIMIT). "
              "Prochain lundi: TRUNC(SYSDATE,'IW') + 7. Pas de point-virgule final.",
}


def executer_sql(sql):
    """Exécute une requête SELECT et renvoie un DataFrame."""
    with engine.connect() as conn:
        df = pd.read_sql_query(text(sql.strip().rstrip(";")), conn)
    for col in df.columns:
        if df[col].dtype == object and len(df) and isinstance(df[col].iloc[0], Decimal):
            df[col] = df[col].astype(float)
    return df