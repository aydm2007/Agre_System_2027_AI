import os
import sys
import socket
import django
from django.conf import settings

# 1. Setup Environment
print("[-] Setting up Django Environment...")
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")

try:
    django.setup()
    print("[+] Django Setup Complete.")
except Exception as e:
    print(f"[!] Django Setup Failed: {e}")
    sys.exit(1)

# 2. Test Database Connection
print("[-] Testing Database Connection...")
from django.db import connections
try:
    conn = connections['default']
    conn.cursor()
    print("[+] Database Connection Successful.")
except Exception as e:
    print(f"[!] Database Connection Failed: {e}")
    # Don't exit, might be just DB issue, server can still start

# 3. Test Port Binding (8005)
PORT = 8005
print(f"[-] Testing Port Binding on {PORT}...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.bind(('0.0.0.0', PORT))
    sock.close()
    print(f"[+] Port {PORT} is FREE and available.")
except Exception as e:
    print(f"[!] Port {PORT} is BUSY or Unavailable: {e}")
    sys.exit(1)

# 4. Check Installed Apps
print("[-] Checking Installed Apps...")
try:
    from django.apps import apps
    print(f"[+] Loaded Apps: {len(apps.get_app_configs())}")
except Exception as e:
    print(f"[!] App Check Failed: {e}")

print("\n[=] DIAGNOSIS COMPLETE. READY TO LAUNCH ON 8005.")
