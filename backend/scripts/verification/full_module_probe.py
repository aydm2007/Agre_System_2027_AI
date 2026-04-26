
import requests
import sys
import json

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "Ibrahim"
PASSWORD = "12345"

LOG_FILE = "module_probe_results.log"

def log(f, message, status="INFO"):
    line = f"[{status}] {message}"
    print(line)
    f.write(line + "\n")

def probe_modules():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        log(f, f"🚀 Starting Full Module Probe for user: {USERNAME}")
        
        # 1. Login
        login_url = f"{BASE_URL}/api/auth/token/"
        try:
            resp = requests.post(login_url, json={"username": USERNAME, "password": PASSWORD}, timeout=5)
            if resp.status_code != 200:
                log(f, f"Login Failed: {resp.status_code}", "FAIL")
                return
            token = resp.json()['access']
            headers = {'Authorization': f'Bearer {token}'}
            log(f, "Authenticated Successfully.", "PASS")
        except Exception as e:
            log(f, f"Authentication Exception: {e}", "CRIT")
            return

        # 2. Module Definitions
        modules = [
            # Daily Logs (Injaz)
            {"name": "Daily Logs", "url": "/api/v1/daily-logs/", "params": {"limit": 5}},
            {"name": "Activities", "url": "/api/v1/activities/", "params": {"limit": 5}},
            
            # Inventory (Warehouses)
            {"name": "Inventory Items", "url": "/api/v1/inventory/items/", "params": {"limit": 5}},
            # {"name": "Stock Movements", "url": "/api/v1/inventory/movements/", "params": {"limit": 5}}, # Verify url later using router
            
            # Sales
            {"name": "Sales Invoices", "url": "/api/v1/sales/invoices/", "params": {"limit": 5}},
            {"name": "Customers", "url": "/api/v1/sales/customers/", "params": {"limit": 5}},
            
            # Services (Service Linking)
            {"name": "Service Providers", "url": "/api/v1/service-providers/", "params": {"limit": 5}},
            
            # Reports
            {"name": "Dashboard Stats", "url": "/api/v1/dashboard-stats/", "params": {}},
            {"name": "Advanced Report", "url": "/api/v1/advanced-report/", "params": {"start": "2025-01-01", "end": "2026-12-31"}},
        ]

        failures = 0
        
        for mod in modules:
            url = f"{BASE_URL}{mod['url']}"
            log(f, f"Testing Module: {mod['name']} ({url})...")
            try:
                r = requests.get(url, headers=headers, params=mod.get('params'), timeout=15)
                if r.status_code == 200:
                    try:
                        data = r.json()
                        count = len(data.get('results', [])) if 'results' in data else 'N/A'
                        log(f, f"  -> OK (Status: 200, Items: {count})", "PASS")
                    except:
                         log(f, f"  -> OK (Status: 200, Not JSON)", "PASS")
                else:
                    log(f, f"  -> FAILED (Status: {r.status_code})", "FAIL")
                    if r.status_code >= 500:
                        log(f, f"     Response: {r.text[:500]}", "DEBUG")
                    failures += 1
            except Exception as e:
                log(f, f"  -> EXCEPTION: {e}", "CRIT")
                failures += 1

        log(f, "-"*30)
        if failures == 0:
            log(f, "🎉 ALL MODULES VERIFIED SUCCESSFULLY.", "SUCCESS")
        else:
            log(f, f"⚠️ FOUND {failures} MODULE FAILURES.", "WARN")

if __name__ == "__main__":
    probe_modules()
