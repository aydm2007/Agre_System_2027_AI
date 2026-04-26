from rest_framework import routers
from .dashboard import DashboardViewSet
from smart_agri.core.api.activities import ActivityViewSet
from smart_agri.core.api.viewsets import (
    FarmViewSet, LocationViewSet, AssetViewSet,
    LocationIrrigationPolicyViewSet,
    CropViewSet, FarmCropViewSet, TaskViewSet, SupervisorViewSet,
    AuditLogViewSet, AttachmentViewSet, DailyLogViewSet,
    UnitViewSet, UnitConversionViewSet, ItemViewSet, ItemInventoryViewSet,
    StockMovementViewSet, MaterialCatalogViewSet, HarvestProductCatalogViewSet,
    HarvestLotViewSet, LocationWellViewSet, SeasonViewSet, CostConfigurationViewSet,
    FarmSettingsViewSet, PolicyPackageViewSet, PolicyVersionViewSet, FarmPolicyBindingViewSet, PolicyActivationRequestViewSet, PolicyExceptionRequestViewSet,
    SyncRecordViewSet, CropVarietyViewSet, CropProductViewSet, CropMaterialViewSet,
    CropPlanViewSet, CropPlanBudgetLineViewSet, PlanImportLogViewSet,
    PlannedActivityViewSet, PlannedMaterialViewSet, CropCardViewSet,
    TreeLossReasonViewSet, TreeProductivityStatusViewSet,
    MaterialVarianceAlertViewSet,
    LaborEstimateViewSet,
    CropTemplateViewSet, CropTemplateTaskViewSet, CropTemplateMaterialViewSet,
    ServiceCardViewSet, HarvestLogViewSet, # CommercialViewSet, # ActualExpenseViewSet,
    StubServiceProviderViewSet, StubMaterialCardViewSet,
    CropRecipeViewSet, CropRecipeMaterialViewSet, CropRecipeTaskViewSet,
    CustodyTransferViewSet, CustodyBalanceViewSet,
    HardenedOfflineDailyLogReplayViewSet, OfflineHarvestReplayViewSet,
    OfflineCustodyReplayViewSet, SyncConflictDLQViewSet,
    OfflineSyncQuarantineViewSet, OfflineSyncRecordViewSet,
)
from smart_agri.inventory.api.viewsets import (
   TreeInventoryAdminViewSet, TreeInventorySummaryViewSet, TreeInventoryEventViewSet,
   PurchaseOrderViewSet
)
from smart_agri.core.api.viewsets.audit import AuditLogViewSet as ForensicAuditLogViewSet, log_ui_breach
from smart_agri.core.api.viewsets.inventory import (
   BiologicalAssetCohortViewSet, BiologicalAssetTransactionViewSet, 
   TreeCensusVarianceAlertViewSet, MassCasualtyWriteoffViewSet
)
from smart_agri.core.api.viewsets.shadow_ledger import ShadowLedgerViewSet
from smart_agri.core.api.viewsets.reports import (
    ReportsViewSet, ResourceAnalyticsViewSet
)

# Note: ServiceCardViewSet, MaterialCardViewSet available

router = routers.DefaultRouter()
router.register(r"harvest-logs", HarvestLogViewSet, basename="harvest-logs")

# [Visibility Engine]
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

router.register(r"farms", FarmViewSet, basename="farms")
router.register(r"locations", LocationViewSet, basename="locations")
router.register(r"assets", AssetViewSet, basename="assets")
router.register(r"crops", CropViewSet, basename="crops")
router.register(r"farm-crops", FarmCropViewSet, basename="farmcrops")
router.register(r"tasks", TaskViewSet, basename="tasks")
router.register(r"supervisors", SupervisorViewSet, basename="supervisors")
router.register(r"variance-alerts", MaterialVarianceAlertViewSet, basename="variance-alerts")
router.register(r"labor-estimates", LaborEstimateViewSet, basename="labor-estimates")
router.register(r"audit-logs", AuditLogViewSet, basename="auditlogs")
router.register(r"attachments", AttachmentViewSet, basename="attachments")
router.register(r"daily-logs", DailyLogViewSet, basename="dailylogs")
router.register(r"activities", ActivityViewSet, basename="activities")
router.register(r"units", UnitViewSet, basename="units")
router.register(r"unit-conversions", UnitConversionViewSet, basename="unit-conversions")
router.register(r"items", ItemViewSet, basename="items")
router.register(r"item-inventories", ItemInventoryViewSet, basename="item-inventories")
router.register(r"inventory/custody-transfers", CustodyTransferViewSet, basename="inventory-custody-transfers")
router.register(r"inventory/custody-balance", CustodyBalanceViewSet, basename="inventory-custody-balance")
router.register(r"offline/daily-log-replay/atomic", HardenedOfflineDailyLogReplayViewSet, basename="offline-daily-log-replay-atomic")
router.register(r"offline/harvest-replay/atomic", OfflineHarvestReplayViewSet, basename="offline-harvest-replay-atomic")
router.register(r"offline/custody-replay/atomic", OfflineCustodyReplayViewSet, basename="offline-custody-replay-atomic")
router.register(r"stock-ledger", StockMovementViewSet, basename="stockledger")
router.register(r"shadow-ledger", ShadowLedgerViewSet, basename="shadow-ledger")
router.register(r"purchase-orders", PurchaseOrderViewSet, basename="purchase-orders")
router.register(r"material-catalog", MaterialCatalogViewSet, basename="material-catalog")
router.register(r"harvest-product-catalog", HarvestProductCatalogViewSet, basename="harvest-product-catalog")
router.register(r"reports", ReportsViewSet, basename="reports")
router.register(r"harvest-lots", HarvestLotViewSet, basename="harvestlots")
router.register(r"location-wells", LocationWellViewSet, basename="locationwells")
router.register(r"location-irrigation-policies", LocationIrrigationPolicyViewSet, basename="location-irrigation-policies")
router.register(r"seasons", SeasonViewSet, basename="seasons")
router.register(r"cost-configurations", CostConfigurationViewSet, basename="cost-configurations")
router.register(r"farm-settings", FarmSettingsViewSet, basename="farm-settings")
router.register(r"policy-packages", PolicyPackageViewSet, basename="policy-packages")
router.register(r"policy-versions", PolicyVersionViewSet, basename="policy-versions")
router.register(r"farm-policy-bindings", FarmPolicyBindingViewSet, basename="farm-policy-bindings")
router.register(r"policy-activation-requests", PolicyActivationRequestViewSet, basename="policy-activation-requests")
router.register(r"policy-exception-requests", PolicyExceptionRequestViewSet, basename="policy-exception-requests")
router.register(r"sync-records", OfflineSyncRecordViewSet, basename="syncrecords")
router.register(r"sync-conflict-dlq", SyncConflictDLQViewSet, basename="sync-conflict-dlq")
router.register(r"offline-sync-quarantines", OfflineSyncQuarantineViewSet, basename="offline-sync-quarantines")
router.register(r"crop-varieties", CropVarietyViewSet, basename="crop-varieties")
router.register(r"crop-products", CropProductViewSet, basename="crop-products")
router.register(r"crop-materials", CropMaterialViewSet, basename="crop-materials") 
router.register(r"crop-recipes", CropRecipeViewSet, basename="crop-recipes")
router.register(r"crop-recipe-materials", CropRecipeMaterialViewSet, basename="crop-recipe-materials")
router.register(r"crop-recipe-tasks", CropRecipeTaskViewSet, basename="crop-recipe-tasks")
router.register(r"crop-templates", CropTemplateViewSet, basename="crop-templates")
router.register(r"crop-template-tasks", CropTemplateTaskViewSet, basename="crop-template-tasks")
router.register(r"crop-template-materials", CropTemplateMaterialViewSet, basename="crop-template-materials")
router.register(r"crop-plans", CropPlanViewSet, basename="crop-plans")
router.register(r"crop-plan-budget-lines", CropPlanBudgetLineViewSet, basename="crop-plan-budget-lines")
router.register(r"plan-import-logs", PlanImportLogViewSet, basename="plan-import-logs")
router.register(r"planned-activities", PlannedActivityViewSet, basename="planned-activities")
router.register(r"planned-materials", PlannedMaterialViewSet, basename="planned-materials")
router.register(r"crop-cards", CropCardViewSet, basename="crop-cards")
router.register(r"service-cards", ServiceCardViewSet, basename="service-cards")
# [Phase 5] Stub for pending MaterialCard feature
router.register(r"material-cards", StubMaterialCardViewSet, basename="material-cards")
router.register(r"tree-loss-reasons", TreeLossReasonViewSet, basename="tree-loss-reasons")
router.register(r"tree-productivity-statuses", TreeProductivityStatusViewSet, basename="tree-productivity-statuses")
router.register(r"tree-inventory/admin", TreeInventoryAdminViewSet, basename="tree-inventory-admin")
router.register(r"tree-inventory/summary", TreeInventorySummaryViewSet, basename="tree-inventory-summary")
router.register(r"tree-inventory/events", TreeInventoryEventViewSet, basename="tree-inventory-events")

# [AGRI-GUARDIAN] Axis 11 Compliance: Biological Asset Hierarchy
router.register(r"biological-asset-cohorts", BiologicalAssetCohortViewSet, basename="biological-asset-cohorts")
router.register(r"biological-asset-transactions", BiologicalAssetTransactionViewSet, basename="biological-asset-transactions")
router.register(r"tree-census-variance-alerts", TreeCensusVarianceAlertViewSet, basename="tree-census-variance-alerts")
router.register(r"mass-casualty-writeoff", MassCasualtyWriteoffViewSet, basename="mass-casualty-writeoff")

router.register(r"resource-analytics", ResourceAnalyticsViewSet, basename="resource-analytics")
# router.register(r"commercial", CommercialViewSet, basename="commercial")
# router.register(r"expenses", ActualExpenseViewSet, basename="expenses")
# [Phase 5] Stub for deprecated ServiceProvider (model deleted)
router.register(r"service-providers", StubServiceProviderViewSet, basename="service-providers")

# [AGRI-GUARDIAN §6] Centralized Forensic Audit Dashboard API
router.register(r"forensic-audit-logs", ForensicAuditLogViewSet, basename="forensic-audit-logs")

# ─── YECO Hybrid ERP: Shadow Mode & Partnerships ────────────────────
from smart_agri.core.api.viewsets.variance_radar import VarianceRadarViewSet
from smart_agri.core.views.predictive_variance import PredictiveVarianceViewSet
from smart_agri.core.api.viewsets.partnerships_api import (
    SharecroppingContractViewSet, TouringAssessmentViewSet, SharecroppingReceiptViewSet
)
from smart_agri.core.api.viewsets.frictionless_log import FrictionlessDailyLogViewSet
from smart_agri.core.api.viewsets.qr_operations import QROperationsViewSet

router.register(r"variance-radar", VarianceRadarViewSet, basename="variance-radar")
router.register(r"predictive-variance", PredictiveVarianceViewSet, basename="predictive-variance")
router.register(r"qr-operations", QROperationsViewSet, basename="qr-operations")
router.register(r"sharecropping-contracts", SharecroppingContractViewSet, basename="sharecropping-contracts")
router.register(r"touring-assessments", TouringAssessmentViewSet, basename="touring-assessments")
router.register(r"sharecropping-receipts", SharecroppingReceiptViewSet, basename="sharecropping-receipts")
router.register(r"frictionless-daily-logs", FrictionlessDailyLogViewSet, basename="frictionless-daily-logs")

# ─── YECO Adaptive UI: System Mode Toggle ────────────────────────────
from smart_agri.core.api.viewsets.system_mode import SystemModeViewSet
router.register(r"system-mode", SystemModeViewSet, basename="system-mode")

# ─── Solar Fleet Monitor Dashboard ────────────────────────────
from smart_agri.core.views.solar_dashboard import SolarFleetViewSet
router.register(r"solar-fleet", SolarFleetViewSet, basename="solar-fleet")

# —— Fixed Assets Dashboard ————————————————————————————————
from smart_agri.core.views.fixed_assets_dashboard import FixedAssetsDashboardViewSet
router.register(r"fixed-assets", FixedAssetsDashboardViewSet, basename="fixed-assets")

from smart_agri.core.views.fuel_reconciliation_dashboard import FuelReconciliationDashboardViewSet
router.register(r"fuel-reconciliation", FuelReconciliationDashboardViewSet, basename="fuel-reconciliation")

# ─── YECO Total Completion: Advanced GRP Modules ─────────────────────
from smart_agri.core.api.viewsets.financial_reports import FinancialReportViewSet
from smart_agri.core.api.viewsets.procurement import RFQViewSet, QuotationViewSet
from smart_agri.core.api.viewsets.pos import POSSessionViewSet, POSOrderViewSet
from smart_agri.core.api.viewsets.warehouse import WarehouseViewSet, WarehouseZoneViewSet, BinLocationViewSet
from smart_agri.core.api.viewsets.dynamic_report import ReportTemplateViewSet, SavedReportViewSet
from smart_agri.core.api.viewsets.maintenance import MaintenanceScheduleViewSet, MaintenanceTaskViewSet

router.register(r"financial-reports", FinancialReportViewSet, basename="financial-reports")
router.register(r"procurement/rfq", RFQViewSet, basename="rfq")
router.register(r"procurement/quotations", QuotationViewSet, basename="quotations")
router.register(r"pos/sessions", POSSessionViewSet, basename="pos-sessions")
router.register(r"pos/orders", POSOrderViewSet, basename="pos-orders")
router.register(r"warehouse/warehouses", WarehouseViewSet, basename="warehouses")
router.register(r"warehouse/zones", WarehouseZoneViewSet, basename="warehouse-zones")
router.register(r"warehouse/bins", BinLocationViewSet, basename="bins")
router.register(r"reports/dynamic-templates", ReportTemplateViewSet, basename="report-templates")
router.register(r"reports/saved-instances", SavedReportViewSet, basename="saved-reports")
router.register(r"maintenance/schedules", MaintenanceScheduleViewSet, basename="maintenance-schedules")
router.register(r"maintenance/tasks", MaintenanceTaskViewSet, basename="maintenance-tasks")

# ─── Bootstrap: Seed Tree Inventory (Admin-Only) ─────────────────────
# Function-based view — registered in urls.py via path()
