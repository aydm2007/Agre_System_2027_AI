import subprocess
import sys

def install():
    print("🚀 Starting dependency installation...")
    try:
        # Upgrade pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        # Install requirements
        cmd = [sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"]
        print(f"Running: {' '.join(cmd)}")
        subprocess.check_call(cmd)
        print("✅ Installation Successful!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Verification failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    install()
