import tkinter as tk
import ttkbootstrap as ttk
from PIL import Image, ImageTk
from pathlib import Path
from settings import load_settings, save_settings


BASE_DIR = Path(__file__).parent.parent.parent
ICONS_DIR = BASE_DIR / "assets" / "icons"


class DeskNoteApp:

    def __init__(self):

        self.themes = {
            "light": {
                "bg": "#faf5ff",
                "sidebar_bg": "#f38545",
                "fg": "black",
                "ttkbootstrap_theme": "flatly",
                "font": ("Segoe UI", 9)
            },
            "dark": {
                "bg": "#2b2b2b",
                "sidebar_bg": "#1e1e1e",
                "fg": "white",
                "ttkbootstrap_theme": "darkly",
                "font": ("Segoe UI", 9)
            }
        }

        self.current_theme = "light"

        self.root = tk.Tk()
        self.root.title("DesK Note")
        self.root.geometry("400x500")

        self.style = ttk.Style(
            theme=self.themes[self.current_theme]["ttkbootstrap_theme"])

        self.root.grid_columnconfigure(0, weight=0)   # colonne sidebar
        self.root.grid_columnconfigure(1, weight=1)   # colonne contenu
        self.root.grid_rowconfigure(0, weight=1)      # ligne Canvas
        self.root.grid_rowconfigure(1, weight=0)      # ligne barre de saisie

        # Sidebar
        self.sidebar = tk.Frame(self.root, width=50)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="ns")
        self.sidebar.grid_propagate(False)

        # load settings
        self.settings = self._load_settings()
        self.sound_clicks_var = tk.BooleanVar(
            value=self.settings.get("sound_clicks", True))

        # sound toggle in sidebar
        self._sound_chk = tk.Checkbutton(
            self.sidebar,
            text="Sons de frappe",
            variable=self.sound_clicks_var,
            onvalue=True,
            offvalue=False,
            bg=self.themes[self.current_theme]["sidebar_bg"],
            fg=self.themes[self.current_theme]["fg"],
            command=self._on_sound_toggle
        )
        self._sound_chk.pack(padx=6, pady=6)

        # Canvas
        self.history_canvas = tk.Canvas(self.root, highlightthickness=0)
        self.history_canvas.grid(row=0, column=1, sticky="nsew")

        # zone de saisie
        self.input_area = tk.Frame(self.root)
        self.input_area.grid(row=1, column=1, sticky="nsew", padx=5)
        self.input_area.grid_rowconfigure(0, weight=1)
        self.input_area.grid_rowconfigure(1, weight=0)
        self.input_area.grid_columnconfigure(0, weight=1)

        # zone de boutons
        self.buttons_area = tk.Frame(self.input_area)
        self.buttons_area.grid(row=1, column=0, sticky="ew", pady=8)

        # importing buttons icons
        send_image = Image.open(ICONS_DIR / "send.png").resize((20, 20))
        self.send_icon = ImageTk.PhotoImage(send_image)

        # boutons
        self.send_button = tk.Button(
            self.buttons_area,
            image=self.send_icon,
            bg=self.themes[self.current_theme]["sidebar_bg"],
            activebackground="#ffffff",
            bd=0,
            highlightthickness=0,
            cursor="hand2"
        )
        self.send_button.pack(side="right", padx=5, pady=5)

        # champ de saisie
        self.input_text = tk.Text(
            self.input_area,
            height=3,
            wrap=tk.WORD,
            font=self.themes[self.current_theme]["font"],
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["fg"],
            insertbackground=self.themes[self.current_theme]["fg"]
        )
        self.input_text.grid(row=0, column=0, sticky="ew",  pady=5)

        self.root.update()
        # self.input_area.config(
        #     bg=self.themes[self.current_theme]["sidebar_bg"])
        self.send_button.config(
            bg="#ffffff")
        self.sidebar.config(bg=self.themes[self.current_theme]["sidebar_bg"])
        self.history_canvas.config(bg=self.themes[self.current_theme]["bg"])
        self.root.configure(bg=self.themes[self.current_theme]["bg"])

    def _load_settings(self) -> dict:
        return load_settings()

    def _save_settings(self):
        try:
            save_settings(self.settings)
        except Exception:
            pass

    def _on_sound_toggle(self):
        self.settings["sound_clicks"] = bool(self.sound_clicks_var.get())
        self._save_settings()

    def get_sound_clicks(self) -> bool:
        """Return current sound_clicks UI preference."""
        return bool(self.sound_clicks_var.get())


if __name__ == "__main__":
    app = DeskNoteApp()
    app.root.mainloop()
