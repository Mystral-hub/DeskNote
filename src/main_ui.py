# src/main_ui.py

from queue import Queue

from database import Database
from planner import Planner
from executor import Executor
from observer import Observer
from ui.app import DeskNoteApp


NOM_MODELE = "qwen2.5-1.5b-instruct-q4_k_m.gguf"


def main():

    # --- initialisation du backend ---
    print("[Init] Connexion à la base de données...")
    db = Database()

    print("[Init] Chargement du modèle LLM...")
    try:
        planner = Planner(NOM_MODELE)
    except FileNotFoundError as e:
        print(f"[Erreur] {e}")
        print("[Info] Lancement en mode démonstration sans LLM.")
        planner = None

    queue = Queue()

    if planner:
        executor = Executor(database=db, queue_resultats=queue)
        observer = Observer(executor=executor)
    else:
        executor = None
        observer = None

    # --- lancement de l'interface ---
    print("[Init] Lancement de l'interface...")
    app = DeskNoteApp(
        planner=planner,
        executor=executor,
        observer=observer,
        database=db,
        queue_resultats=queue
    )
    app.lancer()

    # --- fermeture propre ---
    if executor:
        executor.fermer()
    db.fermer()
    print("[Init] Application fermée proprement.")


if __name__ == "__main__":
    main()
