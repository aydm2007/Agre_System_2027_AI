import subprocess

with open('axis1_results.txt', 'w', encoding='utf-8') as f:
    f.write("=== SHOWMIGRATIONS ===\n")
    proc1 = subprocess.run(['python', 'manage.py', 'showmigrations'], capture_output=True, text=True)
    f.write(proc1.stdout)
    if proc1.stderr:
        f.write("ERROR:\n" + proc1.stderr)
        
    f.write("\n=== DETECT ZOMBIES ===\n")
    proc2 = subprocess.run(['python', 'scripts/detect_zombies.py'], capture_output=True, text=True)
    f.write(proc2.stdout)
    if proc2.stderr:
        f.write("ERROR:\n" + proc2.stderr)
