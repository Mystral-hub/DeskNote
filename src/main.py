import time
from queue import Queue, Empty

from database import Database
from planner import Planner
from executor import Executor
from observer import Observer


NOM_MODELE = "qwen2.5-1.5b-instruct-q4_k_m.gguf"


def traiter_message(message: str, planner, executor, observer, db) -> dict:
    """
    Orchestre le flux complet pour un message utilisateur :
    planner → executor → observer → database
    """

    # étape 1 — extraire l'intention
    print(f"\n[Planner] Analyse du message...")
    json_action = planner.planifier(message)
    print(f"[Planner] JSON extrait : {json_action}")

    action = json_action.get("action")
    statut = None

    # étape 2 — action incomprise
    if action == "incompris":
        message_agent = json_action.get(
            "message_utilisateur", "Je n'ai pas compris.")
        print(f"\n[Agent] {message_agent}")

        db.sauvegarder_message(
            role="utilisateur",
            message=message,
            action=action,
            json_complet=json_action,
            statut="incompris"
        )
        db.sauvegarder_message(
            role="agent",
            message=message_agent,
            action=action,
            json_complet=None,
            statut="incompris"
        )
        return {"statut": "incompris", "message": message_agent}

    # étape 3 — confirmation requise
    if json_action.get("confirmation_requise"):
        message_confirmation = json_action.get(
            "message_confirmation", "Confirmer ?")
        print(f"\n[Agent] {message_confirmation}")
        print("[Agent] Tapez 'oui' pour confirmer ou 'non' pour annuler : ", end="")
        reponse = input().strip().lower()

        if reponse != "oui":
            print("[Agent] Action annulée.")
            db.sauvegarder_message(
                role="utilisateur",
                message=message,
                action=action,
                json_complet=json_action,
                statut="annule"
            )
            return {"statut": "annule", "message": "Action annulée par l'utilisateur."}

    # étape 4 — sauvegarder le message utilisateur
    db.sauvegarder_message(
        role="utilisateur",
        message=message,
        action=action,
        json_complet=json_action,
        statut=None
    )

    # étape 5 — exécuter l'action dans un thread
    print(f"\n[Executor] Exécution de l'action : {action}")
    executor.executer(json_action)

    # étape 6 — attendre le résultat depuis la queue
    resultat_executor = None
    try:
        resultat_executor = executor.queue_resultats.get(timeout=30)
        print(f"[Executor] Résultat : {resultat_executor}")
    except Empty:
        resultat_executor = {
            "statut":  "echec",
            "message": "L'action a pris trop de temps et a été abandonnée.",
            "donnees": None
        }

    # étape 7 — vérification par l'observer
    print(f"\n[Observer] Vérification en cours...")
    resultat_final = observer.verifier(json_action, resultat_executor)
    print(f"[Observer] Résultat final : {resultat_final}")

    # étape 8 — sauvegarder la réponse de l'agent
    db.sauvegarder_message(
        role="agent",
        message=resultat_final["message"],
        action=action,
        json_complet=resultat_executor,
        statut=resultat_final["statut"]
    )

    return resultat_final


def main():
    print("=" * 50)
    print("       DeskNote — Agent bureautique local")
    print("=" * 50)

    # initialisation dans le bon ordre
    print("\n[Init] Connexion à la base de données...")
    db = Database()

    print("[Init] Chargement du modèle LLM...")
    try:
        planner = Planner(NOM_MODELE)
    except FileNotFoundError as e:
        print(f"[Erreur] {e}")
        return

    queue = Queue()
    executor = Executor(database=db, queue_resultats=queue)
    observer = Observer(executor=executor)

    print("\n[Init] Tout est prêt. Tapez votre commande.")
    print("[Init] Tapez 'quitter' pour arrêter.\n")

    # boucle principale
    while True:
        print("-" * 50)
        message = input("Vous : ").strip()

        if not message:
            continue

        if message.lower() in ["quitter", "exit", "quit"]:
            print("\n[Agent] Au revoir !")
            break

        resultat = traiter_message(
            message=message,
            planner=planner,
            executor=executor,
            observer=observer,
            db=db
        )

        print(f"\n[Agent] {resultat['message']}")

    # fermeture propre
    executor.fermer()
    db.fermer()
    print("[Init] Application fermée proprement.")


if __name__ == "__main__":
    main()
