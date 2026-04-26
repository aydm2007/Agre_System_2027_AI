export const SERVICE_SCOPE_OPTIONS = [
  { value: 'general', label: 'خدمة عامة' },
  { value: 'irrigation', label: 'ري' },
  { value: 'fertilization', label: 'تسميد' },
  { value: 'pruning', label: 'تقليم' },
  { value: 'cleaning', label: 'تنظيف' },
  { value: 'protection', label: 'حماية' },
]

export const SERVICE_SCOPE_LABEL_MAP = SERVICE_SCOPE_OPTIONS.reduce((acc, option) => {
  acc[option.value] = option.label
  return acc
}, {})

export const DEFAULT_SERVICE_SCOPE = SERVICE_SCOPE_OPTIONS[0].value

export const TEXT = {
  title: 'سجل الإنجاز اليومي',
  offlineNotice: 'تعمل حالياً دون اتصال. سيتم حفظ الإدخالات وإرسالها تلقائياً فور توفر الشبكة.',
  queueNotice: (count) => `لديك ${count} عنصر في قائمة الانتظار، سيتم رفعها عند الاتصال.`,
  queueSync: 'مزامنة الآن',
  queueSyncing: 'جاري المزامنة...',
  fields: {
    date: 'تاريخ الإنجاز',
    farm: 'المزرعة',
    location: 'الموقع',
    crop: 'المحصول',
    task: 'المهمة',
    choose: 'اختر',
    noFarms: 'لا توجد مزارع متاحة',
    noLocations: 'لا توجد مواقع متاحة',
    noCrops: 'لا توجد محاصيل متاحة',
    noTasks: 'لا توجد مهام متاحة',
    team: 'فريق التنفيذ',
    teamPlaceholder: 'أدخل أسماء الفريق (سطر لكل اسم أو مفصولة بفواصل)',
    hours: 'عدد الساعات',
    hoursPlaceholder: 'مثال: 8',
  },
  requirements: {
    wellTitle: 'متطلبات الآبار',
    wellSelect: 'اختر البئر',
    wellInfo: 'حدد البئر والقراءة لضمان دقة تسجيل الصرف المائي.',
    wellReadingPlaceholder: 'قراءة العداد (م³)',
    wellReadingHint: 'في حال عدم توفر القراءة يجب امتلاك صلاحية تخطي الإدخال.',
    solarPower: 'ري بالطاقة الشمسية',
    solarPowerHint: 'تفعيل هذا الخيار يعفي من إدخال الديزل.',
    dieselQty: 'كمية الديزل (لتر)',
    dieselQtyPlaceholder: 'أدخل الكمية',
    dieselQtyHint: 'اتركه فارغاً إذا لم يستهلك.',
    areaTitle: 'المساحة المنفذة',
    areaPlaceholder: 'أدخل المساحة',
    areaHint: 'استخدم وحدة القياس المناسبة (م²، دونم، إلخ).',
    machineryTitle: 'متطلبات الآليات',
    machineryAsset: 'اختر الآلة',
    machineHoursPlaceholder: 'ساعات التشغيل',
    machineMeterPlaceholder: 'قراءة العداد',
    fuelPlaceholder: 'الوقود المستهلك (لتر)',
    suggestedAssetsTitle: 'الأصول المقترحة',
    suggestedAssetsHint: 'اختر الأصل الملائم لتعبئة البيانات بسرعة.',
    suggestedAssetsEmpty: 'لا توجد أصول متاحة مطابقة لهذا النوع.',
    suggestedAssetsUse: 'استخدام الأصل',
    assetDetailTitle: 'تفاصيل الأصل المحدد',
    assetCategory: 'الفئة',
    assetCode: 'الكود',
    assetUnavailable: 'معلومات الأصل غير مكتملة.',
    harvestTitle: 'بيانات الحصاد',
    harvestSelectPlaceholder: 'اختر الصنف المحصود',
    harvestQtyPlaceholder: 'الكمية',
  },
  alerts: {
    heading: 'تنبيهات المهمة الحالية',
    noMachinery: 'المهمة تتطلب آليات ولا يوجد أصل مناسب متاح حالياً.',
    noWell: 'هذه المهمة تحتاج مصدر ماء ولم يتم تحديد بئر أو نظام ري.',
    noProducts: 'المهمة حصاد ولم يتم ربط منتجات بالمحصول بعد.',
    missingArea: 'يرجى إدخال المساحة لضمان اكتمال السجل.',
  },
  queue: {
    pending: (count) => `طلبات غير متزامنة: ${count}`,
    syncing: 'جاري المزامنة...',
    manage: 'إدارة العناصر غير المتزامنة',
    inspect: 'عرض تفاصيل الطابور',
    detailsTitle: 'تفاصيل العناصر قيد الانتظار',
    detailsEmpty: 'لا توجد عناصر حالية في الطابور.',
    failedHeader: 'عناصر فشلت في المزامنة',
    close: 'إغلاق النافذة',
    syncSuccess: (count) => `تمت مزامنة ${count} عنصر${count > 1 ? 'اً' : ''} بنجاح.`,
    viewLatest: 'عرض الإدخالات الأحدث',
  },
  status: {
    online: 'متصل',
    offline: 'دون اتصال',
    queuePending: (count) => `عناصر متبقية: ${count}`,
    queueEmpty: 'لا توجد عناصر مؤجلة',
  },
  sections: {
    toggleShow: 'عرض التفاصيل',
    toggleHide: 'إخفاء التفاصيل',
    team: {
      title: 'فريق التنفيذ والوقت',
      hint: 'أدخل أسماء الفريق وعدد الساعات المنجزة لكل نشاط.',
    },
    resources: {
      title: 'تفاصيل الخدمة والموارد',
      hint: 'بيانات اختيارية للمياه والسماد ولوحة الأعداد الخدمية.',
    },
    requirements: {
      title: 'متطلبات إضافية مرتبطة بالمهمة',
      hint: 'تظهر فقط عند الحاجة مثل الآبار أو المساحة.',
    },
  },
  materials: {
    title: 'الخامات والمواد',
    materialPlaceholder: 'اختر المادة',
    quantityPlaceholder: 'الكمية',
    unitPlaceholder: 'الوحدة',
    pendingTitle: 'مرفقات قيد الرفع',
    uploadedTitle: 'مرفقات تم رفعها',
    remove: 'إزالة',
  },
  review: {
    title: 'مراجعة البيانات قبل الحفظ',
    teamReady: 'تم تحديد فريق التنفيذ وساعات العمل.',
    teamMissing: 'لم يتم إدخال فريق التنفيذ أو الساعات بشكل صحيح.',
    harvestReady: 'بيانات الحصاد مكتملة.',
    harvestMissing: 'لا توجد بيانات حصاد لهذه المهمة.',
    materialsReady: 'تم تحديد مادة أو مرفق لهذا النشاط.',
    materialsMissing: 'لا توجد مواد مرتبطة بالنشاط.',
    attachments: (pending, uploaded) => `مرفقات: ${uploaded} مرفق مرفوع / ${pending} قيد الانتظار`,
    harvestPreview: (product, qty, uom) => `الحصاد: ${product} • ${qty} ${uom}`,
    materialsPreview: (title, qty, uom) => `المادة: ${title} • ${qty} ${uom}`,
  },
  validation: {
    teamRequired: 'أدخل اسم واحد على الأقل لفريق التنفيذ.',
    hoursRequired: 'يرجى إدخال عدد ساعات صالح أكبر من صفر.',
  },
  tree: {
    title: 'بيانات الأشجار المعمرة',
    variety: 'الصنف',
    varietyPlaceholder: 'اختر الصنف',
    delta: 'تغير عدد الأشجار',
    deltaHint: 'أدخل الفرق النهائي (موجب للزيادة، سالب للفقد).',
    serviced: 'العدد الخدمي المنجز',
    servicedPlaceholder: 'عدد الأشجار التي تمت خدمتها',
    lossReason: 'سبب الفقد',
    harvestQuantity: 'كمية الإنتاج (اختياري)',
    waterVolume: 'كمية المياه',
    waterUom: 'وحدة المياه',
    fertilizerQuantity: 'كمية السماد',
    fertilizerUom: 'وحدة السماد',
    servicePanelTitle: 'العدد الخدمي حسب الأصناف',
    servicePanelHint: 'حدد لكل صنف عدد الأشجار التي تمت خدمتها فعلياً في هذا النشاط.',
    serviceOffline: 'لا يمكن تحميل بيانات الجرد حالياً لعدم توفر الاتصال بالشبكة.',
    serviceError: 'تعذر تحميل بيانات الأصناف لهذا الموقع.',
    serviceEmpty: 'لا توجد أصناف مرتبطة بالموقع، يمكن إضافتها يدوياً من هنا.',
    serviceVariety: 'صنف غير معرّف',
    serviceCurrent: 'الرصيد الحالي',
    serviceCount: 'العدد الخدمي',
    serviceScope: 'نطاق الخدمة',
    serviceAfter: 'الرصيد بعد الخدمة',
    serviceNotes: 'ملاحظات الخدمة',
    serviceNotesPlaceholder: 'أدخل أي ملاحظات إضافية',
    serviceRemove: 'حذف السطر',
    serviceAddSelected: 'إضافة صنف للخدمة',
    serviceTotal: (value) => `مجموع الأعداد الخدمية: ${value}`,
    serviceExistingTotal: (value) => `الأعداد المسجلة اليوم: ${value}`,
    serviceProjected: (value) => `إجمالي الخدمة بعد الإضافة: ${value}`,
    serviceExistingToday: (value) => `تم تسجيل ${value} شجرة في هذا اليوم.`,
    serviceCoverageToday: (value) => `تغطية اليوم: ${value}`,
    serviceCoverageLifetime: (value) => `التغطية التراكمية: ${value}`,
    serviceRemaining: (value) => `متبقي ضمن الرصيد: ${value}`,
    serviceCompleted: 'تمت تغطية كامل الرصيد لهذا الصنف اليوم.',
    serviceWarningExceeded: 'سيؤدي هذا الإدخال إلى تجاوز الرصيد الفعلي للموقع.',
    serviceLastRecorded: (date, count, type) => `آخر خدمة: ${date} • ${count} • ${type}`,
    serviceLatestBy: (name) => `مسجل بواسطة: ${name}`,
    serviceLifetimeTotal: (value) => `إجمالي الخدمة التراكمية: ${value}`,
    serviceLatestMissing: 'لا توجد خدمات مسجلة ضمن الفترة المحددة.',
    serviceLocationCurrent: (value) => `إجمالي الأشجار في الموقع: ${value}`,
    serviceLocationStocks: (value) => `عدد الأصناف المرتبطة: ${value}`,
    serviceLocationUpdated: (value) => `آخر تحديث للجرد: ${value}`,
    summaryTitle: 'ملخص الأشجار المعمرة',
    summaryActivities: (count) => `${count} نشاط شجري مسجل`,
    summaryCurrent: 'إجمالي الرصيد الحالي',
    summaryServiced: 'عدد الأشجار المخدومة',
    summaryNet: 'الصافي',
    summaryGain: 'زيادة',
    summaryLoss: 'نقص',
    summaryEmpty: 'لا توجد بيانات شجرية لعرضها في هذا اليوم.',
    summaryEntriesTitle: 'تفاصيل حسب المحصول والصنف',
    tableHeaders: {
      crop: 'المحصول',
      variety: 'الصنف',
      location: 'الموقع',
      activities: 'عدد الأنشطة',
      treesServiced: 'العدد الخدمي',
      currentCount: 'الرصيد الحالي',
      netChange: 'التغير الصافي',
    },
  },
  summary: {
    title: 'ملخص اليوم',
    loading: 'جاري تحميل الملخص...',
    error: 'تعذر تحميل البيانات.',
    logs: 'عدد السجلات',
    activities: 'عدد الأنشطة',
    distinct_supervisors: 'المراقبين', // Added missing key based on usage
  },
  activitySummary: {
    title: 'قائمة الأنشطة',
    loading: 'جاري تحميل الأنشطة...',
    error: 'تعذر تحميل الأنشطة.',
    empty: 'لا توجد أنشطة مسجلة لهذا اليوم.',
    viewOnly: 'لا تملك صلاحية التعديل على هذا النشاط.',
    editMode: 'يتم الآن تعديل النشاط.',
    cancelEdit: 'إلغاء التعديل',
    edit: 'تعديل',
    delete: 'حذف',
    deleteConfirm: 'هل تريد حذف هذا النشاط؟',
    editSuccess: 'تم تحديث النشاط بنجاح.',
    editError: 'تعذر تعديل النشاط.',
    deleteSuccess: 'تم حذف النشاط بنجاح.',
    deleteError: 'تعذر حذف النشاط.',
    offlineEditError: 'لا يمكن تعديل النشاط أثناء عدم الاتصال.',
    offlinePending: 'بانتظار المزامنة',
    existingAttachment: 'مرفق مرفوع مسبقاً',
    actions: 'الإجراءات',
    updatedAt: 'آخر تحديث',
  },
  submit: {
    ready: 'حفظ النشاط',
    sending: 'جاري الحفظ...',
  },
}

export const AREA_UOMS = [
  { value: 'm2', label: 'متر مربع' },
  { value: 'dunum', label: 'دونم' },
  { value: 'hectare', label: 'هكتار' },
  { value: 'libnah', label: 'لبنة' },
]

export const MATERIAL_TYPES = {
  FERTILIZER: 'أسمدة',
  PESTICIDE: 'مبيدات',
  SEED: 'بذور',
  FUEL: 'وقود',
  FEED: 'أعلاف',
  PACKAGING: 'تعبئة وتغليف',
  SPARE_PARTS: 'قطع غيار',
  TOOLS: 'أدوات',
  ORGANIC: 'أسمدة عضوية',
  CHEMICAL: 'كيماويات',
  OTHER: 'أخرى',
}

export const describeDataSource = (source) => {
  if (source === 'cache') {
    return 'بيانات من النسخة المخزنة'
  }
  if (source === 'offline') {
    return 'لا يمكن تحديث البيانات أثناء عدم الاتصال'
  }
  return 'تم التحديث من الخادم'
}

export const formatTimestamp = (value) => {
  if (!value) {
    return ''
  }
  try {
    return new Date(value).toLocaleString('ar-EG', { hour12: false })
  } catch (error) {
    return String(value)
  }
}

export const formatDataSourceMeta = ({ source, storedAt }) => {
  const label = describeDataSource(source)
  if (storedAt) {
    return `${label} • ${formatTimestamp(storedAt)}`
  }
  return label
}

export const WATER_UOMS = [
  { value: 'm3', label: 'متر مكعب' },
  { value: 'liter', label: 'لتر' },
  { value: 'gallon', label: 'جالون' },
]

export const FERTILIZER_UOMS = [
  { value: 'kg', label: 'كيلوجرام' },
  { value: 'g', label: 'جرام' },
  { value: 'liter', label: 'لتر' },
  { value: 'ton', label: 'طن' },
]

export const emptyServiceStats = {
  period: { coverageRatio: 0, lastServiceDate: null },
  lifetime: { coverageRatio: 0, totalServiced: 0, lastServiceDate: null },
  latestEntry: null,
}

export const formatPercent = (value) => {
  // [AGRI-GUARDIAN §1.II] Use Number() for display-only formatting
  const num = Number(value)
  if (!Number.isFinite(num)) return '0%'
  return `${(num * 100).toFixed(1)}%`
}

export const formatDateOnly = (value) => {
  if (!value) return ''
  try {
    return new Date(value).toISOString().slice(0, 10)
  } catch {
    return ''
  }
}
