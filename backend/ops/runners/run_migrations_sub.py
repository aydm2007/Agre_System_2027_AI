import os
import subprocess

if __name__ == '__main__':
    backend_dir = r"c:\tools\workspace\Agre_ERP_2027-main\backend"
    python_exe = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
    manage_script = os.path.join(backend_dir, "manage.py")
    
    print(f"Running makemigrations...")
    result1 = subprocess.run([python_exe, manage_script, "makemigrations", "--noinput"], cwd=backend_dir, capture_output=True, text=True)
    print("STDOUT 1:")
    print(result1.stdout)
    print("STDERR 1:")
    print(result1.stderr)
    
    print(f"\nRunning migrate...")
    result2 = subprocess.run([python_exe, manage_script, "migrate", "--noinput"], cwd=backend_dir, capture_output=True, text=True)
    print("STDOUT 2:")
    print(result2.stdout)
    print("STDERR 2:")
    print(result2.stderr)
