"""
Simple test suite for DeskNote - no heavy imports.
"""

from unittest.mock import patch
import shutil
import tempfile
import pytest
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ============================================================================
# UTILS TESTS - import locally in each test to avoid hanging
# ============================================================================

class TestUtilsResolve:
    """Test path resolution in utils.py"""

    def test_resoudre_chemin_known_folder(self):
        """Test resolving known folder names"""
        from utils import resoudre_chemin
        result = resoudre_chemin("documents")
        assert result is not None
        assert result == Path.home() / "Documents"

    def test_resoudre_chemin_case_insensitive(self):
        """Test case-insensitive folder resolution"""
        from utils import resoudre_chemin
        result1 = resoudre_chemin("documents")
        result2 = resoudre_chemin("DOCUMENTS")
        result3 = resoudre_chemin("Documents")
        assert result1 == result2 == result3

    def test_resoudre_chemin_none(self):
        """Test resolving None returns None"""
        from utils import resoudre_chemin
        result = resoudre_chemin(None)
        assert result is None

    def test_resoudre_chemin_invalid(self):
        """Test resolving invalid/unknown folder returns None"""
        from utils import resoudre_chemin
        result = resoudre_chemin("dossier_inexistant_xyz")
        assert result is None

    def test_resoudre_chemin_all_known(self):
        """Test all known folders resolve correctly"""
        from utils import resoudre_chemin
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
        from utils import nettoyer_valeur
        assert nettoyer_valeur(None) is None

    def test_nettoyer_valeur_null_string(self):
        """Test cleaning 'null' string returns None"""
        from utils import nettoyer_valeur
        assert nettoyer_valeur("null") is None

    def test_nettoyer_valeur_empty(self):
        """Test cleaning empty string returns None"""
        from utils import nettoyer_valeur
        assert nettoyer_valeur("") is None

    def test_nettoyer_valeur_whitespace(self):
        """Test cleaning strips whitespace"""
        from utils import nettoyer_valeur
        result = nettoyer_valeur("  hello world  ")
        assert result == "hello world"

    def test_nettoyer_nom_fichier_invalid_chars(self):
        """Test filename cleaning removes Windows forbidden chars"""
        from utils import nettoyer_nom_fichier
        bad_name = 'file<name>:with"forbidden|chars?.txt'
        result = nettoyer_nom_fichier(bad_name)
        assert result == "filenamewithforbiddenchars.txt"

    def test_nettoyer_nom_fichier_none(self):
        """Test cleaning None filename returns None"""
        from utils import nettoyer_nom_fichier
        assert nettoyer_nom_fichier(None) is None

    def test_nettoyer_nom_fichier_valid(self):
        """Test cleaning valid filename"""
        from utils import nettoyer_nom_fichier
        result = nettoyer_nom_fichier("  document.txt  ")
        assert result == "document.txt"


class TestUtilsSearch:
    """Test file search utilities"""

    def test_formater_resultats_recherche_empty(self):
        """Test formatting empty search results"""
        from utils import formater_resultats_recherche
        result = formater_resultats_recherche([])
        assert "Aucun fichier trouvé" in result

    def test_formater_resultats_recherche_multiple(self):
        """Test formatting multiple search results"""
        from utils import formater_resultats_recherche
        results = [Path("C:/Users/test/Downloads/file1.txt"),
                   Path("C:/Users/test/Documents/file2.txt")]
        formatted = formater_resultats_recherche(results)
        assert "file1.txt" in formatted
        assert "file2.txt" in formatted


# ============================================================================
# PROMPTS TESTS
# ============================================================================

class TestPrompts:
    """Test prompt configuration"""

    def test_system_prompt_exists(self):
        """Test that SYSTEM_PROMPT is defined"""
        from prompts import SYSTEM_PROMPT
        assert SYSTEM_PROMPT is not None
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0

    def test_system_prompt_has_rules(self):
        """Test system prompt contains important rules"""
        from prompts import SYSTEM_PROMPT
        assert "RÈGLES STRICTES" in SYSTEM_PROMPT
        assert "JSON" in SYSTEM_PROMPT

    def test_system_prompt_has_actions(self):
        """Test system prompt defines all expected actions"""
        from prompts import SYSTEM_PROMPT
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
        from prompts import SYSTEM_PROMPT
        assert "utilisateur:" in SYSTEM_PROMPT
        assert "ouvre notepad" in SYSTEM_PROMPT


# ============================================================================
# DATABASE TESTS
# ============================================================================


class TestDatabase:
    """Test database functionality"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        temp_dir = tempfile.mkdtemp()
        test_db_path = Path(temp_dir) / "test.db"

        with patch('database.DB_PATH', test_db_path):
            from database import Database
            db = Database()
            yield db
            db.fermer()

        shutil.rmtree(temp_dir)

    def test_database_init_creates_tables(self, temp_db):
        """Test database initialization creates required tables"""
        cursor = temp_db.cursor
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='historique_conversations'"
        )
        assert cursor.fetchone() is not None

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='logs_actions'"
        )
        assert cursor.fetchone() is not None

    def test_sauvegarder_message(self, temp_db):
        """Test saving conversation messages"""
        temp_db.sauvegarder_message(
            role="utilisateur",
            message="ouvre notepad",
            action="ouvrir_app",
            json_complet={"action": "ouvrir_app"},
            statut="succes"
        )

        historique = temp_db.recuperer_historique()
        assert len(historique) > 0
        last = historique[-1]
        assert last["role"] == "utilisateur"
        assert last["message"] == "ouvre notepad"
        assert last["action"] == "ouvrir_app"

    def test_sauvegarder_log(self, temp_db):
        """Test saving action logs"""
        temp_db.sauvegarder_log(
            action="ouvrir_app",
            parametres={"nom_app": "notepad"},
            statut="succes",
            message_erreur=None
        )

        cursor = temp_db.cursor
        cursor.execute("SELECT * FROM logs_actions ORDER BY id DESC LIMIT 1")
        log = cursor.fetchone()
        assert log is not None
        assert log["action"] == "ouvrir_app"
        assert log["statut"] == "succes"

    def test_recuperer_historique(self, temp_db):
        """Test retrieving conversation history"""
        for i in range(5):
            temp_db.sauvegarder_message(
                role="utilisateur" if i % 2 == 0 else "agent",
                message=f"message {i}",
                action="test",
                statut="succes"
            )

        historique = temp_db.recuperer_historique()
        assert len(historique) == 5
        assert historique[0]["message"] == "message 0"
        assert historique[-1]["message"] == "message 4"

    def test_recuperer_historique_limit(self, temp_db):
        """Test history limit parameter"""
        for i in range(20):
            temp_db.sauvegarder_message(
                role="utilisateur",
                message=f"message {i}",
                statut="succes"
            )

        historique = temp_db.recuperer_historique(limite=10)
        assert len(historique) == 10


# ============================================================================
# JSON & SCHEMA TESTS
# ============================================================================

class TestJSONSchema:
    """Test JSON schema completeness"""

    def test_prompt_examples_valid_json(self):
        """Test that prompt examples contain valid JSON"""
        from prompts import SYSTEM_PROMPT
        import re

        examples = re.findall(r'\{"action"[^}]+\}', SYSTEM_PROMPT)
        assert len(examples) > 0

        for ex in examples[:5]:
            try:
                parsed = json.loads(ex)
                assert "action" in parsed
                assert "parametres" in parsed
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in prompt: {ex}\n{e}")

    def test_all_actions_in_examples(self):
        """Test that key actions have examples in prompt"""
        from prompts import SYSTEM_PROMPT

        key_actions = ["ouvrir_app",
                       "supprimer_fichier", "creer_fichier_texte"]
        for action in key_actions:
            assert action in SYSTEM_PROMPT


# ============================================================================
# SMOKE TESTS
# ============================================================================

class TestSmoke:
    """Smoke tests - verify basic module structure"""

    def test_can_import_utils(self):
        """Test utils module import"""
        try:
            import utils
            assert hasattr(utils, 'resoudre_chemin')
            assert hasattr(utils, 'nettoyer_valeur')
            assert hasattr(utils, 'nettoyer_nom_fichier')
        except ImportError as e:
            pytest.fail(f"Failed to import utils: {e}")

    def test_can_import_prompts(self):
        """Test prompts module import"""
        try:
            import prompts
            assert hasattr(prompts, 'SYSTEM_PROMPT')
            assert len(prompts.SYSTEM_PROMPT) > 0
        except ImportError as e:
            pytest.fail(f"Failed to import prompts: {e}")

    def test_can_import_database(self):
        """Test database module import"""
        try:
            from database import Database
            assert callable(Database)
        except ImportError as e:
            pytest.fail(f"Failed to import database: {e}")

    def test_can_import_planner(self):
        """Test planner module can be imported (even without model)"""
        try:
            from planner import Planner
            assert callable(Planner)
        except ImportError as e:
            pytest.fail(f"Failed to import planner: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
