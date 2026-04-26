import os
import sys
import socket
import subprocess
import importlib.util
from pathlib import Path

def check_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return "✅ Online"
    except OSError:
        return "❌ Offline (Cannot pip install)"

def check_django():
    if importlib.util.find_spec("django"):
        return f"✅ Installed ({sys.executable})"
    return f"❌ Not Found in {sys.executable}"

def check_docker():
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return "✅ Running"
        return "❌ Installed but Daemon Stopped"
    except FileNotFoundError:
        return "❌ Not Installed"
    except subprocess.TimeoutExpired:
        return "❌ Hanging (Daemon Unresponsive)"

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return "✅ Open" if s.connect_ex(("localhost", port)) == 0 else "❌ Closed"

def main():
    # Force UTF-8 for Windows consoles
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("="*60)
    print(" 🏥 AgriAsset 2025 - Environment Diagnostic Tool")
    print("="*60)
    
    print(f"\n1. INTERNET CONNECTIVITY: {check_internet()}")
    print(f"2. PYTHON ENVIRONMENT:    {check_django()}")
    print(f"3. DOCKER SERVICE:        {check_docker()}")
    print(f"4. POSTGRES PORT (5432):  {check_port(5432)}")
    print(f"5. BACKEND PORT (8000):   {check_port(8000)}")
    
    print("\n" + "="*60)
    print(" RECOMMENDATION:")
    
    django = "✅" in check_django()
    docker = "✅" in check_docker()
    
    if not django and not docker:
        print(" 🛑 CRITICAL: Neither Django nor Docker is ready.")
        print("    -> ACTION: Start Docker Desktop manually.")
    elif docker:
        print(" 🟢 Docker is ready! Run: docker-compose up -d")
    elif django:
        print(" 🟢 Django is ready! Run: python backend/manage.py runserver")

if __name__ == "__main__":
    main()
