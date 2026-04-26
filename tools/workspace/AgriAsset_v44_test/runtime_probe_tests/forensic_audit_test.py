import os
import json
from django.test import TransactionTestCase
from django.core.files.storage import default_storage
from django.conf import settings

class ForensicAuditTest(TransactionTestCase):
	def setUp(self):
		self.base_path = os.path.join(settings.BASE_DIR, 'runtime_probe_data')
		self.file_name = 'forensic_data.json'
		self.file_path = os.path.join(self.base_path, self.file_name)

	def test_forensic_audit_match(self):
		default_storage.save(self.file_path, None)
		with open(self.file_path) as file:
			user_docs = json.load(file)
			for user, doc in user_docs.items():
				self.assertEqual(user, doc['user'])
				self.assertEqual(doc['file'], doc['filename'])
