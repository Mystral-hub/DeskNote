# src/ui/input_area.py

import tkinter as tk
import ttkbootstrap as ttk
from PIL import Image, ImageTk
from pathlib import Path
from .theme import get_theme
import threading
import time
from vocals.speech_recognizer import SpeechRecognizer

ICONS_DIR = Path(__file__).parent.parent.parent / "assets" / "icons"

SUGGESTIONS = [
    "Créer un fichier",
    "Faire une présentation",
    "Rédiger une note",
]


class InputArea(tk.Frame):

    def __init__(self, parent, theme_nom: str = "light",
                 icones=None, on_send=None, on_attach=None, on_voice=None, on_stop=None,
                 speech_recognizer=None, **kwargs):

        self.theme = get_theme(theme_nom)

        super().__init__(
            parent,
            bg=self.theme["bg"],
            **kwargs
        )

        self._on_send = on_send
        self._on_attach = on_attach
        self._on_voice = on_voice
        self._on_stop = on_stop
        # autorise un dict d'icônes passé par l'appelant (ne pas forward à tk.Frame)
        self._icons = icones or {}

        self._build()

        # speech recognizer: use provided instance or lazy-load when needed
        self._sr = speech_recognizer
        self._sr_lock = threading.Lock()

    # ------------------------------------------------------------------ #
    #  CONSTRUCTION                                                        #
    # ------------------------------------------------------------------ #

    def _build(self):
        """Construit la zone de saisie complète."""
        self._build_suggestions()
        self._build_input()
        self._build_buttons()

    def _build_suggestions(self):
        """Boutons de suggestions au-dessus de la zone de saisie."""
        self.suggestions_frame = tk.Frame(self, bg=self.theme["bg"])
        self.suggestions_frame.pack(fill="x", padx=8, pady=(8, 4))

        for texte in SUGGESTIONS:
            btn = ttk.Button(
                self.suggestions_frame,
                text=texte,
                bootstyle="outline-secondary",
                command=lambda t=texte: self._on_suggestion_click(t)
            )
            btn.pack(side="left", padx=4)
            btn.configure(cursor="hand2", width=16)

    def _build_input(self):
        """Zone de saisie de texte."""
        self.input_frame = tk.Frame(
            self,
            bg=self.theme["input_bg"],
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=self.theme["border_input"],
            highlightcolor=self.theme["btn_send_bg"]
        )
        self.input_frame.pack(fill="x", padx=8, pady=4)

        self.input_text = tk.Text(
            self.input_frame,
            height=3,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            bg=self.theme["input_bg"],
            fg=self.theme["fg"],
            insertbackground=self.theme["insertbackground"],
            relief="flat",
            bd=0,
            padx=10,
            pady=8
        )
        self.input_text.pack(fill="both", expand=True)

        # placeholder
        self._placeholder = "comment puis-je vous aider ?"
        self._placeholder_active = True
        self.input_text.insert("1.0", self._placeholder)
        self.input_text.config(fg=self.theme["fg_muted"])

        self.input_text.bind("<FocusIn>",  self._on_focus_in)
        self.input_text.bind("<FocusOut>", self._on_focus_out)
        self.input_text.bind("<Return>",   self._on_return)
        self.input_text.bind("<Shift-Return>", self._on_shift_return)

    def _build_buttons(self):
        """Barre de boutons sous la zone de saisie."""
        self.buttons_frame = tk.Frame(self, bg=self.theme["bg"])
        self.buttons_frame.pack(fill="x", padx=8, pady=(0, 8))

        # bouton + (joindre fichier) — gauche
        self._charger_icone("attach", "file-plus.png", (18, 18))
        self.attach_btn = tk.Button(
            self.buttons_frame,
            image=self._icons.get("attach"),
            text="+" if "attach" not in self._icons else "",
            bg=self.theme["bg"],
            activebackground=self.theme["bg"],
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            command=self._on_attach
        )
        self.attach_btn.pack(side="left", padx=(0, 4))

        # bouton micro — gauche
        self._charger_icone("micro", "audio-lines.png", (18, 18))
        self.voice_btn = tk.Button(
            self.buttons_frame,
            image=self._icons.get("micro"),
            text="🎤" if "micro" not in self._icons else "",
            bg=self.theme["bg"],
            activebackground=self.theme["bg"],
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        # press-and-hold behaviour: start on press, stop on release
        self.voice_btn.bind("<ButtonPress-1>", self._on_voice_press)
        self.voice_btn.bind("<ButtonRelease-1>", self._on_voice_release)
        self.voice_btn.pack(side="left", padx=4)

        # bouton envoyer — droite
        self._charger_icone("send", "send.png", (20, 20))
        self.send_btn = tk.Button(
            self.buttons_frame,
            image=self._icons.get("send"),
            text="➤" if "send" not in self._icons else "",
            bg=self.theme["btn_send_bg"],
            activebackground=self.theme["btn_search_bg"],
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            width=36,
            height=36,
            command=self._envoyer
        )
        self.send_btn.pack(side="right", padx=(4, 0))

        # bouton stop — droite (arrêt global des actions en cours)
        self._charger_icone("stop", "stop-icon.png", (18, 18))
        self.stop_btn = tk.Button(
            self.buttons_frame,
            image=self._icons.get("stop"),
            text="■" if "stop" not in self._icons else "",
            bg=self.theme["bg"],
            activebackground=self.theme["bg"],
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            command=self._on_stop
        )
        self.stop_btn.pack(side="right", padx=(4, 0))

    # ------------------------------------------------------------------ #
    #  MÉTHODES PUBLIQUES                                                  #
    # ------------------------------------------------------------------ #

    def get_texte(self) -> str:
        """Retourne le texte saisi sans le placeholder."""
        texte = self.input_text.get("1.0", tk.END).strip()
        if texte == self._placeholder:
            return ""
        return texte

    def effacer(self):
        """Vide la zone de saisie et remet le placeholder."""
        self.input_text.delete("1.0", tk.END)
        self._placeholder_active = True
        self.input_text.insert("1.0", self._placeholder)
        self.input_text.config(fg=self.theme["fg_muted"])

    def set_texte(self, texte: str):
        """Insère un texte dans la zone de saisie."""
        self.input_text.delete("1.0", tk.END)
        self._placeholder_active = False
        self.input_text.insert("1.0", texte)
        self.input_text.config(fg=self.theme["fg"])
        self.input_text.focus_set()

    # ---------------- Speech handling ---------------------------------
    def _ensure_recognizer(self):
        with self._sr_lock:
            if self._sr is None:
                # load model in background to avoid blocking UI
                def _load():
                    try:
                        self._sr = SpeechRecognizer(
                            model_size="base", language="fr")
                    except Exception:
                        self._sr = None
                t = threading.Thread(target=_load, daemon=True)
                t.start()
                # wait briefly for model to initialize a little
                time_waited = 0
                while self._sr is None and time_waited < 0.5:
                    t.join(timeout=0.1)
                    time_waited += 0.1

    def _on_voice_press(self, event=None):
        # visual feedback
        try:
            self.voice_btn.config(bg=self.theme.get("btn_search_bg", "#ddd"))
        except Exception:
            pass

        # ensure recognizer exists (load lazily)
        self._ensure_recognizer()

        # start recording (non-blocking)
        def _start():
            try:
                if self._sr is None:
                    # wait until loaded
                    with self._sr_lock:
                        pass
                if self._sr:
                    self._sr.start_recording(sample_rate=16000)
            except Exception:
                pass

        threading.Thread(target=_start, daemon=True).start()

    def _on_voice_release(self, event=None):
        # reset visual feedback
        try:
            self.voice_btn.config(bg=self.theme.get("bg", "#fff"))
        except Exception:
            pass

        # stop and transcribe in background
        def _stop_and_transcribe():
            try:
                if not self._sr:
                    return
                # show temporary placeholder
                self.after(0, lambda: self.set_texte(
                    "[Transcription en cours...]"))
                texte = self._sr.stop_and_transcribe()
                if texte:
                    self.after(0, lambda: self.set_texte(texte))
                else:
                    # clear placeholder if nothing recognized
                    self.after(0, lambda: self.effacer())
            except Exception:
                self.after(0, lambda: self.effacer())

        threading.Thread(target=_stop_and_transcribe, daemon=True).start()

    def desactiver(self):
        """Désactive la zone de saisie pendant le traitement."""
        self.input_text.config(state="disabled")
        self.send_btn.config(state="disabled")
        try:
            self.stop_btn.config(state="normal")
        except Exception:
            pass

    def activer(self):
        """Réactive la zone de saisie après le traitement."""
        self.input_text.config(state="normal")
        self.send_btn.config(state="normal")
        try:
            self.stop_btn.config(state="normal")
        except Exception:
            pass

    def appliquer_theme(self, theme_nom: str):
        """Met à jour toutes les couleurs selon le thème."""
        self.theme = get_theme(theme_nom)
        self._refresh_colors()

    # ------------------------------------------------------------------ #
    #  ÉVÉNEMENTS                                                          #
    # ------------------------------------------------------------------ #

    def _on_focus_in(self, event):
        """Efface le placeholder quand l'utilisateur clique."""
        if self._placeholder_active:
            self.input_text.delete("1.0", tk.END)
            self.input_text.config(fg=self.theme["fg"])
            self._placeholder_active = False

    def _on_focus_out(self, event):
        """Remet le placeholder si la zone est vide."""
        if not self.input_text.get("1.0", tk.END).strip():
            self.effacer()

    def _on_return(self, event):
        """Envoie le message sur Entrée."""
        self._envoyer()
        return "break"  # empêche le saut de ligne

    def _on_shift_return(self, event):
        """Shift+Entrée insère un saut de ligne."""
        return None

    def _on_suggestion_click(self, texte: str):
        """Pré-remplit la zone de saisie avec la suggestion."""
        self.set_texte(texte)

    def _envoyer(self):
        """Récupère le texte et appelle le callback on_send."""
        texte = self.get_texte()
        if not texte:
            return
        if self._on_send:
            self._on_send(texte)

    # ------------------------------------------------------------------ #
    #  UTILITAIRES                                                         #
    # ------------------------------------------------------------------ #

    def _charger_icone(self, nom: str, fichier: str, taille: tuple):
        """Charge une icône PNG et la stocke dans self._icons."""
        # Si l'appelant a fourni un chemin/Path pour cette icône, charge-le d'abord
        try:
            val = self._icons.get(nom)
            if val:
                from pathlib import Path
                p = Path(val)
                if p.exists():
                    img = Image.open(p).resize(taille)
                    self._icons[nom] = ImageTk.PhotoImage(img)
                    return
        except Exception:
            # ignore et essayer le fichier par défaut
            pass

        chemin = ICONS_DIR / fichier
        if not chemin.exists():
            return
        try:
            img = Image.open(chemin).resize(taille)
            self._icons[nom] = ImageTk.PhotoImage(img)
        except Exception:
            pass

    def _refresh_colors(self):
        """Reapplique les couleurs sur tous les widgets."""
        self.config(bg=self.theme["bg"])
        self.suggestions_frame.config(bg=self.theme["bg"])
        self.input_frame.config(
            bg=self.theme["input_bg"],
            highlightbackground=self.theme["border_input"]
        )
        self.input_text.config(
            bg=self.theme["input_bg"],
            fg=self.theme["fg"],
            insertbackground=self.theme["insertbackground"]
        )
        self.buttons_frame.config(bg=self.theme["bg"])
        self.attach_btn.config(
            bg=self.theme["bg"], activebackground=self.theme["bg"])
        self.voice_btn.config(
            bg=self.theme["bg"],  activebackground=self.theme["bg"])
        self.send_btn.config(bg=self.theme["btn_send_bg"])
        try:
            self.stop_btn.config(
                bg=self.theme["bg"], activebackground=self.theme["bg"])
        except Exception:
            pass
