import subprocess
import sys

def main():
    cmd = ["C:\\Users\\ibrahim\\AppData\\Local\\Programs\\Python\\Python311\\python.exe", "manage.py", "test", "smart_agri.core.tests.test_al_jaruba_simple_cycle", "--keepdb", "--noinput"]
    print("Running:", " ".join(cmd))
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60, cwd="c:\\tools\\workspace\\AgriAsset_v44\\backend")
        with open("jaruba_final_test.log", "w", encoding="utf-8") as f:
            f.write(res.stdout)
        print("Success! Log generated.")
    except Exception as e:
        with open("jaruba_final_test.log", "w", encoding="utf-8") as f:
            f.write(str(e))
        print("Failed! Check log.")

if __name__ == "__main__":
    main()
