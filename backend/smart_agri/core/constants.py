from django.db import models

class AssetStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'
    MAINTENANCE = 'maintenance', 'Maintenance'

class StandardUOM(models.TextChoices):
    # Area
    LIBNAH = 'libnah', 'لبنة'
    MAAD = 'maad', 'معاد'
    HECTARE = 'hectare', 'هكتار'
    M2 = 'm2', 'متر مربع'
    # Weight
    KG = 'kg', 'كيلوجرام'
    TON = 'ton', 'طن'
    GRAM = 'g', 'جرام'
    # Volume
    LITER = 'L', 'لتر'
    M3 = 'm3', 'متر مكعب'
    # Others
    PCS = 'pcs', 'حبة/قطعة'
    PACK = 'pack', 'عبوة'
    UNIT = 'Unit', 'وحدة قياسية'
    # Labor & Tasks (Yemeni Architecture)
    SURRA = 'surra', 'فترة (صرة)'
    HOUR = 'hour', 'ساعة'
    DAY = 'day', 'يوم'
    LOT = 'lot', 'مقطوعية'

class CropPlanStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    COMPLETED = 'completed', 'Completed'
    SETTLED = 'settled', 'Settled (WIP Closed)'
    ARCHIVED = 'archived', 'Archived'

class DailyLogStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    SUBMITTED = 'submitted', 'Submitted'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    # Keeping Pending/Reviewed if needed for migration, otherwise consolidating
    # PENDING = 'pending', 'Pending' # Deprecated
    # REVIEWED = 'reviewed', 'Reviewed' # Deprecated

class SyncStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    SUCCESS = 'success', 'Success'
    FAILED = 'failed', 'Failed'

class SyncCategory(models.TextChoices):
    DAILY_LOG = 'daily_log', 'Daily Log'
    HARVEST = 'harvest', 'Harvest'
    CUSTODY = 'custody', 'Custody'
    HTTP_REQUEST = 'http_request', 'HTTP Request'
