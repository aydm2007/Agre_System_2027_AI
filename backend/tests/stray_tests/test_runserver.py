import subprocess
import time

print("Starting Django server...")
process = subprocess.Popen(
    ['python', 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

time.sleep(5)  # Wait for startup
process.poll() # check if it crashed

if process.returncode is not None:
    print(f"Crashed with exit code {process.returncode}")
    out, err = process.communicate()
    print("STDOUT:", out)
    print("STDERR:", err)
else:
    print("Server is running successfully!")
    process.terminate()
