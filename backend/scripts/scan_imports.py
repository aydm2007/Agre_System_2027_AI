
import os

ROOT_DIR = "smart_agri"
PATTERNS = [
    "from smart_agri.core.models.inventory",
    "import smart_agri.core.models.inventory",
    "from smart_agri.core.services.inventory_service",
    "import smart_agri.core.services.inventory_service",
    # Logic in files might import specific classes like 'Item' from core.models
    "from smart_agri.core.models import Item",
    "from smart_agri.core.models import Unit",
    "from smart_agri.core.models import ItemInventory",
    "from smart_agri.core.models import StockMovement"
]

def scan():
    print(f"🔍 Scanning {ROOT_DIR} for outdated imports...")
    for root, dirs, files in os.walk(ROOT_DIR):
        for file in files:
            if not file.endswith(".py"):
                continue
            
            path = os.path.join(root, file)
            # Skip the old file itself and new file
            if "core\\models\\inventory.py" in path: continue
            if "inventory\\models.py" in path: continue
            if "core\\services\\inventory_service.py" in path: continue
            if "inventory\\services.py" in path: continue

            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                found = []
                for p in PATTERNS:
                    if p in content:
                        found.append(p)
                
                if found:
                    print(f"📄 {path}: Found {len(found)} issues: {found}")
            except Exception as e:
                print(f"⚠️ Error reading {path}: {e}")

if __name__ == "__main__":
    scan()
