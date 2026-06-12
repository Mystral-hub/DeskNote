"""Live typing action — opens an application and types text character by character."""

import time
import subprocess
import shutil
from pathlib import Path
from utils import nettoyer_valeur
from settings import load_settings
import textwrap
import threading

# winsound is Windows-only; if unavailable, sound feature is silently disabled
try:
    import winsound
    _HAS_WINSOUND = True
except Exception:
    winsound = None
    _HAS_WINSOUND = False


def live_typing(parametres: dict, resolve_executable_func, cancel_event=None) -> dict:
    """Ouvre une application et tape un texte lettre par lettre.

    Utilise:
    - `subprocess.Popen` pour lancer l'application et récupérer le PID
    - `pywinauto.Application.connect(process=pid)` avec retries
    - Fallback sur recherche par titre si nécessaire

    Paramètres:
        parametres: dict with 'application', 'texte', 'ouvrir_app'
        resolve_executable_func: fonction pour résoudre le chemin d'une app

    Retour:
        dict: {'statut': 'succes'|'echec', 'message': str, 'donnees': dict|None}
    """
    from pywinauto import Application, findwindows
    from pywinauto.keyboard import send_keys

    application = nettoyer_valeur(parametres.get("application"))
    texte = parametres.get("texte") or ""
    ouvrir_app = str(parametres.get("ouvrir_app", "true")).lower() == "true"
    default_settings = load_settings()
    # play keyboard click sounds while typing (True/False)
    sound_clicks = bool(parametres.get(
        "sound_clicks", default_settings.get("sound_clicks", True)))
    # maximum line length in characters to avoid horizontal scrollbar in target app
    max_line_length = int(parametres.get("max_line_length", 80))

    def _wrap_text_for_live_typing(s: str, width: int) -> str:
        # preserve existing paragraphs and wrap each paragraph
        paragraphs = s.split("\n")
        wrapped = []
        for p in paragraphs:
            if not p.strip():
                wrapped.append("")
                continue
            lines = textwrap.wrap(p, width=width, replace_whitespace=False)
            if not lines:
                wrapped.append("")
            else:
                wrapped.extend(lines)
        return "\n".join(wrapped)

    if not application:
        return {"statut": "echec", "message": "Aucune application spécifiée.", "donnees": None}

    if not texte:
        return {"statut": "echec", "message": "Aucun texte à taper.", "donnees": None}

    pid = None
    try:
        # --- étape 1 : ouvrir l'application si demandé ---
        if ouvrir_app:
            target = shutil.which(application) or shutil.which(
                f"{application}.exe") or application
            try:
                p = subprocess.Popen(
                    [str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
            except Exception:
                p = subprocess.Popen(str(
                    target), shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
            pid = getattr(p, "pid", None)

        # --- étape 2 : se connecter à l'application (préférer PID) ---
        app = None
        attempts = 8
        for _ in range(attempts):
            try:
                if pid:
                    app = Application(backend="uia").connect(
                        process=pid, timeout=2)
                else:
                    app = Application(backend="uia").connect(
                        title_re=f".*{application}.*", timeout=2)
                break
            except Exception:
                time.sleep(0.5)

        # fallback: tenter via findwindows puis connect
        if not app:
            try:
                wins = findwindows.find_windows(title_re=f".*{application}.*")
                if wins:
                    try:
                        app = Application(backend="uia").connect(
                            process=wins[0])
                    except Exception:
                        pass
            except Exception:
                pass

        if not app:
            return {"statut": "echec", "message": f"Impossible de trouver la fenêtre pour '{application}'.", "donnees": None}

        fenetre = app.top_window()
        fenetre.set_focus()
        time.sleep(0.2)

        # --- étape 3 : préparer et taper lettre par lettre ---
        texte_prepared = _wrap_text_for_live_typing(texte, max_line_length)

        caracteres_speciaux = {"\n": "{ENTER}", "\t": "{TAB}", " ": "{SPACE}"}

        # sound worker: loop short beeps while typing (best-effort)
        stop_sound = threading.Event()
        sound_thread = None
        if sound_clicks and _HAS_WINSOUND:
            def _sound_worker(stop_evt: threading.Event):
                try:
                    while not stop_evt.is_set():
                        # short beep ~30ms
                        winsound.Beep(1000, 30)
                        # small pause to avoid continuous tone
                        time.sleep(0.02)
                except Exception:
                    return

            sound_thread = threading.Thread(
                target=_sound_worker, args=(stop_sound,), daemon=True)
            sound_thread.start()

        try:
            for lettre in texte_prepared:
                # check for cancellation
                try:
                    if (cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)()):
                        return {"statut": "annule", "message": "Live typing annulé.", "donnees": None}
                    from cancel_registry import is_all_set
                    if is_all_set():
                        return {"statut": "annule", "message": "Live typing annulé (stop global).", "donnees": None}
                except Exception:
                    pass

                if lettre in caracteres_speciaux:
                    send_keys(caracteres_speciaux[lettre])
                else:
                    send_keys(lettre, with_spaces=True)
                time.sleep(0.05)
        finally:
            if sound_thread is not None:
                stop_sound.set()
                try:
                    sound_thread.join(timeout=0.5)
                except Exception:
                    pass

        return {
            "statut": "succes",
            "message": f"Texte tapé dans {application} : {texte[:30]}..." if len(texte) > 30 else f"Texte tapé dans {application}.",
            "donnees": {"pid": pid}
        }

    except Exception as e:
        return {
            "statut": "echec",
            "message": f"Erreur lors du live typing dans {application} : {repr(e)}",
            "donnees": None
        }


def prepare_text_for_live_typing(texte: str, max_line_length: int = 80) -> str:
    """Utility: wrap text for live typing (preserve paragraphs)."""
    import textwrap as _tw
    paragraphs = texte.split("\n")
    wrapped = []
    for p in paragraphs:
        if not p.strip():
            wrapped.append("")
            continue
        lines = _tw.wrap(p, width=max_line_length, replace_whitespace=False)
        if not lines:
            wrapped.append("")
        else:
            wrapped.extend(lines)
    return "\n".join(wrapped)
