"""Système GenAI multi-agents pour l'analyse et le monitoring des opérations post-trade.
Entrée : texte OU voix. Base : SQLite / PostgreSQL / Oracle (à régler dans DB_URL).
Lancer : streamlit run app.py
"""
import json
import re
import time
from datetime import date, datetime, timedelta
from decimal import Decimal

import altair as alt
import rapport_ui
import garde
import menu_discussions as disc
import ollama
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

# =====================  CONFIGURATION  =====================
MODEL = "qwen2.5-coder:3b"
VOICE_LANG = "fr"
WHISPER_SIZE = "tiny"

DB_URL = "postgresql+psycopg2://agent_ro:agent_ro_pwd@localhost:5432/posttrade"
# DB_URL = "sqlite:///file:post_trade.db?mode=ro&uri=true"
# DB_URL = "oracle+oracledb://user:motdepasse@localhost:1521/?service_name=XE"

DIALECT = make_url(DB_URL).get_backend_name()

DIALECT_HINTS = {
    "sqlite": "Base SQLite. Dates: date('now'), date('now','+7 days'). Limiter: LIMIT n. "
              "Prochain lundi: date('now','weekday 1','+1 day','weekday 1').",
    "postgresql": "Base PostgreSQL. Dates: CURRENT_DATE, CURRENT_DATE + INTERVAL '7 days'. Limiter: LIMIT n. "
                  "Prochain lundi: (date_trunc('week', CURRENT_DATE) + INTERVAL '7 days')::date. "
                  "Les colonnes de date sont de type DATE.",
    "oracle": "Base Oracle. Dates: TRUNC(SYSDATE), TRUNC(SYSDATE) + 7. Limiter: FETCH FIRST n ROWS ONLY "
              "(jamais LIMIT). Prochain lundi: TRUNC(SYSDATE,'IW') + 7. Pas de point-virgule final.",
}

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

# =====================  AGENT 1 : SQL  =====================
PROMPT_SQL = """Tu es l'Agent SQL d'un système de monitoring post-trade (règlement-livraison, custody, cash).
Date du jour : {today}. {dialect_hint}
Tu réponds UNIQUEMENT en JSON : {"sql": "...", "affichage": "courbe|histogramme|tableau|kpi", "titre": "..."}

Règles :
- Uniquement une requête SELECT, sur les tables ci-dessous, sans point-virgule final.
- "semaine prochaine" = du lundi prochain au dimanche suivant (7 jours).
- "échoué" = statut 'echoue'. "en TND" = devise 'TND'.
- affichage : kpi = un seul chiffre ; courbe = évolution dans le temps ;
  histogramme = comparaison entre catégories ; tableau = liste de lignes.
- Si l'utilisateur demande une liste (clients, comptes...), utilise "tableau".
- Si la question n'a aucun rapport avec les données post-trade (salutation, culture générale, texte incompréhensible), réponds {"sql": "", "affichage": "tableau", "titre": "", "hors_sujet": true}.

Schéma :
{schema}

Exemples :
Q: donner tous les clients
R: {"sql": "SELECT * FROM clients", "affichage": "tableau", "titre": "Tous les clients"}
Q: donner les comptes en TND
R: {"sql": "SELECT c.nom, cc.type_compte, cc.solde FROM comptes_clients cc JOIN clients c ON c.id_client=cc.id_client WHERE cc.devise='TND'", "affichage": "tableau", "titre": "Comptes en TND"}
Q: nombre d'instructions échouées par motif
R: {"sql": "SELECT motif_echec, COUNT(*) AS nb FROM instructions WHERE statut='echoue' GROUP BY motif_echec", "affichage": "histogramme", "titre": "Échecs par motif"}
Q: évolution du nombre d'instructions par jour de règlement
R: {"sql": "SELECT date_reglement, COUNT(*) AS nb FROM instructions GROUP BY date_reglement ORDER BY date_reglement", "affichage": "courbe", "titre": "Instructions par date de règlement"}
Q: répartition des instructions par statut
R: {"sql": "SELECT statut, COUNT(*) AS nb FROM instructions GROUP BY statut", "affichage": "histogramme", "titre": "Instructions par statut"}
Q: montant total des instructions par devise
R: {"sql": "SELECT devise, SUM(montant) AS total FROM instructions GROUP BY devise", "affichage": "histogramme", "titre": "Montant total par devise"}
Q: combien d'instructions sont en attente ?
R: {"sql": "SELECT COUNT(*) AS nb FROM instructions WHERE statut='en_attente'", "affichage": "kpi", "titre": "Instructions en attente"}
Q: bonjour
R: {"sql": "", "affichage": "tableau", "titre": "", "hors_sujet": true}
Q: quelle est la capitale de la France
R: {"sql": "", "affichage": "tableau", "titre": "", "hors_sujet": true}
"""

PROMPT_ANALYSTE = """Tu es l'Agent Analyste post-trade. À partir de la question et du résultat,
écris un commentaire de 1 à 2 phrases en français. Cite uniquement des faits chiffrés présents dans le résultat
(valeur la plus grande, la plus petite, total). N'interprète pas, n'invente rien."""

engine = create_engine(DB_URL)


def appeler_llm(system, user, json_mode=False):
    kwargs = {"format": "json"} if json_mode else {}
    rep = ollama.chat(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        **kwargs,
    )
    return rep["message"]["content"]


def agent_sql(question, erreur=None):
    system = (PROMPT_SQL.replace("{today}", date.today().isoformat())
              .replace("{dialect_hint}", DIALECT_HINTS[DIALECT])
              .replace("{schema}", SCHEMA))
    user = question if not erreur else f"{question}\n\nTa requête précédente a échoué : {erreur}. Corrige-la."
    return json.loads(appeler_llm(system, user, json_mode=True))


# =====================  AGENT 2 : CONTRÔLE  =====================
def agent_controle(sql):
    s = sql.strip().rstrip(";").lower()
    interdits = r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum|truncate|grant|merge|exec|execute)\b"
    if not (s.startswith("select") or s.startswith("with")):
        return False, "Seules les requêtes SELECT sont autorisées."
    if re.search(interdits, s):
        return False, "Mot-clé interdit détecté."
    if ";" in s:
        return False, "Une seule requête est autorisée."
    return True, "OK"


def executer(sql):
    with engine.connect() as conn:
        df = pd.read_sql_query(text(sql.strip().rstrip(";")), conn)
    for col in df.columns:
        if df[col].dtype == object and len(df) and isinstance(df[col].iloc[0], Decimal):
            df[col] = df[col].astype(float)
    return df


# =====================  AGENT 4 : AFFICHAGE  =====================
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
    return [c for c in df.columns
            if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]


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
        items += [(str(c) if str(c).lower().startswith("total") else f"Total {c}", fmt(df[c].sum()))
                  for c in colonnes_numeriques(df)[:3]]
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
    st.altair_chart(barres + etiquettes)


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
    st.altair_chart(courbe)


def dessiner_tableau(df):
    a_formater = [c for c in colonnes_numeriques(df) if not str(c).lower().startswith("id")]
    st.dataframe(df.style.format({c: fmt for c in a_formater}), hide_index=True)


RENDUS = {"Tableau": dessiner_tableau, "Histogramme": dessiner_histogramme,
          "Courbe": dessiner_courbe, "KPI": dessiner_kpi}


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
            vue = st.radio("Affichage", list(RENDUS), index=list(RENDUS).index(defaut),
                           horizontal=True, key=f"vue_{res['id']}")
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
        "Taux de règlement (%)": (
            "SELECT ROUND(100.0 * SUM(CASE WHEN statut='regle' THEN 1 ELSE 0 END) / "
            "NULLIF(SUM(CASE WHEN statut IN ('regle','echoue') THEN 1 ELSE 0 END), 0), 1) FROM instructions", {}),
        "Règlements à venir (7 jours)": (
            "SELECT COUNT(*) FROM instructions WHERE date_reglement BETWEEN :d1 AND :d2 "
            "AND statut IN ('en_attente','apparie')", {"d1": d1, "d2": d2}),
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


# =====================  TRAITEMENT D'UNE QUESTION  =====================
def traiter(question):
    etapes = []

    def noter(texte):
        etapes.append(texte)
        st.write(texte)

    nom_rapport = rapport_ui.detecter_rapport(question)
    if nom_rapport:
        return rapport_ui.traiter_rapport(nom_rapport, engine, appeler_llm, noter)
    message_garde = garde.reponse_garde(question)
    if message_garde:
        return {"id": time.time_ns(), "question": question, "info": message_garde, "sql": "", "etapes": []}
    noter("Agent SQL : génération de la requête")
    rep = agent_sql(question)
    if rep.get("hors_sujet") or not str(rep.get("sql", "")).strip():
        return {"id": time.time_ns(), "question": question, "info": garde.MESSAGE_AIDE, "sql": "", "etapes": []}
    ok, msg = agent_controle(rep["sql"])
    noter(f"Agent Contrôle : {msg}")
    if not ok:
        raise ValueError(msg)
    try:
        df = executer(rep["sql"])
    except Exception as e:
        noter("Agent SQL : correction après erreur")
        rep = agent_sql(question, erreur=str(e))
        ok, msg = agent_controle(rep["sql"])
        if not ok:
            raise ValueError(msg)
        df = executer(rep["sql"])
    vue = choisir_vue(df, rep.get("affichage", "tableau"), question)
    noter(f"Agent Affichage : {len(df)} ligne(s), vue choisie « {vue} »")
    commentaire = ""

    return {"id": time.time_ns(), "question": question, "sql": rep["sql"], "df": df,
            "affichage": vue, "titre": rep.get("titre", "Résultat"),
            "commentaire": commentaire, "etapes": etapes}


# =====================  INTERFACE  =====================
st.set_page_config(page_title="Post-trade GenAI", layout="wide")

# --- Menu latéral : discussions enregistrées + bouton "+ Nouveau" ---
disc.menu()

st.title("Assistant GenAI  : monitoring post-trade")
afficher_indicateurs()


def _envoyer_brouillon():
    st.session_state["question_en_attente"] = st.session_state.get("brouillon_vocal", "").strip()
    st.session_state.pop("brouillon_vocal", None)


def _annuler_brouillon():
    st.session_state.pop("brouillon_vocal", None)


# --- 1) Historique de la discussion courante ---
for res in disc.resultats_courants():
    if res.get("rapport"):
        st.chat_message("user").write(res.get("question", ""))
        with st.chat_message("assistant"):
            rap = res["rapport"]
            titre = rap.get("titre", "Rapport") if isinstance(rap, dict) else "Rapport"
            periode = rap.get("periode", "") if isinstance(rap, dict) else ""
            genere = rap.get("genere_le", "") if isinstance(rap, dict) else ""
            st.markdown(f"### 📄 {titre}")
            if periode or genere:
                st.caption(f"{periode}  |  généré le {genere}")
            st.info("Rapport enregistré. Cliquez ci-dessous pour le régénérer avec les données actuelles.")
            if st.button("🔄 Régénérer ce rapport", key=f"regen_{res['id']}"):
                st.session_state["question_en_attente"] = res.get("question", "")
                st.rerun()
        continue
    afficher_resultat(res)

# --- 2) Saisie utilisateur ---
question = st.session_state.pop("question_en_attente", None)
try:
    saisie = st.chat_input("Écris ton prompt ou clique sur le micro...", accept_audio=True)
except TypeError:
    st.sidebar.warning("Pour avoir le micro dans la barre : pip install -U streamlit")
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


# --- 3) Traitement + enregistrement + rafraîchissement immédiat ---
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

    # On enregistre TOUS les résultats (SQL + rapports allégés)
    r = st.session_state.get("resultat")
    if r and "erreur" not in r and not r.get("info"):
        disc.ajouter(r)
        st.rerun()


# --- 4) Afficher le dernier résultat s'il n'est pas dans l'historique ---
if st.session_state.get("resultat"):
    dernier = st.session_state["resultat"]
    if dernier.get("rapport") or dernier.get("info") or "erreur" in dernier:
        afficher_resultat(dernier)


# --- 5) Brouillon vocal ---
if "brouillon_vocal" in st.session_state:
    with st.container(border=True):
        st.caption("Message vocal reconnu : modifie-le ou ajoute du texte, puis clique sur Envoyer.")
        st.text_area("Message", key="brouillon_vocal", label_visibility="collapsed")
        b1, b2, _ = st.columns([1, 1, 6])
        b1.button("Envoyer", type="primary", on_click=_envoyer_brouillon)
        b2.button("Annuler", on_click=_annuler_brouillon)