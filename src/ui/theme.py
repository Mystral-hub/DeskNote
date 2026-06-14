# src/ui/theme.py

# ------------------------------------------------------------------ #
#  DIMENSIONS                                                          #
# ------------------------------------------------------------------ #

SIDEBAR_WIDTH_FULL = 200
SIDEBAR_WIDTH_REDUCED = 60

WIN_FULL_MIN_W = 900
WIN_FULL_MIN_H = 600
WIN_REDUCED_MAX_W = 400
WIN_REDUCED_MIN_H = 400
# largeur minimale du panneau 'Connecter vos applications'
APPS_PANEL_MIN_W = 100
APPS_PANEL_REDUCED_MIN_W = 80


#  POLICES                                                             #


FONT_MAIN = "Segoe UI"
FONT_TITLE = "Segoe UI Semibold"

FONT_SIZE_SM = 11
FONT_SIZE_MD = 13
FONT_SIZE_LG = 15
FONT_SIZE_TITLE = 17


THEMES = {
    "light": {
        # --- arrière-plans ---
        "bg":                "#F6F6F6",
        "sidebar_bg":        "#132F2E",
        "input_bg":          "#FFFFFF",
        "apps_panel_bg":     "#FFFFFF",

        # --- textes ---
        "fg":                "#231F20",
        "fg_sidebar":        "#FFFFFF",
        "fg_muted":          "#888888",
        "insertbackground":  "#231F20",

        # --- bulles de conversation ---
        "bulle_user_bg":     "#1B4742",
        "bulle_user_fg":     "#F5EDEF",
        "bulle_agent_bg":    "#FFFFFF",
        "bulle_agent_fg":    "#231F20",

        # --- boutons ---
        "btn_send_bg":       "#10B981",
        "btn_send_fg":       "#FFFFFF",
        "btn_search_bg":     "#1B4742",
        "btn_search_fg":     "#FFFFFF",
        "btn_new_task_bg":   "#FFFFFF",
        "btn_new_task_fg":   "#231F20",

        # --- bordures ---
        "border":            "#E0E0E0",
        "border_input":      "#CCCCCC",

        # --- suggestions ---
        "suggestion_bg":     "#FFFFFF",
        "suggestion_fg":     "#231F20",
        "suggestion_border": "#E0E0E0",

        # --- processing ---
        "processing_bg":     "#F0F0F0",
        "processing_fg":     "#888888",

        # --- récents sidebar ---
        "recent_fg":         "#CCCCCC",
        "recent_hover_bg":   "#1B4742",

        # --- ttkbootstrap ---
        "ttkbootstrap_theme": "flatly",

        # --- police ---
        "font": (FONT_MAIN, FONT_SIZE_MD),
    },

    "dark": {
        # --- arrière-plans ---
        "bg":                "#1A1A1A",
        "sidebar_bg":        "#0A1F1E",
        "input_bg":          "#2A2A2A",
        "apps_panel_bg":     "#242424",

        # --- textes ---
        "fg":                "#F0F0F0",
        "fg_sidebar":        "#FFFFFF",
        "fg_muted":          "#888888",
        "insertbackground":  "#F0F0F0",

        # --- bulles de conversation ---
        "bulle_user_bg":     "#2E2E2E",
        "bulle_user_fg":     "#F0F0F0",
        "bulle_agent_bg":    "#242424",
        "bulle_agent_fg":    "#F0F0F0",

        # --- boutons ---
        "btn_send_bg":       "#10B981",
        "btn_send_fg":       "#FFFFFF",
        "btn_search_bg":     "#1B4742",
        "btn_search_fg":     "#FFFFFF",
        "btn_new_task_bg":   "#2A2A2A",
        "btn_new_task_fg":   "#F0F0F0",

        # --- bordures ---
        "border":            "#333333",
        "border_input":      "#444444",

        # --- suggestions ---
        "suggestion_bg":     "#2A2A2A",
        "suggestion_fg":     "#F0F0F0",
        "suggestion_border": "#444444",

        # --- processing ---
        "processing_bg":     "#2E2E2E",
        "processing_fg":     "#888888",

        # --- récents sidebar ---
        "recent_fg":         "#AAAAAA",
        "recent_hover_bg":   "#1B4742",

        # --- ttkbootstrap ---
        "ttkbootstrap_theme": "darkly",

        # --- police ---
        "font": (FONT_MAIN, FONT_SIZE_MD),
    }
}


def get_theme(nom: str) -> dict:
    """Retourne le dictionnaire de thème par son nom."""
    return THEMES.get(nom, THEMES["light"])
