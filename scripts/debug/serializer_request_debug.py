"""Serializer/endpoint debug helper (dev-only).

This script was previously checked-in as a root-level test_*.py which broke Django test discovery.
It is now a manual debug tool.

Usage:
  python scripts/debug/serializer_request_debug.py

Requires:
- A configured DB with seed data
- A superuser exists
"""

from __future__ import annotations

import os
import sys
import json
import traceback
from pathlib import Path

import django

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.append(str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

from smart_agri.core.models import DailyLog, Task  # noqa: E402
from smart_agri.core.api.activities import ActivityViewSet  # noqa: E402


def main() -> int:
    User = get_user_model()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("No superuser found. Create one first (manage.py createsuperuser).")
        return 1

    log = DailyLog.objects.order_by("-id").first()
    task = Task.objects.filter(is_harvest_task=True).first()
    if not log or not task:
        print("Missing DailyLog or harvest Task in DB. Seed data first.")
        return 1

    payload = {
        "log": log.id,
        "task": task.id,
        "activity_type": "Harvest",
        "harvest_quantity": 200,
        "batch_number": "50 Bags",
        "surrah_count": 1,
    }

    factory = APIRequestFactory()
    request = factory.post("/api/activities/", data=payload, format="json")
    force_authenticate(request, user=admin_user)

    view = ActivityViewSet.as_view({"post": "create"})
    try:
        response = view(request)
        result = {"status_code": response.status_code, "data": getattr(response, "data", None)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if 200 <= response.status_code < 500 else 2
    except Exception:
        print("CRASHED!")
        print(traceback.format_exc())
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
