import os
from unittest.mock import patch

from django.test import SimpleTestCase

from smart_agri.settings import _effective_test_db_name


class TestEffectiveTestDbName(SimpleTestCase):
    def test_uses_stable_default_name_for_test_commands(self):
        with patch.dict(os.environ, {}, clear=False):
            with patch("smart_agri.settings.sys.argv", ["manage.py", "test"]):
                self.assertEqual(_effective_test_db_name("agriasset2026"), "agriasset2026_test")

    def test_allows_explicit_per_process_isolation(self):
        with patch.dict(os.environ, {"DB_TEST_ISOLATE_PER_PROCESS": "true"}, clear=False):
            with patch("smart_agri.settings.sys.argv", ["manage.py", "test"]):
                with patch("smart_agri.settings.os.getpid", return_value=4242):
                    self.assertEqual(_effective_test_db_name("agriasset2026"), "agriasset2026_test_4242")

    def test_honors_explicit_db_test_name_override(self):
        with patch.dict(os.environ, {"DB_TEST_NAME": "custom_test_db"}, clear=False):
            with patch("smart_agri.settings.sys.argv", ["manage.py", "test"]):
                self.assertEqual(_effective_test_db_name("agriasset2026"), "custom_test_db")
