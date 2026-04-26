from django.test import SimpleTestCase
from rest_framework.exceptions import ParseError

from smart_agri.core.permissions import resolve_request_farm_id


class _UnreadableBodyRequest:
    parser_context = {}
    query_params = {}
    headers = {"X-Farm-Id": "17"}
    resolved_farm_id = None
    farm_scope_hint = None

    @property
    def data(self):
        raise ParseError("malformed request body")


class ResolveRequestFarmIdRegressionTests(SimpleTestCase):
    def test_unreadable_mutating_body_falls_back_to_headers(self):
        request = _UnreadableBodyRequest()

        self.assertEqual(resolve_request_farm_id(request), 17)
