from planner import Planner

if __name__ == "__main__":
    # Exemple d'utilisation
    planner = Planner("qwen2.5-0.5b-instruct-q2_k.gguf")
    message = "cree un fichier texte nommé test.txt avec le contenu 'Bonjour, ceci est un test.' dans le dossier Documents."
    resultat = planner.planifier(message)
    print(resultat)
