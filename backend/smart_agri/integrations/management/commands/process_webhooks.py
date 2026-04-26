
from django.core.management.base import BaseCommand
from django.utils import timezone
from time import sleep
from smart_agri.integrations.models import OutboundDelivery
from smart_agri.integrations.utils import _send

class Command(BaseCommand):
    help = "Process pending webhook deliveries with exponential backoff."

    def handle(self, *args, **opts):
        # Round 17: Fix Traffic Jam (HOL Blocking & Concurrency)
        from django.db import transaction
        from datetime import timedelta
        
        now = timezone.now()
        
        # 1. Filter efficiently (Don't fetch waiting items)
        # 2. Lock rows to prevent race conditions (select_for_update)
        with transaction.atomic():
            pend = OutboundDelivery.objects.select_for_update(skip_locked=True).filter(
                status__in=['pending','failed'],
                next_attempt_at__lte=now  # Only fetch ready items
            ).order_by('created_at')[:200]
            
            cnt = 0
            for d in pend:
                # Double check inside lock (optional but safe)
                if d.next_attempt_at and d.next_attempt_at > now:
                     continue
                     
                success = _send(d.id) # Assuming _send returns status or we check DB
                
                # Update next attempt if failed (Logic usually in _send or here)
                # Since _send is opaque here, we assume it updates status/attempts.
                # If we need to set next_attempt_at for retry:
                d.refresh_from_db()
                if d.status == 'failed':
                     wait_minutes = min(8, 2 ** max(0, d.attempts-1))
                     d.next_attempt_at = now + timedelta(minutes=wait_minutes)
                     d.save(update_fields=['next_attempt_at'])
                
                cnt += 1
                sleep(0.05)
                
        self.stdout.write(self.style.SUCCESS(f"Processed {cnt} deliveries"))
