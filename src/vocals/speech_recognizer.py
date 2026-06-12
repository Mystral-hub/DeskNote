
import sounddevice as sd
import numpy as np
import stable_ts


class SpeechRecognizer:
    def __init__(self, model_size="base", language="fr"):

        self.model_size = model_size
        self.language = language

        print(f"[SpeechRecognizer] Chargement du modèle '{model_size}'...")
        self.model = stable_ts.load_model(model_size)
        print(f"[SpeechRecognizer] Modèle à été chargé avec succès!")

    def recognize(self, duration=5, sample_rate=16000):

        print(f"\n[SpeechRecognizer] Enregistrement {duration} secondes...")
        print("Commencer à parler maintenant...")

        try:
            # Capture audio depuis le microphone
            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype=np.float32
            )
            sd.wait()

            print("[SpeechRecognizer] Enregistrement terminer. Traitement audio...")

            audio = audio.flatten()

            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val  # Normalize to [-1, 1]
                audio = np.clip(audio * 1.5, -1, 1)

            # Transcribe utilise Stable Whisper directement avec les tableau numpy
            result = self.model.transcribe(
                audio,
                language=self.language,
                fp16=False
            )

            # Extraction du text de l'objet result
            recognized_text = result.text.strip() if hasattr(result, 'text') else ""

            if not recognized_text:
                print(
                    "[SpeechRecognizer]  aucun speech detecté. Rééssayer à haute voix.")
                return ""

            print(f"[SpeechRecognizer] Reconnaissance terminée!")
            return recognized_text

        except Exception as e:
            print(
                f"[SpeechRecognizer]  Erroeur pendant la reconnaissance: {e}")
            import traceback
            traceback.print_exc()
            return ""


# test rapide
if __name__ == "__main__":
    recognizer = SpeechRecognizer(model_size="base", language="fr")
    text = recognizer.recognize(duration=5)
    print(f"\nRecognized text: {text}")
