import os
import sys
import django
import json
import uuid

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from smart_agri.core.models import Farm, Location, Crop
from smart_agri.core.models.planning import CropPlan
from smart_agri.core.models.inventory import Item


User = get_user_model()

def simulate_cycle():
    client = APIClient()
    
    # 1. Get an active user (preferably admin or someone with permissions)
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("❌ No superuser found. Creating a temporary admin for testing...")
        user = User.objects.create_superuser('testadmin', 'test@test.com', 'admin123')
    
    print(f"👤 Simulated login as: {user.username}")
    client.force_authenticate(user=user)

    # 2. Get Seed Data to use in our payloads
    farm = Farm.objects.filter(deleted_at__isnull=True).first()
    location = Location.objects.filter(farm=farm, deleted_at__isnull=True).first()
    crop = Crop.objects.filter(deleted_at__isnull=True).first()
    crop_plan = CropPlan.objects.filter(farm=farm, crop=crop, status='active', deleted_at__isnull=True).first()
    
    # Material (group containing material or fertilizer)
    material = Item.objects.filter(group__icontains='سماد', deleted_at__isnull=True).first()
    if not material:
         material = Item.objects.filter(deleted_at__isnull=True).first()
    
    # Employee (Fallback to user)
    employee_id = user.id

    if not all([farm, location, crop_plan, material]):
        print("❌ Missing required seed data. Run setup or check DB.")
        print(f"Farm: {farm}, Location: {location}, Plan: {crop_plan}, AppMaterial: {material}")
        return

    print(f"🏠 Context: Farm='{farm.name}', Location='{location.name}', Plan='{crop_plan.name}'")

    # ---------------------------------------------------------
    # ACTION 1: Submit Daily Log (With Material Consumption)
    # ---------------------------------------------------------
    print("\n🚀 [1] Simulating Daily Log Submission (Simple Mode: Frictionless)...")
    daily_log_payload = {
        "farm": farm.id,
        "location": location.id,
        "crop_plan": crop_plan.id,
        "log_date": "2026-03-01",
        "work_hours": "8.50",
        "task_name": "تسميد وقائي للنباتات",  # Setup Task
        "weather_condition": "sunny",
        "status": "submitted",
        "activities": [ # Resources & Details
            {
                "employee": employee_id,
                "worked_hours": "8.50",
                "notes": "تم التسميد بنجاح"
            }
        ],
        "inventory_consumed": [ # Material Consumption
            {
                "item": material.id,
                "quantity": "25.0000",
                "unit_cost": "150.0000", # Explicit cost to ensure Ledger triggers
                "notes": "استهلاك سماد من المستودع"
            }
        ]
    }
    
    response = client.post(
        '/api/v1/daily-logs/',
        data=json.dumps(daily_log_payload),
        content_type='application/json',
        HTTP_APP_VERSION='2.0.0',
        HTTP_X_APP_VERSION='2.0.0',
        HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        SERVER_NAME='127.0.0.1'
    )
    
    if response.status_code == 201:
        log_data = response.json()
        print(f"✅ Daily Log Created Successfully! ID: {log_data.get('id')}")
    else:
        print(f"❌ Failed to create Daily Log. Status: {response.status_code}")
        print(response.json())
        return

    # ---------------------------------------------------------
    # ACTION 2: Submit Harvest Log
    # ---------------------------------------------------------
    print("\n🚀 [2] Simulating Harvest Log Submission...")
    harvest_product = Item.objects.filter(group__icontains='منتج', deleted_at__isnull=True).first()
    if not harvest_product:
        harvest_product = Item.objects.filter(deleted_at__isnull=True).last()
        
    if not harvest_product:
        print("❌ No Harvest Product found in Seed Data. Aborting harvest step.")
        return

    harvest_payload = {
        "farm": farm.id,
        "crop": crop.id,
        "crop_plan": crop_plan.id,
        "harvest_date": "2026-03-01",
        "item": harvest_product.id,
        "quantity": "500.000", # 500 units harvested
        "quality_grade": "A",
        "notes": "حصاد عالي الجودة"
    }

    response = client.post(
        '/api/v1/harvest-logs/',
        data=json.dumps(harvest_payload),
        content_type='application/json',
        HTTP_APP_VERSION='2.0.0',
        HTTP_X_APP_VERSION='2.0.0',
        HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        SERVER_NAME='127.0.0.1'
    )
    
    if response.status_code == 201:
        harvest_data = response.json()
        print(f"✅ Harvest Log Created Successfully! ID: {harvest_data.get('id')}")
    else:
        print(f"❌ Failed to create Harvest Log. Status: {response.status_code}")
        print(response.json())

    print("\n🎯 Simulation Complete. Ready for Auditor Check.")

if __name__ == '__main__':
    simulate_cycle()
