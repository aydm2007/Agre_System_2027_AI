import os

# Test basic write
try:
    with open("debug_log.txt", "w") as f:
        f.write("Python is working!\n")
        f.write(f"CWD: {os.getcwd()}\n")
except Exception as e:
    print(f"Write failed: {e}")

# Test read SQL file
sql_path = r"C:\AgriAsset2025RLSFIX\workspace_v3.1.1.8.8.9.sql"
try:
    if os.path.exists(sql_path):
        with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
            header = f.read(200)
            with open("debug_log.txt", "a") as log:
                log.write(f"SQL Header:\n{header}\n")
    else:
        with open("debug_log.txt", "a") as log:
            log.write(f"SQL file not found: {sql_path}\n")
except Exception as e:
    with open("debug_log.txt", "a") as log:
        log.write(f"Read failed: {e}\n")
