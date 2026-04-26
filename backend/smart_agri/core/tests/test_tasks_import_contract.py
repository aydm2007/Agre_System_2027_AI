import importlib

from django.test import SimpleTestCase


class TasksImportContractTests(SimpleTestCase):
    def test_report_tasks_module_is_importable(self):
        module = importlib.import_module("smart_agri.core.tasks.report_tasks")
        self.assertTrue(hasattr(module, "generate_advanced_report"))
