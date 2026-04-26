
import urllib.request
import urllib.error
import urllib.parse
import json
import base64
import sys

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "Ibrahim"
PASSWORD = "12345"

def log(msg):
    print(msg)
    sys.stdout.flush()

def probe():
    log(f"🚀 STD-LIB Probe for {USERNAME} at {BASE_URL}")
    
    # 1. Login
    login_url = f"{BASE_URL}/api/auth/token/"
    data = json.dumps({"username": USERNAME, "password": PASSWORD}).encode('utf-8')
    req = urllib.request.Request(login_url, data=data, headers={
        'Content-Type': 'application/json'
    })
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                log(f"Login Failed: {response.status}")
                return
            body = response.read()
            token = json.loads(body)['access']
            log("✅ Login Successful.")
    except urllib.error.URLError as e:
        log(f"❌ Connection Failed: {e}")
        return

    # 2. Check Modules
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    modules = [
        {"name": "Daily Logs", "url": "/api/v1/daily-logs/?limit=1"},
        {"name": "Activities", "url": "/api/v1/activities/?limit=1"},
        {"name": "Inventory Items (Stock)", "url": "/api/v1/inventory/items/?limit=1"},
        {"name": "Stock Movements", "url": "/api/v1/inventory/movements/?limit=1"},
        {"name": "Sales Invoices", "url": "/api/v1/sales/invoices/?limit=1"},
        {"name": "Customers", "url": "/api/v1/sales/customers/?limit=1"},
        {"name": "Service Providers", "url": "/api/v1/service-providers/?limit=1"},
        {"name": "Dashboard Stats", "url": "/api/v1/dashboard-stats/"},
        {"name": "Advanced Report", "url": "/api/v1/advanced-report/?start=2025-01-01"},
    ]
    
    for mod in modules:
        url = f"{BASE_URL}{mod['url']}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                log(f"✅ [200] {mod['name']}")
        except urllib.error.HTTPError as e:
            log(f"❌ [{e.code}] {mod['name']} - {e.reason}")
            # Try to read error body
            try:
                err_body = e.read().decode('utf-8')
                log(f"     Error Body: {err_body[:200]}")
            except:
                pass
        except Exception as e:
            log(f"⚠️ [ERR] {mod['name']}: {e}")

if __name__ == "__main__":
    probe()
