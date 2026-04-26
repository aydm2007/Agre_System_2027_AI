import os
import sys
import subprocess

if __name__ == '__main__':
    backend_dir = r"c:\tools\workspace\Agre_ERP_2027-main\backend"
    python_exe = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
    pytest_script = os.path.join(backend_dir, "venv", "Scripts", "pytest.exe")
    
    test_file = sys.argv[1] if len(sys.argv) > 1 else r"smart_agri\core\tests\test_tree_variance.py"
    
    print(f"Running: {pytest_script} {test_file}")
    
    result = subprocess.run([pytest_script, test_file, "-v"], cwd=backend_dir, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    
    print("STDERR:")
    print(result.stderr)
    
    if result.returncode == 0:
         print("TESTS PASSED!")
    else:
         print("TESTS FAILED!")
