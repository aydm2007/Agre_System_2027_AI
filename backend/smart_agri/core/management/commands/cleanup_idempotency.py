from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from smart_agri.core.models.log import IdempotencyRecord

class Command(BaseCommand):
    help = 'Cleans up expired Idempotency Records to prevent disk filling.'

    def handle(self, *args, **options):
        retention_period = timedelta(hours=24)
        cutoff = timezone.now() - retention_period
        
        count, _ = IdempotencyRecord.objects.filter(created_at__lt=cutoff).delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {count} expired idempotency records.')
        )
