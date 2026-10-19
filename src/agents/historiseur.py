"""Agent Historiseur : gère la sauvegarde, l'affichage et la recherche des discussions."""
import io
import os
import pickle
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

# On pointe vers le fichier de sauvegarde à la racine du projet
FICHIER = Path(__file__).parent.parent.parent / "discussions.pkl"


# ---------------------------------------------------------------- sauvegarde sur disque
def _charger():
    try:
        with open(FICHIER, "rb") as f:
            data = pickle.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _allege(res):
    """Copie du résultat sans les gros objets (DataFrames, bytes PDF/Excel)."""
    copie = dict(res)
    if copie.get("rapport"):
        r = copie["rapport"]
        copie["rapport"] = {
            "titre": r.get("titre", "Rapport"),
            "periode": r.get("periode", ""),
            "genere_le": r.get("genere_le", ""),
        }
    copie.pop("pdf", None)
    copie.pop("xlsx", None)
    return copie


def _sauver():
    data = []
    for d in st.session_state.get("discussions", []):
        copie = dict(d)
        copie["resultats"] = [_allege(r) for r in d["resultats"]]
        data.append(copie)
    tmp = FICHIER.with_suffix(".tmp")
    try:
        with open(tmp, "wb") as f:
            pickle.dump(data, f)
        os.replace(tmp, FICHIER)
    except Exception as e:
        st.warning(f"Sauvegarde des discussions impossible : {e}")


def _etat():
    if "discussions" not in st.session_state:
        st.session_state["discussions"] = _charger()
        st.session_state["disc_courante"] = None
    return st.session_state["discussions"]


# ---------------------------------------------------------------- API pour app.py
def resultats_courants():
    for d in _etat():
        if d["id"] == st.session_state.get("disc_courante"):
            return d["resultats"]
    return []


def ajouter(res):
    discussions = _etat()
    courante = None
    for d in discussions:
        if d["id"] == st.session_state.get("disc_courante"):
            courante = d
    if courante is None:
        titre = " ".join(str(res.get("question") or "Discussion").split())
        courante = {
            "id": time.time_ns(),
            "titre": titre[:40] + ("…" if len(titre) > 40 else ""),
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "timestamp": time.time(),
            "resultats": [],
        }
        discussions.append(courante)
        st.session_state["disc_courante"] = courante["id"]
    courante["resultats"].append(res)
    _sauver()


# ---------------------------------------------------------------- actions
def _nouvelle():
    _etat()
    st.session_state["disc_courante"] = None
    st.session_state.pop("brouillon_vocal", None)
    st.session_state.pop("renommer_id", None)


def _ouvrir(id_disc):
    st.session_state["disc_courante"] = id_disc
    st.session_state.pop("brouillon_vocal", None)
    st.session_state.pop("renommer_id", None)


def _supprimer(id_disc):
    st.session_state["discussions"] = [d for d in _etat() if d["id"] != id_disc]
    if st.session_state.get("disc_courante") == id_disc:
        st.session_state["disc_courante"] = None
    if st.session_state.get("renommer_id") == id_disc:
        st.session_state.pop("renommer_id", None)
    _sauver()


def _renommer(id_disc, nouveau_titre):
    nouveau_titre = nouveau_titre.strip()
    if not nouveau_titre:
        return
    for d in _etat():
        if d["id"] == id_disc:
            d["titre"] = nouveau_titre
            break
    st.session_state.pop("renommer_id", None)
    _sauver()


def _vers_texte(disc):
    lignes = [f"Discussion : {disc['titre']}", f"Date : {disc['date']}", "=" * 60, ""]
    for i, res in enumerate(disc["resultats"], 1):
        lignes.append(f"--- Échange {i} ---")
        lignes.append(f"Q : {res.get('question', '')}")
        if res.get("erreur"):
            lignes.append(f"R : [ERREUR] {res['erreur']}")
        elif res.get("info"):
            lignes.append(f"R : {res['info']}")
        elif res.get("rapport"):
            r = res["rapport"]
            lignes.append(f"R : 📄 Rapport « {r.get('titre', '')} »")
            if r.get("periode"):
                lignes.append(f"    {r['periode']}")
        elif res.get("sql"):
            lignes.append(f"R : {res.get('titre', 'Résultat')}")
            lignes.append(f"    SQL : {res['sql']}")
        lignes.append("")
    return "\n".join(lignes).encode("utf-8")


# ---------------------------------------------------------------- regroupement par date
def _groupe_date(ts):
    maintenant = datetime.now()
    dt = datetime.fromtimestamp(ts)
    delta_jours = (maintenant.date() - dt.date()).days
    if delta_jours == 0:
        return "📅 Aujourd'hui"
    if delta_jours == 1:
        return "📅 Hier"
    if delta_jours <= 7:
        return "📅 Cette semaine"
    if delta_jours <= 30:
        return "📅 Ce mois-ci"
    return "📅 Plus ancien"


_ORDRE_GROUPES = ["📅 Aujourd'hui", "📅 Hier", "📅 Cette semaine", "📅 Ce mois-ci", "📅 Plus ancien"]


# ---------------------------------------------------------------- affichage UI
def _bouton(label, **kw):
    for extra in ({"width": "stretch"}, {"use_container_width": True}, {}):
        try:
            return st.button(label, **kw, **extra)
        except TypeError:
            continue


def _ligne_discussion(d, courante):
    en_renommage = st.session_state.get("renommer_id") == d["id"]

    if en_renommage:
        col_input, col_ok, col_ann = st.columns([6, 1, 1], vertical_alignment="center")
        with col_input:
            nouveau = st.text_input("Nouveau nom", value=d["titre"], key=f"ren_{d['id']}", label_visibility="collapsed")
        with col_ok:
            if st.button("✓", key=f"ok_{d['id']}", help="Valider"):
                _renommer(d["id"], nouveau)
                st.rerun()
        with col_ann:
            if st.button("✕", key=f"ann_{d['id']}", help="Annuler"):
                st.session_state.pop("renommer_id", None)
                st.rerun()
        return

    c1, c2, c3, c4 = st.columns([7, 1, 1, 1], vertical_alignment="center")
    with c1:
        _bouton(
            ("▸ " if d["id"] == courante else "") + d["titre"],
            key=f"disc_{d['id']}",
            help=d["date"],
            on_click=_ouvrir,
            args=(d["id"],),
        )
    with c2:
        if st.button("✏️", key=f"renb_{d['id']}", help="Renommer"):
            st.session_state["renommer_id"] = d["id"]
            st.rerun()
    with c3:
        if st.button("🗑️", key=f"supp_{d['id']}", help="Supprimer"):
            _supprimer(d["id"])
            st.rerun()
    with c4:
        st.download_button(
            "📤",
            data=_vers_texte(d),
            file_name=f"{d['titre'][:30] or 'discussion'}.txt".replace("/", "_"),
            mime="text/plain",
            key=f"part_{d['id']}",
            help="Partager (télécharger en .txt)",
        )


def menu():
    discussions = _etat()
    courante = st.session_state.get("disc_courante")

    with st.sidebar:
        st.markdown("### 💬 Discussions")
        _bouton("➕  Nouvelle conversation", key="disc_nouveau", type="primary", on_click=_nouvelle)
        st.write("")

        recherche = st.text_input(
            "Rechercher", placeholder="🔍 Rechercher...", key="disc_recherche", label_visibility="collapsed",
        ).strip().lower()

        if recherche:
            filtrees = [d for d in discussions if recherche in d["titre"].lower()]
        else:
            filtrees = list(discussions)

        if not discussions:
            st.caption("Aucune discussion enregistrée.")
            return

        if not filtrees:
            st.caption("Aucun résultat.")
            return

        groupes = {}
        for d in filtrees:
            ts = d.get("timestamp") or time.time()
            groupes.setdefault(_groupe_date(ts), []).append(d)

        for nom_groupe in _ORDRE_GROUPES:
            if nom_groupe not in groupes:
                continue
            st.markdown(
                f"<div style='font-size:11px;color:#888;margin:12px 0 4px 0;"
                f"text-transform:uppercase;letter-spacing:0.5px'>{nom_groupe}</div>",
                unsafe_allow_html=True,
            )
            for d in sorted(groupes[nom_groupe], key=lambda x: x.get("timestamp", 0), reverse=True):
                _ligne_discussion(d, courante)