import os
import re
import sys

def check_security_hardening():
    """
    [M3.7] Verifies settings.py for secure ALLOWED_HOSTS and dynamic SECRET_KEY.
    Also ensures .env.example lacks hardcoded real passwords.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    settings_path = os.path.join(base_dir, "backend", "config", "settings.py")
    env_example_path = os.path.join(base_dir, ".env.example")
    
    errors = []
    
    # 1. Check settings.py
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            # Check for ALLOWED_HOSTS = ['*']
            if re.search(r"ALLOWED_HOSTS\s*=\s*\[\s*['\"]\*['\"]\s*\]", content):
                errors.append("settings.py contains ALLOWED_HOSTS = ['*'], which is prohibited in hardening.")
                
            # Check if SECRET_KEY is read from env
            if not re.search(r"SECRET_KEY\s*=\s*(os\.environ|env|config)\(", content):
                errors.append("settings.py must read SECRET_KEY dynamically from environment variables.")
    else:
        errors.append(f"Could not find settings file at {settings_path}")
        
    # 2. Check .env.example
    if os.path.exists(env_example_path):
        with open(env_example_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            # Look for DB_PASSWORD=something that isn't a placeholder
            for line in content.splitlines():
                if "PASSWORD" in line.upper() and "=" in line:
                    val = line.split("=", 1)[1].strip()
                    if val and val not in ["your_password_here", "postgres", "placeholder", ""]:
                        errors.append(f".env.example contains a potential real password: {line}")
    else:
        pass # Not strictly required if it doesn't exist, but good to check 
        
    if errors:
        print("[FAIL] Security hardening checks failed:")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("[PASS] Security hardening checks passed. Secret key is dynamic, hosts are bound, and passwords are placeholders.")
        return 0

if __name__ == "__main__":
    sys.exit(check_security_hardening())
