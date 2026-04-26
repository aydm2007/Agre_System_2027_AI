from .base import SoftDeleteModel, SoftDeleteQuerySet
from .farm import Farm, Location, Asset, LocationWell, LocationIrrigationPolicy
from .settings import (
    Supervisor, LaborRate, MachineRate, Uom, SystemSettings, FarmSettings, RemoteReviewLog, RemoteReviewEscalation
)
from .custody import CustodyTransfer
from .crop import (
    Crop, FarmCrop, CropVariety, CropProduct, 
    CropProductUnit, CropMaterial, CropRecipe, CropRecipeMaterial, CropRecipeTask
)
from .task import Task
from .planning import (
    Season, CropTemplate, CropTemplateTask, CropTemplateMaterial,
    CropPlan, PlannedActivity, PlannedMaterial,
    CropPlanBudgetLine, PlanImportLog, Budget, CropPlanLocation
)
from .activity import (
    Activity, HarvestActivity, PlantingActivity,
    ActivityHarvest, ActivityIrrigation, ActivityPlanting, ActivityMaterialApplication,
    ActivityMachineUsage, ActivityItem, ActivityCostSnapshot, ActivityEmployee,
    ActivityLocation
)
from .log import (
    AuditLog, Attachment, AttachmentLifecycleEvent, DailyLog, FuelConsumptionAlert, 
    MaterialVarianceAlert, IdempotencyRecord, SyncRecord
)
from .report import AsyncImportJob, AsyncReportRequest, VarianceAlert
from .sync_conflict import SyncConflictDLQ, OfflineSyncQuarantine
from .ops_alert import OpsAlertReceipt
from .partnerships import SharecroppingContract, TouringAssessment
from .dynamic_report import ReportTemplate, SavedReport
from .preventive_maintenance import MaintenanceSchedule, MaintenanceTask
from .pos import POSOrder, POSOrderLine, POSSession
from .procurement import RequestForQuotation, RFQLine, SupplierQuotation, SupplierQuotationLine
from .warehouse import Warehouse, WarehouseZone, BinLocation, InventoryStock

from smart_agri.inventory.models import (
    Unit, UnitConversion, Item, ItemInventory, ItemInventoryBatch, StockMovement
)
from .inventory import (
    HarvestLot, BiologicalAssetCohort, BiologicalAssetTransaction, TreeCensusVarianceAlert
)
from .tree import (
    TreeProductivityStatus, TreeLossReason, LocationTreeStock,
    TreeStockEvent, TreeServiceCoverage, BiologicalAssetImpairment
)

from .hr import (
    Employee, EmploymentContract, Timesheet, PayrollRun, PayrollSlip,
    EmployeeAdvance, AdvanceStatus, PayrollStatus, EmploymentCategory, EmployeeRole,
)
from .views import FarmDashboardStats

# Backward compatibility re-exports for legacy imports/tests.
from smart_agri.finance.models import CostConfiguration, FinancialLedger
from smart_agri.sales.models import Customer, SalesInvoice, SalesInvoiceItem

from .integration_outbox import IntegrationOutboxEvent
from .policy_engine import (
    PolicyPackage,
    PolicyVersion,
    FarmPolicyBinding,
    PolicyActivationRequest,
    PolicyActivationEvent,
    PolicyExceptionRequest,
    PolicyExceptionEvent,
)
