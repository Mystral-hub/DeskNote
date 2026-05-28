import sqlite3
import json
from pathlib import Path
from datetime import datetime


DB_PATH = Path(__file__).parent.parent / "data" / "desknote.db"


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
