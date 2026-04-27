import { memo } from 'react'
import PropTypes from 'prop-types'
import { ActivityItemsField } from './ActivityItemsField'
import { getAvailableVarietiesForLocation } from '../../utils/agronomyUtils'
import {
  getAssetFarmId,
  isOperationalMachineAsset,
  isWellLikeAsset,
} from '../../utils/assetClassification'

const DailyLogDetailsInner = ({ form, updateField, lookups, perennialLogic, taskContext }) => {
  // Destructure lookups with safe defaults
  const {
    wells = [],
    materials = [],
    tasks = [],
    locations = [],
    varieties = [],
    varietiesMeta: _varietiesMeta = {},
    treeLossReasons = [],
  } = lookups || {}
  const cropScopedVarieties = (varieties || []).filter((variety) => {
    const varietyCropId = variety?.crop?.id || variety?.crop || variety?.crop_id || null
    if (!form.crop) return true
    
    // [FIX] السماح للأصناف العامة (بدون محصول محدد) بالظهور كخيار احتياطي
    if (varietyCropId == null) return false
    
    // [ZENITH 11.5] مقارنة مرنة للسلاسل النصية والأرقام
    return String(varietyCropId) === String(form.crop)
  })

  // [ZENITH 11.5 FALLBACK] إذا كانت القائمة المفلترة فارغة، نعرض كافة الأصناف المتاحة لضمان عدم تعطل العمل
  const effectiveCropVarieties = cropScopedVarieties

  const fullyCoveredVarieties = effectiveCropVarieties.filter((variety) => variety.available_in_all_locations)
  const partiallyCoveredVarieties = effectiveCropVarieties.filter(
    (variety) =>
      Array.isArray(variety.location_ids) &&
      variety.location_ids.length > 0 &&
      !variety.available_in_all_locations,
  )
  const genericVarieties = effectiveCropVarieties.filter(
    (variety) => !Array.isArray(variety.location_ids) || variety.location_ids.length === 0,
  )
  const selectedTask = tasks.find((t) => String(t.id) === String(form.task)) || {}
  const enabledCards = taskContext?.enabledCards || {}
  const requiredInputs = taskContext?.requiredInputs || {
    requiresWell: Boolean(selectedTask?.requires_well),
    requiresMachinery: Boolean(selectedTask?.requires_machinery),
    requiresTreeCount: Boolean(selectedTask?.requires_tree_count),
    isPerennialProcedure: Boolean(selectedTask?.is_perennial_procedure),
    isHarvestTask: Boolean(selectedTask?.is_harvest_task),
    requiresArea: Boolean(selectedTask?.requires_area),
  }
  const name = taskContext?.taskName || selectedTask?.name || ''

  // [STRICT VISIBILITY LOGIC] - §4.II Frontend Contract
  // Cards show ONLY if Task is selected AND Task EXPLICITLY requires it (via boolean flag)
  // [AGRI-GUARDIAN FIX] Added form.task guard: no cards appear without task selection.

  const hasTask = Boolean(form.task)
  const showIrrigation = hasTask && Boolean(enabledCards.well || requiredInputs.requiresWell)
  const showMachinery =
    hasTask &&
    Boolean(enabledCards.machinery || enabledCards.fuel || requiredInputs.requiresMachinery)
  const showHarvest = hasTask && Boolean(enabledCards.harvest || requiredInputs.isHarvestTask)
  const showMaterial = hasTask && Boolean(enabledCards.materials)
  const showAgriDetails =
    hasTask &&
    Boolean(
      enabledCards.perennial ||
        requiredInputs.requiresArea ||
        requiredInputs.requiresTreeCount ||
        requiredInputs.isPerennialProcedure,
    )
  const isPerennialMode = Boolean(
    enabledCards.perennial || requiredInputs.requiresTreeCount || requiredInputs.isPerennialProcedure,
  )
  const selectedLocationIds = Array.isArray(form.locations)
    ? form.locations.map((locationId) => String(locationId))
    : []
  const selectedLocationOptions = locations.filter((location) =>
    selectedLocationIds.includes(String(location.id)),
  )
  const selectedHarvestProduct =
    (lookups.products || []).find((product) => String(product.id) === String(form.product_id)) ||
    null
  const locationNameMap = Object.fromEntries(
    locations.map((location) => [String(location.id), location.name || `الموقع ${location.id}`]),
  )
  const hasMultipleLocations = selectedLocationOptions.length > 1
  const singleLocationId = selectedLocationOptions.length === 1 ? String(selectedLocationOptions[0].id) : ''
  const perennialStats = perennialLogic?.stats || {}
  const getVarietiesForRow = (row) => {
    const effectiveLocationId = hasMultipleLocations ? String(row.locationId || '') : singleLocationId
    if (!effectiveLocationId) {
      return {
        fullyCovered: fullyCoveredVarieties,
        partiallyCovered: partiallyCoveredVarieties,
        generic: genericVarieties,
      }
    }
    const filterByLocation = (variety) =>
      !Array.isArray(variety.location_ids) ||
      variety.location_ids.length === 0 ||
      variety.location_ids.map((locationId) => String(locationId)).includes(effectiveLocationId)

    // FALLBACK TO UNIVERSAL MERGE FUNCTION
    const universalVarieties = getAvailableVarietiesForLocation(effectiveLocationId, {
      cropPlans: lookups?.cropPlans || [],
      tree_census: lookups?.treeVarietySummary || [],
      varieties: lookups?.varieties || []
    })

    // Add universal varieties to generic if they don't exist in the current lists
    const existingIds = new Set([
      ...fullyCoveredVarieties.map(v => String(v.id)),
      ...partiallyCoveredVarieties.map(v => String(v.id)),
      ...genericVarieties.map(v => String(v.id))
    ])

    const extraGenericVarieties = universalVarieties.filter(v => !existingIds.has(String(v.id)))

    return {
      fullyCovered: fullyCoveredVarieties.filter(filterByLocation),
      partiallyCovered: partiallyCoveredVarieties.filter(filterByLocation),
      generic: [...genericVarieties, ...extraGenericVarieties], // Include universal fallback varieties
    }
  }

  // Helper: Empty State
  const isSmartModeEmpty =
    !showIrrigation && !showHarvest && !showMaterial && !showMachinery && !showAgriDetails

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Context Awareness Banner with Requirement Badges */}
      <div
        className={`p-4 rounded-lg ${isSmartModeEmpty ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300' : 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-900 dark:text-emerald-300'}`}
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">{isSmartModeEmpty ? '📝' : '⚡'}</span>
          <div className="flex-1">
            <h4 className="font-bold text-sm">
              {isSmartModeEmpty ? 'تسجيل عام' : 'تسجيل ذكي (Smart Context)'}
            </h4>
            <p className="text-xs opacity-80">
              {isSmartModeEmpty
                ? 'لم يتم اكتشاف متطلبات خاصة للنشاط. يمكنك إضافة التفاصيل يدوياً.'
                : `المهمة: "${name}"`}
            </p>
          </div>
        </div>

        {/* [AGRI-GUARDIAN] Task Requirement Badges - Like the uploaded image */}
        {!isSmartModeEmpty && (
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-700">
            {(enabledCards.well || requiredInputs.requiresWell) && (
              <span className="px-2 py-1 text-xs rounded-full bg-blue-500 text-white">
                💧 يحتاج بئر
              </span>
            )}
            {(enabledCards.machinery || enabledCards.fuel || requiredInputs.requiresMachinery) && (
              <span className="px-2 py-1 text-xs rounded-full bg-orange-500 text-white">
                🚜 يحتاج آليات
              </span>
            )}
            {(enabledCards.harvest || requiredInputs.isHarvestTask) && (
              <span className="px-2 py-1 text-xs rounded-full bg-yellow-500 text-white">
                🌾 مهمة حصاد
              </span>
            )}
            {isPerennialMode && (
              <span className="px-2 py-1 text-xs rounded-full bg-green-600 text-white">
                🌳 إجراء معمّر
              </span>
            )}
            {enabledCards.materials && (
              <span className="px-2 py-1 text-xs rounded-full bg-purple-500 text-white">
                🧪 تسميد ووقاية
              </span>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6">
        {/* CARD 1: MACHINERY & FUEL */}
        {showMachinery && (
          <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 border-r-4 border-r-orange-500 animate-in zoom-in-95">
            <h3 className="text-lg font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2">
              <span className="text-orange-500">🚜</span>
              الآلات والوقود
            </h3>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                الآلة المستخدمة (أصول المزرعة)
              </label>
              <select
                data-testid="machine-asset-select"
                value={form.asset_id || form.asset || ''}
                onChange={(e) => {
                  updateField('asset_id', e.target.value)
                  updateField('asset', e.target.value) // Sync both for compatibility
                }}
                className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-200"
              >
                <option value="">اختر الآلة...</option>
                {lookups.assets
                  ?.filter((a) => {
                    const assetFarmId = getAssetFarmId(a)
                    if (form.farm && assetFarmId && String(assetFarmId) !== String(form.farm)) {
                      return false
                    }
                    return isOperationalMachineAsset(a)
                  })
                  .map((asset) => (
                    <option key={asset.id} value={asset.id}>
                      {asset.name} ({asset.category_display || asset.category || asset.type || 'أصل'})
                    </option>
                  ))}
              </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  ساعات العمل (الآلة)
                </label>
                <input
                  data-testid="machine-hours-input"
                  type="number"
                  min="0"
                  value={form.machine_hours || ''}
                  onChange={(e) => updateField('machine_hours', e.target.value)}
                  placeholder="ساعة"
                  className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-200"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  قراءة العداد (اختياري)
                </label>
                <input
                  type="number"
                  min="0"
                  value={form.machine_meter_reading || ''}
                  onChange={(e) => updateField('machine_meter_reading', e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  الوقود المستهلك (لتر)
                </label>
                <input
                  type="number"
                  min="0"
                  value={form.fuel_consumed || ''}
                  onChange={(e) => updateField('fuel_consumed', e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>
          </div>
        )}

        {/* CARD 2: MATERIALS (UNTOUCHED) */}
        {showMaterial && (
          <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 border-r-4 border-r-purple-500 animate-in zoom-in-95">
            <h3 className="text-lg font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2">
              <span className="text-purple-500">🧪</span>
              المدخلات والمواد
            </h3>
            {/* ... Existing Materials Content ... */}
            <ActivityItemsField 
              items={form.items || []} 
              onUpdate={(items) => updateField('items', items)} 
              materials={materials} 
              farmId={form.farm}
              cropId={form.crop}
            />
          </div>
        )}

        {/* CARD 3: IRRIGATION */}
        {showIrrigation && (
          <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 border-r-4 border-r-blue-500 animate-in zoom-in-95">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-gray-800 dark:text-white flex items-center gap-2">
                <span className="text-blue-500">💧</span>
                الري واستهلاك المياه
              </h3>
              
              {/* [ZENITH 11.5] FIXED SOLAR POWER TOGGLE */}
              <label className="flex items-center gap-2 cursor-pointer bg-blue-50 dark:bg-blue-900/30 px-3 py-1.5 rounded-full border border-blue-200 dark:border-blue-800 transition-all hover:bg-blue-100 dark:hover:bg-blue-800/40 group">
                <div className="relative">
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={Boolean(form.is_solar_powered)}
                    onChange={(e) => {
                      updateField('is_solar_powered', e.target.checked)
                      if (e.target.checked) {
                        updateField('diesel_qty', '')
                        // Water volume becomes optional but we keep current value if any
                      }
                    }}
                  />
                  <div className={`block w-10 h-6 rounded-full transition-colors ${form.is_solar_powered ? 'bg-amber-500' : 'bg-gray-300 dark:bg-slate-600'}`}></div>
                  <div className={`absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${form.is_solar_powered ? 'translate-x-4' : ''}`}></div>
                </div>
                <span className="text-xs font-bold text-blue-900 dark:text-blue-300">☀️ طاقة شمسية</span>
              </label>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  البئر / المصدر
                </label>
                <select
                  data-testid="well-asset-select"
                  value={form.well_id || ''}
                  onChange={(e) => updateField('well_id', e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-200"
                >
                  <option value="">اختر المصدر...</option>
                  {(() => {
                    const locationLinkages = wells.filter((link) => {
                      const linkLocId = Number(link.location || link.location_id)
                      return (
                        Array.isArray(form.locations) &&
                        form.locations.some((loc) => Number(loc) === linkLocId)
                      )
                    })
                    const linkedWellIds = locationLinkages.map((l) => String(l.well || l.well_id))
                    const validWells = lookups.assets?.filter(
                        (asset) => isWellLikeAsset(asset) && linkedWellIds.includes(String(asset.id))
                    ) || []
                    const output = []
                    if (validWells.length > 0) {
                      output.push(
                        <optgroup key="linked" label="✅ المرتبطة بهذا الموقع">
                          {validWells.map((w) => (
                            <option key={w.id} value={w.id}>{w.name}</option>
                          ))}
                        </optgroup>
                      )
                    }
                    const allFarmWells = lookups.assets?.filter(
                        (asset) => isWellLikeAsset(asset) && String(getAssetFarmId(asset) || '') === String(form.farm) && !linkedWellIds.includes(String(asset.id))
                    ) || []
                    if (allFarmWells.length > 0) {
                      output.push(
                        <optgroup key="all" label="⚠️ آبار أخرى في المزرعة">
                          {allFarmWells.map((w) => (
                            <option key={w.id} value={w.id}>{w.name}</option>
                          ))}
                        </optgroup>
                      )
                    }
                    return output.length > 0 ? output : <option disabled>لم يتم العثور على آبار</option>
                  })()}
                </select>
              </div>
              
              {!form.is_solar_powered && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    الديزل المستهلك للمضخة (لتر)
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={form.diesel_qty || ''}
                    onChange={(e) => updateField('diesel_qty', e.target.value)}
                    className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  كمية المياه (م³ {form.is_solar_powered ? '- اختياري' : ''})
                </label>
                <input
                  type="number"
                  min="0"
                  value={form.water_volume || ''}
                  onChange={(e) => updateField('water_volume', e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>
          </div>
        )}

        {/* CARD 4: AGRI DETAILS (Perennial vs Standard) */}
        {showAgriDetails && (
          <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 border-r-4 border-r-emerald-600 animate-in zoom-in-95">
            <h3 className="text-lg font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2">
              <span className="text-emerald-600">🌱</span>
              {isPerennialMode
                ? 'بيانات الأشجار المعمرة'
                : 'تفاصيل المساحة والزراعة'}
            </h3>

            {isPerennialMode ? (
              /* --- MODE 1: PERENNIAL / TREES --- */
              <div className="space-y-4">
                <div className="bg-emerald-50 dark:bg-emerald-900/20 p-2 rounded text-xs text-emerald-800 dark:text-emerald-400 mb-3 border border-emerald-100 dark:border-emerald-800">
                  يتم تتبع الأصناف الآن بشكل تفصيلي لكل صف خدمة بالأسفل.
                </div>

                <div className="space-y-3">
                  {/* Service Rows Header */}
                  <div className="flex justify-between items-center">
                    <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
                      تفاصيل الخدمة (Service Rows)
                    </label>
                    <button
                      type="button"
                      onClick={perennialLogic?.addServiceRow}
                      data-testid="service-row-add"
                      className="text-xs bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-400 px-2 py-1 rounded hover:bg-emerald-200 dark:hover:bg-emerald-800/40 transition"
                    >
                      + إضافة صف خدمة
                    </button>
                  </div>

                  {/* Stats & Smart Variety Pills */}
                  <div className="bg-gray-50 dark:bg-slate-700/50 p-4 rounded-xl border border-gray-100 dark:border-slate-600 space-y-4 shadow-inner">
                    <div className="flex flex-wrap justify-between items-center gap-2 text-sm mb-2 pb-2 border-b border-gray-200 dark:border-slate-600">
                      <span className="text-gray-700 dark:text-slate-300 font-bold flex items-center gap-2">
                        <span>📊</span>{' '}
                        {hasMultipleLocations
                          ? 'إحصائيات الأصناف في المواقع المختارة'
                          : 'إحصائيات الأصناف في الموقع'}
                      </span>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-emerald-800 dark:text-emerald-300 font-bold bg-emerald-100 dark:bg-emerald-900/40 px-3 py-1 rounded-full text-xs shadow-sm">
                          الرصيد الجاري: {perennialStats?.totalTreeCount || 0}
                        </span>
                        {Number(perennialStats?.totalCohortAlive || 0) > 0 && (
                          <span className="text-blue-800 dark:text-blue-300 font-bold bg-blue-100 dark:bg-blue-900/40 px-3 py-1 rounded-full text-xs shadow-sm">
                            الدفعات الحية: {perennialStats?.totalCohortAlive || 0}
                          </span>
                        )}
                      </div>
                    </div>

                    {perennialStats?.perennialVarietySummary?.length > 0 ? (
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {perennialStats.perennialVarietySummary.map((summary, idx) => {
                          const vName =
                            summary.varietyName || 'الصنف غير معروف في ملخص المواقع المختارة'
                          const totalForVariety = Number(summary.currentTreeCountTotal || 0)
                          const mappedCount = Number(summary.mappedCountTotal || 0)

                          const progressPct =
                            totalForVariety > 0
                              ? Math.min(100, Math.round((mappedCount / totalForVariety) * 100))
                              : 0
                          const isComplete = mappedCount === totalForVariety && totalForVariety > 0
                          const isOver = mappedCount > totalForVariety
                          const hasGap = summary.hasReconciliationGap

                          return (
                            <div
                              key={idx}
                              className={`flex flex-col gap-2 p-3 rounded-lg border transition-all duration-300 ${
                                isOver 
                                  ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-800 shadow-sm' 
                                  : hasGap
                                    ? 'border-amber-300 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-800 shadow-sm'
                                    : isComplete 
                                      ? 'border-emerald-300 bg-emerald-50 dark:bg-emerald-900/20 dark:border-emerald-800 shadow-sm' 
                                      : 'border-gray-200 bg-white dark:bg-slate-800 dark:border-slate-700'
                              }`}
                            >
                              <div className="flex justify-between items-center text-xs">
                                <span
                                  className="font-bold text-gray-800 dark:text-slate-200 truncate pr-1"
                                  title={vName}
                                >
                                  🌴 {vName}
                                </span>
                                <span
                                  className={`font-mono font-bold ${isOver ? 'text-red-600 dark:text-red-400' : isComplete ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-500 dark:text-slate-400'}`}
                                >
                                  {mappedCount} / {totalForVariety}
                                </span>
                              </div>
                              <div className="h-2 w-full bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden shadow-inner">
                                <div
                                  className={`h-full transition-all duration-500 ${isOver ? 'bg-red-500' : isComplete ? 'bg-emerald-500' : 'bg-blue-500'}`}
                                  style={{ width: `${progressPct}%` }}
                                ></div>
                              </div>
                              <span className="text-[10px] text-gray-500 dark:text-slate-400">
                                {summary.coverageLabel}
                              </span>
                              {typeof summary.cohortAliveTotal === 'number' &&
                                summary.cohortAliveTotal > 0 && (
                                  <span className="text-[10px] text-blue-600 dark:text-blue-400">
                                    إجمالي الدفعات الحية: {summary.cohortAliveTotal}
                                  </span>
                                )}
                              {summary.hasReconciliationGap && (
                                <span className="text-[10px] font-bold text-amber-700 dark:text-amber-400">
                                  فجوة بين الجرد الجاري والدفعات: {summary.cohortStockDelta}
                                </span>
                              )}
                              {summary.usedCohortFallback && (
                                <span className="text-[10px] font-bold text-blue-700 dark:text-blue-300">
                                  تم استخدام رصيد الدفعات الحية مؤقتًا لأن الرصيد الجاري للموقع غير مُسوّى بعد.
                                </span>
                              )}
                              {Array.isArray(summary.locationNames) && summary.locationNames.length > 0 && (
                                <span className="text-[10px] text-gray-500 dark:text-slate-400">
                                  {summary.locationNames.join('، ')}
                                </span>
                              )}
                              {hasMultipleLocations &&
                                summary.currentTreeCountByLocation &&
                                typeof summary.currentTreeCountByLocation === 'object' && (
                                  <div className="flex flex-wrap gap-1">
                                    {Object.entries(summary.currentTreeCountByLocation).map(
                                      ([locationId, count]) => (
                                        <span
                                          key={`${summary.varietyId}-${locationId}`}
                                          className="text-[10px] rounded bg-slate-100 px-2 py-1 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
                                        >
                                          {(summary.locationNamesById?.[locationId] ||
                                            locationNameMap[locationId] ||
                                            `الموقع ${locationId}`) +
                                            `: ${Number(summary.mappedCountByLocation?.[locationId] || 0)}/${Number(count || 0)}`}
                                        </span>
                                      ),
                                    )}
                                  </div>
                                )}
                              {hasMultipleLocations &&
                                summary.cohortAliveByLocation &&
                                typeof summary.cohortAliveByLocation === 'object' && (
                                  <div className="flex flex-wrap gap-1">
                                    {Object.entries(summary.cohortAliveByLocation).map(
                                      ([locationId, cohortAliveCount]) => (
                                        <span
                                          key={`${summary.varietyId}-${locationId}-cohort`}
                                          className="text-[10px] rounded bg-blue-50 px-2 py-1 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300"
                                        >
                                          {(summary.locationNamesById?.[locationId] ||
                                            locationNameMap[locationId] ||
                                            `الموقع ${locationId}`) +
                                            ` - الدفعات الحية: ${Number(cohortAliveCount || 0)}`}
                                        </span>
                                      ),
                                    )}
                                  </div>
                                )}
                              {isOver && (
                                <span className="text-[10px] text-red-600 dark:text-red-400 font-bold flex items-center gap-1">
                                  <span>⚠️</span> تجاوز العدد الفعلي!
                                </span>
                              )}
                              {isComplete && !isOver && (
                                <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold flex items-center gap-1">
                                  <span>✅</span> تمت الخدمة بالكامل
                                </span>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    ) : (
                      <div className="text-center p-4 border break-words border-dashed border-gray-200 dark:border-slate-600 rounded-lg text-gray-400 dark:text-slate-500 text-xs">
                        {perennialStats?.emptyMessage ||
                          'لا توجد أصناف أشجار فعالة مرتبطة بالمواقع المختارة لهذا المحصول.'}
                      </div>
                    )}
                  </div>

                  {/* Empty State */}
                  {(!form.serviceRows || form.serviceRows.length === 0) && (
                    <div className="text-center p-4 border-2 border-dashed border-gray-200 dark:border-slate-600 rounded-lg text-gray-400 dark:text-slate-500 text-sm">
                      لم يتم إضافة تفاصيل. يمكنك إضافة أصناف متعددة.
                    </div>
                  )}

                  {/* Service Rows List */}
                  {form.serviceRows?.filter((row) => row && row.key).map((row) => {
                    const rowLocationId = hasMultipleLocations
                      ? String(row.locationId || '')
                      : singleLocationId
                    const rowVarieties = getVarietiesForRow(row)
                    return (
                      <div
                        key={row.key}
                        className="grid grid-cols-1 md:grid-cols-12 gap-2 p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg border border-gray-100 dark:border-slate-600 items-end animate-in slide-in-from-left-2"
                      >
                        {hasMultipleLocations && (
                          <div className="md:col-span-3">
                            <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1">
                              الموقع
                            </label>
                            <select
                              data-testid={`service-row-location-${row.key}`}
                              value={row.locationId || ''}
                              onChange={(e) =>
                                perennialLogic.updateServiceRow(row.key, 'locationId', e.target.value)
                              }
                              className="w-full text-sm p-2 rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                            >
                              <option value="">اختر الموقع...</option>
                              {selectedLocationOptions.map((location) => (
                                <option key={location.id} value={location.id}>
                                  {location.name}
                                </option>
                              ))}
                            </select>
                          </div>
                        )}
                        <div className={hasMultipleLocations ? 'md:col-span-3' : 'md:col-span-4'}>
                          <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1">
                            الصنف
                          </label>
                          <select
                            data-testid={`service-row-variety-${row.key}`}
                            value={row.varietyId}
                            onChange={(e) =>
                              perennialLogic.updateServiceRow(row.key, 'varietyId', e.target.value)
                            }
                            className="w-full text-sm p-2 rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                          >
                            <option value="">اختر الصنف...</option>

                            {rowVarieties.fullyCovered.length > 0 && (
                              <optgroup label="✅ متاح في كل المواقع المختارة">
                                {rowVarieties.fullyCovered.map((v) => {
                                  const count = perennialLogic.getVarietyCount(v.id, rowLocationId)
                                  return (
                                    <option key={v.id} value={v.id}>
                                      {count !== '?' ? `${v.name} (متوفر: ${count})` : v.name}
                                    </option>
                                  )
                                })}
                              </optgroup>
                            )}

                            {rowVarieties.partiallyCovered.length > 0 && (
                              <optgroup label="📍 متاح في بعض المواقع المختارة">
                                {rowVarieties.partiallyCovered.map((v) => {
                                  const locationNames = perennialLogic.getVarietyLocationNames(
                                    v.id,
                                    Array.isArray(v.location_ids) ? v.location_ids : [],
                                  )
                                  const count = rowLocationId
                                    ? perennialLogic.getVarietyCount(v.id, rowLocationId)
                                    : '?'
                                  return (
                                    <option key={v.id} value={v.id}>
                                      {rowLocationId && count !== '?'
                                        ? `${v.name} (المتاح: ${count})`
                                        : `${v.name} - متاح في: ${locationNames.join('، ')}`}
                                    </option>
                                  )
                                })}
                              </optgroup>
                            )}

                            {rowVarieties.generic.length > 0 && (
                              <optgroup label="🌱 أصناف أخرى">
                                {rowVarieties.generic.map((v) => {
                                  const count = perennialLogic.getVarietyCount(v.id, rowLocationId)
                                  return (
                                    <option key={v.id} value={v.id}>
                                      {count !== '?' && count > 0 ? `${v.name} (متوفر: ${count})` : v.name}
                                    </option>
                                  )
                                })}
                              </optgroup>
                            )}
                          </select>
                          {hasMultipleLocations && !rowLocationId && (
                            <p className="mt-1 text-[10px] text-amber-600 dark:text-amber-400">
                              اختر الموقع أولاً حتى تظهر الأصناف المتاحة لهذا الصف.
                            </p>
                          )}
                          {rowLocationId &&
                            rowVarieties.fullyCovered.length === 0 &&
                            rowVarieties.partiallyCovered.length === 0 &&
                            rowVarieties.generic.length === 0 && (
                              <p className="mt-1 text-[10px] text-amber-600 dark:text-amber-400">
                                لا يوجد أصناف متاحة في الموقع المحدد لهذا الصف.
                              </p>
                            )}
                          {!hasMultipleLocations && selectedLocationOptions[0] && (
                            <p className="mt-1 text-[10px] text-gray-500 dark:text-slate-400">
                              سيتم ربط هذا الصف تلقائيًا بالموقع: {selectedLocationOptions[0].name}
                            </p>
                          )}
                        </div>
                        <div className="md:col-span-1">
                          <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1">
                            عدد الخدمة
                          </label>
                          <input
                            data-testid={`service-row-count-${row.key}`}
                            type="number"
                            min="0"
                            value={row.serviceCount ?? ''}
                            onChange={(e) =>
                              perennialLogic.updateServiceRow(row.key, 'serviceCount', e.target.value)
                            }
                            className="w-full text-sm p-2 rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                            placeholder="الأشجار المخدومة"
                          />
                        </div>
                        <div className="md:col-span-1">
                          <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1">
                            كمية الإنتاج
                          </label>
                          <input
                            type="number"
                            min="0"
                            value={row.harvestQty ?? ''}
                            onChange={(e) => {
                              const val = parseFloat(e.target.value)
                              if (val < 0) return
                              perennialLogic.updateServiceRow(row.key, 'harvestQty', e.target.value)
                            }}
                            className="w-full text-sm p-2 rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                            placeholder="الكمية"
                          />
                        </div>
                        <div className="md:col-span-1">
                          <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1">
                            تغير العدد
                          </label>
                          <input
                            type="number"
                            value={row.delta ?? ''}
                            onChange={(e) =>
                              perennialLogic.updateServiceRow(row.key, 'delta', e.target.value)
                            }
                            className={`w-full text-sm p-2 rounded border bg-white dark:bg-slate-700 text-gray-900 dark:text-white ${
                              Number(row.delta) > 0
                                ? 'border-emerald-400 dark:border-emerald-600'
                                : Number(row.delta) < 0
                                  ? 'border-red-400 dark:border-red-600'
                                  : 'border-gray-300 dark:border-slate-600'
                            }`}
                            placeholder="0 (+/-)"
                          />
                        </div>
                        {Number(row.delta) < 0 && (
                          <div className={hasMultipleLocations ? 'md:col-span-3' : 'md:col-span-4'}>
                            <label className="block text-xs text-red-800 dark:text-red-400 mb-1">
                              سبب الفقد/التلف
                            </label>
                            <select
                              value={row.lossReasonId || ''}
                              onChange={(e) =>
                                perennialLogic.updateServiceRow(row.key, 'lossReasonId', e.target.value)
                              }
                              className="w-full text-sm p-2 rounded border border-red-200 dark:border-red-800 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                            >
                              <option value="">اختر السبب...</option>
                              {treeLossReasons.map((r) => (
                                <option key={r.id} value={r.id}>
                                  {r.name_ar || r.name_en || r.code}
                                </option>
                              ))}
                            </select>
                          </div>
                        )}
                        <div className={hasMultipleLocations ? 'md:col-span-3' : 'md:col-span-4'}>
                          <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1">
                            ملاحظات
                          </label>
                          <input
                            type="text"
                            value={row.notes}
                            onChange={(e) =>
                              perennialLogic.updateServiceRow(row.key, 'notes', e.target.value)
                            }
                            className="w-full text-sm p-2 rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                            placeholder="مثال: جهة الشمال"
                          />
                        </div>
                        <div className="md:col-span-1 flex justify-center pb-2">
                          <button
                            type="button"
                            onClick={() => perennialLogic.removeServiceRow(row.key)}
                            className="text-red-500 hover:text-red-700"
                            title="حذف الصف"
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>


              </div>
            ) : (
              /* --- MODE 2: STANDARD / SEASONAL --- */
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    المساحة المزروعة (هكتار/دونم)
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={form.planted_area || ''}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value)
                      if (val < 0) return
                      updateField('planted_area', e.target.value)
                    }}
                    className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                  />
                </div>
                <ActivityItemsField
                  items={form.items}
                  onChange={(items) => updateField('items', items)}
                  farmId={form.farm}
                  cropId={form.crop}
                  sourceHint="يتم التحقق من رصيد المواد المقبول عبر عهدة المشرف في الخلفية قبل أي خصم تشغيلي."
                />
              </div>
            )}
          </div>
        )}

        {/* CARD 5: HARVEST */}
        {showHarvest && (
          <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 border-r-4 border-r-green-500 animate-in zoom-in-95">
            <h3 className="text-lg font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2">
              <span className="text-green-500">📦</span>
              الإنتاج والحصاد
            </h3>

            {/* [AGRI-GUARDIAN] Product Dropdown - Missing Feature Added */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                المنتج المحصود
              </label>
              <select
                data-testid="harvest-product-select"
                value={form.product_id || ''}
                onChange={(e) => updateField('product_id', e.target.value)}
                className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-green-200"
              >
                <option value="">اختر المنتج...</option>
                {lookups.products?.length > 0 ? (
                  lookups.products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.pack_uom || 'وحدة'})
                    </option>
                  ))
                ) : (
                  <option disabled>
                    🚫 لم يتم تعريف منتجات لهذا المحصول (يرجى إضافتها في الإعدادات)
                  </option>
                )}
              </select>
              {selectedHarvestProduct ? (
                <p className="mt-2 text-xs text-green-700 dark:text-green-300">
                  الوحدة القياسية للحصاد: {selectedHarvestProduct.pack_uom || 'وحدة'}.
                  يتم احتساب الأثر المالي في الخلفية فقط وفق وضع التشغيل والسياسات الحاكمة.
                </p>
              ) : null}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  الكمية المحصودة
                </label>
                <input
                  data-testid="harvested-qty-input"
                  type="number"
                  min="0"
                  value={form.harvest_quantity || ''}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value)
                    if (val < 0) return
                    updateField('harvest_quantity', e.target.value)
                  }}
                  className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-green-200"
                  placeholder="0.00"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  رقم الدفعة / العبوات (اختياري)
                </label>
                <input
                  data-testid="harvest-batch-input"
                  type="text"
                  value={form.batch_number || ''}
                  onChange={(e) => updateField('batch_number', e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                  placeholder="مثال: 50 صندوق"
                />
              </div>
            </div>
          </div>
        )}

        {/* Common Notes Section */}
        <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            ملاحظات عامة
          </label>
          <textarea
            value={form.notes || ''}
            onChange={(e) => updateField('notes', e.target.value)}
            className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white mb-4"
            rows={2}
            placeholder="أي ملاحظات إضافية..."
          />

          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1 mt-4">
            تبرير الانحراف (اختياري، أو إلزامي عند تجاوز الحد المسموح)
          </label>
          <textarea
            value={form.variance_note || ''}
            onChange={(e) => updateField('variance_note', e.target.value)}
            className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
            rows={2}
            placeholder="يرجى كتابة سبب تجاوز كميات المحددات المعيارية إن وجد لكي لا يتم رفض السجل..."
          />
        </div>

        {/* Toggle Visibility */}
      </div>
    </div>
  )
}

// [AGRI-GUARDIAN] PropTypes for type safety
DailyLogDetailsInner.propTypes = {
  form: PropTypes.object.isRequired,
  updateField: PropTypes.func.isRequired,
  lookups: PropTypes.shape({
    wells: PropTypes.array,
    materials: PropTypes.array,
    tasks: PropTypes.array,
    locations: PropTypes.array,
    varieties: PropTypes.array,
    treeLossReasons: PropTypes.array,
    assets: PropTypes.array,
  }),
  perennialLogic: PropTypes.shape({
    addServiceRow: PropTypes.func,
    removeServiceRow: PropTypes.func,
    updateServiceRow: PropTypes.func,
    getVarietyCount: PropTypes.func,
    stats: PropTypes.object,
  }),
  taskContext: PropTypes.object,
}

// [AGRI-GUARDIAN] Memoized export for performance
export const DailyLogDetails = memo(DailyLogDetailsInner)
