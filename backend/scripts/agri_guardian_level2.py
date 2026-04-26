import os
import re
import sys

# Agri-Guardian Level 2 Audit: The Brutal Truth
# Scans for Code Pollution, Silent Failures, and Technical Debt

BACKEND_ROOT = "c:\\tools\\workspace\\saradud2027\\backend"
FRONTEND_ROOT = "c:\\tools\\workspace\\saradud2027\\frontend\\src"

def run_brutal_audit():
    print("🛡️ AGRI-GUARDIAN LEVEL 2: BRUTAL AUDIT")
    print("========================================")
    
    score = 100
    issues = []
    
    # 1. CODE POLLUTION (Backend)
    # ---------------------------
    print("\n[1] Scanning Backend for Pollution (print statements)...")
    pollution_count = 0
    polluted_files = []
    
    # Exclude scripts and migrations
    exclude_dirs = ['scripts', 'migrations', 'venv', '__pycache__', 'tests', '_emergency_archive']
    
    for root, dirs, files in os.walk(BACKEND_ROOT):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith(".py") and file != "agri_guardian_audit.py" and file != "agri_guardian_level2.py":
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            # simplistic check: print( at start or indented
                            if re.search(r'^\s*print\(', line):
                                pollution_count += 1
                                if path not in polluted_files:
                                    polluted_files.append(os.path.basename(path))
                except:
                    pass

    if pollution_count > 0:
        print(f"❌ FAIL: Found {pollution_count} 'print()' statements in production code.")
        print(f"   -> Culprits: {polluted_files[:5]}...")
        # Penalty: 2 points per print, max 30
        penalty = min(30, pollution_count * 2)
        score -= penalty
        issues.append(f"Code Pollution: {pollution_count} backend print() statements.")
    else:
        print("✅ PASS: Backend is clean of print() statements.")

    # 2. CODE POLLUTION (Frontend)
    # ----------------------------
    print("\n[2] Scanning Frontend for Pollution (console.log)...")
    console_count = 0
    for root, dirs, files in os.walk(FRONTEND_ROOT):
        for file in files:
            if file.endswith(".jsx") or file.endswith(".js"):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        if "console.log" in f.read():
                            console_count += 1
                except:
                    pass
    
    if console_count > 0:
        print(f"⚠️ WARN: Found {console_count} frontend files with 'console.log'.")
        # Penalty: 5 points total (less critical in frontend but sloppy)
        score -= 5
        issues.append(f"Code Pollution: {console_count} frontend files contain console.log.")
    else:
        print("✅ PASS: Frontend is clean of console.log.")

    # 3. SILENT FAILURES (Bare Except)
    # -----------------------------
    print("\n[3] Scanning for Silent Failures (bare except:)...")
    bare_excepts = 0
    for root, dirs, files in os.walk(BACKEND_ROOT):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
             if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        if re.search(r'^\s*except:', f.read(), re.MULTILINE):
                            bare_excepts += 1
                except:
                    pass

    if bare_excepts > 0:
        print(f"❌ FAIL: Found {bare_excepts} files with bare 'except:' blocks.")
        # Penalty: 5 points per file, max 25
        penalty = min(25, bare_excepts * 5)
        score -= penalty
        issues.append(f"Reliability: {bare_excepts} files use dangerous bare 'except:' blocks.")
    else:
        print("✅ PASS: No bare 'except:' blocks found.")

    # 4. TECHNICAL DEBT (TODOs)
    # -------------------------
    print("\n[4] Scanning for Technical Debt (TODO/FIXME)...")
    todo_count = 0
    for root, dirs, files in os.walk(BACKEND_ROOT):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
             if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        cnt = f.read().upper().count("TODO") + f.read().upper().count("FIXME")
                        todo_count += cnt
                except:
                    pass

    if todo_count > 0:
        print(f"ℹ️ INFO: Found {todo_count} TODO/FIXME markers.")
        # Penalty: 1 point per 5 TODOs
        penalty = min(10, todo_count // 5)
        score -= penalty
        issues.append(f"Technical Debt: {todo_count} TODO/FIXME markers found.")
    else:
        print("✅ PASS: Zero technical debt markers.")

    # 5. CONFIGURATION RISK
    # ---------------------
    print("\n[5] Checking Configuration Security...")
    settings_path = os.path.join(BACKEND_ROOT, "smart_agri", "settings.py")
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if "DEBUG = True" in content:
                print("❌ CRITICAL: DEBUG = True found in settings.py!")
                score -= 40 # Huge penalty
                issues.append("Security: DEBUG = True is enabled.")
            else:
                print("✅ PASS: DEBUG seems disabled (or not explicitly True).")
                
            if "SECRET_KEY = 'django-insecure" in content:
                 print("❌ CRITICAL: Insecure default SECRET_KEY detected!")
                 score -= 30
                 issues.append("Security: Insecure default SECRET_KEY used.")
    except:
        print("⚠️ ERROR: Could not read settings.py")

    # SCORING
    final_score = max(0, score)
    print("\n========================================")
    print(f"REAL AGRI-GUARDIAN SCORE: {final_score}/100")
    print("========================================")
    
    if issues:
        print("Brutal Feedback:")
        for i in issues:
            print(f"- {i}")

if __name__ == '__main__':
    # Redirect stdout to file
    import sys
    original_stdout = sys.stdout
    with open('agri_guardian_level2_result.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        run_brutal_audit()
    sys.stdout = original_stdout
    # echo to console
    with open('agri_guardian_level2_result.txt', 'r', encoding='utf-8') as f:
        print(f.read())
