"""
Receipt & Deposit Service - PRD V21 §12.7
[AGENTS.md Rules 1, 2, 4, 5, 10]

Governed service-layer entry point for receipt collection, treasury deposit,
and reconciliation within the append-only financial framework.

SIMPLE: collection posture + anomaly visibility
STRICT: full treasury + deposit trace
"""

import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

STATUS_DRAFT = "DRAFT"
STATUS_COLLECTED = "COLLECTED"
STATUS_DEPOSITED = "DEPOSITED"
STATUS_RECONCILED = "RECONCILED"
STATUS_ANOMALY = "ANOMALY"

VALID_TRANSITIONS = {
    STATUS_DRAFT: {STATUS_COLLECTED},
    STATUS_COLLECTED: {STATUS_DEPOSITED, STATUS_ANOMALY},
    STATUS_DEPOSITED: {STATUS_RECONCILED, STATUS_ANOMALY},
    STATUS_ANOMALY: {STATUS_DRAFT},
    STATUS_RECONCILED: set(),
}


class ReceiptDepositService:
    """
    Service for managing receipt collection, treasury deposit, and reconciliation.

    Lifecycle: DRAFT -> COLLECTED -> DEPOSITED -> RECONCILED
                 v
               ANOMALY -> DRAFT
    """

    @staticmethod
    def _validate_transition(current_status: str, target_status: str) -> None:
        allowed = VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise ValidationError(
                f"لا يمكن الانتقال من حالة '{current_status}' إلى '{target_status}'. "
                f"الانتقالات المسموحة: {allowed or 'لا يوجد (حالة نهائية)'}"
            )

    @staticmethod
    def _ensure_positive_amount(amount) -> Decimal:
        if not isinstance(amount, Decimal):
            raise ValidationError("يجب أن يكون المبلغ من نوع Decimal. استخدام float ممنوع.")
        if amount <= 0:
            raise ValidationError("يجب أن يكون المبلغ أكبر من صفر.")
        return amount

    @staticmethod
    def _acquire_idempotency(*, key: str, user, farm, path: str, body: dict):
        from smart_agri.core.services.idempotency import IdempotencyService

        return IdempotencyService.acquire_lock(
            key=key,
            user=user,
            method="POST",
            path=path,
            body=body,
            farm_id=farm.id,
        )

    @staticmethod
    def _commit_success(*, record, response_body: dict, object_id, model_name: str):
        from smart_agri.core.services.idempotency import IdempotencyService

        IdempotencyService.commit_success(
            record,
            response_status=200,
            response_body=response_body,
            object_id=object_id,
            model_name=model_name,
        )

    @staticmethod
    def _commit_failure(*, record):
        from smart_agri.core.services.idempotency import IdempotencyService

        IdempotencyService.commit_failure(record)

    @staticmethod
    @transaction.atomic
    def record_collection(
        *,
        farm,
        user,
        amount: Decimal,
        source_description: str,
        idempotency_key: str,
        cost_center=None,
        crop_plan=None,
        reference: str = "",
    ) -> dict:
        from smart_agri.finance.services.core_finance import FinanceService
        from smart_agri.core.models.log import AuditLog

        ReceiptDepositService._ensure_positive_amount(amount)
        FinanceService.check_fiscal_period(timezone.localdate(), farm, strict=True)

        record, is_replay, response_tuple = ReceiptDepositService._acquire_idempotency(
            key=idempotency_key,
            user=user,
            farm=farm,
            path=f"/receipt-deposit/{farm.id}/collection/",
            body={
                "amount": str(amount),
                "source_description": source_description,
                "reference": reference,
                "cost_center_id": getattr(cost_center, "id", None),
                "crop_plan_id": getattr(crop_plan, "id", None),
            },
        )
        if is_replay:
            logger.info("Idempotent replay for receipt collection: %s", idempotency_key)
            return response_tuple[1]

        try:
            audit = AuditLog.objects.create(
                actor=user,
                model="ReceiptCollection",
                object_id=reference or idempotency_key,
                action="RECEIPT_COLLECTED",
                farm=farm,
                reason=f"Receipt collected from {source_description}",
                new_payload={
                    "amount": str(amount),
                    "source_description": source_description,
                    "reference": reference,
                    "idempotency_key": idempotency_key,
                    "cost_center_id": getattr(cost_center, "id", None),
                    "crop_plan_id": getattr(crop_plan, "id", None),
                },
            )
            result = {
                "receipt_id": audit.id,
                "status": STATUS_COLLECTED,
                "amount": str(amount),
                "source": source_description,
                "reference": reference,
                "collected_at": timezone.now().isoformat(),
                "collected_by": user.id,
                "replayed": False,
            }
            ReceiptDepositService._commit_success(
                record=record,
                response_body=result,
                object_id=audit.id,
                model_name="ReceiptCollection",
            )
            logger.info(
                "Receipt collected: farm=%s amount=%s source=%s user=%s",
                farm.id,
                amount,
                source_description,
                user.id,
            )
            return result
        except (TypeError, ValueError, ValidationError):
            ReceiptDepositService._commit_failure(record=record)
            raise

    @staticmethod
    @transaction.atomic
    def record_deposit(
        *,
        receipt_id: int,
        farm,
        user,
        deposit_reference: str,
        idempotency_key: str,
        deposit_account: str = "",
    ) -> dict:
        from smart_agri.finance.services.core_finance import FinanceService
        from smart_agri.core.models.log import AuditLog

        FinanceService.check_fiscal_period(timezone.localdate(), farm, strict=True)

        record, is_replay, response_tuple = ReceiptDepositService._acquire_idempotency(
            key=idempotency_key,
            user=user,
            farm=farm,
            path=f"/receipt-deposit/{farm.id}/deposit/",
            body={
                "receipt_id": receipt_id,
                "deposit_reference": deposit_reference,
                "deposit_account": deposit_account,
            },
        )
        if is_replay:
            logger.info("Idempotent replay for receipt deposit: %s", idempotency_key)
            return response_tuple[1]

        try:
            audit = AuditLog.objects.create(
                actor=user,
                model="ReceiptDeposit",
                object_id=str(receipt_id),
                action="RECEIPT_DEPOSITED",
                farm=farm,
                reason=f"Receipt {receipt_id} deposited",
                new_payload={
                    "receipt_id": receipt_id,
                    "deposit_reference": deposit_reference,
                    "deposit_account": deposit_account or "default",
                    "idempotency_key": idempotency_key,
                },
            )
            result = {
                "receipt_id": receipt_id,
                "status": STATUS_DEPOSITED,
                "deposit_reference": deposit_reference,
                "deposited_at": timezone.now().isoformat(),
                "deposited_by": user.id,
                "replayed": False,
            }
            ReceiptDepositService._commit_success(
                record=record,
                response_body=result,
                object_id=audit.id,
                model_name="ReceiptDeposit",
            )
            logger.info(
                "Receipt deposited: receipt=%s farm=%s ref=%s user=%s",
                receipt_id,
                farm.id,
                deposit_reference,
                user.id,
            )
            return result
        except (TypeError, ValueError, ValidationError):
            ReceiptDepositService._commit_failure(record=record)
            raise

    @staticmethod
    @transaction.atomic
    def reconcile(
        *,
        receipt_id: int,
        farm,
        user,
        reconciliation_note: str = "",
    ) -> dict:
        from smart_agri.core.models.log import AuditLog

        AuditLog.objects.create(
            actor=user,
            model="ReceiptReconciliation",
            object_id=str(receipt_id),
            action="RECEIPT_RECONCILED",
            farm=farm,
            reason="Receipt reconciled",
            new_payload={
                "receipt_id": receipt_id,
                "reconciliation_note": reconciliation_note or "",
            },
        )

        logger.info(
            "Receipt reconciled: receipt=%s farm=%s user=%s",
            receipt_id,
            farm.id,
            user.id,
        )

        return {
            "receipt_id": receipt_id,
            "status": STATUS_RECONCILED,
            "reconciled_at": timezone.now().isoformat(),
            "reconciled_by": user.id,
        }

    @staticmethod
    @transaction.atomic
    def flag_anomaly(
        *,
        receipt_id: int,
        farm,
        user,
        anomaly_reason: str,
    ) -> dict:
        if not anomaly_reason or not anomaly_reason.strip():
            raise ValidationError("يجب تحديد سبب الشذوذ.")

        from smart_agri.core.models.log import AuditLog

        AuditLog.objects.create(
            actor=user,
            model="ReceiptAnomaly",
            object_id=str(receipt_id),
            action="RECEIPT_ANOMALY_FLAGGED",
            farm=farm,
            reason="Receipt anomaly flagged",
            new_payload={
                "receipt_id": receipt_id,
                "anomaly_reason": anomaly_reason.strip(),
            },
        )

        logger.info(
            "Receipt anomaly flagged: receipt=%s farm=%s reason=%s user=%s",
            receipt_id,
            farm.id,
            anomaly_reason,
            user.id,
        )

        return {
            "receipt_id": receipt_id,
            "status": STATUS_ANOMALY,
            "anomaly_reason": anomaly_reason.strip(),
            "flagged_at": timezone.now().isoformat(),
            "flagged_by": user.id,
        }
