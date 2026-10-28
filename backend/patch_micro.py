"""Met le micro dans la barre "Écris ton prompt" et permet de modifier le texte reconnu avant l'envoi.
Usage : python patch_micro.py   (depuis le dossier qui contient app.py)
Sauvegarde : app_backup_micro.py"""
import pathlib
import shutil
import sys

chemin = pathlib.Path("app.py")
src = chemin.read_text(encoding="utf-8")

if "brouillon_vocal" in src:
    print("Déjà appliqué : rien à faire.")
    sys.exit(0)

# 1) Fonction de transcription : on lit l'audio en mémoire (évite le bug des fichiers temporaires sous Windows)
debut_f = src.find("def transcrire(audio_bytes):")
marque_f = 'return " ".join(s.text.strip() for s in segments).strip()'
fin_f = src.find(marque_f, debut_f)
if debut_f < 0 or fin_f < 0:
    print("ÉCHEC : fonction transcrire introuvable. Aucun fichier modifié.")
    sys.exit(1)
fin_f += len(marque_f)
nouvelle_transcrire = '''def transcrire(audio_bytes):
    import io
    segments, _ = charger_whisper().transcribe(io.BytesIO(audio_bytes), language=VOICE_LANG)
    return " ".join(s.text.strip() for s in segments).strip()'''
src = src[:debut_f] + nouvelle_transcrire + src[fin_f:]

# 2) Zone de saisie : micro dans la barre + brouillon modifiable
debut_i = src.find("question_vocale = None")
marque_i = 'question = st.chat_input("Écris ton prompt...") or question_vocale'
fin_i = src.find(marque_i, debut_i)
if debut_i < 0 or fin_i < 0:
    print("ÉCHEC : zone de saisie introuvable. Aucun fichier modifié.")
    sys.exit(1)
fin_i += len(marque_i)
nouvelle_saisie = '''def _envoyer_brouillon():
    st.session_state["question_en_attente"] = st.session_state.get("brouillon_vocal", "").strip()
    st.session_state.pop("brouillon_vocal", None)


def _annuler_brouillon():
    st.session_state.pop("brouillon_vocal", None)


question = st.session_state.pop("question_en_attente", None)
try:
    saisie = st.chat_input("Écris ton prompt ou clique sur le micro...", accept_audio=True)
except TypeError:   # Streamlit trop ancien : pas de micro dans la barre
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
        question = texte_saisi'''
src = src[:debut_i] + nouvelle_saisie + src[fin_i:]

# 3) Boîte du message vocal modifiable, affichée à la fin de la page
src = src.rstrip() + '''

if "brouillon_vocal" in st.session_state:
    with st.container(border=True):
        st.caption("Message vocal reconnu : modifie-le ou ajoute du texte, puis clique sur Envoyer.")
        st.text_area("Message", key="brouillon_vocal", label_visibility="collapsed")
        b1, b2, _ = st.columns([1, 1, 6])
        b1.button("Envoyer", type="primary", on_click=_envoyer_brouillon)
        b2.button("Annuler", on_click=_annuler_brouillon)
'''

shutil.copy(chemin, "app_backup_micro.py")
chemin.write_text(src, encoding="utf-8")
print("OK : app.py modifié (sauvegarde : app_backup_micro.py).")
print("Étape suivante : pip install -U streamlit  puis  relancer : streamlit run app.py")
