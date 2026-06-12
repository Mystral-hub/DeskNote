"""Module `social.facebook` — publication Facebook via Playwright.

Architecture notes:
- Uses Playwright sync API to automate login and posting on a personal profile.
- Credentials: username stored in `config/facebook_config.json`, password stored in system keyring when use_keyring=true.
- Cookies persisted to `data/facebook_cookies.json` to avoid repeated logins.
- Provides: `post_now(media_path, caption, privacy)` and `schedule_post(db, media_path, caption, when)`.
- Simple scheduler `run_scheduler(db)` to be executed in a background thread by the app.

This file is intentionally modular and independent.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import keyring
except Exception:
    keyring = None

from playwright.sync_api import sync_playwright

from utils import resoudre_chemin

CONFIG_PATH = Path(__file__).parent.parent.parent / \
    "config" / "facebook_config.json"
COOKIES_DEFAULT = Path(__file__).parent.parent.parent / \
    "data" / "facebook_cookies.json"


def _load_config():
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _get_password(username: str) -> Optional[str]:
    try:
        if keyring is None:
            return None
        return keyring.get_password("desknote_facebook", username)
    except Exception:
        return None


def _save_cookies(cookies, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cookies, ensure_ascii=False), encoding="utf-8")


def _load_cookies(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _is_media_allowed(media_path: Path, max_mb: int) -> bool:
    try:
        if not media_path.exists():
            return False
        size_mb = media_path.stat().st_size / (1024 * 1024)
        return size_mb <= max_mb
    except Exception:
        return False


def post_now(media_path: str, caption: str, privacy: str = "public") -> dict:
    """Publie immédiatement une image/vidéo sur le profil Facebook.

    Returns dict with statut, message, details.
    """
    cfg = _load_config()
    username = cfg.get("username")
    use_keyring = cfg.get("use_keyring", True)
    cookies_path = Path(cfg.get("cookies_path", str(COOKIES_DEFAULT)))
    max_mb = cfg.get("max_media_mb", 20)
    headless = cfg.get("headless", False)

    if not username:
        return {"statut": "echec", "message": "Nom d'utilisateur Facebook non configuré."}

    pwd = _get_password(username) if use_keyring else None
    if use_keyring and not pwd:
        return {"statut": "echec", "message": "Mot de passe non trouvé dans le keyring pour cet utilisateur."}

    path = resoudre_chemin(media_path)
    if path is None:
        return {"statut": "echec", "message": f"Média introuvable: {media_path}"}

    if not _is_media_allowed(path, max_mb):
        return {"statut": "echec", "message": f"Média trop volumineux (> {max_mb} MB) ou introuvable."}

    # Automatisation Playwright
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False) if not headless else p.chromium.launch()
            context = browser.new_context()

            # Try restore cookies
            cookies = _load_cookies(cookies_path)
            if cookies:
                try:
                    context.add_cookies(cookies)
                except Exception:
                    pass

            page = context.new_page()

            # Go to Facebook and ensure logged in (simple heuristics)
            page.goto("https://www.facebook.com/")
            time.sleep(2)

            if "login" in page.url or page.query_selector("input[name='email']"):
                # need to login
                if not pwd:
                    browser.close()
                    return {"statut": "echec", "message": "Login requis et mot de passe manquant."}
                page.fill("input[name='email']", username)
                page.fill("input[name='pass']", pwd)
                page.click("button[name='login']")
                time.sleep(5)

            # Save cookies
            try:
                _save_cookies(context.cookies(), cookies_path)
            except Exception:
                pass

            # Navigate to create post UI
            # Facebook markup changes frequently; attempt robust selectors
            # Click on "Create post" area
            try:
                # open composer
                page.click("[aria-label='Create a post']", timeout=4000)
            except Exception:
                try:
                    page.click("div[aria-label='Create a post']", timeout=4000)
                except Exception:
                    # fallback: focus on composer via role
                    pass

            time.sleep(1)

            # Insert caption
            try:
                # find editable content
                editor = page.query_selector("div[role='textbox']")
                if editor:
                    editor.click()
                    editor.fill(caption or "")
                else:
                    page.keyboard.type(caption or "")
            except Exception:
                pass

            # Attach media
            try:
                # file input
                file_input = page.query_selector("input[type='file']")
                if file_input:
                    file_input.set_input_files(str(path))
                else:
                    # try common button paths
                    page.locator("input[type=file]").set_input_files(str(path))
            except Exception:
                pass

            time.sleep(2)

            # Click Post
            try:
                # try button with text 'Post'
                page.click("div[aria-label='Post']")
            except Exception:
                try:
                    page.click("button:has-text('Post')")
                except Exception:
                    # best-effort: press Enter to submit
                    page.keyboard.press('Enter')

            time.sleep(3)

            browser.close()

            return {"statut": "succes", "message": "Publication postée (tentative)."}

    except Exception as e:
        return {"statut": "echec", "message": f"Erreur Playwright: {e}"}


def schedule_post(db, media_path: str, caption: str, when: Optional[datetime] = None) -> dict:
    """Ajoute un post programmé en base. `when` en datetime locale. Si None => now."""
    when_ts = (when or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    db.sauvegarder_log("post_facebook_schedule", {
                       "media_path": media_path, "caption": caption, "when": when_ts})
    db.cursor.execute(
        "INSERT INTO scheduled_posts (service, media_path, caption, scheduled_for, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("facebook", media_path, caption, when_ts, "pending",
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    db.conn.commit()
    return {"statut": "succes", "message": "Post programmé.", "when": when_ts}


def run_scheduler(db, interval: int = 30):
    """Boucle bloquante à exécuter dans un thread séparé. Vérifie la table `scheduled_posts` every `interval` seconds."""
    while True:
        try:
            now = datetime.now()
            rows = db.cursor.execute(
                "SELECT id, media_path, caption, scheduled_for FROM scheduled_posts WHERE status = 'pending' ORDER BY scheduled_for ASC"
            ).fetchall()
            for row in rows:
                scheduled = datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S")
                if scheduled <= now:
                    # attempt post
                    res = post_now(row[1], row[2])
                    if res.get("statut") == "succes":
                        db.cursor.execute(
                            "UPDATE scheduled_posts SET status = 'done' WHERE id = ?", (row[0],))
                    else:
                        db.cursor.execute(
                            "UPDATE scheduled_posts SET status = 'failed' WHERE id = ?", (row[0],))
                    db.conn.commit()
        except Exception:
            pass
        time.sleep(interval)
