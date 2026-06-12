import pyttsx3


class TextToSpeech:
    def __init__(self, language="fr", rate=150, volume=0.9):
       
        self.language = language
        self.rate = rate
        self.volume = volume
        
        print("[TextToSpeech] Initialisation du moteur pyttsx3...")
        self._init_engine()
        print("[TextToSpeech] moteur prêt!")
    
    def _init_engine(self):
        
        self.engine = pyttsx3.init()
        
        self.engine.setProperty("rate", self.rate)
        self.engine.setProperty("volume", self.volume)
        
        voices = self.engine.getProperty("voices")
        
        print(f"\n[TextToSpeech] voix disponible: {len(voices)}")
        for i, voice in enumerate(voices):
            print(f"  {i}: {voice.name} (ID: {voice.id})")
        
        french_voice_id = None
        for voice in voices:
            if "french" in voice.name.lower():
                french_voice_id = voice.id
                print(f"\n[TextToSpeech]  voix française trouvée: {voice.name}")
                break
        
        # If no French voice found, use first available
        if french_voice_id is None:
            if voices:
                french_voice_id = voices[0].id
                print(f"\n[TextToSpeech] aucune voix française trouvée, utilisation: {voices[0].name}")
        
        if french_voice_id:
            self.engine.setProperty("voice", french_voice_id)
    
    def speak(self, text):
       
        if not text or not text.strip():
            print("[TextToSpeech] text fourni vide")
            return
        
        try:
            print(f"\n[TextToSpeech] parlez: '{text}'")
            self.engine.say(text)
            self.engine.runAndWait()
            
            # Reinitialize engine after speaking to avoid issues
            self._init_engine()
            print("[TextToSpeech]  Fait!")
        except Exception as e:
            print(f"[TextToSpeech] Erreur: {e}")
    
    def set_rate(self, rate):
       
        self.rate = max(50, min(300, rate))
        self.engine.setProperty("rate", self.rate)
        print(f"[TextToSpeech] vitesse d'élocution {self.rate} wpm")
    
    def set_volume(self, volume):
        
        self.volume = max(0.0, min(1.0, volume))
        self.engine.setProperty("volume", self.volume)
        print(f"[TextToSpeech] Volume réglé sur {self.volume}")


# Quick test
if __name__ == "__main__":
    tts = TextToSpeech(language="fr", rate=150, volume=0.9)
    tts.speak("Bonjour, ceci est un test de synthèse vocale")
