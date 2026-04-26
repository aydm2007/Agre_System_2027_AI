from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings, RemoteReviewLog, RemoteReviewEscalation


class RemoteReviewService:
    """Governed weekly remote review controls for small remote farms."""
    REVIEW_WINDOW_DAYS = 7
    OVERDUE_GRACE_DAYS = 3

    @classmethod
    def _review_window_days(cls, farm_settings: FarmSettings) -> int:
        return int(getattr(farm_settings, "remote_review_interval_days", cls.REVIEW_WINDOW_DAYS) or cls.REVIEW_WINDOW_DAYS)

    @classmethod
    def _overdue_grace_days(cls, farm_settings: FarmSettings) -> int:
        return int(getattr(farm_settings, "remote_review_overdue_grace_days", cls.OVERDUE_GRACE_DAYS) or cls.OVERDUE_GRACE_DAYS)

    @staticmethod
    def _open_escalation(farm, level: str, reason: str):
        existing = RemoteReviewEscalation.objects.filter(farm=farm, level=level, resolved_at__isnull=True).first()
        if existing:
            return existing
        return RemoteReviewEscalation.objects.create(farm=farm, level=level, reason=(reason or '')[:255])

    @staticmethod
    def _resolve_open_escalations(farm, note: str = 'review_completed'):
        RemoteReviewEscalation.objects.filter(farm=farm, resolved_at__isnull=True).update(
            resolved_at=timezone.now(),
            resolution_note=(note or '')[:255],
        )

    @staticmethod
    def last_review(farm_id: int):
        return RemoteReviewLog.objects.filter(farm_id=farm_id).order_by('-reviewed_at').first()

    @classmethod
    def review_due(cls, farm_settings: FarmSettings) -> bool:
        if not farm_settings or not farm_settings.remote_site or not farm_settings.weekly_remote_review_required:
            return False
        last = cls.last_review(farm_settings.farm_id)
        if not last:
            return True
        return last.reviewed_at < timezone.now() - timedelta(days=cls._review_window_days(farm_settings))

    @classmethod
    def list_due_farms(cls):
        rows = []
        qs = FarmSettings.objects.select_related('farm').filter(remote_site=True, weekly_remote_review_required=True)
        for settings in qs:
            if cls.review_due(settings):
                last = cls.last_review(settings.farm_id)
                escalation = cls._open_escalation(settings.farm, RemoteReviewEscalation.LEVEL_OVERDUE, 'weekly_remote_review_overdue')
                rows.append({
                    'farm_id': settings.farm_id,
                    'farm_name': settings.farm.name,
                    'last_review_at': last.reviewed_at.isoformat() if last else None,
                    'escalation_id': escalation.id,
                })
        return rows

    @staticmethod
    def record_review(*, farm: Farm, reviewer, notes: str = '', exceptions_found: int = 0, review_type: str = 'weekly'):
        entry = RemoteReviewLog.objects.create(
            farm=farm,
            reviewed_by=reviewer,
            notes=notes,
            exceptions_found=exceptions_found,
            review_type=review_type,
        )
        RemoteReviewService._resolve_open_escalations(farm, note='weekly_review_logged')
        return entry

    @classmethod
    def is_overdue(cls, farm_settings: FarmSettings) -> bool:
        if not cls.review_due(farm_settings):
            return False
        last = cls.last_review(farm_settings.farm_id)
        overdue_anchor = timezone.now() - timedelta(days=cls._review_window_days(farm_settings) + cls._overdue_grace_days(farm_settings))
        if not last:
            return True
        return last.reviewed_at < overdue_anchor

    @classmethod
    def overdue_farms(cls):
        rows = []
        qs = FarmSettings.objects.select_related('farm').filter(remote_site=True, weekly_remote_review_required=True)
        for settings in qs:
            if cls.is_overdue(settings):
                last = cls.last_review(settings.farm_id)
                escalation = cls._open_escalation(settings.farm, RemoteReviewEscalation.LEVEL_DUE, 'weekly_remote_review_due')
                rows.append({
                    'farm_id': settings.farm_id,
                    'farm_name': settings.farm.name,
                    'last_review_at': last.reviewed_at.isoformat() if last else None,
                    'escalation_id': escalation.id,
                })
        return rows

    @classmethod
    def enforce_finance_window(cls, *, farm_settings: FarmSettings):
        if getattr(farm_settings, 'remote_site', False) and getattr(farm_settings, 'weekly_remote_review_required', False) and cls.is_overdue(farm_settings):
            cls._open_escalation(farm_settings.farm, RemoteReviewEscalation.LEVEL_BLOCKED, 'strict_finance_blocked_due_review_overdue')
            raise ValidationError('المزرعة البعيدة متأخرة في المراجعة القطاعية؛ أوقف النظام بعض إجراءات STRICT حتى تتم المراجعة.')

    @classmethod
    def report_due_reviews(cls):
        rows = []
        qs = FarmSettings.objects.select_related('farm').filter(remote_site=True, weekly_remote_review_required=True)
        now = timezone.now()
        for settings in qs:
            if not cls.review_due(settings):
                continue
            last = cls.last_review(settings.farm_id)
            reviewed_at = last.reviewed_at if last else None
            days_since = None
            if reviewed_at is not None:
                days_since = max((now - reviewed_at).days, 0)
            is_overdue = cls.is_overdue(settings)
            open_levels = list(RemoteReviewEscalation.objects.filter(farm=settings.farm, resolved_at__isnull=True).values_list('level', flat=True))
            approval_profile = getattr(settings, 'approval_profile', None)
            rows.append({
                'farm_id': settings.farm_id,
                'farm_name': settings.farm.name,
                'last_review_at': reviewed_at.isoformat() if reviewed_at else None,
                'days_since_last_review': days_since,
                'is_overdue': is_overdue,
                'review_status': 'OVERDUE' if is_overdue else 'DUE',
                'block_strict_finance': bool(is_overdue and getattr(settings, 'remote_site', False) and getattr(settings, 'weekly_remote_review_required', False)),
                'approval_profile': approval_profile,
                'farm_tier': (getattr(settings.farm, 'tier', None) or 'SMALL').upper(),
                'sector_owner_role': 'مدير القطاع' if is_overdue else 'المدير المالي لقطاع المزارع',
                'open_escalation_levels': open_levels,
            })
        return rows

    @classmethod
    def governance_snapshot(cls):
        due_rows = cls.report_due_reviews()
        open_escalations = RemoteReviewEscalation.objects.filter(resolved_at__isnull=True)
        return {
            'due_count': len(due_rows),
            'overdue_count': sum(1 for row in due_rows if row.get('is_overdue')),
            'open_escalations': open_escalations.count(),
            'blocked_escalations': open_escalations.filter(level=RemoteReviewEscalation.LEVEL_BLOCKED).count(),
            'farms': due_rows[:25],
            'generated_at': timezone.now().isoformat(),
        }

