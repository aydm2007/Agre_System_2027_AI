import sys
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from smart_agri.accounts.models import PermissionTemplate
from smart_agri.finance.models import ApprovalRule

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds V21 foundational data (Governance Roles, Permissions, Approval Rules)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting V21 Foundation Seeding..."))
        
        # 1. Governance Roles (RoleTemplateMatrix)
        self.stdout.write("Seeding Governance Role Templates...")
        roles = [
            ("محاسب المزرعة", "farm_accountant", "إدخال العمليات اليومية والسجلات للمزرعة", True),
            ("رئيس حسابات المزرعة", "farm_chief_accountant", "مراجعة محلية واعتماد مبدئي لإغلاق المزرعة", True),
            ("المدير المالي للمزرعة", "farm_finance_manager", "اعتماد مالي نهائي للمزرعة في المود الصارم", True),
            ("محاسب القطاع", "sector_accountant", "مراجعة أولية وتدقيق لعمليات المزارع", True),
            ("مراجع القطاع", "sector_reviewer", "مراجعة استثنائية (Maker-Checker) واعتراضات", True),
            ("رئيس حسابات القطاع", "sector_chief_accountant", "إقفال مالي دوري للقطاع", True),
            ("المدير المالي للقطاع", "sector_finance_director", "الاعتماد النهائي للقطاع المالي", True),
        ]

        for name, slug, desc, is_sys in roles:
            obj, created = PermissionTemplate.objects.get_or_create(
                slug=slug, 
                defaults={"name": name, "description": desc, "is_system": is_sys}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  + Created Role: {name}"))

        self.stdout.write(self.style.SUCCESS("V21 Foundation Seeding Complete!"))
