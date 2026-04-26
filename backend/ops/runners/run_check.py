import os
import subprocess
import sys

if __name__ == '__main__':
    backend_dir = r"c:\tools\workspace\Agre_ERP_2027-main\backend"
    python_exe = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
    manage_script = os.path.join(backend_dir, "manage.py")
    
    print(f"Running django check...")
    result = subprocess.run([python_exe, manage_script, "check"], cwd=backend_dir, capture_output=True, text=True)
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)
