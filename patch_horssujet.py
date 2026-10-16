import pathlib
import shutil
import sys

chemin = pathlib.Path("app.py")
src = chemin.read_text(encoding="utf-8")

if "import garde" in src:
    print("Déjà appliqué : rien à faire.")
    sys.exit(0)

INFO = '{"id": time.time_ns(), "question": question, "info": %s, "sql": "", "etapes": []}'

modifs = [
    ("import",
     "import rapport_ui",
     "import rapport_ui\nimport garde"),

    # 1) filtre Python avant l'Agent SQL
    ("traiter() - filtre",
     "return rapport_ui.traiter_rapport(nom_rapport, engine, appeler_llm, noter)",
     "return rapport_ui.traiter_rapport(nom_rapport, engine, appeler_llm, noter)\n"
     "    message_garde = garde.reponse_garde(question)\n"
     "    if message_garde:\n"
     "        return " + INFO % "message_garde"),

    # 2) le modèle peut lui-même déclarer la question hors sujet
    ("traiter() - hors_sujet du modèle",
     "rep = agent_sql(question)\n",
     "rep = agent_sql(question)\n"
     '    if rep.get("hors_sujet") or not str(rep.get("sql", "")).strip():\n'
     "        return " + INFO % "garde.MESSAGE_AIDE" + "\n"),

    # 3) affichage du message
    ("afficher_resultat()",
     'st.error(res["erreur"])\n            return',
     'st.error(res["erreur"])\n            return\n'
     '        if res.get("info"):\n'
     '            st.info(res["info"])\n'
     "            return"),

    # 4) règle + exemples dans le prompt de l'Agent SQL
    ("prompt - règle",
     'utilise "tableau".',
     'utilise "tableau".\n'
     "- Si la question n'a aucun rapport avec les données post-trade (salutation, culture générale, texte "
     'incompréhensible), réponds {"sql": "", "affichage": "tableau", "titre": "", "hors_sujet": true}.'),
    ("prompt - exemples",
     '"affichage": "kpi", "titre": "Instructions en attente"}',
     '"affichage": "kpi", "titre": "Instructions en attente"}\n'
     "Q: bonjour\n"
     'R: {"sql": "", "affichage": "tableau", "titre": "", "hors_sujet": true}\n'
     "Q: quelle est la capitale de la France\n"
     'R: {"sql": "", "affichage": "tableau", "titre": "", "hors_sujet": true}'),
]

for nom, ancien, nouveau in modifs:
    if src.count(ancien) != 1:
        print(f"ÉCHEC : repère introuvable ou en double pour « {nom} ». Aucun fichier modifié.")
        sys.exit(1)
    src = src.replace(ancien, nouveau)

shutil.copy(chemin, "app_backup_horssujet.py")
chemin.write_text(src, encoding="utf-8")
print("OK : app.py modifié (sauvegarde : app_backup_horssujet.py). Relancez : streamlit run app.py")
