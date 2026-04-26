
import os

DIRS = [
    "smart_agri/core/migrations",
    "smart_agri/inventory/migrations",
    "smart_agri/sales/migrations",
    "smart_agri/accounts/migrations",
    "smart_agri/integrations/migrations"
]

def restore_init():
    for d in DIRS:
        if not os.path.exists(d):
            os.makedirs(d)
        init_file = os.path.join(d, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("")
            print(f"Created {init_file}")

if __name__ == "__main__":
    restore_init()
