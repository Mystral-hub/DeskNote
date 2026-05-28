import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SETTINGS_PATH = DATA_DIR / "settings.json"
DEFAULT_SETTINGS = {
    "sound_clicks": True
}


def load_settings() -> dict:
    """Charge les préférences utilisateur depuis un fichier JSON."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if SETTINGS_PATH.exists():
            with SETTINGS_PATH.open("r", encoding="utf-8") as f:
                settings = json.load(f)
                if isinstance(settings, dict):
                    return {**DEFAULT_SETTINGS, **settings}
    except Exception:
        pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    """Sauvegarde les préférences utilisateur dans un fichier JSON."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with SETTINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump({**DEFAULT_SETTINGS, **settings},
                      f, ensure_ascii=False, indent=2)
    except Exception:
        pass
