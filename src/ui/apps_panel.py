# src/ui/apps_panel.py

import tkinter as tk
import shutil
from pathlib import Path
from PIL import Image, ImageTk
from .theme import get_theme, APPS_PANEL_MIN_W, APPS_PANEL_REDUCED_MIN_W


APPLICATIONS = [
    {
        "nom":      "Word",
        "icone":    "W",
        "couleur":  "#2B579A",
        "executables": ["winword", "winword.exe", "WINWORD.EXE"]
    },
    {
        "nom":      "Excel",
        "icone":    "X",
        "couleur":  "#217346",
        "executables": ["excel", "excel.exe", "EXCEL.EXE"]
    },
    {
        "nom":      "PowerPoint",
        "icone":    "P",
        "couleur":  "#D24726",
        "executables": ["powerpnt", "powerpnt.exe", "POWERPNT.EXE"]
    },
    {
        "nom":      "YouTube",
        "icone":    "YT",
        "couleur":  "#FF0000",
        "executables": []
    },
    {
        "nom":      "TikTok",
        "icone":    "TT",
        "couleur":  "#000000",
        "executables": []
    },
    {
        "nom":      "Facebook",
        "icone":    "f",
        "couleur":  "#1877F2",
        "executables": []
    },
    {
        "nom":      "Photoshop",
        "icone":    "Ps",
        "couleur":  "#31A8FF",
        "executables": ["photoshop", "photoshop.exe", "PHOTOSHOP.EXE"]
    },
]


class AppsPanel(tk.Frame):

    def __init__(self, parent, theme_nom: str = "light",
                 icones=None, on_connect=None, **kwargs):

        self.theme = get_theme(theme_nom)

        super().__init__(
            parent,
            bg=self.theme["apps_panel_bg"],
            **kwargs
        )
        # prevent the grid manager from forcing this frame to grow beyond our width
        try:
            self.config(width=APPS_PANEL_MIN_W)
            self.grid_propagate(False)
        except Exception:
            pass

        self._on_connect = on_connect
        # stocke un dict d'icônes si fourni (ne pas forward à tk.Frame)
        self._icons = icones or {}
        # stockage des PhotoImage pour éviter leur GC
        self._images = {}

        # dossier par défaut des icônes
        self._icons_dir = Path(
            __file__).parent.parent.parent / "assets" / "icons"
        self._statuts = {}

        self._build()
        self._verifier_toutes_apps()

    # ------------------------------------------------------------------ #
    #  CONSTRUCTION                                                        #
    # ------------------------------------------------------------------ #

    def _build(self):
        """Construit le panneau de connexion des applications."""
        self._build_titre()
        self._build_description()
        self._build_separateur()
        self._build_liste_apps()

    def _build_titre(self):
        """Titre du panneau."""
        self.titre_label = tk.Label(
            self,
            text="Connecter vos applications",
            bg=self.theme["apps_panel_bg"],
            fg=self.theme["fg"],
            font=("Segoe UI Semibold", 12),
            anchor="w"
        )
        self.titre_label.pack(fill="x", padx=16, pady=(16, 4))

        # Contrôle de largeur du panneau (scale) pour ajustement manuel
        try:
            self._width_frame = tk.Frame(self, bg=self.theme["apps_panel_bg"])
            self._width_frame.pack(fill="x", padx=16, pady=(0, 8))
            # étendue du slider : réduit -> double de la taille min par défaut
            max_w = APPS_PANEL_MIN_W * 2
            self._width_scale = tk.Scale(
                self._width_frame,
                from_=APPS_PANEL_REDUCED_MIN_W,
                to=max_w,
                orient="horizontal",
                showvalue=False,
                length=180,
                bg=self.theme["apps_panel_bg"],
                troughcolor=self.theme["border"],
                command=self._on_width_change
            )
            # valeur initiale = minsize actuelle de la colonne (si disponible)
            try:
                current = self.master.grid_columnconfigure(
                    2).get("minsize", APPS_PANEL_MIN_W)
            except Exception:
                current = APPS_PANEL_MIN_W
            self._width_scale.set(current)
            self._width_scale.pack(side="right")
        except Exception:
            pass

    def _build_description(self):
        """Description sous le titre."""
        self.desc_label = tk.Label(
            self,
            text="Connectez vos applications afin que\nDeskNote puisse y effectuer des tâches.",
            bg=self.theme["apps_panel_bg"],
            fg=self.theme["fg_muted"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left"
        )
        self.desc_label.pack(fill="x", padx=16, pady=(0, 8))

    def _build_separateur(self):
        """Ligne de séparation."""
        self.separateur = tk.Frame(
            self,
            bg=self.theme["border"],
            height=1
        )
        self.separateur.pack(fill="x", padx=16, pady=(0, 12))

    def _build_liste_apps(self):
        """Liste des applications connectables."""
        self.apps_frame = tk.Frame(self, bg=self.theme["apps_panel_bg"])
        self.apps_frame.pack(fill="x", padx=12)

        for app in APPLICATIONS:
            self._build_app_item(app)

    def _build_app_item(self, app: dict):
        """Construit une ligne pour une application."""
        ligne = tk.Frame(
            self.apps_frame,
            bg=self.theme["apps_panel_bg"],
            pady=4
        )
        ligne.pack(fill="x", pady=2)

        # icone: préférer une image si disponible, sinon affichage couleur+lettre
        nom_key = app["nom"].lower()
        pil_img = None
        # vérifier d'abord le dict self._icons (peut contenir Path/str)
        val = self._icons.get(nom_key)
        if val:
            try:
                p = Path(val)
                if p.exists():
                    pil_img = Image.open(p)
            except Exception:
                pil_img = None

        # fallback fichier par défaut (nom en minuscule + '-icon.png')
        if pil_img is None:
            default_path = self._icons_dir / f"{nom_key}-icon.png"
            if default_path.exists():
                try:
                    pil_img = Image.open(default_path)
                except Exception:
                    pil_img = None

        if pil_img is not None:
            try:
                img = pil_img.resize((36, 36))
                photo = ImageTk.PhotoImage(img)
                # garder référence
                self._images[nom_key] = photo
                icone_label = tk.Label(
                    ligne,
                    image=photo,
                    bg=self.theme["apps_panel_bg"]
                )
                icone_label.pack(side="left", padx=(4, 10))
            except Exception:
                pil_img = None

        if pil_img is None:
            icone_frame = tk.Frame(
                ligne,
                bg=app["couleur"],
                width=36,
                height=36
            )
            icone_frame.pack(side="left", padx=(4, 10))
            icone_frame.pack_propagate(False)

            tk.Label(
                icone_frame,
                text=app["icone"],
                bg=app["couleur"],
                fg="#FFFFFF",
                font=("Segoe UI Semibold", 14)
            ).place(relx=0.5, rely=0.5, anchor="center")

        # nom de l'application
        nom_label = tk.Label(
            ligne,
            text=app["nom"],
            bg=self.theme["apps_panel_bg"],
            fg=self.theme["fg"],
            font=("Segoe UI", 10),
            anchor="w"
        )
        nom_label.pack(side="left", fill="x", expand=True)

        # bouton +  /  ✓
        btn = tk.Button(
            ligne,
            text="+",
            bg=self.theme["apps_panel_bg"],
            fg=self.theme["fg_muted"],
            font=("Segoe UI", 14),
            bd=0,
            relief="flat",
            cursor="hand2",
            width=3,
            command=lambda a=app, b=None: self._on_btn_click(a, btn)
        )
        btn.pack(side="right", padx=4)

        # correction du command pour passer le bon btn
        btn.config(command=lambda a=app, b=btn: self._on_btn_click(a, b))

        # stocker la référence du bouton pour mise à jour
        self._statuts[app["nom"]] = {
            "btn":       btn,
            "connectee": False
        }

    # ------------------------------------------------------------------ #
    #  VÉRIFICATION DES APPLICATIONS                                       #
    # ------------------------------------------------------------------ #

    def _verifier_toutes_apps(self):
        """Vérifie si chaque application est installée sur le PC."""
        for app in APPLICATIONS:
            installee = self._verifier_app(app)
            self._mettre_a_jour_statut(app["nom"], installee)

    def _verifier_app(self, app: dict) -> bool:
        """
        Vérifie si une application est installée.
        Cherche dans le PATH et dans le registre Windows.
        """
        # chercher dans le PATH
        for exe in app["executables"]:
            if shutil.which(exe):
                return True

        # chercher dans le registre Windows
        try:
            import winreg
            base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
            for exe in app["executables"]:
                for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                    try:
                        with winreg.OpenKey(hive, f"{base}\\{exe}"):
                            return True
                    except Exception:
                        continue
        except Exception:
            pass

        # chercher dans les emplacements Office habituels
        from pathlib import Path
        emplacements_office = [
            Path("C:/Program Files/Microsoft Office/root/Office16"),
            Path("C:/Program Files (x86)/Microsoft Office/root/Office16"),
            Path("C:/Program Files/Microsoft Office/Office16"),
        ]
        for exe in app["executables"]:
            for dossier in emplacements_office:
                if (dossier / exe.upper()).exists():
                    return True

        return False

    def _mettre_a_jour_statut(self, nom_app: str, connectee: bool):
        """Met à jour l'affichage du bouton selon le statut."""
        if nom_app not in self._statuts:
            return

        entree = self._statuts[nom_app]
        entree["connectee"] = connectee

        if connectee:
            entree["btn"].config(
                text="✓",
                fg=self.theme["btn_send_bg"],
                cursor="arrow",
                state="disabled"
            )
        else:
            entree["btn"].config(
                text="+",
                fg=self.theme["fg_muted"],
                cursor="hand2",
                state="normal"
            )

    # ------------------------------------------------------------------ #
    #  ÉVÉNEMENTS                                                          #
    # ------------------------------------------------------------------ #

    def _on_btn_click(self, app: dict, btn: tk.Button):
        """
        Quand l'utilisateur clique sur + :
        vérifie si l'app est installée et met à jour le statut.
        """
        installee = self._verifier_app(app)

        if installee:
            self._mettre_a_jour_statut(app["nom"], True)
            if self._on_connect:
                self._on_connect(app["nom"], True)
        else:
            # afficher un message discret sous le bouton
            self._afficher_message_erreur(app["nom"])

    def _on_width_change(self, val):
        """Callback du slider de largeur: ajuste la minsize de la colonne 2."""
        try:
            w = int(float(val))
            root = self.master
            root.grid_columnconfigure(2, minsize=w)
        except Exception:
            pass

    def _afficher_message_erreur(self, nom_app: str):
        """Affiche un message si l'application n'est pas installée."""
        if not hasattr(self, "_erreur_label"):
            self._erreur_label = tk.Label(
                self,
                bg=self.theme["apps_panel_bg"],
                fg="#E53E3E",
                font=("Segoe UI", 8),
                anchor="w"
            )
            self._erreur_label.pack(fill="x", padx=16, pady=(4, 0))

        self._erreur_label.config(
            text=f"{nom_app} n'est pas installé sur ce PC."
        )
        # effacer le message après 3 secondes
        self._erreur_label.after(
            3000,
            lambda: self._erreur_label.config(text="")
        )

    # ------------------------------------------------------------------ #
    #  THÈME                                                               #
    # ------------------------------------------------------------------ #

    def appliquer_theme(self, theme_nom: str):
        """Met à jour toutes les couleurs selon le thème."""
        self.theme = get_theme(theme_nom)
        self.config(bg=self.theme["apps_panel_bg"])
        self.titre_label.config(
            bg=self.theme["apps_panel_bg"],
            fg=self.theme["fg"]
        )
        self.desc_label.config(
            bg=self.theme["apps_panel_bg"],
            fg=self.theme["fg_muted"]
        )
        self.separateur.config(bg=self.theme["border"])
        self.apps_frame.config(bg=self.theme["apps_panel_bg"])
