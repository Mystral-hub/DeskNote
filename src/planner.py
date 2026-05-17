# planner.py
import json
import os
import sys
from llama_cpp import Llama
import os

# path = "models/LFM2.5-1.2B-Instruct-BF16.gguf"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, "..", "models", "Phi-4-mini-instruct-Q4_K_M.gguf")


class Planner:
    def __init__(self, model_path=model_path):
        self.llm = Llama(model_path=model_path, verbose=False)
        self.system_prompt = """Tu es un assistant Windows. Transforme la demande de l'utilisateur en 
        une liste d'actions au format JSON"""  # colle le prompt ci-dessus

    def plan(self, user_input: str) -> list:
        # Construit le prompt au format chat (instruction tuning)
        prompt = f"<|system|>\n{self.system_prompt}\n<|user|>\n{user_input}\n<|assistant|>"
        output = self.llm(prompt, max_tokens=500, stop=[
                          "<|user|>", "<|system|>"], temperature=0.0)
        response_text = output['choices'][0]['text'].strip() # type: ignore
        # Nettoie la réponse (parfois le modèle ajoute des backticks ou du texte)
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        try:
            plan = json.loads(response_text)
            return plan
        except json.JSONDecodeError:
            return [{"action": "error", "message": "Le modèle n'a pas produit un plan valide."}]


# Test rapide en ligne de commande
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : ")
        sys.exit(1)
    planner = Planner()
    result = planner.plan(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
