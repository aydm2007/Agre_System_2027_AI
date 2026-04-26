from django.test import SimpleTestCase

from smart_agri.finance.services.approval_state_transitions import append_history


class ApprovalStateTransitionTests(SimpleTestCase):
    def test_append_history_preserves_existing_entries_and_appends_stage(self):
        req = type('Req', (), {'approval_history': [{'stage': 0}], 'current_stage': 2})()
        user = type('User', (), {'id': 7, 'username': 'reviewer'})()

        history = append_history(req=req, user=user, decision='APPROVED', role='role-x', note='ok')

        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]['stage'], 2)
        self.assertEqual(history[-1]['actor_id'], 7)
        self.assertEqual(history[-1]['actor_username'], 'reviewer')
