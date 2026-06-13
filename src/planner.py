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
import threading


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

        # Llama C backend is not safe to call concurrently from multiple
        # Python threads when using a single Llama instance. Protect calls
        # with a lock to serialize access and avoid segmentation faults.
        self._llm_lock = threading.Lock()

        print("Modèle chargé et prêt.")

    def planifier(self, message_utilisateur: str) -> dict:
        reponse_brute = self._appeler_llm(message_utilisateur, retry=False)

        # Debug: log raw LLM response to console and to file for inspection
        try:
            from pathlib import Path
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            (data_dir / "last_llm_response.txt").write_text(reponse_brute, encoding="utf-8")
        except Exception:
            pass

        print(f"[Planner] RAW RESPONSE:\n{reponse_brute}\n---end raw---")

        json_nettoye = self._nettoyer_reponse(reponse_brute)
        resultat = self._valider_json(json_nettoye)

        # Post-process extracted JSON for specific actions to improve robustness
        try:
            if resultat.get("action") == "post_facebook":
                resultat = self._extraire_params_post_facebook(
                    message_utilisateur, resultat)
        except Exception:
            pass

        if resultat.get("action") == "incompris":
            try:
                from pathlib import Path
                data_dir = Path(__file__).parent.parent / "data"
                data_dir.mkdir(exist_ok=True)
                (data_dir / "last_invalid_json.txt").write_text(
                    json_nettoye or reponse_brute, encoding="utf-8")
            except Exception:
                pass

            print(
                "[Planner] La première réponse JSON est invalide, tentative de relance... ")
            reponse_brute = self._appeler_llm(message_utilisateur, retry=True)
            try:
                from pathlib import Path
                data_dir = Path(__file__).parent.parent / "data"
                (data_dir / "last_llm_response_retry.txt").write_text(reponse_brute,
                                                                      encoding="utf-8")
            except Exception:
                pass

            print(
                f"[Planner] RAW RESPONSE RETRY:\n{reponse_brute}\n---end raw retry---")
            json_nettoye = self._nettoyer_reponse(reponse_brute)
            resultat = self._valider_json(json_nettoye)

        return resultat

    def _appeler_llm(self, message: str, retry: bool = False) -> str:
        user_message = message
        if retry:
            user_message = (
                message
                + "\nRéponds uniquement avec un JSON complet et valide."
                + " Ne retourne aucun texte explicatif supplémentaire."
            )

        # serialize access to the LLM instance
        with self._llm_lock:
            reponse = self.llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=2000,
                temperature=0.0,
                top_p=1.0,
            )

        # Debug: save the full raw response object when possible
        try:
            from pathlib import Path
            import json as _json
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            (_json.dumps(reponse, ensure_ascii=False, indent=2))
            (data_dir / "last_llm_response_raw.json").write_text(
                _json.dumps(reponse, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

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

    def _extraire_params_post_facebook(self, texte: str, resultat: dict) -> dict:
        """Renforce l'extraction des paramètres pour l'action `post_facebook`.

        Cherche dans le texte utilisateur : chemins Windows/UNIX, noms de fichiers médias,
        dates/heures (plusieurs formats), et mots-clés de confidentialité.
        Complète `resultat['parametres']` sans écraser les valeurs fournies par le LLM.
        """
        params = resultat.get("parametres") or {}

        def set_if_missing(key, value):
            if value and (key not in params or not params.get(key)):
                params[key] = value

        # 1) chemin ou nom de fichier média (Windows path, unix path, or bare filename)
        media = None
        # Windows drive path
        m = re.search(
            r"[A-Za-z]:\\[\w\d\-_.\\ ]+\.(?:png|jpg|jpeg|gif|mp4|mov|webm)", texte, re.IGNORECASE)
        if m:
            media = m.group(0)
        if not media:
            m = re.search(
                r"/[^\s']+\.(?:png|jpg|jpeg|gif|mp4|mov|webm)", texte, re.IGNORECASE)
            if m:
                media = m.group(0)
        if not media:
            m = re.search(
                r"['\"]([^'\"]+\.(?:png|jpg|jpeg|gif|mp4|mov|webm))['\"]", texte, re.IGNORECASE)
            if m:
                media = m.group(1)
        if not media:
            m = re.search(
                r"\b([\w\-]+\.(?:png|jpg|jpeg|gif|mp4|mov|webm))\b", texte, re.IGNORECASE)
            if m:
                media = m.group(1)

        set_if_missing("media_path", media)
        set_if_missing("nom_fichier", media)

        # 2) confidentialité
        privacy = None
        if re.search(r"\b(public|publique)\b", texte, re.IGNORECASE):
            privacy = "public"
        elif re.search(r"\b(friends|amis|amies)\b", texte, re.IGNORECASE):
            privacy = "friends"
        elif re.search(r"\b(only ?me|seulement moi|privé|prive)\b", texte, re.IGNORECASE):
            privacy = "only_me"

        set_if_missing("privacy", privacy)

        # 3) date / heure — essayer plusieurs formats
        when = None
        # ISO like yyyy-mm-dd HH:MM or yyyy/mm/dd HH:MM
        m = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2})", texte)
        if m:
            cand = m.group(1).replace('/', '-')
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
                try:
                    when = __import__('datetime').datetime.strptime(cand, fmt)
                    break
                except Exception:
                    continue

        # French dd/mm/YYYY HH:MM
        if not when:
            m = re.search(r"(\d{1,2}/\d{1,2}/\d{4}[ T]\d{1,2}:\d{2})", texte)
            if m:
                cand = m.group(1)
                for fmt in ("%d/%m/%Y %H:%M",):
                    try:
                        when = __import__(
                            'datetime').datetime.strptime(cand, fmt)
                        break
                    except Exception:
                        continue

        # Date without time (assume 09:00)
        if not when:
            m = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", texte)
            if m:
                cand = m.group(1).replace('/', '-')
                try:
                    when = __import__('datetime').datetime.strptime(
                        cand, "%Y-%m-%d")
                except Exception:
                    when = None

        if when:
            # normalize to string consistent with DB
            set_if_missing("scheduled_for", when.strftime("%Y-%m-%d %H:%M:%S"))

        # 4) caption — if none provided, use the message trimmed of detected tokens
        caption = params.get("texte") or params.get(
            "caption") or params.get("message")
        if not caption:
            # remove detected media, date and privacy tokens from the message
            cleaned = texte
            if media:
                cleaned = cleaned.replace(media, "")
            if when:
                cleaned = re.sub(
                    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}", "", cleaned)
                cleaned = re.sub(
                    r"\d{1,2}/\d{1,2}/\d{4}[ T]\d{1,2}:\d{2}", "", cleaned)
            # remove privacy words
            cleaned = re.sub(
                r"\b(public|publique|friends|amis|only ?me|seulement moi|privé|prive)\b", "", cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip()
            if cleaned:
                set_if_missing("texte", cleaned)

        resultat["parametres"] = params
        return resultat
