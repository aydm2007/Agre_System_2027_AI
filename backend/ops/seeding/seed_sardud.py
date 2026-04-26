#!/usr/bin/env python3
"""Seed script for Sardud demo data (dev-only).

Release hygiene:
- No hardcoded credentials.
- No local log files created by default.
- Uses env AGRIASSET_SEED_DEFAULT_PASSWORD when creating a superuser.
"""
from __future__ import annotations

import os
import sys
import traceback
import secrets

def _resolve_seed_password() -> str:
    pwd = (os.environ.get("AGRIASSET_SEED_DEFAULT_PASSWORD") or "").strip()
    if pwd:
        return pwd
    # Dev-only fallback: generate an ephemeral password and print it once.
    generated = secrets.token_urlsafe(18)
    print("⚠️  AGRIASSET_SEED_DEFAULT_PASSWORD not set; generated a one-time seed password.", file=sys.stderr)
    print(f"SEED_USER_PASSWORD={generated}", file=sys.stderr)
    return generated

def main() -> int:
    print("Starting Sardud seed...", flush=True)
    try:
        import django
        from decimal import Decimal
        from datetime import date, timedelta

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
        django.setup()

        from django.contrib.auth import get_user_model
        from smart_agri.core.models.farm import Farm, Location
        from smart_agri.core.models.crop import Crop, CropVariety
        from smart_agri.core.models.planning import CropPlan, CropPlanLocation
        from smart_agri.finance.models import FiscalYear, FiscalPeriod
        from smart_agri.core.models.settings import FarmSettings

        User = get_user_model()
        seed_password = _resolve_seed_password()

        # 1) Superuser (dev/demo)
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.create_superuser("admin_sardud", "admin@example.com", seed_password)
            print("Created demo superuser admin_sardud", flush=True)

        # 2) Farm (LARGE by area>=250)
        farm, _ = Farm.objects.get_or_create(
            slug="sardud",
            defaults={
                "name": "مزرعة سردود",
                "region": "Sardud",
                "description": "مزرعة سردود النموذجية لإنتاج المحاصيل النقدية",
                "area": Decimal("300.00"),
            },
        )
        FarmSettings.objects.get_or_create(farm=farm, defaults={"mode": FarmSettings.MODE_STRICT})
        print(f"Farm: {farm.name} (ID: {farm.id})", flush=True)

        # 3) Locations
        loc1, _ = Location.objects.get_or_create(farm=farm, name="القطاع الشمالي - سردود", defaults={"code": "SARD-N"})
        loc2, _ = Location.objects.get_or_create(farm=farm, name="القطاع الأوسط - سردود", defaults={"code": "SARD-M"})

        # 4) Crops & varieties
        crop_seasonal, _ = Crop.objects.get_or_create(name="قمح سردود", defaults={"mode": "Open", "is_perennial": False})
        crop_perennial, _ = Crop.objects.get_or_create(name="مانجو سردود", defaults={"mode": "Open", "is_perennial": True})

        var_seasonal, _ = CropVariety.objects.get_or_create(crop=crop_seasonal, name="صنف محلي إنتاجية عالية")
        var_perennial, _ = CropVariety.objects.get_or_create(crop=crop_perennial, name="تيمور")

        # 5) Crop plans + location links
        today = date.today()
        plan_seasonal, _ = CropPlan.objects.get_or_create(
            farm=farm,
            crop=crop_seasonal,
            name="خطة قمح موسم 2026",
            defaults={
                "start_date": today,
                "end_date": today + timedelta(days=90),
                "expected_yield": Decimal("5000.00"),
                "status": "ACTIVE",
                "budget_total": Decimal("2000000.0000"),
            },
        )
        CropPlanLocation.objects.get_or_create(crop_plan=plan_seasonal, location=loc1)

        plan_perennial, _ = CropPlan.objects.get_or_create(
            farm=farm,
            crop=crop_perennial,
            name="عناية أشجار المانجو 2026",
            defaults={
                "start_date": today,
                "end_date": today + timedelta(days=365),
                "status": "ACTIVE",
                "budget_total": Decimal("5000000.0000"),
            },
        )
        CropPlanLocation.objects.get_or_create(crop_plan=plan_perennial, location=loc2)

        # 6) Fiscal Year and Period
        year_obj, _ = FiscalYear.objects.get_or_create(
            farm=farm,
            year=today.year,
            defaults={"start_date": date(today.year, 1, 1), "end_date": date(today.year, 12, 31)},
        )
        FiscalPeriod.objects.get_or_create(
            fiscal_year=year_obj,
            month=today.month,
            defaults={
                "start_date": today.replace(day=1),
                "end_date": (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1),
                "is_closed": False,
            },
        )

        print("✅ Sardud seed completed.", flush=True)
        return 0
    except Exception:
        print("FATAL ERROR:", flush=True)
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
