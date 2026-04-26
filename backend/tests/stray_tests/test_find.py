import os
from pathlib import Path

root = Path(r"c:\tools\workspace\Agre_ERP_2027-main\backend\smart_agri")
count = 0

for file in root.rglob("*.py"):
    if "test" in file.name.lower(): continue
    text = file.read_text(encoding="utf-8")
    if "except Exception" in text:
        print(f"File: {file.name}")
        count += 1

print(f"Total files with except Exception: {count}")
