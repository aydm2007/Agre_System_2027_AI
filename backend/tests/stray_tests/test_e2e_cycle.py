"""E2E Document Cycle test script for YECO Hybrid ERP."""
import requests
import json

BASE = 'http://localhost:8000'

# 1. Get JWT token
r = requests.post(f'{BASE}/api/auth/token/', json={'username': 'admin', 'password': 'ADMIN123'})
token = r.json()['access']
h = {'Authorization': f'Bearer {token}'}
print('=== 1. TOKEN OK ===')

# 2. Get farms
r = requests.get(f'{BASE}/api/v1/farms/', headers=h)
farms = r.json()
print(f'=== 2. FARMS ({r.status_code}) ===')
farm_id = None
if 'results' in farms and farms['results']:
    for f in farms['results'][:3]:
        print(f"  Farm #{f['id']}: {f['name']}")
    farm_id = farms['results'][0]['id']
else:
    print(farms)
print(f'Using farm_id={farm_id}')

# 3. Create frictionless daily log
if farm_id:
    payload = {
        'farm_id': farm_id,
        'log_date': '2026-02-24',
        'activity_name': 'Test E2E Cycle',
        'workers_count': 5,
        'shift_hours': '8.0000',
        'dipstick_start_liters': '100.0000',
        'dipstick_end_liters': '40.0000',
        'notes': 'E2E document cycle test'
    }
    r = requests.post(f'{BASE}/api/v1/frictionless-daily-logs/', json=payload, headers=h)
    print(f'=== 3. FRICTIONLESS LOG ({r.status_code}) ===')
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))

# 4. Check variance alerts
r = requests.get(f'{BASE}/api/v1/variance-radar/', headers=h)
print(f'=== 4. VARIANCE ALERTS ({r.status_code}) ===')
print(json.dumps(r.json(), ensure_ascii=False, indent=2))
