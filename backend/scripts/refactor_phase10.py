
import os

ROOT_DIR = "smart_agri"

REPLACEMENTS = [
    # Sales App Mappings
    ("from smart_agri.core.models.commercial import SalesInvoice", "from smart_agri.sales.models import SalesInvoice"),
    ("from smart_agri.core.models.commercial import Customer", "from smart_agri.sales.models import Customer"),
    ("import smart_agri.core.models.commercial", "import smart_agri.sales.models as sales_models"),
    
    # Finance App Mappings
    ("from smart_agri.core.models.finance import FinancialLedger", "from smart_agri.finance.models import FinancialLedger"),
    ("from smart_agri.core.models.finance import ActualExpense", "from smart_agri.finance.models import ActualExpense"),
    ("from smart_agri.core.models.finance import CostConfiguration", "from smart_agri.finance.models import CostConfiguration"),
    ("import smart_agri.core.models.finance", "import smart_agri.finance.models as finance_models"),

    # Service Mappings
    ("from smart_agri.core.services.financial_integrity_service", "from smart_agri.finance.services.financial_integrity_service"),
    
    # Generic Core Imports (Dangerous but necessary to patch common patterns)
    ("from smart_agri.core.models import SalesInvoice", "from smart_agri.sales.models import SalesInvoice"),
    ("from smart_agri.core.models import Customer", "from smart_agri.sales.models import Customer"),
    ("from smart_agri.core.models import FinancialLedger", "from smart_agri.finance.models import FinancialLedger"),
    ("from smart_agri.core.models import ActualExpense", "from smart_agri.finance.models import ActualExpense"),
]

def refactor():
    print("🚀 Starting Phase 10 Refactor...")
    count = 0
    for root, dirs, files in os.walk(ROOT_DIR):
        for file in files:
            if not file.endswith(".py"): continue
            
            # Skip migration files (they are historical)
            if "migrations" in root: continue
            
            path = os.path.join(root, file)
            
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            new_content = content
            for old, new in REPLACEMENTS:
                new_content = new_content.replace(old, new)
            
            if content != new_content:
                print(f"✏️ Patching: {path}")
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    count += 1
                except Exception as e:
                    print(f"❌ Error patching {path}: {e}")
    
    print(f"✅ Refactored {count} files.")

if __name__ == "__main__":
    refactor()
