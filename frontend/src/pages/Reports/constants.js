import { format } from 'date-fns'

export const REPORT_SECTIONS = [
  {
    key: 'summary',
    label: 'الملخص التنفيذي',
    description: 'المؤشرات الرئيسية للفترة الحالية.',
    defaultSelected: true,
    loadClass: 'fast',
    requires: [],
  },
  {
    key: 'activities',
    label: 'الأنشطة',
    description: 'سجل الأنشطة اليومية التفصيلي.',
    defaultSelected: false,
    loadClass: 'heavy',
    requires: [],
  },
  {
    key: 'charts',
    label: 'الرسوم البيانية',
    description: 'استهلاك المواد وتشغيل الآليات.',
    defaultSelected: false,
    loadClass: 'heavy',
    requires: [],
  },
  {
    key: 'tree_summary',
    label: 'الأشجار',
    description: 'الأرصدة الحالية للأشجار المعمّرة.',
    defaultSelected: false,
    loadClass: 'heavy',
    requires: ['farm'],
  },
  {
    key: 'tree_events',
    label: 'أحداث الأشجار',
    description: 'التغيرات والحركات المرتبطة بالأشجار.',
    defaultSelected: false,
    loadClass: 'heavy',
    requires: ['farm'],
  },
  {
    key: 'risk_zone',
    label: 'منطقة المخاطر',
    description: 'انحرافات التكلفة والمخاطر التشغيلية.',
    defaultSelected: false,
    loadClass: 'heavy',
    requires: ['farm', 'crop_id'],
  },
  {
    key: 'detailed_tables',
    label: 'الجداول التفصيلية',
    description: 'الجداول القابلة للمراجعة والتصدير.',
    defaultSelected: false,
    loadClass: 'heavy',
    requires: [],
  },
]

export const REPORT_SECTION_STATUS_LABELS = {
  idle: 'غير محمّل',
  loading: 'جارٍ التحميل',
  ready: 'جاهز',
  error: 'فشل',
  stale: 'يحتاج تحديث',
}

export const TREE_EVENT_LABELS = {
  planting: 'زراعة',
  loss: 'فقد',
  adjustment: 'تعديل',
  transfer: 'نقل',
  harvest: 'حصاد',
  inspection: 'تفقد',
}

export const TEXT = {
  pageTitle: 'تقارير الأنشطة المتقدمة',
  filters: {
    title: 'خيارات التصفية',
    start: 'من تاريخ',
    end: 'إلى تاريخ',
    season: 'الموسم',
    farm: 'المزرعة',
    location: 'الموقع',
    crop: 'المحصول',
    task: 'المهمة',
    variety: 'الصنف',
    status: 'حالة الأشجار',
    placeholderFarm: 'اختر المزرعة',
    placeholderLocation: 'اختر الموقع',
    placeholderCrop: 'اختر المحصول',
    placeholderTask: 'اختر المهمة',
    placeholderVariety: 'اختر الصنف',
    placeholderStatus: 'اختر حالة الأشجار',
    apply: 'عرض التقرير',
  },
  summary: {
    totalHours: 'إجمالي ساعات العمل',
    machineHours: 'ساعات تشغيل الآليات',
    materialsQty: 'كمية المدخلات المستخدمة',
    harvestQty: 'كمية الحصاد',
    distinctLocations: 'عدد المواقع',
    distinctWells: 'عدد الآبار',
    unitHours: 'ساعة',
    unitQty: 'وحدة',
  },
  charts: {
    materials: 'أكثر المواد استخدامًا',
    machines: 'مؤشرات تشغيل الآليات (ساعات/وقود/عداد)',
    noData: 'لا توجد بيانات متاحة لعرضها.',
  },
  treeSummary: {
    title: 'ملخص الأشجار المعمرة',
    totalTrees: 'إجمالي الأشجار',
    productive: 'أشجار منتجة',
    declining: 'أشجار متراجعة',
    status: 'الحالة الإنتاجية',
    planting: 'تاريخ الزراعة',
    source: 'مصدر الشتلات',
    noData: 'لا توجد بيانات للأشجار ضمن نطاق المرشحات.',
  },
  treeEvents: {
    title: 'أحداث الأشجار المعمرة',
    date: 'التاريخ',
    type: 'نوع الحدث',
    location: 'الموقع',
    variety: 'الصنف',
    delta: 'التغير',
    resulting: 'الرصيد بعد الحدث',
    reason: 'سبب الفقد',
    harvestQuantity: 'كمية الحصاد',
    waterVolume: 'كمية المياه',
    fertilizerQuantity: 'كمية السماد',
    noData: 'لا توجد أحداث للأشجار ضمن نطاق المرشحات.',
  },
  table: {
    title: 'الجدول التفصيلي للأنشطة',
    locationBreakdown: 'إجمالي الجهود حسب الموقع',
    wellBreakdown: 'أداء الآبار',
    date: 'التاريخ',
    farm: 'المزرعة',
    location: 'الموقع',
    well: 'البئر',
    wellReadingTotal: 'إجمالي قراءة البئر',
    asset: 'الآلية / الأصل',
    crop: 'المحصول',
    task: 'المهمة',
    supervisor: 'المشرف',
    hours: 'ساعات العمل',
    machineHours: 'ساعات الآلة',
    machineMeter: 'قراءة العداد',
    wellReading: 'قراءة البئر',
    fuel: 'الوقود (لتر)',
    activitiesCount: 'عدد الأنشطة',
    empty: 'لا توجد بيانات مطابقة للمعايير المحددة.',
    export: 'تصدير',
    exportExcel: 'تصدير Excel',
    exportJson: 'تصدير JSON',
  },
  loading: 'جاري تحميل البيانات...',
  errors: {
    loadFarms: 'تعذر تحميل بيانات المزارع.',
    loadCrops: 'تعذر تحميل بيانات المحاصيل.',
    loadLocations: 'تعذر تحميل بيانات المواقع.',
    loadTasks: 'تعذر تحميل بيانات المهام.',
    loadReport: 'تعذر تحميل التقرير. يرجى المحاولة مجددًا.',
  },
  export: {
    pending: 'تم إرسال طلب التقرير، جار المعالجة...',
    success: 'التقرير جاهز، جاري التنزيل.',
    failed: 'فشل تجهيز التقرير. حاول مجددًا.',
    timeout: 'انتهى وقت انتظار التقرير، أعد المحاولة لاحقًا.',
    jobsTitle: 'مهام التصدير',
    inProgress: 'قيد المعالجة',
    completed: 'مكتمل',
    failedLabel: 'فاشل',
  },
  sections: {
    title: 'مكوّنات التقرير',
    staleHint: 'تم تعديل المرشحات، وبعض الأقسام تحتاج تحديثًا.',
    missingRequirements: 'يتطلب استكمال المرشحات اللازمة قبل التحميل.',
  },
}

export function formatNumber(value, fraction = 2) {
  const number = Number(value ?? 0)
  return Number.isFinite(number) ? number.toFixed(fraction) : '0'
}

export function formatDate(value) {
  if (!value) return '-'
  try {
    return format(new Date(value), 'yyyy-MM-dd')
  } catch (error) {
    return String(value)
  }
}

export function formatDateTimeValue(value) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('ar-EG')
  } catch (error) {
    return String(value)
  }
}
