import os
import subprocess
import sys
import time
import webbrowser
import socket

def wait_for_db(host, port, timeout=60):
    """
    [Agri-Guardian] reckless_startup Fix:
    Wait for Database Port to allow connections before launching Django.
     Prevents "CrashLoopBackOff" if DB is slow to wake up after power cut.
    """
    print(f"⏳ Checking Database Availability ({host}:{port})...")
    start_time = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=1):
                print("✅ Database is ready!")
                return True
        except OSError:
            if time.time() - start_time > timeout:
                print(f"❌ Database unreachable after {timeout}s.")
                return False
            print("   ... Waiting for Database ...")
            time.sleep(2)

def main():
    """
    AgriAsset 2025 - Verified Startup Script
    Replaces legacy .bat files to ensure 'Trash Policy' compliance.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir) # Go up from scripts/ to root
    
    backend_dir = os.path.join(project_root, 'backend')
    frontend_dir = os.path.join(project_root, 'frontend')

    print("\n========================================")
    print(" AgriAsset 2025 - Smart Agricultural System")
    print(" Verified Startup Sequence (Python)")
    print("========================================\n")

    # [Agri-Guardian] Pre-Flight Check
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = int(os.environ.get('DB_PORT', 5432))
    
    # We warn but don't hard-exit if waiting fails on local dev, 
    # as user might want to start DB manually.
    if not wait_for_db(db_host, db_port):
         print("⚠️ WARNING: Database did not respond. Backend may fail to start.")
         # Optional: confirm with user? For now just warn.
         time.sleep(2)

    # 1. Start Backend
    print("[1/2] Starting Backend (Django)...")
    # Use Popen to run in separate console if possible, or background
    if sys.platform == "win32":
        subprocess.Popen(f'start "AgriAsset Backend" cmd /k "cd /d {backend_dir} && python manage.py runserver 0.0.0.0:8000"', shell=True)
    else:
        # Linux/Mac support (basic)
        subprocess.Popen(['x-terminal-emulator', '-e', f'cd {backend_dir} && python3 manage.py runserver 0.0.0.0:8000'])

    time.sleep(3)

    # 2. Start Frontend
    print("[2/2] Starting Frontend (Vite)...")
    if sys.platform == "win32":
        subprocess.Popen(f'start "AgriAsset Frontend" cmd /k "cd /d {frontend_dir} && npm run dev"', shell=True)
    else:
        subprocess.Popen(['x-terminal-emulator', '-e', f'cd {frontend_dir} && npm run dev'])

    print("\n========================================")
    print(" Systems Initializing...")
    print(" Backend:  http://localhost:8000")
    print(" Frontend: http://localhost:5173")
    print("========================================\n")

    time.sleep(2)
    webbrowser.open("http://localhost:5173")

if __name__ == "__main__":
    main()
