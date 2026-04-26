import subprocess
import sys
import time

print("Starting server permanently...")
with open("server_log.txt", "w") as f:
    process = subprocess.Popen(
        [sys.executable, 'manage.py', 'runserver', '0.0.0.0:8000', '--noreload'],
        stdout=f,
        stderr=subprocess.STDOUT
    )
    
    try:
        while True:
            time.sleep(1)
            if process.poll() is not None:
                print(f"Server crashed with exit code {process.returncode}")
                break
    except KeyboardInterrupt:
        process.terminate()
