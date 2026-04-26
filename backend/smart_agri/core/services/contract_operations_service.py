from decimal import Decimal, InvalidOperation
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from smart_agri.core.models.log import AuditLog
from smart_agri.core.models.partnerships import SharecroppingContract, SharecroppingReceipt
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.models import FinancialLedger
ZERO = Decimal("0.0000")


class ContractOperationsService:
    @staticmethod
    def _line_amounts_visible(policy_snapshot) -> bool:
        return (
            policy_snapshot["visibility_level"] == "full_erp"
            and policy_snapshot["cost_visibility"] == FarmSettings.COST_VISIBILITY_FULL
        )

    @staticmethod
    def _get_farm_settings(farm):
        settings, _ = FarmSettings.objects.get_or_create(farm=farm)
        return settings

    @staticmethod
    def _get_rent_audits(contract):
        return list(
            AuditLog.objects.filter(
                action="RENT_PAYMENT",
                model="SharecroppingContract",
                object_id=str(contract.id),
            ).order_by("-timestamp")
        )

    @staticmethod
    def _sum_rent_paid(audits):
        total = ZERO
        for entry in audits:
            try:
                total += Decimal(str(entry.new_payload.get("amount", "0"))).quantize(ZERO)
            except (InvalidOperation, TypeError, ValueError):
                continue
        return total

    @staticmethod
    def _build_contract_row(contract):
        settings = ContractOperationsService._get_farm_settings(contract.farm)
        policy_snapshot = settings.policy_snapshot()
        line_amounts_visible = ContractOperationsService._line_amounts_visible(policy_snapshot)
        latest_assessment = contract.touring_assessments.order_by("-assessment_date", "-id").first()
        latest_receipt = (
            SharecroppingReceipt.objects.filter(assessment__contract=contract)
            .select_related("assessment", "destination_inventory")
            .order_by("-receipt_date", "-id")
            .first()
        )
        rent_audits = ContractOperationsService._get_rent_audits(contract)
        rent_paid_total = ContractOperationsService._sum_rent_paid(rent_audits)
        last_rent_payment = rent_audits[0] if rent_audits else None
        now = timezone.now()

        flags = []
        variance_severity = "normal"

        if contract.contract_type == SharecroppingContract.CONTRACT_TYPE_SHARECROPPING:
            if latest_assessment is None:
                touring_state = "NO_TOURING"
                status = "READY_FOR_TOURING" if contract.is_active else "INACTIVE"
                flags.append("no_touring")
            elif latest_assessment.is_harvested:
                touring_state = "HARVESTED"
                status = "HARVESTED_PENDING_SETTLEMENT"
            else:
                touring_state = "TOURING_RECORDED"
                status = "TOURING_RECORDED"

            if latest_receipt is None:
                receipt_state = "NONE"
                settlement_state = "OPEN"
                if latest_assessment and latest_assessment.is_harvested:
                    flags.append("touring_without_receipt")
            elif latest_receipt.is_posted:
                receipt_state = f"POSTED_{latest_receipt.receipt_type}"
                settlement_state = "SETTLED"
                status = "SETTLED"
            else:
                receipt_state = f"DRAFT_{latest_receipt.receipt_type}"
                settlement_state = "DRAFT"
                flags.append("receipt_not_posted")

            expected_value = (
                latest_assessment.expected_institution_share_kg if latest_assessment else ZERO
            )
            actual_value = ZERO
            if latest_receipt:
                if latest_receipt.receipt_type == SharecroppingReceipt.RECEIPT_TYPE_PHYSICAL:
                    actual_value = latest_receipt.quantity_received_kg or ZERO
                else:
                    actual_value = latest_receipt.amount_received or ZERO

            if (
                latest_receipt
                and policy_snapshot["sharecropping_mode"] == FarmSettings.SHARECROPPING_MODE_PHYSICAL
                and latest_receipt.receipt_type != SharecroppingReceipt.RECEIPT_TYPE_PHYSICAL
            ):
                flags.append("posted_mode_mismatch")

            if (
                latest_assessment
                and latest_receipt
                and latest_receipt.receipt_type == SharecroppingReceipt.RECEIPT_TYPE_PHYSICAL
            ):
                difference = abs((latest_receipt.quantity_received_kg or ZERO) - latest_assessment.expected_institution_share_kg)
                if difference > Decimal("0.0001"):
                    flags.append("expected_actual_mismatch")
        else:
            touring_state = "NOT_REQUIRED"
            receipt_state = "NOT_REQUIRED"
            expected_value = contract.annual_rent_amount or ZERO
            actual_value = rent_paid_total

            if not contract.is_active:
                status = "INACTIVE"
                settlement_state = "INACTIVE"
            elif rent_paid_total <= ZERO:
                status = "ACTIVE"
                settlement_state = "OPEN"
            elif expected_value and rent_paid_total < expected_value:
                status = "PARTIALLY_SETTLED"
                settlement_state = "PARTIAL"
            else:
                status = "SETTLED"
                settlement_state = "SETTLED"

            if (
                contract.is_active
                and expected_value > ZERO
                and rent_paid_total < expected_value
                and contract.created_at <= now - timedelta(days=30)
            ):
                flags.append("overdue_rental")

        if "posted_mode_mismatch" in flags:
            variance_severity = "critical"
        elif flags:
            variance_severity = "warning"

        approval_state = "OPERATIONAL_ONLY"
        if not contract.is_active:
            approval_state = "INACTIVE"
        elif policy_snapshot["contract_mode"] == FarmSettings.CONTRACT_MODE_FULL_ERP:
            approval_state = "STRICT_READY"
            if settlement_state == "SETTLED":
                approval_state = "POSTED"
        elif policy_snapshot["contract_mode"] == FarmSettings.CONTRACT_MODE_DISABLED:
            approval_state = "DISABLED"

        return {
            "id": contract.id,
            "contract_type": contract.contract_type,
            "contract_mode": policy_snapshot["contract_mode"],
            "status": status,
            "approval_state": approval_state,
            "touring_state": touring_state,
            "receipt_state": receipt_state,
            "settlement_state": settlement_state,
            "reconciliation_state": "POSTED" if settlement_state == "SETTLED" else "OPEN",
            "variance_severity": variance_severity,
            "farmer_name": contract.farmer_name,
            "farm_name": contract.farm.name,
            "farm_id": contract.farm_id,
            "crop_name": getattr(contract.crop, "name", ""),
            "season_name": getattr(contract.season, "name", ""),
            "irrigation_type": contract.irrigation_type,
            "sharecropping_mode": policy_snapshot["sharecropping_mode"],
            "institution_percentage": str(contract.institution_percentage),
            "annual_rent_amount": str(contract.annual_rent_amount or ZERO) if line_amounts_visible else None,
            "expected_institution_share": str(expected_value or ZERO) if line_amounts_visible else None,
            "actual_institution_share": str(actual_value or ZERO) if line_amounts_visible else None,
            "expected_vs_actual_gap": str((expected_value or ZERO) - (actual_value or ZERO)) if line_amounts_visible else None,
            "policy_snapshot": policy_snapshot,
            "visibility_level": policy_snapshot["visibility_level"],
            "cost_display_mode": policy_snapshot["cost_visibility"],
            "amounts_redacted": not line_amounts_visible,
            "economic_posture": settlement_state,
            "flags": flags,
            "latest_touring": (
                {
                    "id": latest_assessment.id,
                    "assessment_date": str(latest_assessment.assessment_date),
                    "estimated_total_yield_kg": str(latest_assessment.estimated_total_yield_kg),
                    "expected_institution_share_kg": str(latest_assessment.expected_institution_share_kg),
                    "is_harvested": latest_assessment.is_harvested,
                }
                if latest_assessment
                else None
            ),
            "latest_receipt": (
                {
                    "id": latest_receipt.id,
                    "receipt_date": str(latest_receipt.receipt_date),
                    "receipt_type": latest_receipt.receipt_type,
                    "is_posted": latest_receipt.is_posted,
                    "amount_received": str(latest_receipt.amount_received or ZERO),
                    "quantity_received_kg": str(latest_receipt.quantity_received_kg or ZERO),
                }
                if latest_receipt
                else None
            ),
            "last_rent_payment": (
                {
                    "timestamp": last_rent_payment.timestamp.isoformat(),
                    "amount": str(last_rent_payment.new_payload.get("amount", "0")),
                    "payment_period": last_rent_payment.new_payload.get("payment_period", ""),
                }
                if last_rent_payment
                else None
            ),
            "is_active": contract.is_active,
        }

    @staticmethod
    def build_dashboard(*, farm_id=None):
        queryset = (
            SharecroppingContract.objects.filter(deleted_at__isnull=True)
            .select_related("farm", "crop", "season")
            .prefetch_related("touring_assessments")
            .order_by("-created_at")
        )
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)

        rows = [ContractOperationsService._build_contract_row(contract) for contract in queryset]
        summary = {
            "total_contracts": len(rows),
            "awaiting_touring": sum(1 for row in rows if row["touring_state"] == "NO_TOURING"),
            "touring_completed_unsettled": sum(
                1
                for row in rows
                if row["touring_state"] == "HARVESTED" and row["settlement_state"] != "SETTLED"
            ),
            "overdue_rentals": sum(1 for row in rows if "overdue_rental" in row["flags"]),
            "mismatched_settlements": sum(
                1 for row in rows if "expected_actual_mismatch" in row["flags"] or "posted_mode_mismatch" in row["flags"]
            ),
            "unresolved_contract_variances": sum(1 for row in rows if row["variance_severity"] != "normal"),
        }
        return {"summary": summary, "results": rows}

    @staticmethod
    def record_rent_payment(*, contract_id, amount, payment_period, notes="", user=None):
        from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService

        contract = SharecroppingContract.objects.select_related("farm").filter(
            pk=contract_id,
            deleted_at__isnull=True,
        ).first()
        if not contract:
            raise ValidationError("Contract not found.")

        settings = ContractOperationsService._get_farm_settings(contract.farm)
        if settings.contract_mode != FarmSettings.CONTRACT_MODE_FULL_ERP:
            raise PermissionDenied("Rental settlement requires full_erp contract mode.")
        if settings.treasury_visibility == FarmSettings.TREASURY_VISIBILITY_HIDDEN:
            raise PermissionDenied("Treasury visibility policy blocks rental settlement posting.")
        FarmFinanceAuthorityService.require_profiled_posting_authority(
            user=user,
            farm=contract.farm,
            action_label='ترحيل دفعة إيجار/عقد',
        )

        amount_dec = Decimal(str(amount)).quantize(ZERO)
        if amount_dec <= ZERO:
            raise ValidationError("Rental payment amount must be greater than zero.")

        cost_center = None
        try:
            from smart_agri.finance.models import CostCenter

            cost_center = CostCenter.objects.filter(
                farm_id=contract.farm_id,
                is_active=True,
            ).first()
        except (LookupError, ImportError):
            cost_center = None

        description = (
            f"دفعة إيجار — {contract.farmer_name} | الفترة: {payment_period} | المبلغ: {amount_dec}"
        )
        if notes:
            description += f" | ملاحظات: {notes}"

        debit_entry = FinancialLedger.objects.create(
            farm_id=contract.farm_id,
            account_code=FinancialLedger.ACCOUNT_RENT_EXPENSE,
            cost_center=cost_center,
            debit=amount_dec,
            credit=ZERO,
            description=description,
            created_by=user if getattr(user, "is_authenticated", False) else None,
        )
        credit_entry = FinancialLedger.objects.create(
            farm_id=contract.farm_id,
            account_code=FinancialLedger.ACCOUNT_CASH_ON_HAND,
            cost_center=cost_center,
            debit=ZERO,
            credit=amount_dec,
            description=description,
            created_by=user if getattr(user, "is_authenticated", False) else None,
        )
        AuditLog.objects.create(
            action="RENT_PAYMENT",
            model="SharecroppingContract",
            object_id=str(contract.id),
            actor=user if getattr(user, "is_authenticated", False) else None,
            farm=contract.farm,
            new_payload={
                "amount": str(amount_dec),
                "payment_period": payment_period,
                "farm_id": str(contract.farm_id),
                "farmer_name": contract.farmer_name,
                "debit_entry_id": str(debit_entry.id),
                "credit_entry_id": str(credit_entry.id),
            },
        )
        return {
            "status": "posted",
            "contract_id": contract.id,
            "farmer_name": contract.farmer_name,
            "amount": str(amount_dec),
            "payment_period": payment_period,
            "debit_entry_id": debit_entry.id,
            "credit_entry_id": credit_entry.id,
        }
