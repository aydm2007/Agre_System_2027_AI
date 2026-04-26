from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Count, Sum, Value, DecimalField
from django.db.models.functions import Coalesce, TruncMonth

from smart_agri.core.models import CropPlan, Activity
from smart_agri.core.utils.pdf_generator import FinancialReportPDF
from smart_agri.finance.models import FinancialLedger
from smart_agri.sales.models import SalesInvoice


class CommercialReportingService:
    DECIMAL_2 = Decimal("0.01")
    DECIMAL_4_FIELD = DecimalField(max_digits=19, decimal_places=4)

    @classmethod
    def _decimal(cls, value) -> Decimal:
        return Decimal(str(value or 0)).quantize(cls.DECIMAL_2, rounding=ROUND_HALF_UP)

    @classmethod
    def _normalized_filters(cls, params: dict) -> dict:
        return {
            "farm_id": params.get("farm_id") or params.get("farm") or "",
            "location_id": params.get("location_id") or params.get("location") or "",
            "crop_plan_id": params.get("crop_plan_id") or "",
            "crop_id": params.get("crop_id") or params.get("crop") or "",
            "start": params.get("start") or params.get("start_date") or "",
            "end": params.get("end") or params.get("end_date") or "",
        }

    @classmethod
    def _zero_decimal_value(cls):
        return Value(Decimal("0.0000"), output_field=cls.DECIMAL_4_FIELD)

    @classmethod
    def _build_plan_queryset(cls, filters: dict):
        qs = CropPlan.objects.filter(deleted_at__isnull=True)
        if filters["farm_id"]:
            qs = qs.filter(farm_id=filters["farm_id"])
        if filters["location_id"]:
            qs = qs.filter(plan_locations__location_id=filters["location_id"])
        if filters["crop_plan_id"]:
            qs = qs.filter(id=filters["crop_plan_id"])
        if filters["crop_id"]:
            qs = qs.filter(crop_id=filters["crop_id"])
        if filters["start"]:
            qs = qs.filter(end_date__gte=filters["start"])
        if filters["end"]:
            qs = qs.filter(start_date__lte=filters["end"])
        return qs.distinct()

    @classmethod
    def _build_invoice_queryset(cls, filters: dict):
        qs = SalesInvoice.objects.filter(
            deleted_at__isnull=True,
            status__in=[SalesInvoice.STATUS_APPROVED, SalesInvoice.STATUS_PAID],
        )
        if filters["farm_id"]:
            qs = qs.filter(farm_id=filters["farm_id"])
        if filters["location_id"]:
            qs = qs.filter(location_id=filters["location_id"])
        if filters["crop_plan_id"]:
            qs = qs.filter(items__harvest_lot__crop_plan_id=filters["crop_plan_id"])
        if filters["crop_id"]:
            qs = qs.filter(items__harvest_lot__crop_plan__crop_id=filters["crop_id"])
        if filters["start"]:
            qs = qs.filter(invoice_date__gte=filters["start"])
        if filters["end"]:
            qs = qs.filter(invoice_date__lte=filters["end"])
        return qs.distinct()

    @classmethod
    def _build_ledger_queryset(cls, filters: dict):
        qs = FinancialLedger.objects.all()
        if filters["farm_id"]:
            qs = qs.filter(farm_id=filters["farm_id"])
        if filters["crop_plan_id"]:
            qs = qs.filter(crop_plan_id=filters["crop_plan_id"])
        if filters["start"]:
            qs = qs.filter(created_at__date__gte=filters["start"])
        if filters["end"]:
            qs = qs.filter(created_at__date__lte=filters["end"])
        return qs

    @classmethod
    def build_snapshot(cls, params: dict) -> dict:
        filters = cls._normalized_filters(params or {})
        plan_qs = cls._build_plan_queryset(filters)
        invoice_qs = cls._build_invoice_queryset(filters)
        ledger_qs = cls._build_ledger_queryset(filters)

        total_revenue = invoice_qs.aggregate(
            total=Coalesce(Sum("total_amount"), cls._zero_decimal_value())
        )["total"] or Decimal("0")
        total_cost = plan_qs.annotate(
            actual_cost=Coalesce(Sum("activities__cost_total"), cls._zero_decimal_value())
        ).aggregate(total=Coalesce(Sum("actual_cost"), cls._zero_decimal_value()))["total"] or Decimal("0")
        total_expected = plan_qs.aggregate(
            total=Coalesce(Sum("expected_yield"), cls._zero_decimal_value())
        )["total"] or Decimal("0")
        total_actual = plan_qs.annotate(
            actual_harvest=Coalesce(Sum("harvest_lots__quantity"), cls._zero_decimal_value())
        ).aggregate(total=Coalesce(Sum("actual_harvest"), cls._zero_decimal_value()))["total"] or Decimal("0")

        total_revenue = cls._decimal(total_revenue)
        total_cost = cls._decimal(total_cost)
        total_expected = cls._decimal(total_expected)
        total_actual = cls._decimal(total_actual)
        net_profit = (total_revenue - total_cost).quantize(cls.DECIMAL_2, rounding=ROUND_HALF_UP)
        margin_percent = Decimal("0.00")
        if total_revenue > 0:
            margin_percent = ((net_profit / total_revenue) * Decimal("100")).quantize(  # agri-guardian: decimal-safe
                cls.DECIMAL_2, rounding=ROUND_HALF_UP
            )
        yield_percent = Decimal("0.00")
        if total_expected > 0:
            yield_percent = ((total_actual / total_expected) * Decimal("100")).quantize(  # agri-guardian: decimal-safe
                cls.DECIMAL_2, rounding=ROUND_HALF_UP
            )

        plan_counts = plan_qs.aggregate(active=Count("id"))
        invoice_counts = invoice_qs.aggregate(total=Count("id"))

        invoice_trend = (
            invoice_qs.annotate(month=TruncMonth("invoice_date"))
            .values("month")
            .annotate(revenue=Coalesce(Sum("total_amount"), cls._zero_decimal_value()), invoices=Count("id"))
            .order_by("month")
        )
        activity_qs = Activity.objects.filter(
            deleted_at__isnull=True,
            log__deleted_at__isnull=True,
        )
        if filters["farm_id"]:
            activity_qs = activity_qs.filter(log__farm_id=filters["farm_id"])
        if filters["crop_plan_id"]:
            activity_qs = activity_qs.filter(crop_plan_id=filters["crop_plan_id"])
        if filters["crop_id"]:
            activity_qs = activity_qs.filter(crop_id=filters["crop_id"])
        if filters["location_id"]:
            activity_qs = activity_qs.filter(activity_locations__location_id=filters["location_id"])
        if filters["start"]:
            activity_qs = activity_qs.filter(log__log_date__gte=filters["start"])
        if filters["end"]:
            activity_qs = activity_qs.filter(log__log_date__lte=filters["end"])

        cost_trend = (
            activity_qs.annotate(month=TruncMonth("log__log_date"))
            .values("month")
            .annotate(cost=Coalesce(Sum("cost_total"), cls._zero_decimal_value()))
            .order_by("month")
        )
        cost_map = {row["month"]: cls._decimal(row["cost"]) for row in cost_trend if row["month"]}
        trend_rows = []
        for row in invoice_trend:
            month = row["month"]
            if not month:
                continue
            trend_rows.append(
                {
                    "label": month.strftime("%Y-%m"),
                    "revenue": cls._decimal(row["revenue"]),
                    "cost": cost_map.get(month, Decimal("0.00")),
                    "invoices": row["invoices"],
                }
            )
        if not trend_rows:
            # Preserve empty-state semantics instead of demo data.
            trend_rows = []

        allocation_rows = list(
            ledger_qs.exclude(cost_center__isnull=True)
            .values("cost_center_id", "cost_center__name")
            .annotate(total=Coalesce(Sum("debit"), cls._zero_decimal_value()))
            .order_by("-total")[:5]
        )
        allocations = [
            {
                "cost_center_id": row["cost_center_id"],
                "cost_center_name": row["cost_center__name"] or "غير محدد",
                "total": cls._decimal(row["total"]),
            }
            for row in allocation_rows
        ]

        grading_rows = list(
            plan_qs.values("crop_id", "crop__name")
            .annotate(plans=Count("id"), expected_yield=Coalesce(Sum("expected_yield"), cls._zero_decimal_value()))
            .order_by("-plans", "-expected_yield")[:5]
        )
        grading = [
            {
                "crop_id": row["crop_id"],
                "crop_name": row["crop__name"] or "غير محدد",
                "plans": row["plans"],
                "expected_yield": cls._decimal(row["expected_yield"]),
            }
            for row in grading_rows
        ]

        risk_zone = {
            "margin_percent": margin_percent,
            "zone": "safe" if margin_percent > 20 else "warning" if margin_percent > 10 else "danger",
        }
        pulse = {
            "active_plans": plan_counts["active"] or 0,
            "approved_invoices": invoice_counts["total"] or 0,
            "expected_yield": total_expected,
            "actual_yield": total_actual,
        }

        return {
            "filters": filters,
            "currency": "YER",
            "financials": {
                "revenue": total_revenue,
                "cost": total_cost,
                "net_profit": net_profit,
            },
            "yields": {
                "expected": total_expected,
                "actual": total_actual,
                "yield_percent": yield_percent,
            },
            "risk_zone": risk_zone,
            "pulse": pulse,
            "trend": trend_rows,
            "allocations": allocations,
            "grading": grading,
        }

    @classmethod
    def generate_commercial_pdf(cls, params: dict) -> bytes:
        snapshot = cls.build_snapshot(params)
        subtitle_parts = []
        if snapshot["filters"]["farm_id"]:
            subtitle_parts.append(f"Farm: {snapshot['filters']['farm_id']}")
        if snapshot["filters"]["start"] and snapshot["filters"]["end"]:
            subtitle_parts.append(f"{snapshot['filters']['start']} -> {snapshot['filters']['end']}")
        subtitle = " | ".join(subtitle_parts)
        pdf = FinancialReportPDF(title="التقرير التجاري التنفيذي", subtitle=subtitle)

        kpi_rows = [
            ["صافي الربح", f"{snapshot['financials']['net_profit']:,.2f}"],
            ["إجمالي الإيرادات", f"{snapshot['financials']['revenue']:,.2f}"],
            ["إجمالي التكاليف", f"{snapshot['financials']['cost']:,.2f}"],
            ["هامش الربح", f"{snapshot['risk_zone']['margin_percent']:,.2f}%"],
            ["الإنتاج المتوقع", f"{snapshot['yields']['expected']:,.2f}"],
            ["الإنتاج الفعلي", f"{snapshot['yields']['actual']:,.2f}"],
        ]
        pdf.add_table(headers=["القيمة", "المؤشر"], data_rows=kpi_rows)

        trend_rows = [
            [f"{row['cost']:,.2f}", f"{row['revenue']:,.2f}", row["label"]]
            for row in snapshot["trend"]
        ]
        if trend_rows:
            pdf.add_table(headers=["التكلفة", "الإيراد", "الفترة"], data_rows=trend_rows)

        allocation_rows = [
            [f"{row['total']:,.2f}", row["cost_center_name"]]
            for row in snapshot["allocations"]
        ]
        if allocation_rows:
            pdf.add_table(headers=["الإجمالي", "مركز التكلفة"], data_rows=allocation_rows)

        grading_rows = [
            [f"{row['expected_yield']:,.2f}", str(row["plans"]), row["crop_name"]]
            for row in snapshot["grading"]
        ]
        if grading_rows:
            pdf.add_table(headers=["الإنتاج المتوقع", "عدد الخطط", "المحصول"], data_rows=grading_rows)

        return pdf.generate()
