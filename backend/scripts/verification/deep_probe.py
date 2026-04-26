
import requests
import sys

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "Ibrahim"
PASSWORD = "12345"

def probe():
    print(f"🕵️ Standalone Deep Probe for: {USERNAME}")
    
    with open("probe_results.log", "w", encoding="utf-8") as f:
        f.write(f"Initiating Probe against {BASE_URL}...\n")
        
        # 1. Login
        login_url = f"{BASE_URL}/api/auth/token/"
        try:
            print("Attempting login...")
            resp = requests.post(login_url, json={"username": USERNAME, "password": PASSWORD}, timeout=5)
            print(f"Login Response: {resp.status_code}")
        except Exception as e:
            msg = f"❌ Backend not reachable: {e}"
            print(msg)
            f.write(msg + "\n")
            return

        if resp.status_code != 200:
            msg = f"❌ Login Failed: {resp.status_code} {resp.text}"
            print(msg)
            f.write(msg + "\n")
            return

        token = resp.json()['access']
        headers = {'Authorization': f'Bearer {token}'}
        f.write("✅ Login Successful.\n")

        # 2. Endpoints
        endpoints = [
            "/api/v1/auth/users/me/",
            "/api/v1/dashboard/stats/", 
            "/api/v1/crops/",
            "/api/v1/farms/",
            "/api/v1/financial/ledger/",
            "/api/v1/advanced-report/",
            "/api/v1/activities/",
            "/api/v1/notifications/",
        ]
        
        failures = []
        for ep in endpoints:
            url = f"{BASE_URL}{ep}"
            try:
                r = requests.get(url, headers=headers, timeout=10)
                status = r.status_code
                log_line = f"[{status}] {ep}"
                print(log_line)
                f.write(log_line + "\n")
                
                if status >= 500:
                    failures.append(log_line)
            except Exception as e:
                err = f"[ERR] {ep}: {e}"
                print(err)
                f.write(err + "\n")
                failures.append(err)

        f.write("\nSummary:\n")
        if failures:
            f.write(f"Failures found: {len(failures)}\n")
        else:
            f.write("All systems nominal.\n")

if __name__ == "__main__":
    probe()
