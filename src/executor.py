import os
import subprocess
import shutil
import ctypes
import webbrowser
import time
from pathlib import Path
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None

from utils import (
    resoudre_chemin,
    nettoyer_valeur,
    nettoyer_nom_fichier,
    rechercher_fichier,
    formater_resultats_recherche,
    placer_dans_repertoire,
    revenir_repertoire_base
)
from database import Database
from actions.live_typing import live_typing as action_live_typing
from actions.creer_facture import creer_facture as action_creer_facture
from actions.ouvrir_app import ouvrir_app as action_ouvrir_app
from actions.supprimer_fichier import supprimer_fichier as action_supprimer_fichier
from actions.creer_fichier_texte import creer_fichier_texte as action_creer_fichier_texte
from actions.lire_document import lire_document as action_lire_document
from actions.recherche_en_ligne import recherche_en_ligne as action_recherche_en_ligne
from actions.organiser_fichiers import organiser_fichiers as action_organiser_fichiers
from actions.changer_fond_ecran import changer_fond_ecran as action_changer_fond_ecran
from actions.lancer_media import lancer_media as action_lancer_media
from actions.rechercher_fichier import rechercher_fichier_action as action_rechercher_fichier
from actions.creer_pwp import run as action_creer_presentation


class Executor:

    def __init__(self, database: Database, queue_resultats: Queue):
        self.db = database
        self.queue_resultats = queue_resultats
        self.pool = ThreadPoolExecutor(max_workers=4)

        self.actions = {
            "ouvrir_app":          self._ouvrir_app,
            "supprimer_fichier":   self._supprimer_fichier,
            "creer_fichier_texte": self._creer_fichier_texte,
            "lire_document":       self._lire_document,
            "recherche_en_ligne":  self._recherche_en_ligne,
            "organiser_fichiers":  self._organiser_fichiers,
            "changer_fond_ecran":  self._changer_fond_ecran,
            "lancer_media":        self._lancer_media,
            "rechercher_fichier":  self._rechercher_fichier,
            "creer_facture":       self._creer_facture,
            "live_typing":         self._live_typing,
            "creer_presentation":  self._creer_presentation,
        }

    def executer(self, json_action: dict):
        """Point d'entrée principal — soumet l'action au pool de threads."""
        self.pool.submit(self._executer_action, json_action)

    def _executer_action(self, json_action: dict):
        """Wrapper exécuté dans un thread — dispatch vers la bonne méthode."""
        action = json_action.get("action") or "unknown"
        parametres = json_action.get("parametres", {})

        if action not in self.actions:
            resultat = self._resultat(
                "echec",
                f"Action inconnue : {action}"
            )
        else:
            try:
                resultat = self.actions[action](parametres)
            except Exception as e:
                resultat = self._resultat("echec", str(e))

        # sauvegarder le log
        message_err = resultat["message"] if resultat["statut"] == "echec" else None
        try:
            self.db.sauvegarder_log(
                action=action,
                parametres=parametres,
                statut=resultat["statut"],
                message_erreur=message_err
            )
        except Exception as e:
            # ne pas faire échouer l'exécution si la sauvegarde échoue
            print(f"[Executor] Erreur lors de la sauvegarde du log : {e}")

        # mettre le résultat dans la queue pour l'interface
        try:
            self.queue_resultats.put(resultat)
        except Exception as e:
            print(
                f"[Executor] Impossible de mettre le résultat dans la queue : {e}")

    # ------------------------------------------------------------------ #
    #  ACTIONS                                                             #
    # ------------------------------------------------------------------ #

    def _ouvrir_app(self, parametres: dict) -> dict:
        """Wrapper pour l'action `ouvrir_app` (extraite dans actions/ouvrir_app.py)."""
        return action_ouvrir_app(parametres, self._resolve_executable_for_app)

    def _supprimer_fichier(self, parametres: dict) -> dict:
        """Wrapper pour l'action `supprimer_fichier` (extraite dans actions/supprimer_fichier.py)."""
        return action_supprimer_fichier(parametres, self._resolve_executable_for_app)

    def _creer_presentation(self, parametres: dict) -> dict:
        """Wrapper pour l'action `creer_presentation` (extraite dans actions/creer_presentation.py)."""
        return action_creer_presentation(parametres)

    def _resolve_executable_for_app(self, nom_app: str) -> Path | None:
        """Resolve an executable path from a human-friendly app name.

        Strategy (fast, non-blocking):
        - try variants with shutil.which
        - fuzzy search in registry App Paths keys
        - limited search in Start Menu .lnk files (resolve via win32com)
        """
        if not nom_app:
            return None

        name = nom_app.lower().strip()
        variants = [name, name.replace(' ', ''), name.replace(
            ' ', '_'), name.replace(' ', '-')]

        # 1) PATH
        for v in variants:
            try:
                p = shutil.which(v) or shutil.which(f"{v}.exe")
                if p:
                    return Path(p)
            except Exception:
                continue

        # 2) Registry App Paths (fuzzy match on key name)
        try:
            import winreg

            base = r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths"
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(hive, base) as key:
                        i = 0
                        while True:
                            try:
                                sub = winreg.EnumKey(key, i)
                                sub_l = sub.lower()
                                for v in variants:
                                    if v in sub_l:
                                        try:
                                            with winreg.OpenKey(hive, base + "\\" + sub) as sk:
                                                val, _ = winreg.QueryValueEx(
                                                    sk, None)
                                                if val:
                                                    return Path(val)
                                        except Exception:
                                            pass
                                i += 1
                            except OSError:
                                break
                except Exception:
                    continue
        except Exception:
            pass

        # 3) Start Menu .lnk (limited)
        try:
            try:
                from win32com.client import Dispatch
            except Exception:
                Dispatch = None

            start_paths = [
                Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) /
                'Microsoft/Windows/Start Menu/Programs',
                Path(os.environ.get('APPDATA', Path.home() / 'AppData/Roaming')
                     ) / 'Microsoft/Windows/Start Menu/Programs'
            ]

            found = 0
            for sp in start_paths:
                if not sp.exists():
                    continue
                for lnk in sp.rglob('*.lnk'):
                    found += 1
                    if found > 300:
                        break
                    fname = lnk.stem.lower()
                    for v in variants:
                        if v in fname:
                            if Dispatch is None:
                                continue
                            try:
                                shell = Dispatch('WScript.Shell')
                                shortcut = shell.CreateShortcut(str(lnk))
                                target = shortcut.Targetpath
                                if target:
                                    return Path(target)
                            except Exception:
                                continue
                if found > 300:
                    break
        except Exception:
            pass

        return None

    def _creer_fichier_texte(self, parametres: dict) -> dict:
        """Wrapper pour l'action `creer_fichier_texte` (extraite dans actions/creer_fichier_texte.py)."""
        return action_creer_fichier_texte(parametres, self._resolve_executable_for_app)

    def _lire_document(self, parametres: dict) -> dict:
        """Wrapper pour l'action `lire_document` (extraite dans actions/lire_document.py)."""
        return action_lire_document(parametres, self._resolve_executable_for_app)

    def _recherche_en_ligne(self, parametres: dict) -> dict:
        """Wrapper pour l'action `recherche_en_ligne` (extraite dans actions/recherche_en_ligne.py)."""
        return action_recherche_en_ligne(parametres, self._resolve_executable_for_app)

    def _organiser_fichiers(self, parametres: dict) -> dict:
        """Wrapper pour l'action `organiser_fichiers` (extraite dans actions/organiser_fichiers.py)."""
        return action_organiser_fichiers(parametres, self._resolve_executable_for_app)

    def _changer_fond_ecran(self, parametres: dict) -> dict:
        """Wrapper pour l'action `changer_fond_ecran` (extraite dans actions/changer_fond_ecran.py)."""
        return action_changer_fond_ecran(parametres, self._resolve_executable_for_app)

    def _lancer_media(self, parametres: dict) -> dict:
        """Wrapper pour l'action `lancer_media` (extraite dans actions/lancer_media.py)."""
        return action_lancer_media(parametres, self._resolve_executable_for_app)

    def _rechercher_fichier(self, parametres: dict) -> dict:
        """Wrapper pour l'action `rechercher_fichier` (extraite dans actions/rechercher_fichier.py)."""
        return action_rechercher_fichier(parametres, self._resolve_executable_for_app)

    def _creer_facture(self, parametres: dict) -> dict:
        return action_creer_facture(parametres)

    def _live_typing(self, parametres: dict) -> dict:
        """Wrapper pour l'action live_typing (extraite dans actions/live_typing.py)."""
        return action_live_typing(parametres, self._resolve_executable_for_app)

    def _type_fichier(self, extension: str) -> str:
        """Retourne la catégorie d'un fichier selon son extension."""
        categories = {
            "Images":     [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
            "Videos":     [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
            "Audio":      [".mp3", ".wav", ".flac", ".aac", ".ogg"],
            "Documents":  [".pdf", ".docx", ".doc", ".txt", ".odt"],
            "Tableurs":   [".xlsx", ".xls", ".csv", ".ods"],
            "Archives":   [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Code":       [".py", ".js", ".html", ".css", ".json"],
        }
        ext = extension.lower()
        for categorie, extensions in categories.items():
            if ext in extensions:
                return categorie
        return "Divers"

    def _resultat(self, statut: str, message: str, donnees: dict | None = None) -> dict:
        """Fabrique un dictionnaire de résultat standard."""
        return {
            "statut": statut,
            "message": message,
            "donnees": donnees
        }

    def fermer(self):
        """Arrête proprement le pool de threads."""
        self.pool.shutdown(wait=True)
