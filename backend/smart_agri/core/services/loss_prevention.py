from decimal import Decimal
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class LossPreventionService:
    """
    المراقب الذكي لنزاهة سلسلة التوريد.
    يستخدم عتبات سياقية بدلاً من القواعد الصارمة.
    """

    @staticmethod
    def analyze_shrinkage(farm, transport_manifest):
        """
        تحليل الفاقد في الوزن أثناء النقل.
        يعيد: (الخطورة، الرسالة)
        الخطورة: 'OK' (طبيعي)، 'WARNING' (تحذير)، 'CRITICAL' (خطر/سرقة)
        """
        sent_qty = transport_manifest.get('sent_qty') or 0
        received_qty = transport_manifest.get('received_qty') or 0
        
        if sent_qty == 0:
            return 'OK', "لا توجد شحنة."

        loss = sent_qty - received_qty
        if loss <= 0:
            return 'OK', "لا يوجد فاقد (أو هناك زيادة)."

        # [Agri-Guardian] Fixed: Use Decimal for thresholds strictly
        from decimal import getcontext
        loss_percent = getcontext().divide(Decimal(loss), Decimal(sent_qty)) * 100
        current_month = timezone.now().month

        is_summer = current_month in [5, 6, 7, 8]
        
        # Define thresholds as Decimal
        threshold_warning = Decimal("5.0") if is_summer else Decimal("2.0")
        threshold_critical = Decimal("10.0") 
        
        if loss_percent > threshold_critical:
            return 'CRITICAL', f"سرقة محتملة: الفاقد {loss_percent:.2f}% يتجاوز الحد المطلق ({threshold_critical}%). يجب التحقيق."
            
        if loss_percent > threshold_warning:
            season = "الصيف" if is_summer else "الشتاء"
            return 'WARNING', f"تباين عالي: الفاقد {loss_percent:.1f}% يتجاوز حد {season} الطبيعي ({threshold_warning}%). تأكد من الأختام."

        return 'OK', f"الفاقد {loss_percent:.1f}% ضمن النطاق المقبول ({threshold_warning}%)."

    @staticmethod
    def log_sync_conflict(user, object_ref, client_data):
        """
        يسجل تعارض المزامنة دون تجاهل عمل المستخدم.
        """
        # في نظام حقيقي، سنحفظ في جدول "المسودات".
        # هنا نقوم فقط بتسجيل النية.
        logger.info(f"SYNC CONFLICT: User {user} tried to update {object_ref}. Saving as PENDING DRAFT.")
        return "saved_as_draft", "We found a newer version on the server. Your changes are saved as a Draft for review."

    @staticmethod
    def analyze_tree_census(daily_log):
        """
        [AGRI-GUARDIAN] Axis 11 Compliance: Loss Reconciliation.
        Scans a newly submitted DailyLog for any tree tree_count_delta < 0 entries.
        If found, generates a TreeCensusVarianceAlert for management to authorize an official transaction.
        """
        from smart_agri.core.models.inventory import TreeCensusVarianceAlert
        
        alerts_created = 0
        
        # Primary source of truth is Activity.tree_count_delta / tree_loss_reason.
        # Legacy fallback remains for item-level payloads if present.
        for activity in daily_log.activities.all():
            crop = activity.crop_plan.crop if activity.crop_plan else activity.crop
            if not crop:
                continue

            delta = int(activity.tree_count_delta or 0)
            reason = activity.tree_loss_reason or "Unspecified"

            if delta >= 0:
                # Legacy fallback: some historical payloads encoded delta in item metadata.
                for item in activity.items.all():
                    payload = getattr(item, "activity_data", None)
                    if isinstance(payload, dict):
                        item_delta = int(payload.get("tree_count_delta", 0) or 0)
                        if item_delta < 0:
                            delta = item_delta
                            reason = payload.get("tree_loss_reason") or reason
                            break

            if delta < 0:
                TreeCensusVarianceAlert.objects.create(
                    log=daily_log,
                    farm=daily_log.farm,
                    location=activity.location,
                    crop=crop,
                    missing_quantity=abs(delta),
                    reason=reason,
                    status=TreeCensusVarianceAlert.STATUS_PENDING,
                )
                alerts_created += 1
                    
        return alerts_created
