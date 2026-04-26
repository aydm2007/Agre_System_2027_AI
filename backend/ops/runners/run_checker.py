import subprocess
with open("checker_stdout.txt", "w", encoding="utf-8") as f:
    res = subprocess.run(["python", "scripts/check_no_float_mutations.py"], capture_output=True, text=True, encoding="utf-8")
    f.write(res.stdout)
    f.write(res.stderr)
