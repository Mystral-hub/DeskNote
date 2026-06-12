import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime


def _locate_db_path() -> Path:
    """Locate an existing `desknote.db` in common bundle/source locations.

    Search order (returns first hit):
    - source `../data/desknote.db` (when running from source)
    - PyInstaller `sys._MEIPASS/data/desknote.db`
    - executable parent `data/desknote.db`
    - executable parent `_internal/data/desknote.db` (observed in one-dir builds)

    If none found, create a `data/` directory next to the executable (when
    frozen) or in the repo root (when running from source) and return that
    path for a new DB.
    """
    source_path = Path(__file__).parent.parent / "data" / "desknote.db"
    if source_path.exists():
        return source_path

    if getattr(sys, "frozen", False):
        # PyInstaller temporary bundle dir
        if hasattr(sys, "_MEIPASS"):
            p = Path(sys._MEIPASS) / "data" / "desknote.db"
            if p.exists():
                return p

        exe_parent = Path(sys.executable).parent
        # common placement from --add-data: data/ -> ./data
        p = exe_parent / "data" / "desknote.db"
        if p.exists():
            return p

        # some PyInstaller one-dir layouts put data under _internal/data
        p = exe_parent / "_internal" / "data" / "desknote.db"
        if p.exists():
            return p

        # not found: choose exe_parent/data as writable location and ensure it exists
        target_dir = exe_parent / "data"
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / "desknote.db"

    # fallback for non-frozen runs: ensure source data dir exists
    source_dir = Path(__file__).parent.parent / "data"
    source_dir.mkdir(parents=True, exist_ok=True)
    return source_dir / "desknote.db"


DB_PATH = _locate_db_path()
print(f"Using database path: {DB_PATH}")


class Database:

    def __init__(self):
        # Allow access from multiple threads (Executor runs DB calls from worker threads)
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._creer_tables()
        print("Base de données connectée.")

    def _creer_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS historique_conversations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                date_heure      TEXT NOT NULL,
                role            TEXT NOT NULL,
                message         TEXT NOT NULL,
                action          TEXT,
                json_complet    TEXT,
                statut          TEXT
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs_actions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                date_heure      TEXT NOT NULL,
                action          TEXT NOT NULL,
                parametres      TEXT,
                statut          TEXT NOT NULL,
                message_erreur  TEXT
            )
        """)

        # Table pour les publications programmées sur les réseaux sociaux
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                service         TEXT NOT NULL,
                media_path      TEXT,
                caption         TEXT,
                scheduled_for   TEXT,
                status          TEXT DEFAULT 'pending',
                created_at      TEXT NOT NULL
            )
        """)

        self.conn.commit()

    def sauvegarder_message(self,
                            role: str,
                            message: str,
                            action: str = None,  # type: ignore
                            json_complet: dict = None,   # type: ignore
                            statut: str = None):  # type: ignore
        self.cursor.execute("""
            INSERT INTO historique_conversations
                (date_heure, role, message, action, json_complet, statut)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            role,
            message,
            action,
            json.dumps(
                json_complet, ensure_ascii=False) if json_complet else None,
            statut
        ))
        self.conn.commit()

    def sauvegarder_log(self,
                        action: str,
                        parametres: dict | None = None,
                        statut: str = "succes",
                        message_erreur: str | None = None):
        self.cursor.execute("""
            INSERT INTO logs_actions
                (date_heure, action, parametres, statut, message_erreur)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action,
            json.dumps(parametres, ensure_ascii=False) if parametres else None,
            statut,
            message_erreur
        ))
        self.conn.commit()

    def recuperer_historique(self, limite: int = 50) -> list:
        self.cursor.execute("""
            SELECT id, date_heure, role, message, action, statut
            FROM historique_conversations
            ORDER BY id DESC
            LIMIT ?
        """, (limite,))

        lignes = self.cursor.fetchall()
        return [dict(ligne) for ligne in reversed(lignes)]

    def fermer(self):
        self.conn.close()
