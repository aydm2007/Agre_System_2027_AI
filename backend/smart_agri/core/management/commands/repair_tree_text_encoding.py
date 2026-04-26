from django.core.management.base import BaseCommand

from smart_agri.core.models import TreeLossReason, TreeProductivityStatus


def repair_mojibake(value):
    if not isinstance(value, str) or not value:
        return value
    if "Ø" not in value and "Ù" not in value:
        return value
    try:
        repaired = value.encode("latin-1").decode("utf-8")
        if any("\u0600" <= ch <= "\u06FF" for ch in repaired):
            return repaired
    except (UnicodeDecodeError, UnicodeEncodeError):
        return value
    return value


class Command(BaseCommand):
    help = "Repair mojibake Arabic text in TreeProductivityStatus/TreeLossReason labels."

    def handle(self, *args, **options):
        fixed_status = 0
        fixed_reason = 0
        canonical_status_ar = {
            "juvenile": "أشجار غير منتجة",
            "productive": "منتجة",
            "declining": "متراجعة",
            "dormant": "خاملة / تحت الصيانة",
        }

        for row in TreeProductivityStatus.objects.all():
            repaired = canonical_status_ar.get(row.code, repair_mojibake(row.name_ar))
            if repaired != row.name_ar:
                row.name_ar = repaired
                row.save(update_fields=["name_ar"])
                fixed_status += 1

        for row in TreeLossReason.objects.all():
            repaired = repair_mojibake(row.name_ar)
            if repaired != row.name_ar:
                row.name_ar = repaired
                row.save(update_fields=["name_ar"])
                fixed_reason += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Repaired labels: TreeProductivityStatus={fixed_status}, TreeLossReason={fixed_reason}"
            )
        )
