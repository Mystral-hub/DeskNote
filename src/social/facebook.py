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

# For testing only: if you want to hardcode credentials directly, set them here.
# WARNING: do NOT commit real credentials to version control.
TEST_FACEBOOK_USERNAME: str = "MJ Mystral"
TEST_FACEBOOK_PASSWORD: str = "mystral0987"


def _try_attach_existing_edge(p):
    """Try to connect to an existing Edge instance started with --remote-debugging-port=9222.
    Returns a tuple (browser, context, page) or (None, None, None) on failure.
    """
    try:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    except Exception:
        return None, None, None

    try:
        # search for a page that looks like Facebook
        for context in browser.contexts:
            for page in context.pages:
                try:
                    url = page.url or ""
                except Exception:
                    url = ""
                try:
                    title = page.title().lower() if page.title() else ""
                except Exception:
                    title = ""
                if "facebook.com" in url or "facebook" in title:
                    return browser, context, page
    except Exception:
        pass

    try:
        browser.close()
    except Exception:
        pass
    return None, None, None


def _post_on_page(page, path: Path, caption: str) -> dict:
    """Perform post actions on an existing Playwright `page` object. Returns result dict."""
    try:
        try:
            if "facebook.com" not in (page.url or ""):
                page.goto("https://www.facebook.com/")
                time.sleep(2)
        except Exception:
            pass

        try:
            page.click("[aria-label='Create a post']", timeout=3000)
        except Exception:
            try:
                page.click("div[aria-label='Create a post']", timeout=3000)
            except Exception:
                pass

        time.sleep(1)

        try:
            editor = page.query_selector("div[role='textbox']")
            if editor:
                editor.click()
                try:
                    editor.fill(caption or "")
                except Exception:
                    page.keyboard.type(caption or "")
            else:
                page.keyboard.type(caption or "")
        except Exception:
            pass

        try:
            file_input = page.query_selector("input[type='file']")
            if file_input:
                file_input.set_input_files(str(path))
            else:
                page.locator("input[type=file]").set_input_files(str(path))
        except Exception:
            pass

        time.sleep(2)

        try:
            try:
                page.click("div[aria-label='Post']", timeout=8000)
            except Exception:
                try:
                    page.click("button:has-text('Post')", timeout=8000)
                except Exception:
                    try:
                        page.keyboard.press('Enter')
                    except Exception:
                        pass

            time.sleep(4)
        except Exception as e:
            return {"statut": "echec", "message": f"Erreur lors du clic Post: {e}"}

        return {"statut": "succes", "message": "Publication postée (attaching to existing Edge)."}

    except Exception as e:
        return {"statut": "echec", "message": f"Erreur interne lors du post sur page existante: {e}"}


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
        # must be a file and exist
        if not media_path.exists() or not media_path.is_file():
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
    # prefer hardcoded test values if provided (test only)
    username = TEST_FACEBOOK_USERNAME or cfg.get("username")
    use_keyring = cfg.get("use_keyring", True)
    cookies_path = Path(cfg.get("cookies_path", str(COOKIES_DEFAULT)))
    max_mb = cfg.get("max_media_mb", 20)
    headless = cfg.get("headless", False)

    if not username:
        return {"statut": "echec", "message": "Nom d'utilisateur Facebook non configuré."}

    # password precedence: TEST_FACEBOOK_PASSWORD -> keyring (if enabled) -> None
    if TEST_FACEBOOK_PASSWORD:
        pwd = TEST_FACEBOOK_PASSWORD
    else:
        pwd = _get_password(username) if use_keyring else None
    if not pwd and use_keyring:
        # if use_keyring requested but nothing found, warn the caller
        return {"statut": "echec", "message": "Mot de passe non trouvé (keyring vide) — définissez TEST_FACEBOOK_PASSWORD pour les tests ou configurez le keyring."}

    path = resoudre_chemin(media_path)
    if path is None:
        return {"statut": "echec", "message": f"Média introuvable: {media_path}"}

    if not _is_media_allowed(path, max_mb):
        return {"statut": "echec", "message": f"Média trop volumineux (> {max_mb} MB) ou introuvable."}

    # Automatisation Playwright
    try:
        with sync_playwright() as p:
            # First attempt: connect to an existing Edge started with remote debugging
            browser_att, context_att, page_att = _try_attach_existing_edge(p)
            if page_att is not None:
                # We attached to an existing browser; perform actions on that page.
                res = _post_on_page(page_att, path, caption)
                # Do not close the user's browser when attaching
                return res

            # Prefer using installed Microsoft Edge (msedge channel) to avoid
            # requiring Playwright-managed browser downloads. Fall back to
            # default Chromium launch if Edge channel isn't available.
            try:
                if not headless:
                    browser = p.chromium.launch(
                        channel="msedge", headless=False)
                else:
                    browser = p.chromium.launch(
                        channel="msedge", headless=True)
            except Exception:
                # fallback to standard launch (may require playwright browsers installed)
                browser = p.chromium.launch(
                    headless=False) if not headless else p.chromium.launch()
            # create a browser context before opening pages
            context = browser.new_context()
            page = context.new_page()

            # Go to Facebook and ensure logged in (simple heuristics)
            page.goto("https://www.facebook.com/")
            time.sleep(2)

            # Login if the page shows a login form
            if "login" in page.url or page.query_selector("input[name='email']"):
                if not pwd:
                    browser.close()
                    return {"statut": "echec", "message": "Login requis et mot de passe manquant."}
                page.fill("input[name='email']", username)
                page.fill("input[name='pass']", pwd)
                try:
                    page.click("button[name='login']", timeout=10000)
                except Exception:
                    try:
                        page.keyboard.press('Enter')
                    except Exception:
                        pass
                time.sleep(6)

            # verify login success: wait for composer element
            try:
                page.wait_for_selector(
                    "[aria-label='Create a post']", timeout=10000)
                logged_in = True
            except Exception:
                logged_in = False

            if not logged_in:
                # save debug artifacts
                try:
                    debug_dir = Path(
                        __file__).parent.parent.parent / "data" / "facebook_debug"
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = debug_dir / f"login_failed_{ts}.png"
                    html_path = debug_dir / f"login_failed_{ts}.html"
                    try:
                        page.screenshot(path=str(screenshot_path))
                    except Exception:
                        pass
                    try:
                        html = page.content()
                        html_path.write_text(html, encoding="utf-8")
                    except Exception:
                        pass
                except Exception:
                    pass

                browser.close()
                return {"statut": "echec", "message": "Login Facebook non confirmé. Debug artifacts saved.", "details": {"screenshot": str(screenshot_path) if 'screenshot_path' in locals() else None, "html": str(html_path) if 'html_path' in locals() else None}}

            # Save cookies
            try:
                _save_cookies(context.cookies(), cookies_path)
            except Exception:
                pass

            # Try to open composer (be tolerant with selectors)
            try:
                try:
                    page.click("[aria-label='Create a post']", timeout=4000)
                except Exception:
                    try:
                        page.click(
                            "div[aria-label='Create a post']", timeout=4000)
                    except Exception:
                        pass
            except Exception:
                pass

            time.sleep(1)

            # Insert caption
            try:
                editor = page.query_selector("div[role='textbox']")
                if editor:
                    editor.click()
                    try:
                        editor.fill(caption or "")
                    except Exception:
                        page.keyboard.type(caption or "")
                else:
                    page.keyboard.type(caption or "")
            except Exception:
                pass

            # Attach media
            try:
                file_input = page.query_selector("input[type='file']")
                if file_input:
                    file_input.set_input_files(str(path))
                else:
                    page.locator("input[type=file]").set_input_files(str(path))
            except Exception:
                try:
                    debug_dir = Path(
                        __file__).parent.parent.parent / "data" / "facebook_debug"
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ss = debug_dir / f"attach_failed_{ts}.png"
                    try:
                        page.screenshot(path=str(ss))
                    except Exception:
                        pass
                except Exception:
                    pass

            time.sleep(2)

            # Click Post (try multiple selectors)
            try:
                try:
                    page.click("div[aria-label='Post']", timeout=8000)
                except Exception:
                    try:
                        page.click("button:has-text('Post')", timeout=8000)
                    except Exception:
                        try:
                            page.keyboard.press('Enter')
                        except Exception:
                            pass

                time.sleep(4)

                try:
                    still_open = page.query_selector(
                        "[aria-label='Create a post']")
                    if still_open:
                        debug_dir = Path(
                            __file__).parent.parent.parent / "data" / "facebook_debug"
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        ss = debug_dir / f"post_maybe_failed_{ts}.png"
                        try:
                            page.screenshot(path=str(ss))
                        except Exception:
                            pass
                        browser.close()
                        return {"statut": "echec", "message": "La publication ne semble pas avoir réussi. Debug saved.", "details": {"screenshot": str(ss)}}
                except Exception:
                    pass

            except Exception as e:
                try:
                    debug_dir = Path(
                        __file__).parent.parent.parent / "data" / "facebook_debug"
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ss = debug_dir / f"post_error_{ts}.png"
                    try:
                        page.screenshot(path=str(ss))
                    except Exception:
                        pass
                except Exception:
                    pass
                browser.close()
                return {"statut": "echec", "message": f"Erreur lors de la tentative de publication: {e}", "details": {"screenshot": str(ss) if 'ss' in locals() else None}}

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
