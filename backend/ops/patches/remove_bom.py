import os

files = [
    r"c:\tools\workspace\Agre_ERP_2027-main\backend/smart_agri/sales\services.py",
    r"c:\tools\workspace\Agre_ERP_2027-main\backend/smart_agri/core/services\costing.py",
    r"c:\tools\workspace\Agre_ERP_2027-main\backend/smart_agri/core/services\inventory_service.py",
    r"c:\tools\workspace\Agre_ERP_2027-main\backend/smart_agri/core/services\costing\__init__.py",
    r"c:\tools\workspace\Agre_ERP_2027-main\backend/smart_agri/core/services\inventory\service.py"
]

print("Scanning for BOM...")
for f in files:
    path = os.path.abspath(f)
    if os.path.exists(path):
        with open(path, "rb") as file:
            content = file.read()
        if content.startswith(b'\xef\xbb\xbf'):
            with open(path, "wb") as file:
                file.write(content[3:])
            print(f"Removed BOM from {path}")
        else:
            print(f"No BOM found in {path}")
    else:
        print(f"File not found: {path}")
