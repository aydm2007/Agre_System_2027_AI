from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import IntegrityError, connection, transaction


ROLE_PERMISSIONS = {
    "مزارع": [
        "add_dailylog",
        "view_dailylog",
        "add_activity",
        "view_activity",
    ],
    "مشرف ميداني": [
        "add_dailylog",
        "change_dailylog",
        "view_dailylog",
        "add_activity",
        "change_activity",
        "view_activity",
        "view_iteminventory",
    ],
    "فني زراعي": [
        "view_dailylog",
        "change_dailylog",
        "view_activity",
        "change_activity",
        "view_iteminventory",
    ],
    "مدير المزرعة": [
        "view_dailylog",
        "change_dailylog",
        "view_activity",
        "change_activity",
        "delete_activity",
        "view_financialledger",
        "view_fiscalperiod",
        "change_fiscalperiod",
        "view_iteminventory",
        "view_farmgovernanceprofile",
        "change_farmgovernanceprofile",
        "view_roledelegation",
        "add_roledelegation",
    ],
    "أمين مخزن": [
        "view_iteminventory",
        "add_stockmovement",
        "view_stockmovement",
        "change_stockmovement",
    ],
    "أمين صندوق": [
        "view_cashbox",
        "add_treasurytransaction",
        "view_treasurytransaction",
    ],
    "محاسب المزرعة": [
        "view_financialledger",
        "view_actualexpense",
        "change_actualexpense",
        "can_manage_expenses",
    ],
    "رئيس الحسابات": [
        "view_financialledger",
        "view_actualexpense",
        "change_actualexpense",
        "can_manage_expenses",
        "can_post_treasury",
        "view_farmgovernanceprofile",
        "change_farmgovernanceprofile",
        "view_racitemplate",
        "add_racitemplate",
        "change_racitemplate",
        "view_roledelegation",
        "add_roledelegation",
        "change_roledelegation",
    ],
    "المدير المالي للمزرعة": [
        "view_financialledger",
        "view_actualexpense",
        "change_actualexpense",
        "can_manage_expenses",
        "can_post_treasury",
        "view_fiscalperiod",
        "change_fiscalperiod",
        "view_farmgovernanceprofile",
    ],
    "محاسب القطاع": [
        "view_financialledger",
        "view_actualexpense",
        "view_farmgovernanceprofile",
        "view_roledelegation",
    ],
    "مراجع القطاع": [
        "view_financialledger",
        "view_actualexpense",
        "view_cashbox",
        "view_treasurytransaction",
        "view_farm",
        "view_stockmovement",
        "view_iteminventory",
        "view_cropplan",
    ],
    "رئيس حسابات القطاع": [
        "view_financialledger",
        "view_actualexpense",
        "change_actualexpense",
        "can_manage_expenses",
        "view_farmgovernanceprofile",
        "change_farmgovernanceprofile",
        "view_racitemplate",
        "add_racitemplate",
        "change_racitemplate",
        "view_roledelegation",
        "add_roledelegation",
        "change_roledelegation",
    ],
    "المدير المالي لقطاع المزارع": [
        "view_financialledger",
        "view_actualexpense",
        "can_hard_close_period",
        "can_sector_finance_approve",
        "view_farmgovernanceprofile",
        "change_farmgovernanceprofile",
        "view_racitemplate",
        "view_roledelegation",
    ],
    "مدير القطاع": [
        "view_financialledger",
        "view_farmgovernanceprofile",
        "view_racitemplate",
        "view_roledelegation",
    ],
    "مدقق مالي": [
        "view_financialledger",
        "view_actualexpense",
        "view_cashbox",
        "view_treasurytransaction",
        "view_farm",
        "view_stockmovement",
        "view_iteminventory",
        "view_cropplan",
    ],
    "مهندس زراعي": [
        "view_farm",
        "add_cropplan",
        "change_cropplan",
        "view_cropplan",
        "add_activity",
        "change_activity",
        "view_activity",
        "view_dailylog",
    ],
    "مدير مبيعات": [
        "view_farm",
        "view_customer",
        "add_customer",
        "change_customer",
        "view_salesinvoice",
        "add_salesinvoice",
        "change_salesinvoice",
    ],
    "مسئول مشتريات": [
        "view_iteminventory",
        "add_stockmovement",
        "view_stockmovement",
        "view_cashbox",
        "view_actualexpense",
    ],
    "مدخل بيانات": [
        "view_farm",
        "add_dailylog",
        "change_dailylog",
        "view_dailylog",
        "add_activity",
        "view_activity",
    ],
    "مشاهد": [
        "view_farm",
        "view_cropplan",
        "view_activity",
        "view_dailylog",
        "view_financialledger",
        "view_iteminventory",
    ],
    "مدير النظام": [],
}


class Command(BaseCommand):
    help = "Seed YECO role groups with baseline permissions for farm + sector governance."

    def handle(self, *args, **options):
        created_groups = 0
        for group_name, codenames in ROLE_PERMISSIONS.items():
            group, created = self._get_or_create_group_safe(group_name)
            if created:
                created_groups += 1
            attached = 0
            for codename in codenames:
                perm = Permission.objects.filter(codename=codename).first()
                if not perm:
                    self.stdout.write(self.style.WARNING(f"Permission not found: {codename}"))
                    continue
                group.permissions.add(perm)
                attached += 1
            self.stdout.write(self.style.SUCCESS(f"{group_name}: permissions linked={attached}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Role seeding complete. groups_total={len(ROLE_PERMISSIONS)} created={created_groups}"
            )
        )

    def _get_or_create_group_safe(self, name):
        group = Group.objects.filter(name=name).first()
        if group:
            return group, False
        try:
            with transaction.atomic():
                return Group.objects.create(name=name), True
        except IntegrityError:
            self._sync_pk_sequence(Group)
            with transaction.atomic():
                return Group.objects.get_or_create(name=name)

    def _sync_pk_sequence(self, model):
        table = model._meta.db_table
        pk = model._meta.pk
        if pk.get_internal_type() not in {"AutoField", "BigAutoField", "SmallAutoField"}:
            return
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table}), 1),
                    true
                )
                """
            )
