import time
import subprocess
from pathlib import Path


class Observer:

    def __init__(self, executor):
        # référence vers l'executor pour pouvoir retenter une action
        self.executor = executor

    def verifier(self, json_action: dict, resultat_executor: dict) -> dict:
        """
        Point d'entrée principal.
        Vérifie le résultat de l'executor et retente si nécessaire.
        """
        # si l'executor a déjà signalé un échec, pas besoin de vérifier
        if resultat_executor["statut"] == "echec":
            return resultat_executor

        action = json_action.get("action")
        parametres = json_action.get("parametres", {})

        verificateurs = {
            "ouvrir_app":          self._verifier_fenetre,
            "creer_fichier_texte": self._verifier_fichier_existe,
            "supprimer_fichier":   self._verifier_fichier_supprime,
            "creer_facture":       self._verifier_fichier_existe,
            "recherche_en_ligne":  self._verifier_fichier_existe,
            "organiser_fichiers":  self._verifier_dossiers_crees,
        }

        if action not in verificateurs:
            return {
                "statut":  "non_verifie",
                "message": "Action exécutée. Vérification non disponible.",
                "donnees": resultat_executor.get("donnees")
            }

        # première vérification
        if action == "ouvrir_app":
            resultat_verification = self._verifier_fenetre(
                parametres, resultat_executor)
        else:
            resultat_verification = verificateurs[action](parametres)

        if resultat_verification["statut"] == "confirme":
            return resultat_verification

        # échec de vérification → on retente l'action une fois
        print(
            f"[Observer] Vérification échouée pour '{action}'. Nouvelle tentative...")
        time.sleep(1)

        self.executor._executer_action(json_action)
        time.sleep(2)

        # deuxième vérification après la nouvelle tentative
        if action == "ouvrir_app":
            resultat_final = self._verifier_fenetre(
                parametres, resultat_executor)
        else:
            resultat_final = verificateurs[action](parametres)

        if resultat_final["statut"] == "confirme":
            return resultat_final

        # échec définitif → on remonte l'erreur à l'interface
        return {
            "statut":  "echec_verifie",
            "message": (
                f"L'action '{action}' a été tentée deux fois sans succès. "
                f"Vérifiez que vous avez les droits nécessaires ou reformulez votre demande."
            ),
            "donnees": None
        }

    # ------------------------------------------------------------------ #
    #  VÉRIFICATEURS                                                       #
    # ------------------------------------------------------------------ #

    def _verifier_fenetre(self, parametres: dict, resultat_executor: dict | None = None) -> dict:
        """Vérifie qu'une fenêtre d'application est bien ouverte."""
        try:
            from pywinauto import findwindows

            nom_app = parametres.get("nom_app", "")

            # If executor provided process info, prefer PID-based verification
            pid = None
            donnees = {}
            if isinstance(resultat_executor, dict):
                donnees = resultat_executor.get("donnees") or {}

            if not donnees and isinstance(parametres, dict):
                donnees = parametres.get("donnees") or {}

            pid = donnees.get("pid") if isinstance(donnees, dict) else None

            if pid:
                # try psutil first
                try:
                    import psutil
                    if psutil.pid_exists(pid):
                        try:
                            p = psutil.Process(pid)
                            pname = p.name()
                            pexe = None
                            try:
                                pexe = p.exe()
                            except Exception:
                                pexe = None
                            # log to console for debugging and include in result
                            print(
                                f"[Observer] Process detected: PID={pid}, name={pname}, exe={pexe}")
                            return {
                                "statut": "confirme",
                                "message": f"Processus détecté (PID {pid}) : {pname}" + (f" ({pexe})" if pexe else ""),
                                "donnees": {"pid": pid, "name": pname, "exe": pexe}
                            }
                        except Exception:
                            return {"statut": "confirme", "message": f"Processus détecté (PID {pid}) : {nom_app}", "donnees": {"pid": pid}}
                except Exception:
                    # fallback to tasklist
                    try:
                        out = subprocess.check_output(
                            ["tasklist", "/FI", f"PID eq {pid}"], text=True, stderr=subprocess.DEVNULL)
                        if str(pid) in out:
                            # attempt to parse image name from tasklist output line
                            lines = [l for l in out.splitlines(
                            ) if l.strip() and str(pid) in l]
                            imagename = None
                            if lines:
                                parts = lines[0].split()
                                if parts:
                                    imagename = parts[0]
                            print(
                                f"[Observer] tasklist shows PID={pid}, image={imagename}")
                            return {"statut": "confirme", "message": f"Processus détecté (PID {pid}) : {imagename or nom_app}", "donnees": {"pid": pid, "name": imagename}}
                    except Exception:
                        pass

            # Fallback: title-based search with short retries (startup latency)
            attempts = 6
            for i in range(attempts):
                try:
                    fenetres = findwindows.find_windows(
                        title_re=f".*{nom_app}.*")
                    if fenetres:
                        return {"statut": "confirme", "message": f"Application ouverte avec succès : {nom_app}"}
                except Exception:
                    pass
                time.sleep(0.5)

            return {"statut": "echec_verifie", "message": f"La fenêtre '{nom_app}' n'a pas été détectée."}

        except Exception as e:
            return {
                "statut":  "non_verifie",
                "message": f"Vérification fenêtre impossible : {e}"
            }

    def _verifier_fichier_existe(self, parametres: dict) -> dict:
        """Vérifie qu'un fichier a bien été créé sur le disque."""
        from utils import resoudre_chemin, nettoyer_nom_fichier

        # gère les deux cas : fichier texte et facture
        nom_fichier = (
            nettoyer_nom_fichier(parametres.get("nom_fichier"))
            or nettoyer_nom_fichier(parametres.get("nom_fichier_resultat"))
            or self._nom_facture(parametres)
        )
        repertoire = parametres.get("repertoire_cible")

        if nom_fichier is None:
            return {
                "statut":  "non_verifie",
                "message": "Nom de fichier introuvable pour la vérification."
            }

        chemin_dossier = resoudre_chemin(
            repertoire) if repertoire else Path.home() / "Documents"
        chemin_fichier = chemin_dossier / nom_fichier

        if chemin_fichier.exists():
            return {
                "statut":  "confirme",
                "message": f"Fichier créé avec succès : {chemin_fichier}"
            }

        return {
            "statut":  "echec_verifie",
            "message": f"Le fichier '{nom_fichier}' n'a pas été trouvé sur le disque."
        }

    def _verifier_fichier_supprime(self, parametres: dict) -> dict:
        """Vérifie qu'un fichier a bien été supprimé."""
        from utils import resoudre_chemin, nettoyer_nom_fichier

        nom_fichier = nettoyer_nom_fichier(parametres.get("nom_fichier"))
        repertoire = parametres.get("repertoire_cible")
        chemin_dossier = resoudre_chemin(
            repertoire) if repertoire else Path.home() / "Documents"

        if nom_fichier is None:
            return {
                "statut":  "non_verifie",
                "message": "Nom de fichier introuvable pour la vérification."
            }

        chemin_fichier = chemin_dossier / nom_fichier

        if not chemin_fichier.exists():
            return {
                "statut":  "confirme",
                "message": f"Fichier supprimé avec succès : {nom_fichier}"
            }

        return {
            "statut":  "echec_verifie",
            "message": f"Le fichier '{nom_fichier}' existe encore sur le disque."
        }

    def _verifier_dossiers_crees(self, parametres: dict) -> dict:
        """Vérifie que des sous-dossiers ont été créés après organisation."""
        from utils import resoudre_chemin

        repertoire = parametres.get("repertoire_cible")
        chemin_dossier = resoudre_chemin(repertoire)

        if chemin_dossier is None or not chemin_dossier.exists():
            return {
                "statut":  "echec_verifie",
                "message": f"Dossier introuvable : {repertoire}"
            }

        sous_dossiers = [f for f in chemin_dossier.iterdir() if f.is_dir()]

        if sous_dossiers:
            return {
                "statut":  "confirme",
                "message": f"Fichiers organisés — {len(sous_dossiers)} dossiers créés dans {repertoire}"
            }

        return {
            "statut":  "echec_verifie",
            "message": f"Aucun sous-dossier créé dans {repertoire}."
        }

    # ------------------------------------------------------------------ #
    #  UTILITAIRES                                                         #
    # ------------------------------------------------------------------ #

    def _nom_facture(self, parametres: dict) -> str | None:
        """Reconstruit le nom du fichier facture depuis les paramètres."""
        client_nom = parametres.get("client_nom")
        numero = parametres.get("numero_facture") or "001"

        if client_nom:
            return f"facture_{client_nom.replace(' ', '_')}_{numero}.docx"

        return None
