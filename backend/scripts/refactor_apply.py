
import os
import re

ROOT_DIR = "smart_agri"

# Mapping of Old -> New logic
REPLACEMENTS = [
    # Services
    ("from smart_agri.core.services.inventory_service import InventoryService", "from smart_agri.inventory.services import InventoryService"),
    ("import smart_agri.core.services.inventory_service", "import smart_agri.inventory.services as inventory_service"),
    
    # Models Module
    ("from smart_agri.core.models.inventory", "from smart_agri.inventory.models"),
    ("import smart_agri.core.models.inventory", "import smart_agri.inventory.models"),
    
    # Specific Class Imports from base core.models (Tricky, handle with Regex or precise strings)
    # Often imports look like: from smart_agri.core.models import Farm, Item, User
    # We need to split this. This is hard to regex safely in one go.
    # STRATEGY: We will warn about mixed imports but fix explicit sub-module imports first.
]

def refactor():
    print("🚀 Starting Refactor...")
    count = 0
    for root, dirs, files in os.walk(ROOT_DIR):
        for file in files:
            if not file.endswith(".py"): continue
            
            # Skip the definition files themselves to avoid circular refactor
            if "core\\models\\inventory.py" in os.path.join(root, file): continue
            
            path = os.path.join(root, file)
            
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            new_content = content
            for old, new in REPLACEMENTS:
                new_content = new_content.replace(old, new)
            
            # Special Case: "from smart_agri.core.models import ..., Item, ..."
            # This is dangerous to regex blindly.
            # We will log these for manual check or simpler regex if possible.
            
            if content != new_content:
                print(f"✏️ Patching: {path}")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                count += 1
    
    print(f"✅ Refactored {count} files.")

if __name__ == "__main__":
    refactor()
