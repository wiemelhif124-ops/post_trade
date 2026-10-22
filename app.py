"""Système GenAI multi-agents pour l'analyse et le monitoring des opérations post-trade."""
import os
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
import json
import re
import time
from datetime import date, datetime, timedelta
from decimal import Decimal

import altair as alt
import rapport_ui 
from src.agents import historiseur as disc
import ollama
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url 

from src.agents import securite as garde_v2
from src.agents import controle as controle_v2
from src.agents import sql_agent as sql_agent_v2 
from src.agents import analyste as analyste_v2 
from src.agents import rapporteur as rapporteur_v2 
from src.core.config import DB_URL 
from src.agents import routeur as routeur_v2
from src.agents import correcteur as correcteur_v2

# =====================  CONFIGURATION  =====================
MODEL = "qwen2.5-coder:3b"
VOICE_LANG = "fr"
WHISPER_SIZE = "tiny"

DIALECT = make_url(DB_URL).get_backend_name()
engine = create_engine(DB_URL)

DIALECT_HINTS = {
    "postgresql": "Base PostgreSQL. Dates: CURRENT_DATE, CURRENT_DATE + INTERVAL '7 days'. Limiter: LIMIT n. "
                  "Prochain lundi: (date_trunc('week', CURRENT_DATE) + INTERVAL '7 days')::date.",
}

SCHEMA = """
clients(id_client, nom, pays, type_client)
comptes_clients(id_compte, id_client, type_compte, devise, solde)
titres(isin, nom, type_titre, emetteur)
instructions(id_instruction, id_compte, isin, sens, quantite, montant, devise,
             date_negociation, date_reglement, statut, motif_echec)
mouvements_cash(id_mouvement, id_compte, sens, montant, devise, date_valeur, statut)
"""

PROMPT_SQL = """Tu es l'Agent SQL. Date du jour : {today}. {dialect_hint}
Tu réponds UNIQUEMENT en JSON : {"sql": "...", "affichage": "courbe|histogramme|tableau|kpi", "titre": "..."}
Règles : Uniquement SELECT. Schéma : {schema}
"""

PROMPT_ANALYSTE = """Tu es l'Agent Analyste. Écris un commentaire de 1 à 2 phrases en français."""


def appeler_llm(system, user, json_mode=False):
    kwargs = {"format": "json"} if json_mode else {}
    rep = ollama.chat(model=MODEL, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **kwargs)
    return rep["message"]["content"]


def executer(sql):
    with engine.connect() as conn:
        df = pd.read_sql_query(text(sql.strip().rstrip(";")), conn)
    for col in df.columns:
        if df[col].dtype == object and len(df) and isinstance(df[col].iloc[0], Decimal):
            df[col] = df[col].astype(float)
    return df


# =====================  AFFICHAGE  =====================
AFFICHAGES = {"tableau": "Tableau", "histogramme": "Histogramme", "courbe": "Courbe", "kpi": "KPI"}


def fmt(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f != f:
        return "—"
    if f == int(f):
        return f"{f:,.0f}".replace(",", " ")
    return f"{f:,.2f}".replace(",", " ").replace(".", ",")


def colonnes_numeriques(df):
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]

def est_colonne_date(serie):
    premier = serie.dropna().iloc[0] if serie.notna().any() else None
    return bool(pd.api.types.is_datetime64_any_dtype(serie) or isinstance(premier, (date, datetime))
                or (isinstance(premier, str) and re.match(r"\d{4}-\d{2}-\d{2}", premier)))

def choisir_vue(df, propose, question):
    propose = propose if propose in AFFICHAGES else "tableau"
    if df.shape == (1, 1):
        return "kpi"
    if propose != "tableau" or df.empty or df.shape[1] != 2 or not 2 <= len(df) <= 40:
        return propose
    num = colonnes_numeriques(df)
    q = question.lower()
    if len(num) == 1 and df.columns[0] not in num:
        if est_colonne_date(df[df.columns[0]]) and re.search(r"[ée]volution|tendance|par (jour|mois|date)", q):
            return "courbe"
        if re.search(r"\bpar\b|r[ée]partition|total|nombre|combien|somme|moyenne", q):
            return "histogramme"
    return propose

def dessiner_kpi(df):
    if len(df) == 1:
        items = [(str(c), fmt(df.iloc[0][c])) for c in df.columns[:4]]
    else:
        items = [("Nombre de lignes", fmt(len(df)))]
        items += [(str(c) if str(c).lower().startswith("total") else f"Total {c}", fmt(df[c].sum())) for c in colonnes_numeriques(df)[:3]]
    cols = st.columns(len(items))
    for col, (label, valeur) in zip(cols, items):
        with col.container(border=True):
            st.metric(label, valeur)

def dessiner_histogramme(df):
    num = colonnes_numeriques(df)
    if len(df.columns) < 2 or not num:
        return False
    x = next((c for c in df.columns if c not in num), df.columns[0])
    y = next((c for c in num if c != x), None)
    if y is None:
        return False
    d = df[[x, y]].rename(columns={x: "categorie", y: "valeur"})
    d["categorie"] = d["categorie"].astype(str)
    base = alt.Chart(d).encode(
        x=alt.X("categorie", type="nominal", sort="-y", title=str(x), axis=alt.Axis(labelAngle=-30)),
        y=alt.Y("valeur", type="quantitative", title=str(y), axis=alt.Axis(tickMinStep=1)),
        tooltip=[alt.Tooltip("categorie", title=str(x)), alt.Tooltip("valeur", title=str(y), format=",.2f")],
    )
    barres = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#E8615B")
    etiquettes = base.mark_text(dy=-8).encode(text=alt.Text("valeur", type="quantitative", format=",.0f"))
    st.altair_chart(barres + etiquettes, use_container_width=True)

def dessiner_courbe(df):
    num = colonnes_numeriques(df)
    if len(df.columns) < 2:
        return False
    x = df.columns[0]
    ys = [c for c in num if c != x]
    if not ys:
        return False
    d = df[[x] + ys].rename(columns={x: "axe"})
    if est_colonne_date(d["axe"]):
        d["axe"] = pd.to_datetime(d["axe"])
        type_x = "temporal"
    else:
        d["axe"] = d["axe"].astype(str)
        type_x = "ordinal"
    d = d.melt(id_vars="axe", var_name="serie", value_name="valeur")
    courbe = alt.Chart(d).mark_line(point=True).encode(
        x=alt.X("axe", type=type_x, title=str(x)),
        y=alt.Y("valeur", type="quantitative", title=None, axis=alt.Axis(tickMinStep=1)),
        color=alt.Color("serie", type="nominal", legend=None if len(ys) == 1 else alt.Legend(title=None)),
        tooltip=["axe", "serie", alt.Tooltip("valeur", format=",.2f")],
    )
    st.altair_chart(courbe, use_container_width=True)

def dessiner_tableau(df):
    a_formater = [c for c in colonnes_numeriques(df) if not str(c).lower().startswith("id")]
    st.dataframe(df.style.format({c: fmt for c in a_formater}), use_container_width=True, hide_index=True)

RENDUS = {"Tableau": dessiner_tableau, "Histogramme": dessiner_histogramme, "Courbe": dessiner_courbe, "KPI": dessiner_kpi}


def afficher_resultat(res):
    st.chat_message("user").write(res["question"])
    with st.chat_message("assistant"):
        if "erreur" in res:
            st.error(res["erreur"])
            return
        if res.get("info"):
            st.info(res["info"])
            return
        if res.get("rapport"):
            rapport_ui.afficher(res, RENDUS)
            return
        df = res["df"]
        st.subheader(res["titre"])
        if df.empty:
            st.info("Aucun résultat.")
        else:
            defaut = "KPI" if df.shape == (1, 1) else AFFICHAGES.get(res["affichage"], "Tableau")
            vue = st.radio("Affichage", list(RENDUS), index=list(RENDUS).index(defaut), horizontal=True, key=f"vue_{res['id']}")
            if RENDUS[vue](df) is False:
                st.info(f"La vue « {vue} » ne convient pas à ces données : affichage en tableau.")
                dessiner_tableau(df)
            if res["commentaire"]:
                st.write(res["commentaire"])
        with st.expander("Détails des agents et requête SQL"):
            for etape in res["etapes"]:
                st.write("• " + etape)
            st.code(res["sql"], language="sql")


# =====================  TABLEAU DE BORD  =====================
@st.cache_data(ttl=60)
def indicateurs():
    d1 = date.today()
    d2 = d1 + timedelta(days=7)
    requetes = {
        "Instructions en attente": ("SELECT COUNT(*) FROM instructions WHERE statut='en_attente'", {}),
        "Instructions échouées": ("SELECT COUNT(*) FROM instructions WHERE statut='echoue'", {}),
        "Taux de règlement (%)": ("SELECT ROUND(100.0 * SUM(CASE WHEN statut='regle' THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN statut IN ('regle','echoue') THEN 1 ELSE 0 END), 0), 1) FROM instructions", {}),
        "Règlements à venir (7 jours)": ("SELECT COUNT(*) FROM instructions WHERE date_reglement BETWEEN :d1 AND :d2 AND statut IN ('en_attente','apparie')", {"d1": d1, "d2": d2}),
    }
    valeurs = {}
    for label, (sql, params) in requetes.items():
        try:
            with engine.connect() as conn:
                valeurs[label] = conn.execute(text(sql), params).scalar()
        except Exception:
            valeurs[label] = None
    return valeurs


def afficher_indicateurs():
    valeurs = indicateurs()
    for col, (label, v) in zip(st.columns(len(valeurs)), valeurs.items()):
        with col.container(border=True):
            st.metric(label, "—" if v is None else fmt(v))


# =====================  VOIX  =====================
@st.cache_resource
def charger_whisper():
    from faster_whisper import WhisperModel
    return WhisperModel(WHISPER_SIZE, device="cpu", compute_type="int8")


def transcrire(audio_bytes):
    import io
    segments, _ = charger_whisper().transcribe(io.BytesIO(audio_bytes), language=VOICE_LANG)
    return " ".join(s.text.strip() for s in segments).strip()


# =====================  TRAITEMENT  =====================
def traiter(question):
    etapes = []
    def noter(texte):
        etapes.append(texte)
        st.write(texte)

    # --- L'AGENT ROUTEUR ---
    intention = routeur_v2.router(question)
    noter(f"Agent Routeur : intention « {intention} »")

    if intention == "salutation":
        return {"id": time.time_ns(), "question": question, "info": "Bonjour ! Je suis votre assistant post-trade. Que puis-je faire ?", "sql": "", "etapes": etapes}
    if intention == "meta":
        noter("Agent Routeur : génération d'une réponse métier...")
        reponse_meta = routeur_v2.repondre_meta(question)
        return {"id": time.time_ns(), "question": question, "info": reponse_meta, "sql": "", "etapes": etapes}
    if intention == "hors_sujet":
        return {"id": time.time_ns(), "question": question, "info": "Désolé, je ne peux répondre qu'aux questions post-trade.", "sql": "", "etapes": etapes}

    # --- SUITE NORMALE ---
    nom_rapport = rapport_ui.detecter_rapport(question)
    if nom_rapport:
        return rapporteur_v2.generer(nom_rapport, engine, noter)
        
    message_garde = garde_v2.reponse_garde(question)
    if message_garde:
        return {"id": time.time_ns(), "question": question, "info": message_garde, "sql": "", "etapes": []}
        
    noter("Agent SQL : génération de la requête")
    rep = sql_agent_v2.generer(question)
    
    if rep.get("hors_sujet") or not str(rep.get("sql", "")).strip():
        return {"id": time.time_ns(), "question": question, "info": garde_v2.MESSAGE_AIDE, "sql": "", "etapes": []}
        
    ok, msg = controle_v2.verifier(rep["sql"])
    noter(f"Agent Contrôle : {msg}")
    if not ok:
        raise ValueError(msg)

    try:
        df = executer(rep["sql"])
    except Exception as e:
        noter("Agent Correcteur : la requête a échoué, tentative de correction...")
        # ON APPELLE L'AGENT CORRECTEUR ICI
        rep = correcteur_v2.corriger(question, rep["sql"], str(e))
        
        ok, msg = controle_v2.verifier(rep["sql"])
        if not ok:
            raise ValueError(msg)
        df = executer(rep["sql"])
        
    vue = choisir_vue(df, rep.get("affichage", "tableau"), question)
    noter(f"Agent Affichage : {len(df)} ligne(s), vue choisie « {vue} »")
    commentaire = analyste_v2.commenter(question, df)
    
    return {"id": time.time_ns(), "question": question, "sql": rep["sql"], "df": df,
            "affichage": vue, "titre": rep.get("titre", "Résultat"),
            "commentaire": commentaire, "etapes": etapes}


# =====================  INTERFACE  =====================
st.set_page_config(page_title="Post-trade GenAI", layout="wide")
disc.menu()

st.title("Assistant GenAI : monitoring post-trade")
afficher_indicateurs()

def _envoyer_brouillon():
    st.session_state["question_en_attente"] = st.session_state.get("brouillon_vocal", "").strip()
    st.session_state.pop("brouillon_vocal", None)

def _annuler_brouillon():
    st.session_state.pop("brouillon_vocal", None)

# --- 1) Historique ---
for res in disc.resultats_courants():
    afficher_resultat(res)

# --- 2) Saisie ---
question = st.session_state.pop("question_en_attente", None)
try:
    saisie = st.chat_input("Écris ton prompt ou clique sur le micro...", accept_audio=True)
except TypeError:
    saisie = st.chat_input("Écris ton prompt...")

if saisie:
    texte_saisi = (saisie if isinstance(saisie, str) else (saisie.text or "")).strip()
    audio = None if isinstance(saisie, str) else getattr(saisie, "audio", None)
    if audio is not None:
        with st.spinner("Transcription..."):
            transcrit = transcrire(audio.getvalue())
        st.session_state["brouillon_vocal"] = f"{texte_saisi} {transcrit}".strip()
    elif texte_saisi:
        question = texte_saisi

# --- 3) Traitement ---
if question:
    zone = st.empty()
    with zone.container():
        st.chat_message("user").write(question)
        with st.chat_message("assistant"):
            with st.status("Agents au travail...") as status:
                try:
                    st.session_state["resultat"] = traiter(question)
                    status.update(label="Terminé", state="complete")
                except Exception as e:
                    st.session_state["resultat"] = {"question": question, "erreur": f"Erreur : {e}"}
                    status.update(label="Erreur", state="error")
    zone.empty()

    r = st.session_state.get("resultat")
    if r:
        disc.ajouter(r)
        st.rerun()

# --- 4) Affichage du dernier résultat ---
if st.session_state.get("resultat"):
    dernier = st.session_state["resultat"]
    deja_affiche = any(r.get("id") == dernier.get("id") for r in disc.resultats_courants())
    if not deja_affiche:
        afficher_resultat(dernier)
    if not dernier.get("erreur"): 
        st.session_state.pop("resultat", None)

# --- 5) Brouillon vocal ---
if "brouillon_vocal" in st.session_state:
    with st.container(border=True):
        st.caption("Message vocal reconnu : modifie-le ou ajoute du texte, puis clique sur Envoyer.")
        st.text_area("Message", key="brouillon_vocal", label_visibility="collapsed")
        b1, b2, _ = st.columns([1, 1, 6])
        b1.button("Envoyer", type="primary", on_click=_envoyer_brouillon)
        b2.button("Annuler", on_click=_annuler_brouillon)