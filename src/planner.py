import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # allow static type checkers to know the type without requiring the package at edit time
    from llama_cpp import Llama  # type: ignore
else:
    try:
        from llama_cpp import Llama
    except Exception:
        Llama = None  # runtime will raise a clear error if model code is invoked without the library

from prompts import SYSTEM_PROMPT


MODELS_DIR = Path(__file__).parent.parent / "models"


class Planner:

    def __init__(self, nom_modele: str):
        modele_path = MODELS_DIR / nom_modele

        if not modele_path.exists():
            raise FileNotFoundError(
                f"Modèle introuvable : {modele_path}\n"
                f"Vérifiez que le fichier est bien dans le dossier models/"
            )

        print(f"Chargement du modèle : {nom_modele}...")

        if Llama is None:
            raise RuntimeError(
                "La bibliothèque 'llama_cpp' est introuvable. Activez l'environnement virtuel ou installez la dépendance.")

        self.llm = Llama(
            model_path=str(modele_path),
            n_ctx=4096,
            n_threads=4,
            n_gpu_layers=0,
            verbose=False
        )

        print("Modèle chargé et prêt.")

    def planifier(self, message_utilisateur: str) -> dict:
        reponse_brute = self._appeler_llm(message_utilisateur)
        json_nettoye = self._nettoyer_reponse(reponse_brute)
        resultat = self._valider_json(json_nettoye)
        return resultat

    def _appeler_llm(self, message: str) -> str:
        reponse = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
            max_tokens=2000,
            temperature=0.0,
            top_p=1.0,
        )

        # type:ignore
        return reponse["choices"][0]["message"]["content"].strip()

    def _nettoyer_reponse(self, reponse: str) -> str:
        # cas 1 : JSON entre backticks markdown ```json ... ```
        match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", reponse, re.DOTALL)
        if match:
            return match.group(1).strip()

        # cas 2 : JSON brut quelque part dans la réponse
        match = re.search(r"\{.*\}", reponse, re.DOTALL)
        if match:
            return match.group(0).strip()

        # cas 3 : rien trouvé, on retourne la réponse telle quelle
        return reponse

    def _valider_json(self, json_brut: str) -> dict:
        try:
            resultat = json.loads(json_brut)

            # vérifier que le champ action est présent
            if "action" not in resultat:
                return self._json_incompris(
                    "La réponse ne contient pas de champ action."
                )

            # vérifier que le champ parametres est présent
            if "parametres" not in resultat:
                resultat["parametres"] = {}

            return resultat

        except json.JSONDecodeError:
            return self._json_incompris(
                "Je n'ai pas pu interpréter votre demande. "
                "Pouvez-vous la reformuler différemment ?"
            )

    def _json_incompris(self, message: str) -> dict:
        return {
            "action": "incompris",
            "confirmation_requise": False,
            "message_confirmation": None,
            "message_utilisateur": message,
            "parametres": {}
        }
