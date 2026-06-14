# src/ui/sidebar.py

import tkinter as tk
import ttkbootstrap as ttk
from PIL import Image, ImageTk
from pathlib import Path
from .theme import get_theme, SIDEBAR_WIDTH_FULL, SIDEBAR_WIDTH_REDUCED

ICONS_DIR = Path(__file__).parent.parent.parent / "assets" / "icons"


class Sidebar(tk.Frame):

    def __init__(self, parent, theme_nom: str = "light", icones=None, on_new_task=None,
                 on_settings=None, on_search=None, on_recent_click=None, **kwargs):

        self.theme = get_theme(theme_nom)

        super().__init__(
            parent,
            bg=self.theme["sidebar_bg"],
            width=SIDEBAR_WIDTH_FULL,
            **kwargs
        )
        self.grid_propagate(False)

        self._on_new_task = on_new_task
        self._on_settings = on_settings
        self._on_search = on_search
        self._on_recent_click = on_recent_click

        # initialiser les icônes si fournies (ne pas passer ce dict à tk.Frame)
        self._icons = icones or {}
        self._recent_items = []
        self._is_reduced = False

        self._build()

    # ------------------------------------------------------------------ #
    #  CONSTRUCTION                                                        #
    # ------------------------------------------------------------------ #

    def _build(self):
        """Construit tous les éléments de la sidebar."""
        self._build_logo()
        self._build_new_task_btn()
        self._build_search()
        self._build_recents()
        self._build_bottom()

    def _build_logo(self):
        """Zone logo en haut de la sidebar."""
        self.logo_frame = tk.Frame(self, bg=self.theme["sidebar_bg"])
        self.logo_frame.pack(fill="x", padx=10, pady=(16, 8))
        # Sidebar shows text label only; logo moved to welcome message
        self.logo_label = tk.Label(
            self.logo_frame,
            text="DeskNote",
            bg=self.theme["sidebar_bg"],
            fg=self.theme["btn_send_bg"],
            font=("Segoe UI Semibold", 16),
            anchor="w"
        )
        self.logo_label.pack(side="left")

    def _build_new_task_btn(self):
        """Bouton nouvelle tâche."""
        self.new_task_frame = tk.Frame(self, bg=self.theme["sidebar_bg"])
        self.new_task_frame.pack(fill="x", padx=10, pady=(8, 4))

        self.new_task_btn = ttk.Button(
            self.new_task_frame,
            text="+ Nouvelle tâche",
            bootstyle="primary",
            command=self._on_new_task,
        )
        # style adjustments
        self.new_task_btn.configure(cursor="hand2", width=18)
        self.new_task_btn.pack(fill="x")

    def _build_search(self):
        """Barre de recherche."""
        self.search_frame = tk.Frame(
            self,
            bg=self.theme["btn_search_bg"],
            pady=4
        )
        self.search_frame.pack(fill="x", padx=10, pady=(4, 8))

        self.search_icon_label = tk.Label(
            self.search_frame,
            text="🔍",
            bg=self.theme["btn_search_bg"],
            fg=self.theme["fg_sidebar"],
            font=("Segoe UI", 10)
        )
        self.search_icon_label.pack(side="left", padx=(8, 0))

        self.search_entry = tk.Entry(
            self.search_frame,
            bg=self.theme["btn_search_bg"],
            fg=self.theme["fg_sidebar"],
            insertbackground=self.theme["fg_sidebar"],
            relief="flat",
            font=("Segoe UI", 10),
            bd=0
        )
        self.search_entry.insert(0, "Rechercher")
        self.search_entry.bind("<FocusIn>",  self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)
        self.search_entry.bind("<KeyRelease>", self._on_search_keyrelease)
        self.search_entry.pack(side="left", fill="x",
                               expand=True, padx=8, pady=4)

    def _build_recents(self):
        """Section des tâches récentes."""
        self.recents_label = tk.Label(
            self,
            text="Récents",
            bg=self.theme["sidebar_bg"],
            fg=self.theme["fg_muted"],
            font=("Segoe UI", 9),
            anchor="w"
        )
        self.recents_label.pack(fill="x", padx=14, pady=(8, 4))

        self.recents_frame = tk.Frame(self, bg=self.theme["sidebar_bg"])
        self.recents_frame.pack(fill="x", padx=10)

    def _build_bottom(self):
        """Bouton paramètres en bas de la sidebar."""
        self.bottom_frame = tk.Frame(self, bg=self.theme["sidebar_bg"])
        self.bottom_frame.pack(side="bottom", fill="x", padx=10, pady=12)

        self.upgrade_btn = ttk.Button(
            self.bottom_frame,
            text="⬆ Mettre à niveau",
            bootstyle="outline-secondary",
            command=lambda: None,
        )
        self.upgrade_btn.configure(cursor="hand2")
        self.upgrade_btn.pack(fill="x", pady=(0, 8))

        self.settings_btn = ttk.Button(
            self.bottom_frame,
            text="⚙",
            bootstyle="secondary",
            command=self._on_settings
        )
        self.settings_btn.configure(cursor="hand2")
        self.settings_btn.pack(side="left")

    # ------------------------------------------------------------------ #
    #  RÉCENTS                                                             #
    # ------------------------------------------------------------------ #

    def charger_recents(self, items: list):
        """
        Charge et affiche les tâches récentes.
        items = liste de dicts {id, message}
        """
        for widget in self.recents_frame.winfo_children():
            widget.destroy()

        self._recent_items = items

        for item in items[:8]:
            texte = item.get("message", "")
            texte_court = texte[:28] + "..." if len(texte) > 28 else texte

            btn = tk.Button(
                self.recents_frame,
                text=texte_court,
                bg=self.theme["sidebar_bg"],
                fg=self.theme["recent_fg"],
                font=("Segoe UI", 9),
                bd=0,
                relief="flat",
                cursor="hand2",
                anchor="w",
                padx=8,
                pady=4,
                command=lambda i=item: self._on_recent_click(
                    i) if self._on_recent_click else None
            )
            btn.pack(fill="x")
            btn.bind("<Enter>", lambda e, b=btn: b.config(
                bg=self.theme["recent_hover_bg"]))
            btn.bind("<Leave>", lambda e, b=btn: b.config(
                bg=self.theme["sidebar_bg"]))

    # ------------------------------------------------------------------ #
    #  MODE RÉDUIT / PLEIN ÉCRAN                                           #
    # ------------------------------------------------------------------ #

    def passer_mode_reduit(self):
        """Passe la sidebar en mode réduit — icônes uniquement."""
        self._is_reduced = True
        self.config(width=SIDEBAR_WIDTH_REDUCED)

        # cacher les éléments texte
        self.logo_label.config(text="DN", image="")
        self.new_task_btn.config(text="+")
        self.search_frame.pack_forget()
        self.recents_label.pack_forget()
        self.recents_frame.pack_forget()
        self.upgrade_btn.pack_forget()

    def passer_mode_plein(self):
        """Passe la sidebar en mode plein écran."""
        self._is_reduced = False
        self.config(width=SIDEBAR_WIDTH_FULL)

        # rétablir les éléments texte
        self.logo_label.config(text="DeskNote", image="")
        self.new_task_btn.config(text="+ Nouvelle tâche")
        self.search_frame.pack(fill="x", padx=10, pady=(4, 8))
        self.recents_label.pack(fill="x", padx=14, pady=(8, 4))
        self.recents_frame.pack(fill="x", padx=10)
        self.upgrade_btn.pack(fill="x", pady=(0, 8))

    # ------------------------------------------------------------------ #
    #  THÈME                                                               #
    # ------------------------------------------------------------------ #

    def appliquer_theme(self, theme_nom: str):
        """Met à jour toutes les couleurs selon le thème."""
        self.theme = get_theme(theme_nom)
        self.root.update()
        self._refresh_colors()

    def _refresh_colors(self):
        """Reapplique les couleurs sur tous les widgets."""
        self.config(bg=self.theme["sidebar_bg"])
        self.logo_frame.config(bg=self.theme["sidebar_bg"])
        self.logo_label.config(
            bg=self.theme["sidebar_bg"], fg=self.theme["btn_send_bg"])
        self.new_task_frame.config(bg=self.theme["sidebar_bg"])
        # ttk Buttons may not accept bg/fg; try and fallback to bootstyle
        try:
            self.new_task_btn.config(
                bg=self.theme["btn_new_task_bg"], fg=self.theme["btn_new_task_fg"])
        except Exception:
            try:
                self.new_task_btn.configure(bootstyle="primary")
            except Exception:
                pass
        self.search_frame.config(bg=self.theme["btn_search_bg"])
        self.search_icon_label.config(bg=self.theme["btn_search_bg"])
        self.search_entry.config(
            bg=self.theme["btn_search_bg"], fg=self.theme["fg_sidebar"])
        self.recents_label.config(
            bg=self.theme["sidebar_bg"], fg=self.theme["fg_muted"])
        self.recents_frame.config(bg=self.theme["sidebar_bg"])
        self.bottom_frame.config(bg=self.theme["sidebar_bg"])
        try:
            self.upgrade_btn.config(
                bg=self.theme["btn_search_bg"], fg=self.theme["fg_sidebar"])
        except Exception:
            try:
                self.upgrade_btn.configure(bootstyle="outline-secondary")
            except Exception:
                pass
        try:
            self.settings_btn.config(
                bg=self.theme["sidebar_bg"], fg=self.theme["fg_sidebar"])
        except Exception:
            try:
                self.settings_btn.configure(bootstyle="secondary")
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  ÉVÉNEMENTS                                                          #
    # ------------------------------------------------------------------ #

    def _on_search_focus_in(self, event):
        if self.search_entry.get() == "Rechercher":
            self.search_entry.delete(0, tk.END)

    def _on_search_focus_out(self, event):
        if not self.search_entry.get():
            self.search_entry.insert(0, "Rechercher")

    def _on_search_keyrelease(self, event):
        if self._on_search:
            self._on_search(self.search_entry.get())
