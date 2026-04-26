export const TEXT = {
  title: 'إدارة منتجات الحصاد',
  description: 'أضف منتجات الحصاد المرتبطة بمحاصيلك وتابع أداء الإنتاج عبر جميع المزارع.',
  cropLabel: 'المحصول',
  itemLabel: 'المنتج',
  primaryLabel: 'منتج رئيسي',
  notesLabel: 'ملاحظات',
  submit: 'إضافة المنتج',
  reset: 'إعادة التعيين',
  catalogTitle: 'كتالوج منتجات الحصاد',
  totalHarvest: 'إجمالي كمية الحصاد',
  lastHarvest: 'آخر تاريخ حصاد',
  actions: 'الإجراءات',
  deleteConfirm: 'حذف',
  deleteConfirmMessage: (name) => `هل ترغب في حذف المنتج «${name}»؟`,
  loading: 'جاري تحميل بيانات كتالوج منتجات الحصاد...',
  error: 'حدث خطأ أثناء تحميل بيانات منتجات الحصاد.',
  successCreate: (name) => `تم إنشاء المنتج «${name}» بنجاح.`,
  successDelete: (name) => `تم حذف المنتج «${name}» بنجاح.`,
  edit: 'تعديل',
  save: 'حفظ',
  cancel: 'إلغاء',
  notesColumn: 'الملاحظات',
  primaryColumn: 'رئيسي',
  updateSuccess: (name) => `تم تحديث المنتج «${name}» بنجاح.`,
  noResults: 'لا توجد منتجات حصاد مطابقة للمرشحات الحالية.',
  farmFilterLabel: 'المزرعة',
  cropFilterLabel: 'المحصول',
  allOption: 'جميع القيم',
  farmDetails: 'تفاصيل المزارع',
  farmTotal: 'الإجمالي',
  farmLastHarvest: 'آخر حصاد',
  filterHint: 'يمكنك تصفية النتائج حسب المزرعة أو المحصول.',
  createItemTitle: 'إنشاء منتج حصاد جديد',
  createItemButton: 'حفظ المنتج',
  itemNameLabel: 'اسم المنتج',
  unitLabel: 'الوحدة',
  uomLabel: 'وحدة القياس',
  catalogTableTitle: 'قائمة منتجات الحصاد الحالية',
  farmSummaryNone: 'لا توجد بيانات حصاد لهذا المنتج في المزارع المحددة.',
  formValidationError: 'يرجى اختيار المحصول والمنتج قبل الإرسال.',
  itemValidationError: 'يرجى إدخال اسم المنتج.',
  unitColumn: 'الوحدة الافتراضية',
  yes: 'نعم',
  no: 'لا',
  packagingColumn: 'التعبئة والجودة والوحدات',
  qualityLabel: 'درجة الجودة',
  packingTypeLabel: 'نوع التعبئة',
  referencePriceLabel: 'السعر المرجعي (ريال)',
  packSizeLabel: 'حجم العبوة',
  packUomLabel: 'وحدة الحجم',
  unitsSectionTitle: 'وحدات المنتج والتحويلات',
  addUnitButton: 'إضافة وحدة',
  unitSelectLabel: 'الوحدة',
  unitMultiplierLabel: 'المعامل',
  unitUomLabel: 'رمز الوحدة',
  unitDefaultLabel: 'أساسي',
  removeUnitButton: 'حذف',
  unitsEmpty: 'لا توجد وحدات مرتبطة بعد.',
  unitDefaultTag: 'أساسي',
  unitValidationError: 'أضف وحدة واحدة على الأقل لكل منتج.',
}

export const createUnitRow = (overrides = {}) => ({
  id: null,
  unit: '',
  multiplier: '',
  uom: '',
  is_default: false,
  ...overrides,
})

export const ensureDefaultUnitSelection = (units) => {
  if (!units.length) {
    return [createUnitRow({ is_default: true, multiplier: '1' })]
  }
  let defaultFound = false
  const normalized = units.map((unit) => {
    if (unit.is_default && !defaultFound) {
      defaultFound = true
      return unit
    }
    if (unit.is_default && defaultFound) {
      return { ...unit, is_default: false }
    }
    return unit
  })
  if (!defaultFound) {
    normalized[0] = { ...normalized[0], is_default: true }
  }
  return normalized
}

export const toNumberOrNull = (value) => {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

export const coerceId = (value) => {
  if (value === null || value === undefined || value === '') {
    return null
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

export const prepareProductPayload = (source, { includeIdentifiers = false } = {}) => {
  const payload = {
    is_primary: Boolean(source.is_primary),
    notes: source.notes?.trim() || '',
    quality_grade: source.quality_grade?.trim() || '',
    packing_type: source.packing_type?.trim() || '',
    reference_price: toNumberOrNull(source.reference_price),
    pack_size: toNumberOrNull(source.pack_size),
    pack_uom: source.pack_uom?.trim() || '',
  }

  const unitsPayload = (source.units || [])
    .map((unitRow) => {
      const multiplier = toNumberOrNull(unitRow.multiplier)
      const unitId = unitRow.unit ? Number(unitRow.unit) : null
      if (!unitId || !multiplier || multiplier <= 0) {
        return null
      }
      return {
        id: unitRow.id,
        unit: unitId,
        multiplier,
        uom: unitRow.uom?.trim() || undefined,
        is_default: Boolean(unitRow.is_default),
      }
    })
    .filter(Boolean)

  if (unitsPayload.length && !unitsPayload.some((unit) => unit.is_default)) {
    unitsPayload[0].is_default = true
  }

  payload.units = unitsPayload

  if (includeIdentifiers) {
    payload.farm = coerceId(source.farm)
    payload.crop = coerceId(source.crop)
    payload.item = coerceId(source.item)
  }

  return payload
}

export const formatNumber = (value) => {
  if (value === null || value === undefined) return '-'
  const number = Number(value)
  if (Number.isNaN(number)) return '-'
  return number.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
