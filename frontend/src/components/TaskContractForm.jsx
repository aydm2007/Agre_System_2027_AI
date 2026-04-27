import React, { useMemo, useState, useCallback, useEffect } from 'react'

export const CARD_ORDER = ['execution', 'materials', 'labor', 'well', 'machinery', 'fuel', 'perennial', 'harvest', 'control', 'variance', 'financial_trace']
export const MANDATORY_CARDS = new Set(['execution', 'control', 'variance'])
export const OPTIONAL_CARDS = CARD_ORDER.filter((cardKey) => !MANDATORY_CARDS.has(cardKey) && cardKey !== 'financial_trace')

export const CARD_LABELS = {
  execution: 'التنفيذ', materials: 'المواد', labor: 'العمالة',
  well: 'الري/البئر', machinery: 'الآليات', fuel: 'الوقود',
  perennial: 'الخدمة المعمرة', harvest: 'الحصاد', control: 'الرقابة',
  variance: 'الانحراف', financial_trace: 'الأثر المالي',
}

export const CARD_DESCRIPTIONS = {
  execution: 'بطاقة إلزامية للتقدم والتنفيذ اليومي.', materials: 'تربط الاستخدام الفعلي للمواد والانحرافات.',
  labor: 'تربط دفعات العمالة ومؤشرات السُّرّة.', well: 'تربط قراءة البئر والري والانحرافات.',
  machinery: 'تربط المعدة وساعات التشغيل.', fuel: 'تتبع الوقود المتوقع مقابل الفعلي.',
  perennial: 'تغطي الخدمة المعمرة وعدّ الأشجار.', harvest: 'تغطي الحصاد والكميات المنتجة.',
  control: 'بطاقة إلزامية للرقابة.', variance: 'بطاقة إلزامية للانحراف.',
  financial_trace: 'معاينة governed للأثر المالي.',
}

export const ARCHETYPE_LABELS = {
  GENERAL: 'مهمة عامة', IRRIGATION: 'ري مباشر (بئر)', MACHINERY: 'آليات ومعدات',
  HARVEST: 'حصاد وإنتاج', PERENNIAL_SERVICE: 'خدمة أشجار معمرة', LABOR_INTENSIVE: 'عمالة كثيفة',
  MATERIAL_INTENSIVE: 'مواد كثيفة (أسمدة/مبيدات)', FUEL_SENSITIVE: 'وقود مكثف',
  BIOLOGICAL_ADJUSTMENT: 'تسوية بيولوجية (خلع/تلف)', CONTRACT_SETTLEMENT_LINKED: 'مرتبطة بتسوية تعاقدية',
}

export const PRESET_OPTIONS = {
  GENERAL_SEASONAL: { label: 'موسمي عام', description: 'مهمة موسمية مرنة.', archetype: 'GENERAL', selectedCards: ['materials', 'labor'], requiresArea: true, isAssetTask: false, assetType: '' },
  ORCHARD_SERVICE: { label: 'خدمة بستان/أشجار معمرة', description: 'خدمة دورية للأشجار المعمرة.', archetype: 'PERENNIAL_SERVICE', selectedCards: ['labor', 'perennial'], requiresArea: true, isAssetTask: false, assetType: '' },
  MANGO: { label: 'مانجو', description: 'تسميد وخدمة ورعاية لمانجو.', archetype: 'PERENNIAL_SERVICE', selectedCards: ['materials', 'labor', 'perennial'], requiresArea: true, isAssetTask: false, assetType: '' },
  BANANA: { label: 'موز', description: 'قالب موز مع ري ومواد وعمالة.', archetype: 'PERENNIAL_SERVICE', selectedCards: ['materials', 'labor', 'well', 'perennial'], requiresArea: true, isAssetTask: false, assetType: '' },
  SEASONAL_HARVEST: { label: 'حصاد موسمي', description: 'حصاد لمحصول موسمي.', archetype: 'HARVEST', selectedCards: ['materials', 'labor', 'harvest'], requiresArea: true, isAssetTask: false, assetType: '' },
  PERENNIAL_HARVEST: { label: 'حصاد معمّر', description: 'حصاد لمحصول معمّر.', archetype: 'HARVEST', selectedCards: ['materials', 'labor', 'harvest', 'perennial'], requiresArea: true, isAssetTask: false, assetType: '' },
  IRRIGATION_SERVICE: { label: 'خدمة ري', description: 'تشغيل يعتمد على البئر.', archetype: 'IRRIGATION', selectedCards: ['well', 'labor'], requiresArea: true, isAssetTask: false, assetType: '' },
  PEST_CONTROL: { label: 'مكافحة/رش', description: 'مواد وعمالة وآليات في مهمة واحدة.', archetype: 'MATERIAL_INTENSIVE', selectedCards: ['materials', 'labor', 'machinery'], requiresArea: true, isAssetTask: false, assetType: '' },
}

export const STAGES = {
  preparation: 'التحضير', planting: 'الزراعة', growing: 'النمو الخضري',
  harvest: 'الحصاد', postHarvest: 'ما بعد الحصاد', undefined: 'مرحلة غير محددة',
}

const TEXT = {
  stage: 'المرحلة', name: 'اسم الخدمة/المهمة', crop: 'المحصول',
  preset: 'قالب التطبيق الذكي (V21 Standard)', presetHint: 'اختر النموذج الذي سيولد العقد الذكي لهذه المهمة.',
  archetype: 'النموذج التشغيلي (Archetype)', cards: 'البطاقات الذكية والتكامل',
  cardsHint: 'البطاقات الإلزامية مفعلة تلقائياً للامتثال.',
  requirements: 'متطلبات التنفيذ الميداني', preview: 'معاينة مسار الاعتماد والظهور',
  previewSimple: 'يظهر للمشرف في SIMPLE', previewStrict: 'يظهر في اعتمادات STRICT',
  requiredInputs: 'حقول التنفيذ المتوقعة', derivedFlags: 'المعطيات الذكية المستخلصة',
  requiresArea: 'تحتاج مساحة', isAssetTask: 'مرتبطة بأصل/معدّة', assetType: 'نوع الأصل',
  customLabel: 'مخصص', save: 'حفظ العقد الذكي للمهمة', cancel: 'إلغاء'
}

export const createSelectedCards = (cards = []) =>
  OPTIONAL_CARDS.reduce((acc, cardKey) => ({ ...acc, [cardKey]: cards.includes(cardKey) }), {})

export const enabledCardsFromSelection = (selectedCards = {}) => {
  const enabled = new Set(['execution', 'control', 'variance'])
  Object.entries(selectedCards).forEach(([cardKey, value]) => value && enabled.add(cardKey))
  return CARD_ORDER.filter((cardKey) => enabled.has(cardKey))
}

export const buildTaskContract = ({ archetype, selectedCards, requiresArea, isAssetTask, assetType }) => {
  const enabled = enabledCardsFromSelection(selectedCards)
  const has = (cardKey) => enabled.includes(cardKey)
  return {
    input_profile: {
      requires_well: has('well'), requires_machinery: has('machinery') || has('fuel'),
      requires_area: Boolean(requiresArea), requires_tree_count: has('perennial'),
      is_harvest_task: has('harvest'), is_perennial_procedure: has('perennial'),
      requires_materials: has('materials'), requires_labor_batch: has('labor'),
      requires_service_rows: has('perennial') || has('materials'), asset_type: assetType || '',
      target_asset_type: !isAssetTask ? 'NONE' : has('well') ? 'WELL' : has('machinery') || has('fuel') ? 'MACHINE' : has('perennial') ? 'TREE' : 'NONE',
    },
    smart_cards: CARD_ORDER.reduce((acc, cardKey) => {
      acc[cardKey] = { enabled: cardKey === 'financial_trace' ? true : MANDATORY_CARDS.has(cardKey) || enabled.includes(cardKey) }
      return acc
    }, {}),
    control_rules: {
      approval_posture: archetype === 'GENERAL' ? 'basic' : 'tiered',
      criticality: has('harvest') || has('perennial') || has('fuel') ? 'high' : 'normal',
      mandatory_readings: { well_reading: has('well'), machine_hours: has('machinery') || has('fuel'), tree_count: has('perennial') },
    },
    variance_rules: {
      behavior: 'warn', categories: { cost: true, quantity: has('materials') || has('harvest'), time: true, water: has('well'), fuel: has('fuel'), tree_loss: has('perennial'), harvest_gap: has('harvest') },
      thresholds: { warning_pct: 10, critical_pct: 20 },
    },
    financial_profile: {
      shadow_mode: archetype === 'GENERAL' ? 'shadow_only' : 'shadow_and_trace',
      wip_impact: has('materials') || has('labor') || has('machinery') || has('fuel'),
      petty_cash_relevant: has('labor'), inventory_linked: has('materials') || has('harvest') || has('fuel'),
      settlement_linked: has('harvest') || archetype === 'CONTRACT_SETTLEMENT_LINKED', biological_asset_linked: has('perennial'),
    },
    presentation: { simple_preview: enabled, strict_preview: [...enabled, 'financial_trace'], card_order: CARD_ORDER },
  }
}

export const buildTaskPayload = (cropId, formData) => {
  const taskContract = buildTaskContract(formData)
  return {
    crop: cropId, stage: formData.stage.trim() || 'غير مصنف', name: formData.name.trim(),
    archetype: formData.archetype, requires_area: taskContract.input_profile.requires_area,
    requires_machinery: taskContract.input_profile.requires_machinery, requires_well: taskContract.input_profile.requires_well,
    requires_tree_count: taskContract.input_profile.requires_tree_count, is_harvest_task: taskContract.input_profile.is_harvest_task,
    is_perennial_procedure: taskContract.input_profile.is_perennial_procedure, is_asset_task: formData.isAssetTask,
    asset_type: formData.isAssetTask ? formData.assetType.trim() : '', target_asset_type: taskContract.input_profile.target_asset_type,
    task_contract: taskContract,
  }
}

const badgeClass = {
  emerald: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
  amber: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
  blue: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
  rose: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
  slate: 'bg-slate-500/10 text-slate-600 dark:text-slate-300 border-slate-500/20',
}

export const Badge = ({ label, color = 'emerald', testId }) => <span data-testid={testId} className={`rounded-md border px-2 py-0.5 text-[10px] font-bold ${badgeClass[color]}`}>{label}</span>
export const CardBadge = ({ cardKey, testId }) => <Badge testId={testId} color={cardKey === 'financial_trace' ? 'amber' : 'emerald'} label={CARD_LABELS[cardKey] || cardKey} />

export const createFormState = (overrides = {}) => ({
  stage: '', name: '', presetKey: 'GENERAL_SEASONAL', archetype: 'GENERAL',
  selectedCards: createSelectedCards(PRESET_OPTIONS.GENERAL_SEASONAL.selectedCards),
  requiresArea: true, isAssetTask: false, assetType: '', cropId: '', ...overrides,
})

export default function TaskContractForm({ initialData = {}, onSubmit, onCancel, showCropSelector = false, crops = [] }) {
  const [formData, setFormData] = useState(() => createFormState(initialData))

  const applyPreset = useCallback((presetKey) => {
    if (presetKey === 'CUSTOM') {
      setFormData((prev) => ({ ...prev, presetKey }))
      return
    }
    const preset = PRESET_OPTIONS[presetKey] || PRESET_OPTIONS.GENERAL_SEASONAL
    setFormData((prev) => ({
      ...prev, presetKey, archetype: preset.archetype, selectedCards: createSelectedCards(preset.selectedCards),
      requiresArea: preset.requiresArea, isAssetTask: preset.isAssetTask, assetType: preset.assetType,
    }))
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (showCropSelector && !formData.cropId) {
      alert('يرجى اختيار المحصول')
      return
    }
    onSubmit(formData, buildTaskPayload(formData.cropId || initialData.cropId, formData))
  }

  const previewContract = useMemo(() => buildTaskContract(formData), [formData])

  const derivedFlags = [
    previewContract.input_profile.requires_well ? 'يعتمد على بئر' : null,
    previewContract.input_profile.requires_machinery ? 'يتطلب معدة/رافعة' : null,
    previewContract.input_profile.requires_tree_count ? 'يتطلب عداد أشجار' : null,
    previewContract.input_profile.is_perennial_procedure ? 'إجراء معمّر' : null,
    previewContract.input_profile.is_harvest_task ? 'مهمة حصاد' : null,
  ].filter(Boolean)
  
  const requiredInputs = [
    previewContract.input_profile.requires_area ? 'المساحة المنفذة' : null,
    previewContract.input_profile.requires_well ? 'قراءة البئر/الضخ' : null,
    previewContract.input_profile.requires_machinery ? 'المعدة وساعات التشغيل' : null,
    previewContract.input_profile.requires_tree_count ? 'عداد الأشجار/التغير الشجري' : null,
    previewContract.input_profile.is_harvest_task ? 'كمية الحصاد والمنتج' : null,
  ].filter(Boolean)

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {showCropSelector && (
          <div className="md:col-span-2">
            <label className="mb-2 block text-sm font-bold text-gray-700 dark:text-zinc-400">{TEXT.crop}</label>
            <select required className="w-full rounded-xl border border-emerald-200 bg-white p-3 text-sm text-gray-900 focus:border-emerald-500/50 focus:outline-none dark:border-white/10 dark:bg-black/20 dark:text-white" value={formData.cropId} onChange={(e) => setFormData((prev) => ({ ...prev, cropId: e.target.value }))}>
              <option value="">اختر المحصول</option>
              {crops.map((crop) => <option key={crop.id} value={String(crop.id)}>{crop.name}</option>)}
            </select>
          </div>
        )}
        <div>
          <label htmlFor="crop-task-stage" className="mb-2 block text-sm font-bold text-gray-700 dark:text-zinc-400">{TEXT.stage}</label>
          <input id="crop-task-stage" required list="stages-list" className="w-full rounded-xl border border-gray-200 bg-gray-50 p-3 text-gray-900 focus:border-emerald-500/50 focus:outline-none dark:border-white/10 dark:bg-black/20 dark:text-white" value={formData.stage} onChange={(e) => setFormData((prev) => ({ ...prev, stage: e.target.value }))} placeholder="مثال: الزراعة" />
          <datalist id="stages-list">{Object.values(STAGES).map((stage) => <option key={stage} value={stage} />)}</datalist>
        </div>
        <div>
          <label htmlFor="crop-task-name" className="mb-2 block text-sm font-bold text-gray-700 dark:text-zinc-400">{TEXT.name}</label>
          <input id="crop-task-name" aria-label="اسم المهمة" required className="w-full rounded-xl border border-gray-200 bg-gray-50 p-3 text-gray-900 focus:border-emerald-500/50 focus:outline-none dark:border-white/10 dark:bg-black/20 dark:text-white" value={formData.name} onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))} placeholder="مثال: تسميد أشجار المانجو" />
        </div>
      </div>

      <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-5 dark:border-emerald-800/50 dark:bg-emerald-900/10">
        <label className="mb-2 block text-sm font-bold text-emerald-800 dark:text-emerald-300">{TEXT.preset}</label>
        <p className="mb-4 text-xs text-emerald-600 dark:text-emerald-500">{TEXT.presetHint}</p>
        <select data-testid="crop-task-preset" className="w-full rounded-xl border border-emerald-200 bg-white p-3 text-sm text-gray-900 focus:border-emerald-500/50 focus:outline-none dark:border-white/10 dark:bg-black/20 dark:text-white" value={formData.presetKey} onChange={(e) => applyPreset(e.target.value)}>
          {Object.entries(PRESET_OPTIONS).map(([key, preset]) => <option key={key} value={key}>{preset.label}</option>)}
          <option value="CUSTOM">{TEXT.customLabel}</option>
        </select>
      </div>

      <div className="rounded-2xl border border-emerald-100 bg-white p-5 dark:border-white/10 dark:bg-black/10">
        <label className="mb-3 block text-sm font-bold text-emerald-800 dark:text-emerald-300">{TEXT.archetype}</label>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {Object.entries(ARCHETYPE_LABELS).map(([key, label]) => (
            <label key={key} className={`flex cursor-pointer items-center rounded-xl border p-3 transition-all ${formData.archetype === key ? 'border-emerald-600 bg-emerald-600 text-white shadow-md shadow-emerald-500/20' : 'border-gray-200 bg-white text-gray-700 hover:border-emerald-500/50 dark:border-white/10 dark:bg-black/20 dark:text-zinc-300'}`}>
              <input type="radio" name="archetype" className="hidden" value={key} checked={formData.archetype === key} onChange={(e) => setFormData((prev) => ({ ...prev, archetype: e.target.value, presetKey: prev.presetKey === 'CUSTOM' ? 'CUSTOM' : prev.presetKey }))} />
              <span className="w-full text-center text-xs font-bold">{label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-white/10 dark:bg-black/10">
        <div className="mb-3">
          <label className="block text-sm font-bold text-gray-800 dark:text-zinc-200">{TEXT.cards}</label>
          <p className="mt-1 text-xs text-gray-500 dark:text-zinc-500">{TEXT.cardsHint}</p>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {CARD_ORDER.map((cardKey) => {
            const isMandatory = MANDATORY_CARDS.has(cardKey)
            const isPreviewOnly = cardKey === 'financial_trace'
            const checked = isPreviewOnly ? true : isMandatory || formData.selectedCards[cardKey]
            return (
              <label key={cardKey} className={`rounded-2xl border p-4 transition-all ${checked ? 'border-emerald-500/40 bg-emerald-50 dark:border-emerald-500/30 dark:bg-emerald-950/20' : 'border-gray-200 bg-gray-50 dark:border-white/10 dark:bg-black/20'}`}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-bold text-gray-900 dark:text-white">{CARD_LABELS[cardKey]}</div>
                    <p className="mt-1 text-xs text-gray-500 dark:text-zinc-500">{CARD_DESCRIPTIONS[cardKey]}</p>
                  </div>
                  <input data-testid={`crop-task-card-${cardKey}`} type="checkbox" checked={checked} disabled={isMandatory || isPreviewOnly} onChange={() => setFormData((prev) => ({ ...prev, presetKey: 'CUSTOM', selectedCards: { ...prev.selectedCards, [cardKey]: !prev.selectedCards[cardKey] } }))} />
                </div>
              </label>
            )
          })}
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-white/10 dark:bg-black/10">
        <label className="mb-3 block text-sm font-bold text-gray-800 dark:text-zinc-200">{TEXT.requirements}</label>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="flex items-center justify-between rounded-xl border border-gray-200 p-3 dark:border-white/10">
            <span className="text-sm text-gray-700 dark:text-zinc-300">{TEXT.requiresArea}</span>
            <input type="checkbox" checked={formData.requiresArea} onChange={(e) => setFormData((prev) => ({ ...prev, requiresArea: e.target.checked }))} />
          </label>
          <label className="flex items-center justify-between rounded-xl border border-gray-200 p-3 dark:border-white/10">
            <span className="text-sm text-gray-700 dark:text-zinc-300">{TEXT.isAssetTask}</span>
            <input type="checkbox" checked={formData.isAssetTask} onChange={(e) => setFormData((prev) => ({ ...prev, isAssetTask: e.target.checked, assetType: e.target.checked ? prev.assetType : '' }))} />
          </label>
        </div>
        {formData.isAssetTask && (
          <div className="mt-4">
            <label className="mb-2 block text-sm text-gray-700 dark:text-zinc-400">{TEXT.assetType}</label>
            <input className="w-full rounded-xl border border-gray-200 bg-gray-50 p-3 text-gray-900 focus:border-emerald-500/50 focus:outline-none dark:border-white/10 dark:bg-black/20 dark:text-white" value={formData.assetType} onChange={(e) => setFormData((prev) => ({ ...prev, assetType: e.target.value }))} placeholder="مثال: جرار / بئر / معدات خدمة" />
          </div>
        )}
        <div className="mt-4">
          <div className="mb-2 text-xs font-bold text-gray-600 dark:text-zinc-400">{TEXT.derivedFlags}</div>
          <div data-testid="crop-task-derived-flags" className="flex flex-wrap gap-2">
            {derivedFlags.map((flag) => <Badge key={flag} label={flag} color="slate" />)}
            {derivedFlags.length === 0 && <span className="text-xs text-gray-400 dark:text-zinc-600">لا توجد متطلبات مشتقة إضافية.</span>}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-slate-50 p-5 dark:border-white/10 dark:bg-slate-950/30">
        <label className="mb-3 block text-sm font-bold text-gray-800 dark:text-zinc-200">{TEXT.preview}</label>
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <div className="rounded-2xl border border-white/30 bg-white p-4 dark:border-white/10 dark:bg-black/20">
            <div className="mb-3 text-xs font-bold text-emerald-700 dark:text-emerald-400">{TEXT.previewSimple}</div>
            <div className="flex flex-wrap gap-2">{previewContract.presentation.simple_preview.map((cardKey) => <CardBadge key={`simple-${cardKey}`} testId={`crop-task-preview-simple-${cardKey}`} cardKey={cardKey} />)}</div>
          </div>
          <div className="rounded-2xl border border-white/30 bg-white p-4 dark:border-white/10 dark:bg-black/20">
            <div className="mb-3 text-xs font-bold text-amber-700 dark:text-amber-400">{TEXT.previewStrict}</div>
            <div className="flex flex-wrap gap-2">{previewContract.presentation.strict_preview.map((cardKey) => <CardBadge key={`strict-${cardKey}`} testId={`crop-task-preview-strict-${cardKey}`} cardKey={cardKey} />)}</div>
          </div>
          <div className="rounded-2xl border border-white/30 bg-white p-4 dark:border-white/10 dark:bg-black/20">
            <div className="mb-3 text-xs font-bold text-slate-700 dark:text-slate-300">{TEXT.requiredInputs}</div>
            <div className="flex flex-wrap gap-2">
              {requiredInputs.map((item) => <Badge key={item} label={item} color="blue" />)}
              {requiredInputs.length === 0 && <span className="text-xs text-gray-400 dark:text-zinc-600">لا توجد حقول إضافية.</span>}
            </div>
          </div>
        </div>
      </div>

      <div className="flex gap-3 pt-4">
        <button data-testid="crop-task-submit" type="submit" className="flex-1 rounded-xl bg-emerald-600 py-3.5 font-bold text-white transition-all hover:bg-emerald-500">{TEXT.save}</button>
        {onCancel && <button type="button" onClick={onCancel} className="rounded-xl border border-black/10 bg-black/5 dark:border-white/10 dark:bg-white/5 px-6 dark:text-white transition-all hover:bg-black/10 dark:hover:bg-white/10">{TEXT.cancel}</button>}
      </div>
    </form>
  )
}
