import os
import django
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model

factory = APIRequestFactory()
# Switch to non-superuser!
user = get_user_model().objects.filter(is_superuser=False, username='evidence_manager').first()
if getattr(user, 'is_superuser', False):
    print("User is a superuser, this defeats the test.")

if not user:
    print("No standard user found.")
    sys.exit()

print("Testing with user:", user.username)

request = factory.get('/api/v1/finance/ledger/?farm=31')
force_authenticate(request, user=user)

from smart_agri.core.middleware.route_breach_middleware import RouteBreachAuditMiddleware
from django.http import HttpResponse

def dummy_get_response(req):
    return HttpResponse("SUCCESS_BYPASS", status=200)

middleware = RouteBreachAuditMiddleware(dummy_get_response)

try:
    resp = middleware(request)
    print("STATUS:", resp.status_code)
    try:
        print("DATA:", getattr(resp, 'data', resp.content.decode()))
    except:
        pass
except Exception as e:
    traceback.print_exc()
