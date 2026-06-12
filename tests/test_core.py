"""
Test suite for DeskNote core components.
Tests utilities, database, and planner without requiring LLM or Windows-specific dependencies.
"""

from database import Database
from prompts import SYSTEM_PROMPT
from utils import (
    resoudre_chemin,
    nettoyer_valeur,
    nettoyer_nom_fichier,
    rechercher_fichier,
    formater_resultats_recherche
)
import pytest
import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import tempfile
import shutil

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ============================================================================
# UTILS TESTS
# ============================================================================

class TestUtilsResolve:
    """Test path resolution in utils.py"""

    def test_resoudre_chemin_known_folder(self):
        """Test resolving known folder names"""
        result = resoudre_chemin("documents")
        assert result is not None
        assert result == Path.home() / "Documents"

    def test_resoudre_chemin_case_insensitive(self):
        """Test case-insensitive folder resolution"""
        result1 = resoudre_chemin("documents")
        result2 = resoudre_chemin("DOCUMENTS")
        result3 = resoudre_chemin("Documents")
        assert result1 == result2 == result3

    def test_resoudre_chemin_none(self):
        """Test resolving None returns None"""
        result = resoudre_chemin(None)
        assert result is None

    def test_resoudre_chemin_invalid(self):
        """Test resolving invalid/unknown folder returns None"""
        result = resoudre_chemin("dossier_inexistant_xyz")
        assert result is None

    def test_resoudre_chemin_all_known(self):
        """Test all known folders resolve correctly"""
        folders = [
            ("documents", Path.home() / "Documents"),
            ("bureau", Path.home() / "Desktop"),
            ("images", Path.home() / "Pictures"),
            ("telechargements", Path.home() / "Downloads"),
            ("musique", Path.home() / "Music"),
            ("videos", Path.home() / "Videos"),
        ]
        for name, expected in folders:
            result = resoudre_chemin(name)
            assert result == expected, f"Failed for {name}"


class TestUtilsCleaning:
    """Test value and filename cleaning"""

    def test_nettoyer_valeur_none(self):
        """Test cleaning None returns None"""
        assert nettoyer_valeur(None) is None

    def test_nettoyer_valeur_null_string(self):
        """Test cleaning 'null' string returns None"""
        assert nettoyer_valeur("null") is None

    def test_nettoyer_valeur_empty(self):
        """Test cleaning empty string returns None"""
        assert nettoyer_valeur("") is None

    def test_nettoyer_valeur_whitespace(self):
        """Test cleaning strips whitespace"""
        result = nettoyer_valeur("  hello world  ")
        assert result == "hello world"

    def test_nettoyer_nom_fichier_invalid_chars(self):
        """Test filename cleaning removes Windows forbidden chars"""
        bad_name = 'file<name>:with"forbidden|chars?.txt'
        result = nettoyer_nom_fichier(bad_name)
        assert result == "filenamewithforbiddenchars.txt"

    def test_nettoyer_nom_fichier_none(self):
        """Test cleaning None filename returns None"""
        assert nettoyer_nom_fichier(None) is None

    def test_nettoyer_nom_fichier_valid(self):
        """Test cleaning valid filename"""
        result = nettoyer_nom_fichier("  document.txt  ")
        assert result == "document.txt"


class TestUtilsSearch:
    """Test file search utilities"""

    def test_formater_resultats_recherche_empty(self):
        """Test formatting empty search results"""
        result = formater_resultats_recherche([])
        assert "Aucun fichier trouvé" in result

    def test_formater_resultats_recherche_multiple(self):
        """Test formatting multiple search results"""
        results = [Path("C:/Users/test/Downloads/file1.txt"),
                   Path("C:/Users/test/Documents/file2.txt")]
        formatted = formater_resultats_recherche(results)
        assert "Plusieurs fichiers" in formatted or "plusieurs" in formatted.lower()
        assert "file1.txt" in formatted
        assert "file2.txt" in formatted


# ============================================================================
# PROMPTS TESTS
# ============================================================================

class TestPrompts:
    """Test prompt configuration"""

    def test_system_prompt_exists(self):
        """Test that SYSTEM_PROMPT is defined"""
        assert SYSTEM_PROMPT is not None
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0

    def test_system_prompt_has_rules(self):
        """Test system prompt contains important rules"""
        assert "RÈGLES STRICTES" in SYSTEM_PROMPT
        assert "JSON" in SYSTEM_PROMPT

    def test_system_prompt_has_actions(self):
        """Test system prompt defines all expected actions"""
        actions = [
            "ouvrir_app",
            "supprimer_fichier",
            "creer_fichier_texte",
            "lire_document",
            "recherche_en_ligne",
            "organiser_fichiers",
            "changer_fond_ecran",
            "lancer_media",
            "rechercher_fichier",
            "incompris",
            "creer_facture",
            "live_typing",
        ]
        for action in actions:
            assert action in SYSTEM_PROMPT, f"Action {action} not in prompt"

    def test_system_prompt_has_examples(self):
        """Test system prompt contains examples"""
        assert "utilisateur:" in SYSTEM_PROMPT
        assert "ouvre notepad" in SYSTEM_PROMPT


# ============================================================================
# DATABASE TESTS
# ============================================================================

class TestDatabase:
    """Test database functionality"""

    @pytest.fixture
    def temp_db_dir(self):
        """Create temporary directory for test database"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_db_path(self, temp_db_dir, monkeypatch):
        """Mock database path to use temporary directory"""
        test_db_path = Path(temp_db_dir) / "test.db"
        with patch('database.DB_PATH', test_db_path):
            yield test_db_path

    def test_database_init_creates_tables(self, mock_db_path):
        """Test database initialization creates required tables"""
        db = Database()

        # Verify tables exist
        cursor = db.cursor
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='historique_conversations'"
        )
        assert cursor.fetchone() is not None

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='logs_actions'"
        )
        assert cursor.fetchone() is not None

        db.fermer()

    def test_sauvegarder_message(self, mock_db_path):
        """Test saving conversation messages"""
        db = Database()

        db.sauvegarder_message(
            role="utilisateur",
            message="ouvre notepad",
            action="ouvrir_app",
            json_complet={"action": "ouvrir_app"},
            statut="succes"
        )

        # Verify message was saved
        historique = db.recuperer_historique()
        assert len(historique) > 0
        last = historique[-1]
        assert last["role"] == "utilisateur"
        assert last["message"] == "ouvre notepad"
        assert last["action"] == "ouvrir_app"

        db.fermer()

    def test_sauvegarder_log(self, mock_db_path):
        """Test saving action logs"""
        db = Database()

        db.sauvegarder_log(
            action="ouvrir_app",
            parametres={"nom_app": "notepad"},
            statut="succes",
            message_erreur=None
        )

        # Verify log was saved
        cursor = db.cursor
        cursor.execute("SELECT * FROM logs_actions ORDER BY id DESC LIMIT 1")
        log = cursor.fetchone()
        assert log is not None
        assert log["action"] == "ouvrir_app"
        assert log["statut"] == "succes"

        db.fermer()

    def test_recuperer_historique(self, mock_db_path):
        """Test retrieving conversation history"""
        db = Database()

        # Add multiple messages
        for i in range(5):
            db.sauvegarder_message(
                role="utilisateur" if i % 2 == 0 else "agent",
                message=f"message {i}",
                action="test",
                statut="succes"
            )

        historique = db.recuperer_historique()
        assert len(historique) == 5

        # Verify order (oldest first)
        assert historique[0]["message"] == "message 0"
        assert historique[-1]["message"] == "message 4"

        db.fermer()

    def test_recuperer_historique_limit(self, mock_db_path):
        """Test history limit parameter"""
        db = Database()

        # Add 20 messages
        for i in range(20):
            db.sauvegarder_message(
                role="utilisateur",
                message=f"message {i}",
                statut="succes"
            )

        historique = db.recuperer_historique(limite=10)
        assert len(historique) == 10

        db.fermer()


# ============================================================================
# PLANNER TESTS (mock-based)
# ============================================================================

class TestPlannerValidation:
    """Test Planner JSON validation logic without LLM"""

    def test_json_valid_action(self):
        """Test valid JSON with action field"""
        json_brut = '{"action": "ouvrir_app", "parametres": {}}'
        result = json.loads(json_brut)
        assert "action" in result
        assert result["action"] == "ouvrir_app"

    def test_json_missing_action(self):
        """Test JSON without action field should be handled"""
        json_brut = '{"parametres": {}}'
        result = json.loads(json_brut)
        assert "action" not in result  # Should be caught by validator

    def test_prompt_extraction_examples(self):
        """Test that prompt examples are valid JSON"""
        # Extract example JSONs from prompt
        import re
        examples = re.findall(r'\{"action"[^}]+\}', SYSTEM_PROMPT)

        # At least should have some examples
        assert len(examples) > 0

        # Each should be valid JSON
        for ex in examples[:5]:  # Test first 5
            try:
                parsed = json.loads(ex)
                assert "action" in parsed
                assert "parametres" in parsed
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in prompt example: {ex}\n{e}")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration-level tests"""

    def test_utils_and_database_together(self, monkeypatch):
        """Test utils and database working together"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_db = Path(tmpdir) / "test.db"
            with patch('database.DB_PATH', test_db):
                db = Database()

                # Resolve a path and save it in db
                doc_path = resoudre_chemin("documents")

                db.sauvegarder_message(
                    role="utilisateur",
                    message="organize documents",
                    parametres={"repertoire_cible": "documents"}
                )

                # Verify it was saved
                hist = db.recuperer_historique()
                assert len(hist) > 0

                db.fermer()

    def test_json_schema_completeness(self):
        """Test that all action schemas in prompt are complete"""
        # Extract all action definitions from prompt
        import re

        # Find all action blocks
        actions = re.findall(r'"action":\s*"([^"]+)"', SYSTEM_PROMPT)
        unique_actions = set(actions)

        # All should have parametres
        assert len(unique_actions) > 0

        # Verify key actions are present
        expected = {
            "ouvrir_app", "supprimer_fichier", "creer_fichier_texte",
            "lire_document", "recherche_en_ligne", "organiser_fichiers",
            "changer_fond_ecran", "lancer_media", "rechercher_fichier",
            "incompris", "creer_facture", "live_typing"
        }
        assert expected.issubset(unique_actions)


# ============================================================================
# SMOKE TESTS
# ============================================================================

class TestSmoke:
    """Smoke tests - verify basic imports and module structure"""

    def test_can_import_main_modules(self):
        """Test that all main modules can be imported"""
        try:
            import src.utils
            import src.prompts
            import src.database
        except ImportError as e:
            pytest.fail(f"Failed to import module: {e}")

    def test_main_py_structure(self):
        """Test main.py has required functions"""
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        from main import traiter_message, main

        # Functions should be callable
        assert callable(traiter_message)
        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
