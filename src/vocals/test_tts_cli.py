
from text_to_speech import TextToSpeech


def main():
    print("=" * 60)
    print("DeskNote - Text-to-Speech Test en ligne de commande")
    print("=" * 60)
    
    # Initialisation du moteur TTS 
    print("\n[INFO] Initializing Text-to-Speech Engine...")
    tts = TextToSpeech(language="fr", rate=150, volume=0.9)
    
    # Boucle principale 
    while True:
        print("\n" + "-" * 60)
        print("Options:")
        print("  1. Entrer text to speak")
        print("  4. Tester avec du text predefini")
        print("  5. sortir")
        print("-" * 60)
        
        choice = input("Entrer votre choix (1-3): ").strip()
        
        if choice == "1":
            text = input("Entrer text to speak: ").strip()
            if text:
                tts.speak(text)
            else:
                print("Text vide. Réessayer.")
        
        elif choice == "2":
            print("\n[INFO] Test avec texts prédéfini...\n")
            test_texts = [
                "Bonjour, je suis l'assistant DeskNote",
                "Je peux lire vos textes et exécuter vos commandes",
                "Comment puis-je vous aider aujourd'hui?",
            ]
            for text in test_texts:
                tts.speak(text)
                print()
        
        elif choice == "3":
            print("\n Au revoir!")
            break
        
        else:
            print("Choix invalide. S'il vous plaît entrer 1-3.")


if __name__ == "__main__":
    main()
