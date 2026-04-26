from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from smart_agri.core.api.permissions import _ensure_user_has_farm_access
from smart_agri.finance.models import FinancialLedger

from .models import ExternalFinanceBatch, ExternalFinanceLine


@dataclass(slots=True)
class ExternalFinanceBatchResult:
    batch: ExternalFinanceBatch
    line_count: int
    status: str
    total_debit: Decimal
    total_credit: Decimal
    detail: str = ""


class ExternalFinanceBatchService:
    @staticmethod
    @transaction.atomic
    def create_batch(*, user: Any, validated_data: dict[str, Any]) -> ExternalFinanceBatch:
        farm = validated_data.get("farm")
        _ensure_user_has_farm_access(user, farm.id if farm else None)
        return ExternalFinanceBatch.objects.create(**validated_data)

    @staticmethod
    @transaction.atomic
    def build_from_ledger(*, user: Any, batch_id: int) -> ExternalFinanceBatchResult:
        batch = ExternalFinanceBatch.objects.select_for_update().get(pk=batch_id)
        _ensure_user_has_farm_access(user, batch.farm_id)
        ExternalFinanceLine.objects.filter(batch=batch).delete()

        ledger_rows = FinancialLedger.objects.filter(
            farm_id=batch.farm_id,
            created_at__date__gte=batch.period_start,
            created_at__date__lte=batch.period_end,
        ).order_by("created_at", "id")
        lines = [
            ExternalFinanceLine(
                batch=batch,
                ledger_id=str(row.id),
                account_code=row.account_code,
                debit=row.debit,
                credit=row.credit,
                description=row.description or "",
                currency=row.currency or "YER",
                entity_ref=str(row.entity_object_id or ""),
            )
            for row in ledger_rows
        ]
        ExternalFinanceLine.objects.bulk_create(lines, batch_size=500)

        totals = batch.lines.aggregate(debit=Sum("debit"), credit=Sum("credit"))
        total_debit = Decimal(str(totals.get("debit") or 0)).quantize(Decimal("0.0001"))
        total_credit = Decimal(str(totals.get("credit") or 0)).quantize(Decimal("0.0001"))
        line_count = batch.lines.count()

        payload = {
            "farm_id": batch.farm_id,
            "period_start": str(batch.period_start),
            "period_end": str(batch.period_end),
            "line_count": line_count,
        }

        batch.total_debit = total_debit
        batch.total_credit = total_credit
        batch.payload = payload

        if total_debit != total_credit:
            batch.status = ExternalFinanceBatch.STATUS_FAILED
            batch.payload = {**payload, "error": "Unbalanced journal batch: debit != credit"}
            batch.save(update_fields=["status", "payload", "total_debit", "total_credit", "updated_at"])
            return ExternalFinanceBatchResult(
                batch=batch,
                line_count=line_count,
                status=batch.status,
                total_debit=total_debit,
                total_credit=total_credit,
                detail="External batch is unbalanced and cannot be exported.",
            )

        batch.status = ExternalFinanceBatch.STATUS_EXPORTED
        batch.exported_by = user
        batch.exported_at = timezone.now()
        batch.save(update_fields=[
            "total_debit", "total_credit", "payload", "status", "exported_by", "exported_at", "updated_at"
        ])
        return ExternalFinanceBatchResult(
            batch=batch,
            line_count=line_count,
            status=batch.status,
            total_debit=total_debit,
            total_credit=total_credit,
            detail="exported",
        )

    @staticmethod
    @transaction.atomic
    def acknowledge_batch(*, user: Any, batch_id: int, external_ref: str) -> ExternalFinanceBatchResult:
        batch = ExternalFinanceBatch.objects.select_for_update().get(pk=batch_id)
        _ensure_user_has_farm_access(user, batch.farm_id)
        ext = str(external_ref or "").strip()
        if not ext:
            raise ValueError("external_ref is required")
        batch.external_ref = ext
        batch.status = ExternalFinanceBatch.STATUS_ACK
        batch.acknowledged_at = timezone.now()
        batch.save(update_fields=["external_ref", "status", "acknowledged_at", "updated_at"])
        return ExternalFinanceBatchResult(
            batch=batch,
            line_count=batch.lines.count(),
            status=batch.status,
            total_debit=Decimal(str(batch.total_debit or 0)).quantize(Decimal("0.0001")),
            total_credit=Decimal(str(batch.total_credit or 0)).quantize(Decimal("0.0001")),
            detail="acknowledged",
        )
