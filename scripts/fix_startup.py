import os
import sys
from pathlib import Path

def fix_startup():
    """
    Startup Sentinel: The Environment Healer
    Fixes common configuration issues preventing manage.py runserver.
    """
    import platform
    if platform.system() == 'Windows':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    print("🚑 Startup Sentinel is scanning your environment...")
    
    base_dir = Path(__file__).resolve().parent.parent
    settings_path = base_dir / "backend" / "smart_agri" / "settings.py"
    
    if not settings_path.exists():
        print(f"❌ Error: settings.py not found at {settings_path}")
        return

    # Check settings.py
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        fixes_needed = []
        
        # 1. ALLOWED_HOSTS check
        if 'ALLOWED_HOSTS = ["*"]' not in content and "ALLOWED_HOSTS = ['*']" not in content:
            valid_hosts = False
            for line in content.splitlines():
                if "ALLOWED_HOSTS" in line and "*" in line and not line.strip().startswith("#"):
                    valid_hosts = True
                    break
            
            if not valid_hosts:
                fixes_needed.append("ALLOWED_HOSTS")

        if fixes_needed:
            print(f"🔧 Applying fixes for: {', '.join(fixes_needed)}...")
            with open(settings_path, 'a', encoding='utf-8') as f:
                f.write('\n# [STARTUP SENTINEL PATCH] Emergency Fallback\n')
                if "ALLOWED_HOSTS" in fixes_needed:
                    f.write('ALLOWED_HOSTS = ["*"]\n')
            print("✅ Patched settings.py")
        else:
            print("✅ settings.py looks healthy (ALLOWED_HOSTS compliant).")

    except Exception as e:
        print(f"❌ Error reading settings.py: {e}")

    # Check DB connection string capability (just env check)
    env_path = base_dir / "backend" / ".env"
    if env_path.exists():
        print("✅ .env file found.")
    else:
        print("⚠️ .env file MISSING! Copying .env.example...")
        example = base_dir / "backend" / ".env.example"
        if example.exists():
            import shutil
            shutil.copy(example, env_path)
            print("✅ Created .env from example.")
        else:
            print("❌ .env.example also missing. Cannot create config.")

if __name__ == "__main__":
    fix_startup()
