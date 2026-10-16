import pathlib
import shutil
import sys

chemin = pathlib.Path("app.py")
src = chemin.read_text(encoding="utf-8")

if "rapport_ui" in src:
    print("app.py est déjà modifié : rien à faire.")
    sys.exit(0)

modifs = [
    ("import",
     "import altair as alt",
     "import altair as alt\nimport rapport_ui"),
    ("traiter()",
     'noter("Agent SQL : génération de la requête")',
     'nom_rapport = rapport_ui.detecter_rapport(question)\n'
     '    if nom_rapport:\n'
     '        return rapport_ui.traiter_rapport(nom_rapport, engine, appeler_llm, noter)\n'
     '    noter("Agent SQL : génération de la requête")'),
    ("afficher_resultat()",
     'st.error(res["erreur"])\n            return',
     'st.error(res["erreur"])\n            return\n'
     '        if res.get("rapport"):\n'
     '            rapport_ui.afficher(res, RENDUS)\n'
     '            return'),
]

for nom, ancien, nouveau in modifs:
    if src.count(ancien) != 1:
        print(f"ÉCHEC : repère introuvable pour {nom}. Aucun fichier modifié.")
        sys.exit(1)
    src = src.replace(ancien, nouveau)

shutil.copy(chemin, "app_backup.py")
chemin.write_text(src, encoding="utf-8")
print("OK : app.py modifié (sauvegarde : app_backup.py). Relancez : streamlit run app.py")
