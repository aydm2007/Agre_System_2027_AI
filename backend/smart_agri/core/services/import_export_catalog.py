from __future__ import annotations

from dataclasses import dataclass

from smart_agri.core.models import AsyncReportRequest


@dataclass(frozen=True)
class ExportDefinition:
    code: str
    title: str
    description: str
    report_group: str
    mode_scope: str
    role_scope: str
    sensitivity_level: str
    default_column_profile: str = "default"
    allowed_formats: tuple[str, ...] = (
        AsyncReportRequest.FORMAT_XLSX,
        AsyncReportRequest.FORMAT_JSON,
    )
    ui_surface: str = "reports_hub"


EXPORT_DEFINITIONS: dict[str, ExportDefinition] = {
    AsyncReportRequest.EXPORT_TYPE_ADVANCED_REPORT: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_ADVANCED_REPORT,
        title="تقارير الأنشطة المتقدمة",
        description="تقرير عام للملخص والأنشطة والمؤشرات الأساسية.",
        report_group="general",
        mode_scope="simple_strict",
        role_scope="farm_or_sector",
        sensitivity_level="operational",
    ),
    AsyncReportRequest.EXPORT_TYPE_DAILY_EXECUTION_SUMMARY: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_DAILY_EXECUTION_SUMMARY,
        title="ملخص التنفيذ اليومي",
        description="تلخيص التنفيذ حسب اليوم والمزرعة والموقع والمحصول والمهمة.",
        report_group="execution",
        mode_scope="simple_strict",
        role_scope="farm_or_sector",
        sensitivity_level="operational",
    ),
    AsyncReportRequest.EXPORT_TYPE_DAILY_EXECUTION_DETAIL: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_DAILY_EXECUTION_DETAIL,
        title="سجل التنفيذ اليومي التفصيلي",
        description="تفصيل الأنشطة مع العمالة والآلة والمياه والمواد.",
        report_group="execution",
        mode_scope="simple_strict",
        role_scope="farm_or_sector",
        sensitivity_level="operational",
    ),
    AsyncReportRequest.EXPORT_TYPE_PLAN_ACTUAL_VARIANCE: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_PLAN_ACTUAL_VARIANCE,
        title="الخطة مقابل الفعلي والانحراف",
        description="مؤشرات CropPlan مع مجموع التنفيذ الفعلي والانحرافات المفتوحة.",
        report_group="variance",
        mode_scope="simple_strict",
        role_scope="farm_or_sector",
        sensitivity_level="operational",
    ),
    AsyncReportRequest.EXPORT_TYPE_PERENNIAL_TREE_BALANCE: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_PERENNIAL_TREE_BALANCE,
        title="رصيد الأشجار والمعمّرات",
        description="الرصيد الحالي والتغيرات وفجوات المطابقة للمحاصيل المعمّرة.",
        report_group="perennial",
        mode_scope="simple_strict",
        role_scope="farm_or_sector",
        sensitivity_level="operational",
    ),
    AsyncReportRequest.EXPORT_TYPE_OPERATIONAL_READINESS: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_OPERATIONAL_READINESS,
        title="جاهزية التشغيل",
        description="logs متأخرة، مرفقات ناقصة، انحرافات معلقة وتنبيهات حرجة.",
        report_group="readiness",
        mode_scope="simple_strict",
        role_scope="farm_or_sector",
        sensitivity_level="posture",
    ),
    AsyncReportRequest.EXPORT_TYPE_INVENTORY_BALANCE: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_INVENTORY_BALANCE,
        title="رصيد المخزون الحالي",
        description="أرصدة المخزون حسب المادة والموقع.",
        report_group="inventory",
        mode_scope="simple_strict",
        role_scope="farm_or_sector",
        sensitivity_level="operational",
        ui_surface="inventory_center",
    ),
    AsyncReportRequest.EXPORT_TYPE_INVENTORY_MOVEMENTS: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_INVENTORY_MOVEMENTS,
        title="حركة المخزون",
        description="حركات الاستلام والصرف والتسويات المخزنية.",
        report_group="inventory",
        mode_scope="simple_strict",
        role_scope="farm_or_sector",
        sensitivity_level="operational",
        ui_surface="inventory_center",
    ),
    AsyncReportRequest.EXPORT_TYPE_INVENTORY_LOW_STOCK: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_INVENTORY_LOW_STOCK,
        title="المواد منخفضة الرصيد",
        description="المواد التي تجاوزت حد إعادة الطلب.",
        report_group="inventory",
        mode_scope="simple_strict",
        role_scope="farm_or_sector",
        sensitivity_level="posture",
        ui_surface="inventory_center",
    ),
    AsyncReportRequest.EXPORT_TYPE_INVENTORY_EXPIRY_BATCHES: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_INVENTORY_EXPIRY_BATCHES,
        title="الدفعات والانتهاء المخزني",
        description="الدفعات الراكدة والقريبة من الانتهاء.",
        report_group="inventory",
        mode_scope="simple_strict",
        role_scope="farm_or_sector",
        sensitivity_level="posture",
        ui_surface="inventory_center",
    ),
    AsyncReportRequest.EXPORT_TYPE_FUEL_POSTURE_REPORT: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_FUEL_POSTURE_REPORT,
        title="وضعية الوقود والانحراف",
        description="expected vs actual fuel والشذوذ ووضعية الاعتماد.",
        report_group="fuel",
        mode_scope="simple_strict",
        role_scope="farm_or_sector",
        sensitivity_level="posture",
        ui_surface="module_local",
    ),
    AsyncReportRequest.EXPORT_TYPE_FIXED_ASSET_REGISTER: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_FIXED_ASSET_REGISTER,
        title="سجل الأصول الثابتة",
        description="asset register ووضعية الإسناد والإهلاك.",
        report_group="fixed_assets",
        mode_scope="simple_strict",
        role_scope="farm_or_sector",
        sensitivity_level="governed",
        ui_surface="module_local",
    ),
    AsyncReportRequest.EXPORT_TYPE_CONTRACT_OPERATIONS_POSTURE: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_CONTRACT_OPERATIONS_POSTURE,
        title="وضعية العقود الزراعية",
        description="sharecropping وtouring والإيجار والتسوية والمخاطر.",
        report_group="contracts",
        mode_scope="simple_strict",
        role_scope="farm_or_sector",
        sensitivity_level="governed",
        ui_surface="module_local",
    ),
    AsyncReportRequest.EXPORT_TYPE_SUPPLIER_SETTLEMENT_POSTURE: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_SUPPLIER_SETTLEMENT_POSTURE,
        title="وضعية تسويات الموردين",
        description="invoice وreview وpayment وreconciliation posture.",
        report_group="finance",
        mode_scope="simple_strict",
        role_scope="finance_or_sector",
        sensitivity_level="governed",
        ui_surface="module_local",
    ),
    AsyncReportRequest.EXPORT_TYPE_PETTY_CASH_POSTURE: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_PETTY_CASH_POSTURE,
        title="وضعية السلف والعهد النقدية",
        description="request وdisbursement وsettlement وexception posture.",
        report_group="finance",
        mode_scope="simple_strict",
        role_scope="finance_or_sector",
        sensitivity_level="governed",
        ui_surface="module_local",
    ),
    AsyncReportRequest.EXPORT_TYPE_RECEIPTS_DEPOSIT_POSTURE: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_RECEIPTS_DEPOSIT_POSTURE,
        title="وضعية التحصيل والإيداع",
        description="collections وdeposit وanomaly posture وتتبع الخزينة.",
        report_group="finance",
        mode_scope="simple_strict",
        role_scope="finance_or_sector",
        sensitivity_level="governed",
        ui_surface="module_local",
    ),
    AsyncReportRequest.EXPORT_TYPE_GOVERNANCE_WORK_QUEUE: ExportDefinition(
        code=AsyncReportRequest.EXPORT_TYPE_GOVERNANCE_WORK_QUEUE,
        title="طوابير الحوكمة والموافقات",
        description="approval lanes وSLA breaches وremote review backlog وattachment evidence status.",
        report_group="governance",
        mode_scope="strict_only",
        role_scope="sector_only",
        sensitivity_level="sector_governed",
        ui_surface="module_local",
    ),
}
