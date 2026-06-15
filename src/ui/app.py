# src/ui/app.py

import tkinter as tk
import ttkbootstrap as ttk
import uuid
from queue import Queue, Empty

from .theme import (
    get_theme,
    WIN_FULL_MIN_W, WIN_FULL_MIN_H,
    WIN_REDUCED_MAX_W, WIN_REDUCED_MIN_H,
    SIDEBAR_WIDTH_FULL, SIDEBAR_WIDTH_REDUCED
)
from .theme import SIDEBAR_MIN_ON_SMALL, APPS_PANEL_MIN_ON_SMALL, INPUT_MIN_W, APPS_PANEL_MIN_W, APPS_PANEL_REDUCED_MIN_W
from .sidebar import Sidebar
from .conversation import Conversation
from .input_area import InputArea
from .apps_panel import AppsPanel
from PIL import Image, ImageTk


# ------------------------------------------------------------------ #
#  ICÔNES — modifier les chemins ici                                  #
# ------------------------------------------------------------------ #

from pathlib import Path
ICONS_DIR = Path(__file__).parent.parent.parent / "assets" / "icons"

ICONE_NOUVELLE_TACHE = ICONS_DIR / "new-task-icon.png"
ICONE_PARAMETRES = ICONS_DIR / "settings-icon.png"
ICONE_ENVOYER = ICONS_DIR / "send-icon.png"
ICONE_MICRO = ICONS_DIR / "micro-icon.png"
ICONE_JOINDRE = ICONS_DIR / "attach-icon.png"
ICONE_WORD = ICONS_DIR / "word-icon.png"
ICONE_EXCEL = ICONS_DIR / "excel-icon.png"
ICONE_POWERPOINT = ICONS_DIR / "powerpoint-icon.png"
ICONE_RECHERCHE = ICONS_DIR / "search-icon.png"
ICONE_LOGO = ICONS_DIR / "desknote-icon.jpeg"


class DeskNoteApp:

    def __init__(self, planner=None, executor=None,
                 observer=None, database=None, queue_resultats: Queue = None,
                 speech_recognizer=None):

        self.planner = planner
        self.executor = executor
        self.observer = observer
        self.db = database
        self.queue_resultats = queue_resultats or Queue()
        self.speech_recognizer = speech_recognizer

        self.current_theme = "light"
        self.theme = get_theme(self.current_theme)
        # map call_id -> processing widget (per action)
        self._processing_widgets: dict[str, object] = {}
        self._is_reduced = False

        self._build_window()
        self._build_layout()
        self._post_init()

    # ------------------------------------------------------------------ #
    #  CONSTRUCTION DE LA FENÊTRE                                          #
    # ------------------------------------------------------------------ #

    def _build_window(self):
        """Initialise la fenêtre principale."""
        # Utiliser ttk.Window de ttkbootstrap pour que les styles s'appliquent correctement
        self.root = ttk.Window(themename=self.theme["ttkbootstrap_theme"])
        self.root.title("DeskNote")
        self.root.geometry(f"{WIN_FULL_MIN_W}x{WIN_FULL_MIN_H}")
        self.root.minsize(WIN_FULL_MIN_W, WIN_FULL_MIN_H)

        self.style = self.root.style

        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)
        # colonne 2 = apps panel ; définir minsize pour permettre redimension
        from .theme import APPS_PANEL_MIN_W
        self.root.grid_columnconfigure(2, weight=0, minsize=APPS_PANEL_MIN_W)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)

        self.root.bind("<Configure>", self._on_window_configure)

        # set window/application icon (taskbar + top-left) if available
        try:
            ico_path = ICONE_LOGO
            if ico_path and ico_path.exists():
                try:
                    img = Image.open(ico_path)
                    self._icon_img = ImageTk.PhotoImage(img)
                    try:
                        # iconphoto works on many platforms including Windows
                        self.root.iconphoto(False, self._icon_img)
                    except Exception:
                        pass
                except Exception:
                    pass
            # also try .ico if present for Windows taskbar
            ico_file = ICONS_DIR / "desknote-icon.ico"
            if ico_file.exists():
                try:
                    self.root.iconbitmap(str(ico_file))
                except Exception:
                    pass
        except Exception:
            pass

    def _build_layout(self):
        """Construit et place tous les composants."""

        icones = {
            "nouvelle_tache": ICONE_NOUVELLE_TACHE,
            "parametres":     ICONE_PARAMETRES,
            "word":           ICONE_WORD,
            "powerpoint":     ICONE_POWERPOINT,
            "recherche":      ICONE_RECHERCHE,
            "logo":           ICONE_LOGO,
        }

        # --- sidebar ---
        self.sidebar = Sidebar(
            self.root,
            theme_nom=self.current_theme,
            icones=icones,
            on_new_task=self._on_new_task,
            on_settings=self._on_settings,
            on_search=self._on_search,
            on_recent_click=self._on_recent_click
        )
        # no mini social UI callbacks — message-driven workflow only
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="ns")

        # --- conversation ---
        self.conversation = Conversation(
            self.root,
            theme_nom=self.current_theme
        )
        self.conversation.grid(row=0, column=1, sticky="nsew")

        # --- zone de saisie ---
        self.input_area = InputArea(
            self.root,
            theme_nom=self.current_theme,
            icones={
                "send":   ICONE_ENVOYER,
                "micro":  ICONE_MICRO,
                "attach": ICONE_JOINDRE,
            },
            on_send=self._on_send,
            on_attach=self._on_attach,
            on_voice=self._on_voice,
            on_stop=self._on_stop, speech_recognizer=self.speech_recognizer
        )
        self.input_area.grid(row=1, column=1, sticky="ew")

        # --- panneau applications ---
        self.apps_panel = AppsPanel(
            self.root,
            theme_nom=self.current_theme,
            icones={
                "word":       ICONE_WORD,
                "excel":      ICONE_EXCEL,
                "powerpoint": ICONE_POWERPOINT,
            },
            on_connect=self._on_app_connect
        )
        self.apps_panel.grid(row=0, column=2, rowspan=2,
                             sticky="ns", padx=(1, 0))

        # ✅ forcer les couleurs après ttkbootstrap
        self.root.update()
        self._forcer_couleurs()

    def _post_init(self):
        self._charger_recents()
        self._surveiller_queue()

    # ------------------------------------------------------------------ #
    #  COULEURS — méthode centrale                                         #
    # ------------------------------------------------------------------ #

    def _forcer_couleurs(self):
        """
        Force les couleurs sur tous les composants après ttkbootstrap.
        Appelée après chaque update() et changement de thème.
        """
        # Ne pas appliquer bg sur ttk.Window; le thème est géré par ttkbootstrap
        self.root.update()

        # forcer sur chaque composant
        self.sidebar.config(bg=self.theme["sidebar_bg"])
        self.conversation.config(bg=self.theme["bg"])
        self.input_area.config(bg=self.theme["bg"])
        self.apps_panel.config(bg=self.theme["apps_panel_bg"])

        # propager aux sous-composants
        self.sidebar._refresh_colors()
        self.conversation.appliquer_theme(self.current_theme)
        # force explicit bubble colors (ttkbootstrap may override)
        try:
            self.conversation.forcer_couleurs_bulles()
        except Exception:
            pass
        self.input_area.appliquer_theme(self.current_theme)
        self.apps_panel.appliquer_theme(self.current_theme)

    # ------------------------------------------------------------------ #
    #  REDIMENSIONNEMENT                                                   #
    # ------------------------------------------------------------------ #

    def _on_window_configure(self, event):
        if event.widget != self.root:
            return
        largeur = self.root.winfo_width()

        if largeur <= WIN_REDUCED_MAX_W and not self._is_reduced:
            self._passer_mode_reduit()
        elif largeur > WIN_REDUCED_MAX_W and self._is_reduced:
            self._passer_mode_plein()

    def _passer_mode_reduit(self):
        self._is_reduced = True
        self.root.minsize(WIN_REDUCED_MAX_W // 2, WIN_REDUCED_MIN_H)
        self.root.maxsize(WIN_REDUCED_MAX_W, 9999)
        self.sidebar.passer_mode_reduit()
        # réduire la largeur du panneau d'applications au lieu de le masquer
        try:
            # choose compact sizes depending on current window width
            largeur = self.root.winfo_width()
            # default reduced sizes
            sidebar_w = SIDEBAR_WIDTH_REDUCED
            apps_w = APPS_PANEL_REDUCED_MIN_W

            # if very narrow window, use extra-small widths
            if largeur and largeur <= (WIN_REDUCED_MAX_W // 1.5):
                sidebar_w = SIDEBAR_MIN_ON_SMALL
                apps_w = APPS_PANEL_MIN_ON_SMALL

            # enforce column min sizes: sidebar (col 0), center (col 1) keep flexible but with a sensible min, apps (col 2)
            center_min = max(INPUT_MIN_W, WIN_REDUCED_MAX_W -
                             (sidebar_w + apps_w))
            self.root.grid_columnconfigure(0, minsize=sidebar_w)
            self.root.grid_columnconfigure(1, minsize=center_min)
            self.root.grid_columnconfigure(2, minsize=apps_w)
            # also set the widget widths explicitly to avoid geometry managers from expanding them
            try:
                self.sidebar.config(width=sidebar_w)
                self.sidebar.grid_propagate(False)
            except Exception:
                pass
            try:
                self.apps_panel.config(width=apps_w)
                self.apps_panel.grid_propagate(False)
            except Exception:
                pass
        except Exception:
            pass

    def _passer_mode_plein(self):
        self._is_reduced = False
        self.root.minsize(WIN_FULL_MIN_W, WIN_FULL_MIN_H)
        self.root.maxsize(9999, 9999)
        self.sidebar.passer_mode_plein()
        # restaurer la largeur normale du panneau d'applications
        try:
            # restore sensible defaults
            self.root.grid_columnconfigure(0, minsize=SIDEBAR_WIDTH_FULL)
            self.root.grid_columnconfigure(
                1, minsize=WIN_FULL_MIN_W - (SIDEBAR_WIDTH_FULL + APPS_PANEL_MIN_W))
            self.root.grid_columnconfigure(2, minsize=APPS_PANEL_MIN_W)
            try:
                self.sidebar.config(width=SIDEBAR_WIDTH_FULL)
                self.sidebar.grid_propagate(False)
            except Exception:
                pass
            try:
                self.apps_panel.config(width=APPS_PANEL_MIN_W)
                self.apps_panel.grid_propagate(False)
            except Exception:
                pass
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  ENVOI DE MESSAGE                                                    #
    # ------------------------------------------------------------------ #

    def _on_send(self, texte: str):
        if not texte.strip():
            return

        self.conversation.ajouter_message(texte, "utilisateur")
        # create a unique call_id for this request and keep input active for concurrent requests
        call_id = str(uuid.uuid4())
        proc_widget = self.conversation.afficher_processing()
        self._processing_widgets[call_id] = proc_widget

        if self.db:
            self.db.sauvegarder_message(role="utilisateur", message=texte)

        if self.planner and self.executor:
            import threading
            threading.Thread(
                target=self._traiter_message,
                args=(texte, call_id),
                daemon=True
            ).start()
        else:
            self.root.after(1500, lambda c=call_id: self._afficher_resultat({
                "statut":  "succes",
                "message": "Backend non connecté — mode démonstration.",
                "call_id": c
            }))

    def _traiter_message(self, texte: str, call_id: str):
        try:
            json_action = self.planner.planifier(texte)
            action = json_action.get("action")

            if action == "incompris":
                msg = json_action.get(
                    "message_utilisateur", "Je n'ai pas compris.")
                self.root.after(0, lambda m=msg, cid=call_id: self._afficher_resultat({
                    "statut": "incompris", "message": m, "call_id": cid
                }))
                return

            if json_action.get("confirmation_requise"):
                msg_conf = json_action.get(
                    "message_confirmation", "Confirmer ?")
                self.root.after(0, lambda m=msg_conf, j=json_action, cid=call_id:
                                self._demander_confirmation(m, j, cid))
                return

            # attach call_id so executor can forward it back in the result
            json_action["call_id"] = call_id
            self.executor.executer(json_action)

        except Exception as e:
            self.root.after(0, lambda err=str(e), cid=call_id: self._afficher_resultat({
                "statut": "echec", "message": f"Erreur : {err}", "call_id": cid
            }))

    # ------------------------------------------------------------------ #
    #  CONFIRMATION                                                        #
    # ------------------------------------------------------------------ #

    def _demander_confirmation(self, message: str, json_action: dict, call_id: str):
        # remove the processing widget associated with this call
        widget = self._processing_widgets.pop(call_id, None)
        self.conversation.supprimer_processing(widget)

        ligne = tk.Frame(self.conversation.inner_frame, bg=self.theme["bg"])
        ligne.pack(fill="x", padx=16, pady=4)

        tk.Label(
            ligne,
            text=message,
            bg=self.theme["bulle_agent_bg"],
            fg=self.theme["bulle_agent_fg"],
            font=("Segoe UI", 10),
            wraplength=400,
            justify="left",
            padx=12, pady=8
        ).pack(anchor="w")

        btn_frame = tk.Frame(ligne, bg=self.theme["bg"])
        btn_frame.pack(anchor="w", pady=(4, 0))

        tk.Button(
            btn_frame,
            text="Oui, confirmer",
            bg=self.theme["btn_send_bg"],
            fg="#FFFFFF",
            font=("Segoe UI", 9),
            bd=0, cursor="hand2",
            padx=12, pady=6,
            command=lambda: self._confirmer(json_action, call_id, ligne)
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame,
            text="Annuler",
            bg=self.theme["border"],
            fg=self.theme["fg"],
            font=("Segoe UI", 9),
            bd=0, cursor="hand2",
            padx=12, pady=6,
            command=lambda: self._annuler(ligne, call_id)
        ).pack(side="left")

        self.conversation._scroll_bas()

    def _confirmer(self, json_action: dict, call_id: str, widget):
        widget.destroy()
        # create a processing widget for this call_id
        proc = self.conversation.afficher_processing()
        self._processing_widgets[call_id] = proc
        self.executor.executer(json_action)

    def _annuler(self, widget, call_id: str):
        widget.destroy()
        # remove processing widget for this call
        self._processing_widgets.pop(call_id, None)
        self.conversation.ajouter_message("Action annulée.", "agent")

    # ------------------------------------------------------------------ #
    #  QUEUE                                                               #
    # ------------------------------------------------------------------ #

    def _surveiller_queue(self):
        try:
            try:
                resultat = self.queue_resultats.get_nowait()
                # defensively handle the resultat to avoid crashing the UI
                try:
                    self._afficher_resultat(resultat)
                except Exception as e:
                    # log and continue; do not let malformed result crash mainloop
                    print(f"[UI] Erreur lors de l'affichage du résultat: {e}")
            except Empty:
                pass
        except Exception as e:
            # catch-all: protect mainloop from any unexpected exception
            print(f"[UI] Exception inattendue dans _surveiller_queue: {e}")
        finally:
            # reschedule polling regardless of errors
            try:
                self.root.after(100, self._surveiller_queue)
            except Exception:
                pass

    def _afficher_resultat(self, resultat: dict):
        try:
            # handle progress messages specially so the processing widget stays
            # visible while sub-step updates arrive
            if isinstance(resultat, dict) and resultat.get("type") == "progress":
                call_id = resultat.get("call_id")
                if call_id:
                    widget = self._processing_widgets.get(call_id)
                    if widget:
                        try:
                            self.conversation.update_processing(
                                widget, resultat.get("message", ""))
                        except Exception:
                            pass
                        return

            # remove the processing widget associated with this call (final result)
            call_id = None
            if isinstance(resultat, dict):
                call_id = resultat.get("call_id")

            if call_id:
                widget = self._processing_widgets.pop(call_id, None)
                try:
                    self.conversation.supprimer_processing(widget)
                except Exception:
                    pass
            else:
                # fallback for old code paths
                try:
                    for widget in list(self._processing_widgets.values()):
                        try:
                            self.conversation.supprimer_processing(widget)
                        except Exception:
                            pass
                    self._processing_widgets.clear()
                except Exception:
                    self._processing_widgets.clear()

            message = ""
            try:
                if isinstance(resultat, dict):
                    message = resultat.get("message", "") or ""
                else:
                    message = str(resultat)
            except Exception:
                message = ""

            try:
                self.conversation.ajouter_message(message, "agent")
            except Exception:
                pass

            if self.db:
                try:
                    self.db.sauvegarder_message(
                        role="agent",
                        message=message,
                        statut=resultat.get("statut") if isinstance(
                            resultat, dict) else None
                    )
                except Exception:
                    pass
            try:
                self._charger_recents()
            except Exception:
                pass
        except Exception as e:
            print(f"[UI] Erreur inattendue dans _afficher_resultat: {e}")

    # ------------------------------------------------------------------ #
    #  RÉCENTS                                                             #
    # ------------------------------------------------------------------ #

    def _charger_recents(self):
        if not self.db:
            return
        try:
            messages = self.db.recuperer_historique(limite=8)
            items = [m for m in messages if m.get("role") == "utilisateur"]
            self.sidebar.charger_recents(items)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  CALLBACKS                                                           #
    # ------------------------------------------------------------------ #

    def _on_new_task(self):
        # clean up any processing widgets from previous requests
        for widget in self._processing_widgets.values():
            self.conversation.supprimer_processing(widget)
        self._processing_widgets.clear()
        self.conversation.charger_historique([])
        self.input_area.effacer()

    def _on_settings(self):
        pass

    def _on_search(self, texte: str):
        if not self.db or not texte:
            return
        try:
            tous = self.db.recuperer_historique(limite=50)
            filtres = [
                m for m in tous
                if texte.lower() in m.get("message", "").lower()
                and m.get("role") == "utilisateur"
            ]
            self.sidebar.charger_recents(filtres)
        except Exception:
            pass

    def _on_recent_click(self, item: dict):
        self.input_area.set_texte(item.get("message", ""))

    def _on_attach(self):
        pass

    def _on_voice(self):
        pass

    def _on_app_connect(self, nom_app: str, connectee: bool):
        print(f"[Apps] {nom_app} connectée : {connectee}")

    def _on_stop(self):
        """Global stop: request cancellation for all active actions."""
        try:
            if self.executor:
                self.executor.cancel_all()
        except Exception:
            pass

        # update processing widgets to reflect stop request
        for wid in list(self._processing_widgets.values()):
            try:
                self.conversation.update_processing(wid, "Arrêt demandé...")
            except Exception:
                pass

    # Note: Facebook composer and scheduled-posts windows removed from UI.
    # Posting is intended to be driven entirely via the message input and planner.

    # ------------------------------------------------------------------ #
    #  THÈME                                                               #
    # ------------------------------------------------------------------ #

    def basculer_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.theme = get_theme(self.current_theme)
        self.style.theme_use(self.theme["ttkbootstrap_theme"])
        self.root.update()
        self._forcer_couleurs()

    # ------------------------------------------------------------------ #
    #  LANCEMENT                                                           #
    # ------------------------------------------------------------------ #

    def lancer(self):
        self.root.mainloop()
