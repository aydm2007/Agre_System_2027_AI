import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.inventory.models import Unit, UnitConversion
from decimal import Decimal

def seed_units():
    print("Seeding Yemeni & Standard Units...")

    units_data = [
        # MASS / WEIGHT
        {"code": "kg", "name": "كيلوجرام", "symbol": "كجم", "category": "mass", "precision": 3},
        {"code": "tonne", "name": "طن", "symbol": "طن", "category": "mass", "precision": 3},
        {"code": "g", "name": "جرام", "symbol": "جرام", "category": "mass", "precision": 3},
        {"code": "sack", "name": "كيس", "symbol": "كيس", "category": "mass", "precision": 2},
        {"code": "qadah", "name": "قدح", "symbol": "قدح", "category": "mass", "precision": 2},
        {"code": "thumn", "name": "ثمن", "symbol": "ثمن", "category": "mass", "precision": 3},
        {"code": "nafar", "name": "نفر", "symbol": "نفر", "category": "mass", "precision": 3},
        {"code": "ratl", "name": "رطل", "symbol": "رطل", "category": "mass", "precision": 3},

        # VOLUME
        {"code": "liter", "name": "لتر", "symbol": "لتر", "category": "volume", "precision": 3},
        {"code": "ml", "name": "مليلتر", "symbol": "مل", "category": "volume", "precision": 3},
        {"code": "dabba", "name": "دبة", "symbol": "دبة", "category": "volume", "precision": 2},
        {"code": "barrel", "name": "برميل", "symbol": "برميل", "category": "volume", "precision": 2},

        # AREA
        {"code": "ha", "name": "هكتار", "symbol": "هكتار", "category": "area", "precision": 4},
        {"code": "sqm", "name": "متر مربع", "symbol": "م²", "category": "area", "precision": 2},
        {"code": "libna", "name": "لبنة", "symbol": "لبنة", "category": "area", "precision": 2},
        {"code": "qasaba", "name": "قصبة", "symbol": "قصبة", "category": "area", "precision": 2},

        # COUNT / OTHER
        {"code": "piece", "name": "حبة / عدد", "symbol": "حبة", "category": "count", "precision": 0},
        {"code": "seedling", "name": "شتلة", "symbol": "شتلة", "category": "count", "precision": 0},
        {"code": "bundle", "name": "ربطة", "symbol": "ربطة", "category": "count", "precision": 0},
    ]

    created_units = {}
    for data in units_data:
        unit, created = Unit.objects.update_or_create(
            code=data["code"],
            defaults={
                "name": data["name"],
                "symbol": data["symbol"],
                "category": data["category"],
                "precision": data["precision"]
            }
        )
        created_units[data["code"]] = unit
        if created:
            print(f"Created unit: {unit.name} ({unit.code})")

    # Base conversions (multiplier: means 1 TO_UNIT = Multiplier * FROM_UNIT?
    # Usually multiplier in systems: to_amount = from_amount * multiplier
    # e.g., 1 tonne = 1000 kg (from_unit=tonne, to_unit=kg, multiplier=1000)
    conversions_data = [
        # Mass Base = kg
        ("tonne", "kg", "1000.00"),
        ("kg", "g", "1000.00"),
        ("sack", "kg", "50.00"),
        ("qadah", "kg", "30.00"),
        ("thumn", "kg", "3.75"),
        ("nafar", "g", "468.75"), # 3.75kg / 8 = 0.46875 kg = 468.75 g
        ("ratl", "g", "450.00"),

        # Volume Base = liter
        ("liter", "ml", "1000.00"),
        ("dabba", "liter", "20.00"),
        ("barrel", "liter", "200.00"),

        # Area Base = sqm
        ("ha", "sqm", "10000.00"),
        ("libna", "sqm", "44.44"),
        ("qasaba", "sqm", "11.11"),
    ]

    print("Seeding conversions...")
    for from_code, to_code, multiplier in conversions_data:
        from_u = created_units.get(from_code)
        to_u = created_units.get(to_code)
        if not from_u or not to_u:
            continue
        
        conv, created = UnitConversion.objects.update_or_create(
            from_unit=from_u,
            to_unit=to_u,
            defaults={"multiplier": Decimal(multiplier)}
        )
        # Add reverse conversion
        reverse_mult = Decimal("1.0") / Decimal(multiplier)
        UnitConversion.objects.update_or_create(
            from_unit=to_u,
            to_unit=from_u,
            defaults={"multiplier": round(reverse_mult, 8)}
        )
        if created:
            print(f"Conversion: 1 {from_u.name} = {multiplier} {to_u.name}")

    print("Done seeding units and conversions.")

if __name__ == "__main__":
    seed_units()
