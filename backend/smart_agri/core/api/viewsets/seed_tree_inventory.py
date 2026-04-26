"""
[AGRI-GUARDIAN] Admin-only endpoint to seed deterministic proof inventory data.
This endpoint is a controlled readiness/bootstrap helper, not a general-purpose
seed bucket or hotfix sink. Superuser required.
"""
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from datetime import date, timedelta
from decimal import Decimal

from smart_agri.core.models import (
    Crop,
    CropVariety,
    Farm,
    FarmCrop,
    LaborRate,
    Location,
    LocationTreeStock,
    TreeProductivityStatus,
    TreeLossReason,
)


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def seed_tree_inventory(request):
    """
    POST /api/v1/seed-tree-inventory/
    Seeds perennial proof crops, crop-scoped proof varieties, productivity
    statuses, labor-rate safety defaults, and location-aware tree stock records.
    Idempotent and safe to rerun against PostgreSQL-backed readiness environments.
    """
    results = {"crops": [], "varieties": [], "statuses": [], "stocks": []}

    # --- 1. Ensure perennial crops ---
    crops_payload = [
        {"name": "Ù†Ø®ÙŠÙ„ Ø§Ù„ØªÙ…Ø±", "mode": "Open", "is_perennial": True},
        {"name": "Ù…Ø§Ù†Ø¬Ùˆ", "mode": "Open", "is_perennial": True},
        {"name": "Ø¨Ù†", "mode": "Open", "is_perennial": True},
        {"name": "Ø±Ù…Ø§Ù†", "mode": "Open", "is_perennial": True},
        {"name": "Ø³Ø¯Ø±", "mode": "Open", "is_perennial": True},
        {"name": "Ù„ÙˆØ²", "mode": "Open", "is_perennial": True},
        {"name": "Ù‚Ø§Øª", "mode": "Open", "is_perennial": True},
    ]
    for c in crops_payload:
        obj, created = Crop.objects.update_or_create(
            name=c["name"], mode=c["mode"],
            defaults={"is_perennial": c["is_perennial"]},
        )
        results["crops"].append({"name": c["name"], "id": obj.id, "created": created})

    # --- 2. Ensure varieties ---
    varieties_map = {
        "Ù†Ø®ÙŠÙ„ Ø§Ù„ØªÙ…Ø±": [
            {"name": "Ø®Ù„Ø§Øµ Ø§Ù„Ø£Ø­Ø³Ø§Ø¡", "code": "PAL-001"},
            {"name": "Ø³ÙƒØ±ÙŠ Ø§Ù„Ù‚ØµÙŠÙ…", "code": "PAL-002"},
            {"name": "Ø¨Ø±Ø­ÙŠ Ø§Ù„Ø¨ØµØ±Ø©", "code": "PAL-003"},
        ],
        "Ù…Ø§Ù†Ø¬Ùˆ": [
            {"name": "ØªÙŠÙ…ÙˆØ±", "code": "MNG-001"},
            {"name": "Ù‚Ù„Ø¨ Ø§Ù„Ø«ÙˆØ±", "code": "MNG-002"},
            {"name": "Ø¹ÙˆÙŠØ³", "code": "MNG-003"},
        ],
        "Ø¨Ù†": [
            {"name": "Ø¨Ù† Ù…Ø­Ù„ÙŠ", "code": "COF-001"},
            {"name": "Ø¨Ù† Ù…Ø·Ø±ÙŠ", "code": "COF-002"},
        ],
        "Ø±Ù…Ø§Ù†": [
            {"name": "Ø±Ù…Ø§Ù† Ø¨Ù„Ø¯ÙŠ", "code": "POM-001"},
            {"name": "Ø±Ù…Ø§Ù† Ø·Ø§Ø¦ÙÙŠ", "code": "POM-002"},
        ],
        "Ø³Ø¯Ø±": [
            {"name": "Ø³Ø¯Ø± Ø¨Ù„Ø¯ÙŠ", "code": "SID-001"},
            {"name": "Ø³Ø¯Ø± Ø¨Ø±ÙŠ", "code": "SID-002"},
        ],
        "Ù„ÙˆØ²": [
            {"name": "Ù„ÙˆØ² Ø¨Ù„Ø¯ÙŠ", "code": "ALM-001"},
            {"name": "Ù„ÙˆØ² Ø­Ø¶Ø±Ù…ÙŠ", "code": "ALM-002"},
        ],
        "Ù‚Ø§Øª": [
            {"name": "Ù‚Ø§Øª Ø±Ø§Ø²Ø­ÙŠ", "code": "QAT-001"},
            {"name": "Ù‚Ø§Øª Ø­Ù…Ø¯ÙŠ", "code": "QAT-002"},
        ],
    }
    all_varieties = []
    for crop_name, var_list in varieties_map.items():
        try:
            crop = Crop.objects.get(name=crop_name, mode="Open")
        except Crop.DoesNotExist:
            continue
        for v in var_list:
            obj, created = CropVariety.objects.update_or_create(
                crop=crop, name=v["name"],
                defaults={"code": v["code"]},
            )
            all_varieties.append(obj)
            results["varieties"].append({"name": v["name"], "crop": crop_name, "id": obj.id, "created": created})

    # Guarantee at least one crop-scoped proof variety for every active perennial crop.
    perennial_crops = Crop.objects.filter(
        is_perennial=True,
        deleted_at__isnull=True,
    ).order_by("id")
    for crop in perennial_crops:
        if CropVariety.objects.filter(crop=crop, deleted_at__isnull=True).exists():
            continue
        proof_variety, created = CropVariety.objects.update_or_create(
            crop=crop,
            code=f"PER-{crop.id:03d}",
            defaults={"name": f"{crop.name} Proof Variety"},
        )
        all_varieties.append(proof_variety)
        results["varieties"].append(
            {
                "name": proof_variety.name,
                "crop": crop.name,
                "id": proof_variety.id,
                "created": created,
                "seeded_as_proof_variety": True,
            }
        )

    # --- 3. Ensure productivity statuses ---
    statuses_payload = [
        {"code": "juvenile", "name_en": "Juvenile / Non-productive", "name_ar": "Ø£Ø´Ø¬Ø§Ø± ØºÙŠØ± Ù…Ù†ØªØ¬Ø©"},
        {"code": "productive", "name_en": "Productive", "name_ar": "Ù…Ù†ØªØ¬Ø©"},
        {"code": "declining", "name_en": "Declining / Aged", "name_ar": "Ù…ØªØ±Ø§Ø¬Ø¹Ø©"},
        {"code": "dormant", "name_en": "Dormant / Under Maintenance", "name_ar": "Ø®Ø§Ù…Ù„Ø© / ØªØ­Øª Ø§Ù„ØµÙŠØ§Ù†Ø©"},
    ]
    productive_status = None
    for s in statuses_payload:
        obj, created = TreeProductivityStatus.objects.update_or_create(
            code=s["code"],
            defaults={"name_en": s["name_en"], "name_ar": s["name_ar"]},
        )
        results["statuses"].append({"code": s["code"], "id": obj.id, "created": created})
        if s["code"] == "productive":
            productive_status = obj

    # --- 4. Ensure loss reasons ---
    loss_payload = [
        {"code": "pest", "name_en": "Pest / Disease", "name_ar": "Ø¢ÙØ© Ø£Ùˆ Ù…Ø±Ø¶"},
        {"code": "water_stress", "name_en": "Water Stress", "name_ar": "Ø¥Ø¬Ù‡Ø§Ø¯ Ù…Ø§Ø¦ÙŠ"},
        {"code": "storm_damage", "name_en": "Storm Damage", "name_ar": "Ø¶Ø±Ø± Ø¹Ø§ØµÙØ©"},
    ]
    for lr in loss_payload:
        TreeLossReason.objects.update_or_create(
            code=lr["code"],
            defaults={"name_en": lr["name_en"], "name_ar": lr["name_ar"]},
        )

    # --- 5. Create deterministic LocationTreeStock proof coverage across farms ---
    planting_base = date.today() - timedelta(days=365 * 3)
    farms = Farm.objects.filter(deleted_at__isnull=True).order_by("id")
    for farm_index, farm in enumerate(farms):
        # Daily-log readiness proofs need a valid farm-scoped labor-rate baseline.
        if not LaborRate.objects.filter(farm=farm, deleted_at__isnull=True).exists():
            LaborRate.objects.create(
                farm=farm,
                role_name="Ø¹Ø§Ù…Ù„ ÙŠÙˆÙ…ÙŠ",
                daily_rate=Decimal("3500.00"),
                cost_per_hour=Decimal("437.50"),
                currency="YER",
                effective_date=date.today(),
            )

        locations = list(
            Location.objects.filter(
                farm=farm,
                deleted_at__isnull=True,
                type__in=["Orchard", "Field"],
            ).order_by("id")
        )
        if not locations:
            loc, _ = Location.objects.get_or_create(
                farm=farm,
                name="Ø¨Ø³ØªØ§Ù† Ø¥Ø«Ø¨Ø§ØªÙŠ",
                defaults={"type": "Orchard", "code": f"ORCH-{farm.id}"},
            )
            locations = [loc]

        var_idx = farm_index
        for loc in locations[:6]:
            for i in range(min(3, len(all_varieties))):
                variety = all_varieties[(var_idx + i) % len(all_varieties)]
                tree_count = 50 + (var_idx * 15) + (i * 20)
                stock, created = LocationTreeStock.objects.update_or_create(
                    location=loc,
                    crop_variety=variety,
                    defaults={
                        "current_tree_count": tree_count,
                        "productivity_status": productive_status,
                        "planting_date": planting_base + timedelta(days=var_idx * 30),
                        "source": "Ù…Ø´ØªÙ„ Ø­ÙƒÙˆÙ…ÙŠ",
                        "notes": f"Ø¨ÙŠØ§Ù†Ø§Øª ØªØ£Ø³ÙŠØ³ÙŠØ© - {variety.name} ÙÙŠ {loc.name}",
                    },
                )
                results["stocks"].append({
                    "location": loc.name,
                    "variety": variety.name,
                    "trees": tree_count,
                    "id": stock.id,
                    "created": created,
                })
            var_idx += 1

        # Guarantee location-aware perennial coverage for active farm crops so
        # E2E perennial execution never depends on ad-hoc manual repair data.
        representative_varieties = (
            CropVariety.objects.filter(
                crop_id__in=FarmCrop.objects.filter(
                    farm=farm,
                    deleted_at__isnull=True,
                    crop__is_perennial=True,
                    crop__deleted_at__isnull=True,
                ).values_list("crop_id", flat=True),
                deleted_at__isnull=True,
            )
            .select_related("crop")
            .order_by("crop_id", "id")
        )
        seen_crop_ids = set()
        for variety in representative_varieties:
            if variety.crop_id in seen_crop_ids:
                continue
            seen_crop_ids.add(variety.crop_id)
            for loc in locations[:6]:
                proof_count = 25 + farm.id + loc.id + variety.crop_id
                stock, created = LocationTreeStock.objects.update_or_create(
                    location=loc,
                    crop_variety=variety,
                    defaults={
                        "current_tree_count": proof_count,
                        "productivity_status": productive_status,
                        "planting_date": planting_base,
                        "source": "Ø¥Ø«Ø¨Ø§Øª Ø¬Ø§Ù‡Ø²ÙŠØ© E2E",
                        "notes": f"ØªØºØ·ÙŠØ© Ø¥Ø«Ø¨Ø§ØªÙŠØ© Ù„Ù„Ù…Ø­ØµÙˆÙ„ {variety.crop.name} ÙÙŠ {loc.name}",
                    },
                )
                results["stocks"].append({
                    "location": loc.name,
                    "variety": variety.name,
                    "trees": proof_count,
                    "id": stock.id,
                    "created": created,
                    "seeded_as_perennial_coverage": True,
                })

    return Response({
        "status": "success",
        "summary": {
            "crops": len(results["crops"]),
            "varieties": len(results["varieties"]),
            "statuses": len(results["statuses"]),
            "stocks": len(results["stocks"]),
        },
        "details": results,
    }, status=status.HTTP_200_OK)
