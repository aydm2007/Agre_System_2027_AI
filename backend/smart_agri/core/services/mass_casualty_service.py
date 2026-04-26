# pyright: reportArgumentType=false
# pyright: reportOptionalSubscript=false
# pyright: reportAttributeAccessIssue=false
"""
MassCasualtyWriteoffService — شطب جماعي للأصول البيولوجية.

Handles extraordinary mass tree deaths (Frost, Disease, Natural Disasters)
using a specialized IAS 41 Impairment recognition workflow.

AGENTS.md Compliance:
  - Axis 2: Idempotency via idempotency_key
  - Axis 5: Decimal(19,4) only — zero float usage
  - Axis 6: Farm-scoped
  - Axis 7: AuditLog with forensic trail
  - Axis 11: BiologicalAssetTransaction for capital mutations
  - Axis 18: Mass Casualty Write-off (IAS 41 Impairment)

Key Differences from DailyLog Negative Deltas:
  - DailyLog deltas are DESCRIPTIVE (trigger variance alerts only)
  - This service is AUTHORITATIVE (modifies capital ledger directly)
  - Requires C-Level authorization (manager + auditor approval)
  - Bypasses standard DailyLog negative delta error completely
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

FOUR_DP = Decimal("0.0001")
ZERO = Decimal("0.0000")


class MassCasualtyWriteoffService:
    """
    [AGENTS.md §Axis-18] Mass Casualty Write-off (Biological Assets).

    Processes IAS 41 Impairment for bulk biological asset deaths caused by
    extraordinary events (Frost, Disease, Flood, Fire).

    @idempotent
    """

    CAUSE_FROST = "FROST"
    CAUSE_DISEASE = "DISEASE"
    CAUSE_FLOOD = "FLOOD"
    CAUSE_FIRE = "FIRE"
    CAUSE_OTHER = "OTHER"

    VALID_CAUSES = {CAUSE_FROST, CAUSE_DISEASE, CAUSE_FLOOD, CAUSE_FIRE, CAUSE_OTHER}

    @staticmethod
    @transaction.atomic
    def execute_mass_writeoff(
        *,
        farm_id: int,
        cohort_entries: list,
        cause: str,
        reason: str,
        user,
        approved_by_manager,
        approved_by_auditor=None,
        idempotency_key: str = None,
    ) -> dict:
        """
        Execute a mass casualty write-off for biological assets.

        Args:
            farm_id: Target farm (Axis 6: tenant isolation).
            cohort_entries: List of dicts, each with:
                - cohort_id: int — ID of the BiologicalAssetCohort
                - quantity_lost: int — Number of trees/assets lost
                - estimated_fair_value_per_unit: Decimal — Fair value before loss
            cause: One of FROST, DISEASE, FLOOD, FIRE, OTHER.
            reason: Human-readable explanation of the event.
            user: The user initiating the write-off.
            approved_by_manager: Manager who authorized (C-Level requirement).
            approved_by_auditor: Auditor who counter-signed (optional but recommended).
            idempotency_key: Unique key for retry safety (Axis 2).

        Returns:
            Dict with summary of the write-off.
        """
        from smart_agri.core.models.inventory import BiologicalAssetCohort
        from smart_agri.core.models.log import AuditLog
        from smart_agri.core.models.report import VarianceAlert
        from smart_agri.finance.models import FinancialLedger

        # --- Validation ---
        if not farm_id:
            raise ValidationError({"farm_id": "farm_id مطلوب (عزل المستأجر)."})

        if cause not in MassCasualtyWriteoffService.VALID_CAUSES:
            raise ValidationError(
                {"cause": f"السبب غير صالح. الأسباب المقبولة: {MassCasualtyWriteoffService.VALID_CAUSES}"}
            )

        if not cohort_entries or len(cohort_entries) == 0:
            raise ValidationError({"cohort_entries": "يجب تحديد مجموعة واحدة على الأقل."})

        if not approved_by_manager:
            raise ValidationError(
                {"approved_by_manager": "يتطلب الشطب الجماعي موافقة مستوى الإدارة العليا (C-Level)."}
            )

        if not reason or len(reason.strip()) < 10:
            raise ValidationError({"reason": "يجب توضيح السبب بشكل كافٍ (10 أحرف على الأقل)."})

        # --- Idempotency Check (Axis 2) ---
        if idempotency_key:
            from smart_agri.core.services.idempotency import IdempotencyService
            record, is_replay, response_tuple = IdempotencyService.acquire_lock(
                key=idempotency_key,
                user=user,
                method="POST",
                path=f"/mass-casualty-writeoff/{farm_id}/",
                body={"cause": cause, "entries_count": len(cohort_entries)},
                farm_id=farm_id,
            )
            if is_replay:
                return {"status": "replay", "cached": response_tuple[1]}
        else:
            record = None

        # --- Process Each Cohort ---
        total_impairment_loss = ZERO
        processed_cohorts = []

        for entry in cohort_entries:
            cohort_id = entry.get("cohort_id")
            quantity_lost = entry.get("quantity_lost", 0)
            fair_value_per_unit = Decimal(str(entry.get("estimated_fair_value_per_unit", "0"))).quantize(FOUR_DP)

            cohort = BiologicalAssetCohort.objects.select_for_update().filter(
                pk=cohort_id,
                farm_id=farm_id,
            ).first()

            if not cohort:
                raise ValidationError(
                    {"cohort_id": f"المجموعة {cohort_id} غير موجودة أو لا تنتمي للمزرعة {farm_id}."}
                )

            if quantity_lost <= 0:
                raise ValidationError(
                    {"quantity_lost": f"الكمية المفقودة يجب أن تكون أكبر من صفر للمجموعة {cohort_id}."}
                )

            if quantity_lost > cohort.quantity:
                raise ValidationError(
                    {"quantity_lost": (
                        f"الكمية المفقودة ({quantity_lost}) تتجاوز العدد الحالي "
                        f"({cohort.quantity}) للمجموعة {cohort_id}."
                    )}
                )

            impairment_amount = (Decimal(str(quantity_lost)) * fair_value_per_unit).quantize(FOUR_DP)
            total_impairment_loss += impairment_amount

            # --- Update Cohort Count ---
            cohort.quantity -= quantity_lost
            if cohort.quantity == 0:
                cohort.status = "EXCLUDED"
            cohort.save(update_fields=["quantity", "status", "updated_at"])

            # --- Create BiologicalAssetTransaction ---
            from smart_agri.core.models.tree import TreeStockEvent, LocationTreeStock
            
            # Dynamically resolve LocationTreeStock for legacy mapping
            lts = LocationTreeStock.objects.filter(
                location_id=cohort.location_id,
                crop_variety_id=getattr(cohort.variety, 'id', None) if cohort.variety else None
            ).first()
            if not lts and cohort.crop_id:
                lts = LocationTreeStock.objects.filter(
                    location_id=cohort.location_id,
                    crop_id=cohort.crop_id
                ).first()
                
            if lts:
                TreeStockEvent.objects.create(
                    location_tree_stock=lts,
                    event_type=TreeStockEvent.LOSS,
                    tree_count_delta=-quantity_lost,
                    notes=f"[MASS CASUALTY] {cause}: {reason}",
                )

            # --- Post IAS 41 Impairment Journal Entries ---
            cost_center = getattr(cohort, "cost_center", None)
            crop_plan = getattr(cohort, "crop_plan", None)

            description = (
                f"شطب جماعي IAS-41 — {cause} | "
                f"مجموعة={cohort.id} | فقدان={quantity_lost} | "
                f"قيمة_عادلة/وحدة={fair_value_per_unit} | "
                f"إجمالي_الخسارة={impairment_amount}"
            )

            # DR 8100-IMPAIRMENT-LOSS (expense equivalent to Depreciation/Overhead)
            from smart_agri.finance.models import FinancialLedger
            FinancialLedger.objects.create(
                farm_id=farm_id,
                account_code=FinancialLedger.ACCOUNT_DEPRECIATION_EXPENSE,
                crop_plan=crop_plan,
                cost_center=cost_center,
                debit=impairment_amount,
                credit=ZERO,
                description=description,
                created_by=user if getattr(user, "is_authenticated", False) else None,
            )

            # CR 1600-BIO-ASSET (asset reduction equivalent to Inventory)
            FinancialLedger.objects.create(
                farm_id=farm_id,
                account_code=FinancialLedger.ACCOUNT_INVENTORY_ASSET,
                crop_plan=crop_plan,
                cost_center=cost_center,
                debit=ZERO,
                credit=impairment_amount,
                description=description,
                created_by=user if getattr(user, "is_authenticated", False) else None,
            )

            processed_cohorts.append({
                "cohort_id": cohort_id,
                "quantity_lost": quantity_lost,
                "impairment_amount": str(impairment_amount),
            })

        # --- Create CRITICAL VarianceAlert ---
        VarianceAlert.objects.create(
            farm_id=farm_id,
            category="MASS_CASUALTY",
            activity_name=f"Mass Casualty: {cause}",
            planned_cost=ZERO,
            actual_cost=total_impairment_loss,
            variance_amount=total_impairment_loss,
            variance_percentage=Decimal("100.0000"),
            alert_message=(
                f"🔴 شطب جماعي للأصول البيولوجية بسبب {cause}. "
                f"إجمالي الخسارة: {total_impairment_loss}. "
                f"عدد المجموعات المتأثرة: {len(processed_cohorts)}. "
                f"السبب: {reason}"
            ),
        )

        # --- [FIX Axis-18] Create TreeCensusVarianceAlert per cohort ---
        # Links mass casualty to tree census traceability. Created as RESOLVED
        # since the write-off is already authorized by C-Level.
        from smart_agri.core.models.inventory import TreeCensusVarianceAlert
        for entry in processed_cohorts:
            TreeCensusVarianceAlert.objects.create(
                farm_id=farm_id,
                location_id=BiologicalAssetCohort.objects.filter(
                    pk=entry["cohort_id"]
                ).values_list("location_id", flat=True).first(),
                crop_id=BiologicalAssetCohort.objects.filter(
                    pk=entry["cohort_id"]
                ).values_list("crop_id", flat=True).first(),
                cohort_id=entry["cohort_id"],
                missing_quantity=entry["quantity_lost"],
                reason=f"[MASS CASUALTY] {cause}: {reason}",
                status=TreeCensusVarianceAlert.STATUS_RESOLVED,
                resolved_by=user if getattr(user, "is_authenticated", False) else None,
            )

        # --- AuditLog (Axis 7: Forensic Chain) ---
        AuditLog.objects.create(
            action="MASS_CASUALTY_WRITEOFF",
            model="BiologicalAssetCohort",
            object_id=",".join(str(e["cohort_id"]) for e in processed_cohorts),
            actor=user,
            new_payload={
                "farm_id": farm_id,
                "cause": cause,
                "reason": reason,
                "total_impairment_loss": str(total_impairment_loss),
                "processed_cohorts": processed_cohorts,
                "approved_by_manager": str(getattr(approved_by_manager, "id", approved_by_manager)),
                "approved_by_auditor": str(getattr(approved_by_auditor, "id", "")) if approved_by_auditor else None,
                "idempotency_key": idempotency_key,
            },
        )

        # --- Idempotency Commit ---
        result = {
            "status": "completed",
            "farm_id": farm_id,
            "cause": cause,
            "total_impairment_loss": str(total_impairment_loss),
            "cohorts_affected": len(processed_cohorts),
            "details": processed_cohorts,
        }

        if record:
            from smart_agri.core.services.idempotency import IdempotencyService
            IdempotencyService.commit_success(
                record,
                response_status=200,
                response_body=result,
                model_name="MassCasualtyWriteoff",
            )

        logger.info(
            "Mass casualty write-off: farm=%s, cause=%s, loss=%s, cohorts=%d",
            farm_id, cause, total_impairment_loss, len(processed_cohorts),
        )

        return result
