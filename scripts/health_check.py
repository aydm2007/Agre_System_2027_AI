import urllib.request
import time
import sys
import io

# [AGRI-GUARDIAN] Windows cp1256 encoding safety
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

URL = "http://127.0.0.1:8000/admin/login/"
MAX_RETRIES = 10

def check_health():
    print(f"Checking health of {URL}...")
    for i in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(URL) as response:
                if response.status == 200:
                    print("[OK] Backend is UP and responding (200 OK)!")
                    return
                else:
                    print(f"[WARN] Backend responded with status: {response.status}")
        except Exception as e:
            print(f"[WAIT] Attempt {i+1}/{MAX_RETRIES}: Backend not ready yet... ({e})")
            time.sleep(2)
    
    print("[FAIL] Backend failed to start within timeout.")

if __name__ == "__main__":
    check_health()

