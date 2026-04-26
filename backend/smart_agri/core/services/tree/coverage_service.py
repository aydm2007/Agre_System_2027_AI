"""
خدمة إدارة تغطية الخدمات للأشجار.

تم استخراج هذه الخدمة من TreeInventoryService كجزء من إعادة الهيكلة المعمارية.
مسؤولة عن إدارة سجلات TreeServiceCoverage المرتبطة بالأنشطة.

FORENSIC AUDIT REFACTORING (2026-01-24): Phase 4 - Architectural Refactoring
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Sequence, Tuple

from django.core.exceptions import ValidationError
from django.db import connection, transaction

from smart_agri.core.models import (
    Activity,
    LocationTreeStock,
    TreeServiceCoverage,
)

logger = logging.getLogger(__name__)


class TreeServiceCoverageService:
    """
    خدمة مخصصة لإدارة تغطية الخدمات للأشجار.
    
    المسؤوليات:
    - مزامنة سجلات TreeServiceCoverage مع بيانات الأنشطة
    - التحقق من صحة عدد الأشجار المخدومة
    - إدارة دورة حياة السجلات (إنشاء/تحديث/حذف)
    """

    def sync_coverages(
        self,
        *,
        activity: Activity,
        entries: Sequence[Dict[str, Any]],
        recorded_by=None,
    ) -> int:
        """
        مزامنة سجلات تغطية الخدمات للنشاط المحدد.
        
        المعاملات:
            activity: النشاط المرتبط بالتغطيات
            entries: قائمة ببيانات التغطيات المطلوبة
            recorded_by: المستخدم الذي سجل التغطيات
            
        الإرجاع:
            عدد السجلات التي تم إنشاؤها أو تحديثها
            
        الاستثناءات:
            ValidationError: عند فشل التحقق من صحة البيانات
        """
        if activity is None:
            raise ValidationError({"activity": "النشاط مطلوب"})

        payloads = list(entries or [])
        created_or_updated = 0
        
        with transaction.atomic():
            existing_qs = TreeServiceCoverage.objects.filter(activity=activity)
            if connection.vendor == "postgresql":
                existing_qs = existing_qs.select_for_update()
            
            existing_map: Dict[Tuple[int, str], TreeServiceCoverage] = {
                (coverage.crop_variety_id, coverage.service_scope): coverage
                for coverage in existing_qs
            }

            # إذا لم تكن هناك بيانات، احذف الموجود
            if not payloads:
                if existing_map:
                    TreeServiceCoverage.objects.filter(
                        pk__in=[cov.pk for cov in existing_map.values()]
                    ).delete()
                return 0

            seen_keys: set[Tuple[int, str]] = set()
            log = getattr(activity, "log", None)

            for payload in payloads:
                result = self._process_coverage_payload(
                    activity=activity,
                    payload=payload,
                    existing_map=existing_map,
                    seen_keys=seen_keys,
                    log=log,
                    recorded_by=recorded_by,
                )
                if result:
                    created_or_updated += 1

            # حذف السجلات القديمة غير الموجودة في البيانات الجديدة
            stale_ids = [cov.pk for key, cov in existing_map.items() if key not in seen_keys]
            if stale_ids:
                TreeServiceCoverage.objects.filter(pk__in=stale_ids).delete()

        return created_or_updated

    def _process_coverage_payload(
        self,
        *,
        activity: Activity,
        payload: Dict[str, Any],
        existing_map: Dict[Tuple[int, str], TreeServiceCoverage],
        seen_keys: set[Tuple[int, str]],
        log,
        recorded_by,
    ) -> bool:
        """معالجة سجل تغطية واحد. ترجع True إذا تم إنشاء أو تحديث."""
        location = payload.get("location")
        variety = payload.get("crop_variety")
        
        if not location or not variety:
            raise ValidationError({
                "service_counts": "يجب تحديد الموقع والصنف"
            })

        service_scope = (
            payload.get("service_scope")
            or payload.get("service_type")
            or TreeServiceCoverage.GENERAL
        )
        service_type = payload.get("service_type") or service_scope
        key = (variety.pk, service_scope)
        seen_keys.add(key)

        service_count = int(payload.get("service_count") or 0)
        
        if service_count < 0:
            raise ValidationError({
                "service_counts": "لا يمكن أن يكون عدد الأشجار المخدومة سالباً"
            })

        # التحقق من عدد الأشجار المتاح
        self._validate_service_count(activity, location, variety, service_count)

        defaults = {
            "location": location,
            "service_count": service_count,
            "service_type": service_type,
            "service_scope": service_scope,
            "total_before": payload.get("total_before"),
            "total_after": payload.get("total_after"),
            "notes": payload.get("notes") or "",
            "source_log": log,
        }
        if recorded_by is not None:
            defaults["recorded_by"] = recorded_by

        existing = existing_map.get(key)
        if existing is None:
            new_record = TreeServiceCoverage.objects.create(
                activity=activity,
                crop_variety=variety,
                **defaults
            )
            existing_map[key] = new_record
            return True

        # تحديث السجل الموجود
        update_fields = []
        for attr, value in defaults.items():
            if getattr(existing, attr) != value:
                setattr(existing, attr, value)
                update_fields.append(attr)
        
        if update_fields:
            existing.save(update_fields=update_fields)
            return True
            
        return False

    def _validate_service_count(
        self,
        activity: Activity,
        location,
        variety,
        service_count: int,
    ) -> None:
        """التحقق من أن عدد الأشجار المخدومة لا يتجاوز المتاح."""
        # تخطي التحقق للأنشطة المخططة (المستقبلية)
        is_planned = getattr(activity, "crop_plan_id", None) is not None
        if is_planned:
            return

        stock = (
            LocationTreeStock.objects.filter(
                location=location,
                crop_variety=variety,
            )
            .only("current_tree_count")
            .first()
        )

        if stock and service_count > (stock.current_tree_count or 0):
            raise ValidationError({
                "service_counts": (
                    f"عدد الأشجار المخدومة ({service_count}) يتجاوز "
                    f"العدد المتاح ({stock.current_tree_count})"
                )
            })

    def delete_for_activity(self, activity: Activity) -> int:
        """حذف جميع سجلات التغطية للنشاط المحدد."""
        if activity is None:
            return 0  # Valid for count return type
        return TreeServiceCoverage.objects.filter(activity=activity).delete()[0]
