from speech_recognizer import SpeechRecognizer


def main():
    print("=" * 60)
    print("DeskNote - Speech-to-Text CLI Test")
    print("=" * 60)
    
    # Initialize the recognizer
    print("\n[INFO] Initialisation de la reconnaissance vocale...")
    recognizer = SpeechRecognizer(model_size="medium", language="fr")
    
    # Main loop
    while True:
        print("\n" + "-" * 60)
        print("Options:")
        print("  1. enregistrement (5 seconds)")
        print("  2. sortir")
        print("-" * 60)
        
        choice = input("Entrer votre choix (1-2): ").strip()
        
        if choice == "1":
            text = recognizer.recognize(duration=10)
            if text:
                print(f"\nvous avez dit: '{text}'")
        
        elif choice == "2":
            print("\n Au revoir")
            break
        
        else:
            print("choix invalide. s'l vous plaît entrez 1 ou 2.")


if __name__ == "__main__":
    main()
