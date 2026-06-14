# src/ui/conversation.py

import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk
from .theme import get_theme

ICONS_DIR = Path(__file__).parent.parent.parent / "assets" / "icons"


class Conversation(tk.Frame):

    def __init__(self, parent, theme_nom: str = "light", **kwargs):

        self.theme = get_theme(theme_nom)

        super().__init__(
            parent,
            bg=self.theme["bg"],
            **kwargs
        )

        self._build()

    # ------------------------------------------------------------------ #
    #  CONSTRUCTION                                                        #
    # ------------------------------------------------------------------ #

    def _build(self):

        # scrollbar verticale
        self.scrollbar = tk.Scrollbar(self, orient="vertical")
        self.scrollbar.pack(side="right", fill="y")

        # canvas principal qui contient les bulles
        self.canvas = tk.Canvas(
            self,
            bg=self.theme["bg"],
            highlightthickness=0,
            yscrollcommand=self.scrollbar.set
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.canvas.yview)

        # frame intérieure qui contient réellement les bulles
        self.inner_frame = tk.Frame(self.canvas, bg=self.theme["bg"])
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.inner_frame,
            anchor="nw"
        )

        # recalculer la scrollregion quand le contenu change
        self.inner_frame.bind("<Configure>", self._on_inner_frame_configure)
        self.canvas.bind("<Configure>",      self._on_canvas_configure)

        # scroll à la molette
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.inner_frame.bind("<MouseWheel>", self._on_mousewheel)

        # message de bienvenue
        self._afficher_bienvenue()

    def _afficher_bienvenue(self):
        """Affiche le message de bienvenue au centre."""
        self.bienvenue_frame = tk.Frame(
            self.inner_frame,
            bg=self.theme["bg"]
        )
        self.bienvenue_frame.pack(expand=True, pady=60)

        # try to show an enlarged logo above the welcome subtitle
        try:
            logo_path = ICONS_DIR / "desknote-icon.jpeg"
            if not logo_path.exists():
                logo_path = ICONS_DIR / "logo-icon.png"
            if logo_path.exists():
                img = Image.open(logo_path)
                h = 96
                w = int(img.width * (h / img.height))
                img_resized = img.resize((w, h))
                self._welcome_logo_img = ImageTk.PhotoImage(img_resized)
                tk.Label(
                    self.bienvenue_frame,
                    image=self._welcome_logo_img,
                    bg=self.theme["bg"]
                ).pack(pady=(0, 12))
            else:
                self._welcome_logo_img = None
        except Exception:
            self._welcome_logo_img = None

        tk.Label(
            self.bienvenue_frame,
            text="Décrivez votre tâche, je m'occupe du reste.",
            bg=self.theme["bg"],
            fg=self.theme["fg_muted"],
            font=("Segoe UI", 11)
        ).pack()

    # ------------------------------------------------------------------ #
    #  BULLES DE MESSAGES                                                  #
    # ------------------------------------------------------------------ #

    def ajouter_message(self, texte: str, role: str):
        """
        Ajoute une bulle de message dans la conversation.
        role = "utilisateur" ou "agent"
        """
        # supprimer le message de bienvenue au premier message
        if hasattr(self, "bienvenue_frame") and self.bienvenue_frame.winfo_exists():
            self.bienvenue_frame.destroy()

        est_utilisateur = role == "utilisateur"

        # conteneur de la ligne
        ligne = tk.Frame(self.inner_frame, bg=self.theme["bg"])
        # taguer le rôle sur la ligne pour recoloration ultérieure
        ligne.role = role
        ligne.pack(fill="x", padx=16, pady=4)

        # couleurs selon le rôle
        bulle_bg = self.theme["bulle_user_bg"] if est_utilisateur else self.theme["bulle_agent_bg"]
        bulle_fg = self.theme["bulle_user_fg"] if est_utilisateur else self.theme["bulle_agent_fg"]
        alignement = "e" if est_utilisateur else "w"

        # frame de la bulle
        bulle = tk.Frame(
            ligne,
            bg=bulle_bg,
            padx=12,
            pady=8
        )
        # garder une référence pour la recoloration si le thème change
        bulle.role = role
        bulle.pack(anchor=alignement)

        # texte de la bulle
        label = tk.Label(
            bulle,
            text=texte,
            bg=bulle_bg,
            fg=bulle_fg,
            font=("Segoe UI", 10),
            wraplength=400,
            justify="left" if not est_utilisateur else "right",
            anchor="w"
        )
        label.pack()
        # stocker la référence du label sur la bulle pour recoloration
        bulle._text_label = label
        # ensure colors are applied immediately (ttkbootstrap may override defaults)
        try:
            bulle.config(bg=bulle_bg)
            label.config(bg=bulle_bg, fg=bulle_fg)
            self.canvas.update_idletasks()
        except Exception:
            pass

        # scroll automatique vers le bas
        self._scroll_bas()

    def afficher_processing(self):
        """
        Affiche une bulle animée 'En cours...' pendant le traitement.
        Retourne la référence pour pouvoir la supprimer après.
        """
        ligne = tk.Frame(self.inner_frame, bg=self.theme["bg"])
        ligne.pack(fill="x", padx=16, pady=4)

        bulle = tk.Frame(
            ligne,
            bg=self.theme["processing_bg"],
            padx=12,
            pady=8
        )
        bulle.pack(anchor="w")

        label = tk.Label(
            bulle,
            text="En cours",
            bg=self.theme["processing_bg"],
            fg=self.theme["processing_fg"],
            font=("Segoe UI", 10)
        )
        label.pack()

        self._scroll_bas()

        # keep a reference to the label on the returned container so callers
        # can update the text while the processing widget is visible
        ligne.processing_label = label

        # lancer l'animation des points
        self._animer_processing(label, 0)

        return ligne

    def supprimer_processing(self, widget):
        """Supprime la bulle de processing après la fin de l'action."""
        if widget and widget.winfo_exists():
            widget.destroy()

    def charger_historique(self, messages: list):
        """
        Charge et affiche une liste de messages depuis la base de données.
        messages = liste de dicts {role, message}
        """
        # vider la conversation
        for widget in self.inner_frame.winfo_children():
            widget.destroy()

        if not messages:
            self._afficher_bienvenue()
            return

        for msg in messages:
            self.ajouter_message(
                texte=msg.get("message", ""),
                role=msg.get("role", "agent")
            )

    # ------------------------------------------------------------------ #
    #  ANIMATION PROCESSING                                                #
    # ------------------------------------------------------------------ #

    def _animer_processing(self, label: tk.Label, etape: int):
        """Animation rotative sur le label de processing."""
        if not label.winfo_exists():
            return

        # if a fixed text is set (via `fixed_text`), show it and stop the
        # rotation animation; otherwise continue the animated dots.
        fixed = getattr(label, "fixed_text", None)
        if fixed:
            try:
                label.config(text=fixed)
            except Exception:
                pass
            # keep checking in case the fixed_text is cleared later
            label.after(500, lambda: self._animer_processing(label, etape))
            return

        etapes = [
            "En cours ·  ",
            "En cours ·· ",
            "En cours ···",
            "En cours ·· ",
            "En cours ·  ",
        ]

        label.config(text=etapes[etape % len(etapes)])
        label.after(300, lambda: self._animer_processing(label, etape + 1))

    def update_processing(self, widget, texte: str):
        """Met à jour le texte affiché dans une bulle de processing sans la supprimer."""
        try:
            if not widget or not getattr(widget, "winfo_exists", lambda: False)():
                return
            lbl = getattr(widget, "processing_label", None)
            if not lbl:
                # best-effort: try to find a label inside the widget
                try:
                    lbl = widget.winfo_children()[0].winfo_children()[0]
                except Exception:
                    lbl = None
            if lbl:
                lbl.fixed_text = texte
                lbl.config(text=texte)
                self._scroll_bas()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  THÈME                                                               #
    # ------------------------------------------------------------------ #

    def appliquer_theme(self, theme_nom: str):
        """Met à jour toutes les couleurs selon le thème."""
        self.theme = get_theme(theme_nom)
        self.config(bg=self.theme["bg"])
        self.canvas.config(bg=self.theme["bg"])
        self.inner_frame.config(bg=self.theme["bg"])
        # Recolor existing message bubbles (if any)
        try:
            for ligne in self.inner_frame.winfo_children():
                # each "ligne" is a Frame containing the bubble
                try:
                    role = getattr(ligne, "role", None)
                    # find first child that is the bubble frame
                    bulle = None
                    for child in ligne.winfo_children():
                        if isinstance(child, tk.Frame):
                            bulle = child
                            break
                    if not bulle:
                        continue
                    if role == "utilisateur":
                        bg = self.theme.get("bulle_user_bg", self.theme["bg"])
                        fg = self.theme.get("bulle_user_fg", self.theme["fg"])
                    else:
                        bg = self.theme.get("bulle_agent_bg", self.theme["bg"])
                        fg = self.theme.get("bulle_agent_fg", self.theme["fg"])

                    try:
                        bulle.config(bg=bg)
                    except Exception:
                        pass

                    # recolor nested text label if present
                    txt = getattr(bulle, "_text_label", None)
                    if txt and getattr(txt, "winfo_exists", lambda: False)():
                        try:
                            txt.config(bg=bg, fg=fg)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    def forcer_couleurs_bulles(self):
        """Forcer explicitement les couleurs sur toutes les bulles (écrase éventuellement
        les styles hérités de ttkbootstrap)."""
        try:
            for ligne in self.inner_frame.winfo_children():
                try:
                    role = getattr(ligne, "role", None)
                    # trouver la bulle (premier Frame enfant)
                    bulle = None
                    for child in ligne.winfo_children():
                        if isinstance(child, tk.Frame):
                            bulle = child
                            break
                    if not bulle:
                        continue
                    if role == "utilisateur":
                        bg = self.theme.get("bulle_user_bg", self.theme["bg"])
                        fg = self.theme.get("bulle_user_fg", self.theme["fg"])
                    else:
                        bg = self.theme.get("bulle_agent_bg", self.theme["bg"])
                        fg = self.theme.get("bulle_agent_fg", self.theme["fg"])
                    try:
                        bulle.configure(bg=bg)
                    except Exception:
                        pass
                    txt = getattr(bulle, "_text_label", None)
                    if txt and getattr(txt, "winfo_exists", lambda: False)():
                        try:
                            txt.configure(bg=bg, fg=fg)
                        except Exception:
                            pass
                except Exception:
                    pass
            self.canvas.update_idletasks()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  ÉVÉNEMENTS                                                          #
    # ------------------------------------------------------------------ #

    def _on_inner_frame_configure(self, event):
        """Recalcule la scrollregion quand le contenu change."""
        self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        )

    def _on_canvas_configure(self, event):
        """Adapte la largeur de la frame intérieure au canvas."""
        self.canvas.itemconfig(
            self.canvas_window,
            width=event.width
        )

    def _on_mousewheel(self, event):
        """Scroll à la molette de souris."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _scroll_bas(self):
        """Fait défiler automatiquement vers le dernier message."""
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)
