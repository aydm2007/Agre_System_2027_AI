# Serializers - Re-exports
# Explicitly import from submodules to expose them at package level

from .farm import FarmSerializer, LocationWellSerializer, LocationIrrigationPolicySerializer
from .location import LocationSerializer
from .asset import AssetSerializer
from .season import SeasonSerializer
from .unit import UnitSerializer, UnitConversionSerializer
from .item import ItemSerializer
from .task import TaskSerializer

from .crop import (
    CropSerializer, 
    CropProductSerializer, 
    CropProductUnitSerializer,
    CropVarietySerializer, 
    CropMaterialSerializer, 
    CropTemplateSerializer,
    CropTemplateMaterialSerializer,
    CropTemplateTaskSerializer,
    FarmCropSerializer,
    CropRecipeSerializer,
    CropRecipeMaterialSerializer,
    CropRecipeTaskSerializer
)

from .daily_log import (
    DailyLogSerializer, 
    DailyLogBasicSerializer,
    SupervisorSerializer,
    AttachmentSerializer,
    AuditLogSerializer,
    SyncRecordSerializer,
    SyncConflictDLQSerializer,
    OfflineSyncQuarantineSerializer,
)
from .custody import CustodyTransferSerializer, CustodyIssueSerializer, CustodyTransitionSerializer

from .tree import (
    TreeProductivityStatusSerializer,
    TreeLossReasonSerializer,
    LocationTreeStockSerializer,
    TreeStockEventSerializer,
    ManualTreeAdjustmentSerializer,
    TreeProductivityRefreshSerializer,
    ActivityTreeServiceCoverageSerializer,
    ActivityTreeServiceCoverageInputSerializer
)

from .activity import (
    ActivitySerializer,
    ActivityHarvestSerializer,
    ActivityIrrigationSerializer,
    ActivityMaterialApplicationSerializer,
    ActivityMachineUsageSerializer
)

from .inventory import (
    ItemInventorySerializer,
    StockMovementSerializer,
    HarvestLotSerializer,
    # HarvestLogSerializer,
    MaterialCatalogSerializer,
    HarvestProductFarmStatsSerializer,
    BiologicalAssetCohortSerializer,
    BiologicalAssetTransactionSerializer,
    TreeCensusVarianceAlertSerializer,
    MassCasualtyWriteoffRequestSerializer,
    MassCasualtyCohortEntrySerializer,
)

from .settings import CostConfigurationSerializer, FarmSettingsSerializer
from .policy_engine import (
    PolicyPackageSerializer,
    PolicyVersionSerializer,
    FarmPolicyBindingSerializer,
    PolicyActivationRequestSerializer,
    PolicyActivationEventSerializer,
    PolicyExceptionRequestSerializer,
    PolicyExceptionEventSerializer,
)

from .planning import (
    CropPlanSerializer, 
    CropPlanBudgetLineSerializer, PlanImportLogSerializer,
    PlannedActivitySerializer,
    PlannedMaterialSerializer
)

from .commercial import (
    FinancialLedgerSerializer,
    CostAllocationInputSerializer,
    HarvestGradingInputSerializer,
    ProfitabilityReportSerializer,
    SalesInvoiceSerializer,
    SalesInvoiceItemSerializer,
    CustomerSerializer,
    # ServiceProviderSerializer  # Disabled: Model deleted during Phase 1 purge
)

from .partnerships import (
    SharecroppingContractSerializer,
    TouringAssessmentSerializer,
    SharecroppingReceiptSerializer
)
