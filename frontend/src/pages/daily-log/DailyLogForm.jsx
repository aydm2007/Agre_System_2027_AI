import PropTypes from 'prop-types'
import { toast } from 'react-hot-toast'
import {
  TEXT,
  AREA_UOMS,
  WATER_UOMS,
  formatDataSourceMeta,
  emptyServiceStats,
  formatPercent,
  formatDateOnly,
  SERVICE_SCOPE_LABEL_MAP,
  DEFAULT_SERVICE_SCOPE,
  SERVICE_SCOPE_OPTIONS,
} from './constants'
import CollapsibleCard from '../../components/CollapsibleCard'
import TeamMultiSelect from '../../components/TeamMultiSelect'
import { ActivityItemsField } from '../../components/daily-log/ActivityItemsField'

export default function DailyLogForm({
  form,
  setForm,
  isEditingActivity,
  onFarmChange,
  onLocationChange,
  onCropChange,
  onTaskChange,
  farms,
  locations,
  crops,
  tasks,
  taskMeta,
  selectedCrop,
  isTreeActivity,
  summary,
  summaryLoading,
  summaryError,
  treeSummary,
  hasTreeSummary,
  treeSummaryEntries,
  criticalMessages,
  collapsedSections,
  toggleSection,
  teamOptions,
  teamLoading,
  formErrors,
  clearFieldError,
  setTeamSearchTerm,
  serviceProviders,
  availableWells,
  canSkipWellReading,
  treeSnapshot,
  treeSnapshotMeta,
  varieties,
  selectedLocation,
  selectedVariety,
  helpers,
  treeLossReasons,
  locationSummaryMeta,
  existingServiceCountTotal,
  totalServiceCount,
  projectedServiceCount,
  locationServiceTotals,
  serviceRows,
  serviceRowsLoading,
  serviceRowsError,
  handleRemoveServiceRow,
  handleServiceRowChange,
}) {
  const { formatNumber, toDateInputValue, formatDateTime, formatOptionalNumber } = helpers

  return (
    <>
      <div className="grid md:grid-cols-5 gap-3">
        <div className="space-y-2">
          <label className="block text-sm text-gray-600" htmlFor="daily-log-date">
            {TEXT.fields.date}
          </label>
          <input
            id="daily-log-date"
            type="date"
            max={new Date().toISOString().split('T')[0]} // [Agri-Guardian] Block Future Dates
            className={`border rounded p-2 w-full ${isEditingActivity ? 'bg-gray-100 cursor-not-allowed' : ''}`}
            value={form.date}
            disabled={isEditingActivity}
            onChange={(e) => {
              const val = e.target.value
              const selected = new Date(val)
              const now = new Date()
              const diffTime = Math.abs(now - selected)
              const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

              if (diffDays > 7 && selected < now) {
                toast('تنبيه: أنت تقوم بتسجيل بيانات قديمة جداً. قد تخضع للتدقيق.', {
                  icon: '⚠️',
                })
              }
              setForm((state) => ({ ...state, date: val }))
            }}
          />
        </div>
        <div className="space-y-2">
          <label className="block text-sm text-gray-600" htmlFor="daily-log-farm">
            {TEXT.fields.farm}
          </label>
          <select
            id="daily-log-farm"
            className={`border rounded p-2 w-full ${isEditingActivity ? 'bg-gray-100 cursor-not-allowed' : ''}`}
            value={form.farm}
            disabled={isEditingActivity}
            onChange={(event) => onFarmChange(event.target.value)}
          >
            <option value="">{farms.length ? TEXT.fields.choose : TEXT.fields.noFarms}</option>
            {farms.map((farm) => (
              <option key={farm.id || farm.slug} value={String(farm.id ?? farm.slug ?? '')}>
                {farm.name}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <label className="block text-sm text-gray-600" htmlFor="daily-log-location">
            {TEXT.fields.location} (يمكن اختيار أكثر من موقع)
          </label>
          <select
            id="daily-log-location"
            multiple
            className="border rounded p-2 w-full min-h-[100px]"
            value={form.locations || []}
            disabled={!locations.length}
            required={taskMeta.requires_well}
            onChange={(event) => {
              const selectedOptions = Array.from(event.target.selectedOptions).map(
                (opt) => opt.value,
              )
              onLocationChange(selectedOptions)
            }}
          >
            {locations.length === 0 && (
              <option value="" disabled>
                {TEXT.fields.noLocations}
              </option>
            )}
            {locations.map((location) => (
              <option key={location.id} value={String(location.id)}>
                {location.name}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <label
            className="block text-sm text-gray-600 flex items-center gap-2"
            htmlFor="daily-log-crop"
          >
            {TEXT.fields.crop}
            {selectedCrop?.is_perennial && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                <span aria-hidden="true">🌳</span>
                {TEXT.perennial.badge}
              </span>
            )}
          </label>
          <select
            id="daily-log-crop"
            className="border rounded p-2 w-full"
            value={form.crop}
            disabled={!crops.length}
            onChange={(event) => onCropChange(event.target.value)}
          >
            <option value="">{crops.length ? TEXT.fields.choose : TEXT.fields.noCrops}</option>
            {crops.map((crop) => (
              <option key={crop.id} value={String(crop.id)}>
                {`${crop.name}${crop.is_perennial ? ' 🌳' : ''}${crop.mode ? ` (${crop.mode})` : ''}`}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <label
            className="block text-sm text-gray-600 flex items-center gap-2"
            htmlFor="daily-log-task"
          >
            {TEXT.fields.task}
            {isTreeActivity && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                <span aria-hidden="true">🌱</span>
                {TEXT.perennial.taskBadge}
              </span>
            )}
          </label>
          <select
            id="daily-log-task"
            className="border rounded p-2 w-full"
            value={form.task}
            disabled={!tasks.length}
            onChange={(event) => onTaskChange(event.target.value)}
          >
            <option value="">{tasks.length ? TEXT.fields.choose : TEXT.fields.noTasks}</option>
            {tasks.map((task) => (
              <option key={task.id} value={String(task.id)}>
                {task.stage} - {task.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {summaryLoading && (
        <div className="bg-white border border-gray-200 rounded p-3 text-sm text-gray-600">
          {TEXT.summary.loading}
        </div>
      )}
      {!summaryLoading && summaryError && (
        <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">
          {TEXT.summary.error}
        </div>
      )}
      {!summaryLoading && summary && (
        <div className="bg-white border border-gray-200 rounded p-4">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">{TEXT.summary.title}</h3>
          <div className="grid md:grid-cols-3 gap-3 text-center">
            <div className="bg-slate-50 rounded p-3">
              <div className="text-sm text-gray-500">{TEXT.summary.logs}</div>
              <div className="text-xl font-semibold text-gray-900">
                {summary.metrics?.logs ?? 0}
              </div>
            </div>
            <div className="bg-slate-50 rounded p-3">
              <div className="text-sm text-gray-500">{TEXT.summary.activities}</div>
              <div className="text-xl font-semibold text-gray-900">
                {summary.metrics?.activities ?? 0}
              </div>
            </div>
            <div className="bg-slate-50 rounded p-3">
              <div className="text-sm text-gray-500">{TEXT.activitySummary.updatedAt}</div>
              <div className="text-xl font-semibold text-gray-900">
                {summary.metrics?.distinct_supervisors ?? 0}
              </div>
            </div>
          </div>
        </div>
      )}

      {hasTreeSummary && (
        <div className="bg-white border border-emerald-200 rounded p-4 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
            <h4 className="text-lg font-semibold text-emerald-800">
              {TEXT.perennial.summaryTitle}
            </h4>
            <span className="text-sm text-emerald-700">
              {TEXT.perennial.summaryActivities(Number(treeSummary.activities || 0))}
            </span>
          </div>
          <div className="grid md:grid-cols-4 gap-3 text-center">
            <div className="bg-emerald-50 border border-emerald-100 rounded p-3">
              <div className="text-sm text-emerald-700">{TEXT.perennial.summaryCurrent}</div>
              <div className="text-xl font-semibold text-emerald-900">
                {formatNumber(treeSummary.current_tree_count ?? 0)}
              </div>
            </div>
            <div className="bg-emerald-50 border border-emerald-100 rounded p-3">
              <div className="text-sm text-emerald-700">{TEXT.perennial.summaryServiced}</div>
              <div className="text-xl font-semibold text-emerald-900">
                {formatNumber(treeSummary.trees_serviced ?? 0)}
              </div>
            </div>
            <div className="bg-emerald-50 border border-emerald-100 rounded p-3">
              <div className="text-sm text-emerald-700">{TEXT.perennial.summaryNet}</div>
              <div
                className={`text-xl font-semibold ${Number(treeSummary.net_tree_delta || 0) < 0 ? 'text-red-600' : Number(treeSummary.net_tree_delta || 0) > 0 ? 'text-emerald-800' : 'text-emerald-900'}`}
              >
                {formatNumber(treeSummary.net_tree_delta ?? 0)}
              </div>
              <div className="mt-1 text-xs text-emerald-700 flex flex-wrap justify-center gap-x-3 gap-y-1">
                <span>
                  {TEXT.perennial.summaryGain}:{' '}
                  {formatNumber(Math.max(Number(treeSummary.gain_tree_delta || 0), 0))}
                </span>
                <span>
                  {TEXT.perennial.summaryLoss}:{' '}
                  {formatNumber(Math.abs(Number(treeSummary.loss_tree_delta || 0)))}
                </span>
              </div>
            </div>
            <div className="bg-emerald-50 border border-emerald-100 rounded p-3">
              <div className="text-sm text-emerald-700">{TEXT.summary.activities}</div>
              <div className="text-xl font-semibold text-emerald-900">
                {formatNumber(treeSummary.activities ?? 0)}
              </div>
            </div>
          </div>
          <div>
            <h5 className="text-sm font-semibold text-emerald-800 mb-2">
              تفاصيل الأصناف والمواقع المخدومة
            </h5>
            {treeSummaryEntries.length ? (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm text-end text-emerald-900">
                  <thead className="bg-emerald-50 text-emerald-800">
                    <tr>
                      <th className="px-3 py-2 font-semibold">
                        {TEXT.perennial.tableHeaders.crop}
                      </th>
                      <th className="px-3 py-2 font-semibold">
                        {TEXT.perennial.tableHeaders.variety}
                      </th>
                      <th className="px-3 py-2 font-semibold">
                        {TEXT.perennial.tableHeaders.location}
                      </th>
                      <th className="px-3 py-2 font-semibold">
                        {TEXT.perennial.tableHeaders.activities}
                      </th>
                      <th className="px-3 py-2 font-semibold">
                        {TEXT.perennial.tableHeaders.treesServiced}
                      </th>
                      <th className="px-3 py-2 font-semibold">
                        {TEXT.perennial.tableHeaders.currentCount}
                      </th>
                      <th className="px-3 py-2 font-semibold">
                        {TEXT.perennial.tableHeaders.netChange}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {treeSummaryEntries.map((entry, entryIndex) => {
                      const netValue = Number(entry?.net_tree_delta ?? 0)
                      const netClass =
                        netValue < 0
                          ? 'text-red-600'
                          : netValue > 0
                            ? 'text-emerald-700'
                            : 'text-emerald-900'
                      return (
                        <tr
                          key={`${entry?.crop?.id || 'crop'}-${entryIndex}`}
                          className={entryIndex % 2 === 0 ? 'bg-white' : 'bg-emerald-50'}
                        >
                          <td className="px-3 py-2">{entry?.crop?.name || '-'}</td>
                          <td className="px-3 py-2">{entry?.variety?.name || '-'}</td>
                          <td className="px-3 py-2">{entry?.location?.name || '-'}</td>
                          <td className="px-3 py-2">{formatNumber(entry?.activities ?? 0)}</td>
                          <td className="px-3 py-2">{formatNumber(entry?.trees_serviced ?? 0)}</td>
                          <td className="px-3 py-2">
                            {formatOptionalNumber(entry?.current_tree_count)}
                          </td>
                          <td className={`px-3 py-2 ${netClass}`}>{formatNumber(netValue)}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-emerald-700">{TEXT.perennial.summaryEmpty}</p>
            )}
          </div>
        </div>
      )}

      {criticalMessages.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 space-y-2">
          <div className="text-sm font-semibold text-amber-800">{TEXT.alerts.heading}</div>
          <ul className="space-y-1 text-sm text-amber-700">
            {criticalMessages.map((message, index) => (
              <li key={`critical-${index}`} className="flex items-start gap-2">
                <span
                  className="mt-1 inline-flex h-2 w-2 flex-shrink-0 rounded-full bg-amber-500"
                  aria-hidden="true"
                />
                <span>{message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <CollapsibleCard
        title={TEXT.sections.team.title}
        hint={TEXT.sections.team.hint}
        collapsed={collapsedSections.team}
        onToggle={() => toggleSection('team')}
      >
        <div className="grid gap-3 md:grid-cols-2">
          <div className="space-y-2">
            <label className="block text-sm text-gray-600">{TEXT.fields.team}</label>
            <TeamMultiSelect
              value={form.team}
              onChange={(next) => {
                clearFieldError('team')
                setForm((state) => ({ ...state, team: next }))
              }}
              suggestions={teamOptions}
              onInputChange={(value) => setTeamSearchTerm(value)}
              loading={teamLoading}
              placeholder={TEXT.fields.teamPlaceholder}
              disabled={!form.farm}
            />
            <p className="text-xs text-gray-500">
              يمكنك كتابة اسم جديد أو اختيار أسماء ظهرت في أنشطة سابقة لنفس المزرعة.
            </p>
            {Array.isArray(formErrors?.team) && formErrors.team.length > 0 && (
              <p className="text-xs text-red-600">{formErrors.team[0]}</p>
            )}
          </div>
          <div className="space-y-2">
            <label className="block text-sm text-gray-600">{TEXT.fields.hours}</label>
            <input
              type="number"
              className="border rounded p-2 w-full"
              value={form.hours}
              onChange={(event) => {
                clearFieldError('hours')
                setForm((state) => ({ ...state, hours: event.target.value }))
              }}
              placeholder={TEXT.fields.hoursPlaceholder}
              min="0"
              step="0.25"
            />
            {Array.isArray(formErrors?.hours) && formErrors.hours.length > 0 && (
              <p className="text-xs text-red-600">{formErrors.hours[0]}</p>
            )}
          </div>
          <div className="space-y-2 md:col-span-2">
            <label className="block text-sm text-gray-600 font-bold text-blue-600">
              🚀 منفيذ العمل (مقدم خدمة)
            </label>
            <select
              className="border rounded p-2 w-full bg-blue-50 focus:ring-2 focus:ring-blue-200"
              value={form.service_provider_id}
              onChange={(e) => setForm((s) => ({ ...s, service_provider_id: e.target.value }))}
              disabled={!form.task}
            >
              <option value="">
                {form.task ? '-- عمالة المزرعة (داخلي) --' : '(اختر المهمة أولاً)'}
              </option>
              {serviceProviders
                .filter((sp) => {
                  if (!form.task) return false
                  if (!sp.capabilities || sp.capabilities.length === 0) return true
                  return sp.capabilities.includes(Number(form.task))
                })
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.type_display}) - {p.default_hourly_rate || 0} ريال/س
                  </option>
                ))}
            </select>
            <div className="flex justify-between items-center mt-1">
              <p className="text-[10px] text-gray-500">
                تمت الفلترة بذكاء بناءً على تخصص المقاول في المهمة المختارة.
              </p>
              {form.service_provider_id && form.hours && (
                <div className="text-[10px] font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded">
                  التكلفة التقديرية:{' '}
                  {(
                    (serviceProviders.find(
                      (sp) => String(sp.id) === String(form.service_provider_id),
                    )?.default_hourly_rate || 0) * (Number(form.hours) || 0)
                  ).toLocaleString()}{' '}
                  ريال
                </div>
              )}
            </div>
          </div>
        </div>
      </CollapsibleCard>

      {(taskMeta.requires_well || taskMeta.requires_area) && (
        <CollapsibleCard
          title={TEXT.sections.requirements.title}
          hint={TEXT.sections.requirements.hint}
          collapsed={collapsedSections.requirements}
          onToggle={() => toggleSection('requirements')}
        >
          {taskMeta.requires_well && (
            <div className="space-y-3 rounded border border-sky-200 bg-sky-50 p-4">
              <h4 className="font-semibold text-sky-800">{TEXT.requirements.wellTitle}</h4>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-2">
                  <label className="block text-sm text-gray-600">
                    {TEXT.requirements.wellSelect}
                  </label>
                  <select
                    className="border rounded p-2 w-full"
                    value={form.well_id || ''}
                    onChange={(event) =>
                      setForm((state) => ({ ...state, well_id: event.target.value }))
                    }
                    required={taskMeta.requires_well}
                  >
                    <option value="">
                      {availableWells.length ? TEXT.fields.choose : TEXT.fields.noLocations}
                    </option>
                    {availableWells.map((well) => (
                      <option key={well.id} value={String(well.id)}>
                        {well.name}
                        {well.code ? ` (${well.code})` : ''}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500">{TEXT.requirements.wellInfo}</p>
                </div>
                <div className="space-y-2">
                  <label className="block text-sm text-gray-600">
                    {TEXT.requirements.wellTitle}
                  </label>
                  <input
                    type="number"
                    className="border rounded p-2 w-full"
                    placeholder={TEXT.requirements.wellReadingPlaceholder}
                    value={form.well_reading}
                    onChange={(event) =>
                      setForm((state) => ({ ...state, well_reading: event.target.value }))
                    }
                    required={!canSkipWellReading && Boolean(form.well_id)}
                    min="0"
                    step="0.01"
                  />
                  <p className="text-xs text-gray-500">{TEXT.requirements.wellReadingHint}</p>
                </div>
                
                <div className="space-y-2 flex flex-col justify-center">
                  <label className="flex items-center space-x-2 space-x-reverse cursor-pointer">
                    <input
                      type="checkbox"
                      className="form-checkbox text-sky-600 h-5 w-5"
                      checked={form.is_solar_powered || false}
                      onChange={(event) =>
                        setForm((state) => ({ 
                          ...state, 
                          is_solar_powered: event.target.checked, 
                          diesel_qty: event.target.checked ? '' : state.diesel_qty 
                        }))
                      }
                    />
                    <span className="text-sm font-medium text-gray-700">{TEXT.requirements.solarPower || 'ري بالطاقة الشمسية'}</span>
                  </label>
                  <p className="text-xs text-gray-500">{TEXT.requirements.solarPowerHint || 'لا يتطلب استهلاك ديزل'}</p>
                </div>
                
                {!form.is_solar_powered && (
                  <div className="space-y-2">
                    <label className="block text-sm text-gray-600">
                      {TEXT.requirements.dieselQty || 'كمية الديزل (لتر)'}
                    </label>
                    <input
                      type="number"
                      className="border rounded p-2 w-full"
                      placeholder={TEXT.requirements.dieselQtyPlaceholder || 'أدخل كمية الديزل باللتر'}
                      value={form.diesel_qty || ''}
                      onChange={(event) =>
                        setForm((state) => ({ ...state, diesel_qty: event.target.value }))
                      }
                      min="0"
                      step="0.01"
                    />
                    <p className="text-xs text-gray-500">{TEXT.requirements.dieselQtyHint || 'اتركه فارغاً إذا لم يستهلك'}</p>
                  </div>
                )}
              </div>
            </div>
          )}
          {taskMeta.requires_area && (
            <div className="space-y-3 rounded border border-purple-200 bg-purple-50 p-4">
              <h4 className="font-semibold text-purple-800">{TEXT.requirements.areaTitle}</h4>
              <div className="grid items-center gap-3 md:grid-cols-3">
                <input
                  type="number"
                  className="border rounded p-2"
                  placeholder={TEXT.requirements.areaPlaceholder}
                  value={form.planted_area}
                  onChange={(event) =>
                    setForm((state) => ({ ...state, planted_area: event.target.value }))
                  }
                  min="0"
                  step="0.001"
                />
                <select
                  className="border rounded p-2"
                  value={form.planted_uom}
                  onChange={(event) =>
                    setForm((state) => ({ ...state, planted_uom: event.target.value }))
                  }
                >
                  {AREA_UOMS.map((uom) => (
                    <option key={uom.value} value={uom.value}>
                      {uom.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500">{TEXT.requirements.areaHint}</p>
              </div>
            </div>
          )}
        </CollapsibleCard>
      )}

      {(isTreeActivity ||
        !taskMeta.is_perennial_procedure ||
        (form.locations && form.locations.length > 0)) && (
        <CollapsibleCard
          title={TEXT.sections.resources.title}
          hint={TEXT.sections.resources.hint}
          collapsed={collapsedSections.resources}
          onToggle={() => toggleSection('resources')}
          disableToggle={isTreeActivity}
        >
          {isTreeActivity && (
            <div className="space-y-4 rounded border border-amber-200 bg-amber-50 p-4">
              <h4 className="font-semibold text-amber-800">{TEXT.tree.title}</h4>
              {(treeSnapshotMeta.source !== 'live' || treeSnapshotMeta.storedAt) && (
                <p
                  className={`text-[11px] ${
                    treeSnapshotMeta.source === 'cache'
                      ? 'text-amber-700'
                      : treeSnapshotMeta.source === 'offline'
                        ? 'text-red-600'
                        : 'text-emerald-700'
                  }`}
                >
                  {formatDataSourceMeta(treeSnapshotMeta)}
                </p>
              )}
              <div className="space-y-2">
                {treeSnapshot.loading && (
                  <div className="rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
                    {TEXT.perennial.inventoryLoading}
                  </div>
                )}
                {!treeSnapshot.loading && treeSnapshot.error && (
                  <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                    {treeSnapshot.error}
                  </div>
                )}
                {!treeSnapshot.loading && !treeSnapshot.error && treeSnapshot.data && (
                  <div className="rounded border border-emerald-200 bg-white p-3 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-semibold text-emerald-700">
                        {TEXT.perennial.inventoryTitle}
                      </div>
                      <div className="text-lg font-bold text-emerald-900">
                        {formatNumber(treeSnapshot.data.currentCount)}
                      </div>
                    </div>
                    <div className="mt-1 text-xs text-emerald-600">
                      {[
                        treeSnapshot.data.locationName || selectedLocation?.name || '',
                        treeSnapshot.data.varietyName || selectedVariety?.name || '',
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </div>
                    {treeSnapshot.data.status && (
                      <div className="mt-1 text-xs text-emerald-500">
                        الحالة: {treeSnapshot.data.status}
                      </div>
                    )}
                    {treeSnapshot.data.plantingDate && (
                      <div className="mt-1 text-xs text-emerald-500">
                        تاريخ الزراعة: {toDateInputValue(treeSnapshot.data.plantingDate)}
                      </div>
                    )}
                    {treeSnapshot.data.updatedAt && (
                      <div className="mt-1 text-xs text-emerald-500">
                        {TEXT.perennial.lastUpdated(formatDateTime(treeSnapshot.data.updatedAt))}
                      </div>
                    )}
                  </div>
                )}
                {!treeSnapshot.loading &&
                  !treeSnapshot.error &&
                  !treeSnapshot.data &&
                  form.variety && (
                    <div className="rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
                      {TEXT.perennial.inventoryEmpty}
                    </div>
                  )}
              </div>

              <div className="space-y-2">
                <label className="block text-sm text-gray-600" htmlFor="daily-log-variety">
                  {TEXT.tree.variety}
                </label>
                <select
                  id="daily-log-variety"
                  className="border rounded p-2 w-full"
                  value={form.variety || ''}
                  onChange={(event) =>
                    setForm((state) => ({ ...state, variety: event.target.value }))
                  }
                  required={isTreeActivity}
                >
                  <option value="">{TEXT.tree.varietyPlaceholder}</option>
                  {varieties.map((variety) => (
                    <option key={variety.id} value={String(variety.id)}>
                      {variety.name}
                      {variety.code ? ` (${variety.code})` : ''}
                    </option>
                  ))}
                </select>
                {!varieties.length && (
                  <p className="text-xs text-amber-700">{TEXT.fields.noCrops}</p>
                )}
                {Array.isArray(formErrors?.variety_id) && formErrors.variety_id.length > 0 && (
                  <p className="text-xs text-red-600">{formErrors.variety_id[0]}</p>
                )}
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <div className="space-y-1">
                  <label className="block text-sm text-gray-600">{TEXT.tree.delta}</label>
                  <input
                    type="number"
                    className="border rounded p-2 w-full"
                    value={form.tree_count_delta}
                    onChange={(event) =>
                      setForm((state) => ({ ...state, tree_count_delta: event.target.value }))
                    }
                    placeholder="0"
                    step="1"
                  />
                  <p className="text-xs text-gray-500">{TEXT.tree.deltaHint}</p>
                </div>
                <div className="space-y-1">
                  <label className="block text-sm text-gray-600">{TEXT.tree.serviced}</label>
                  <input
                    id="daily-log-service-count"
                    type="number"
                    className="border rounded p-2 w-full"
                    value={form.activity_tree_count}
                    onChange={(event) =>
                      setForm((state) => ({ ...state, activity_tree_count: event.target.value }))
                    }
                    placeholder={TEXT.tree.servicedPlaceholder}
                    min="0"
                    step="1"
                    required={isTreeActivity}
                  />
                </div>
                <div className="space-y-1">
                  <label className="block text-sm text-gray-600">{TEXT.tree.harvestQuantity}</label>
                  <input
                    type="number"
                    className="border rounded p-2 w-full"
                    value={form.harvest_quantity}
                    onChange={(event) =>
                      setForm((state) => ({ ...state, harvest_quantity: event.target.value }))
                    }
                    min="0"
                    step="0.01"
                  />
                  {Array.isArray(formErrors?.harvest_quantity) &&
                    formErrors.harvest_quantity.length > 0 && (
                      <p className="text-xs text-red-600">{formErrors.harvest_quantity[0]}</p>
                    )}
                </div>
              </div>
              {Number(form.tree_count_delta || 0) < 0 && (
                <div className="space-y-2">
                  <label className="block text-sm text-gray-600">{TEXT.tree.lossReason}</label>
                  <select
                    className="border rounded p-2 w-full"
                    value={form.tree_loss_reason || ''}
                    onChange={(event) =>
                      setForm((state) => ({ ...state, tree_loss_reason: event.target.value }))
                    }
                  >
                    <option value="">{TEXT.fields.choose}</option>
                    {treeLossReasons.map((reason) => (
                      <option key={reason.id} value={String(reason.id)}>
                        {reason.name_ar || reason.name_en || reason.code}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          )}

          {!taskMeta.is_perennial_procedure && (
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1">
                <label className="block text-sm text-gray-600">{TEXT.tree.waterVolume}</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    className="border rounded p-2 flex-1"
                    value={form.water_volume}
                    onChange={(event) =>
                      setForm((state) => ({ ...state, water_volume: event.target.value }))
                    }
                    min="0"
                    step="0.01"
                  />
                  <select
                    className="border rounded p-2"
                    value={form.water_uom}
                    onChange={(event) =>
                      setForm((state) => ({ ...state, water_uom: event.target.value }))
                    }
                  >
                    {WATER_UOMS.map((uom) => (
                      <option key={uom.value} value={uom.value}>
                        {uom.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              {taskMeta?.enabledCards?.materials !== false && (
                <div className="md:col-span-2 space-y-1 mt-2">
                  <ActivityItemsField
                    items={form.items}
                    onChange={(items) => setForm((s) => ({ ...s, items }))}
                    farmId={form.farm}
                    cropId={form.crop}
                  />
                </div>
              )}
            </div>
          )}

          {form.locations && form.locations.length > 0 && (
            <div className="space-y-3 rounded border border-slate-200 bg-white/60 p-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <h5 className="text-base font-semibold text-slate-800">
                    {TEXT.tree.servicePanelTitle}
                  </h5>
                  <p className="text-xs text-slate-500">{TEXT.tree.servicePanelHint}</p>
                  {(locationSummaryMeta.source !== 'live' || locationSummaryMeta.storedAt) && (
                    <p
                      className={`text-[11px] ${
                        locationSummaryMeta.source === 'cache'
                          ? 'text-amber-700'
                          : locationSummaryMeta.source === 'offline'
                            ? 'text-red-600'
                            : 'text-emerald-700'
                      }`}
                    >
                      {formatDataSourceMeta(locationSummaryMeta)}
                    </p>
                  )}
                </div>
                <div className="text-xs text-slate-600 space-y-0.5 text-end md:text-start">
                  <div>
                    {TEXT.tree.serviceExistingTotal(formatNumber(existingServiceCountTotal))}
                  </div>
                  <div>{TEXT.tree.serviceTotal(formatNumber(totalServiceCount))}</div>
                  <div>{TEXT.tree.serviceProjected(formatNumber(projectedServiceCount))}</div>
                  {locationServiceTotals?.total_current_trees != null && (
                    <div>
                      {TEXT.tree.serviceLocationCurrent(
                        formatNumber(locationServiceTotals.total_current_trees),
                      )}
                    </div>
                  )}
                  {locationServiceTotals?.stocks_count != null && (
                    <div>
                      {TEXT.tree.serviceLocationStocks(
                        formatNumber(locationServiceTotals.stocks_count),
                      )}
                    </div>
                  )}
                  {locationServiceTotals?.last_inventory_update && (
                    <div>
                      {TEXT.tree.serviceLocationUpdated(
                        formatDateTime(locationServiceTotals.last_inventory_update),
                      )}
                    </div>
                  )}
                  {locationServiceTotals?.breakdown && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {Object.entries(locationServiceTotals.breakdown).map(([scope, value]) => (
                        <span
                          key={scope}
                          className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600"
                        >
                          {SERVICE_SCOPE_LABEL_MAP[scope] || scope}: {formatNumber(value)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              {serviceRowsLoading && (
                <div className="space-y-3">
                  {Array.from({ length: 2 }).map((_, index) => (
                    <div
                      key={`service-skeleton-${index}`}
                      className="animate-pulse rounded border border-slate-200 bg-slate-50 p-4"
                    >
                      <div className="mb-3 h-4 w-32 rounded bg-slate-200" />
                      <div className="mb-2 h-3 w-full rounded bg-slate-200" />
                      <div className="h-3 w-3/4 rounded bg-slate-200" />
                    </div>
                  ))}
                </div>
              )}
              {!serviceRowsLoading && serviceRowsError && (
                <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  {serviceRowsError}
                </div>
              )}
              {!serviceRowsLoading && !serviceRowsError && !serviceRows.length && (
                <div className="rounded border border-dashed border-slate-300 p-3 text-sm text-slate-600">
                  {TEXT.tree.serviceEmpty}
                </div>
              )}
              {serviceRows.map((row) => {
                const stats = row.serviceStats || emptyServiceStats
                const periodStats = stats?.period || emptyServiceStats.period
                const lifetimeStats = stats?.lifetime || emptyServiceStats.lifetime
                const latestEntry = stats?.latestEntry || null
                const existingTodayRaw = Number(row.existingServiceToday || 0)
                const existingToday = Number.isFinite(existingTodayRaw) ? existingTodayRaw : 0
                const serviceCountRaw = Number(row.serviceCount || 0)
                const additionalService = Number.isFinite(serviceCountRaw) ? serviceCountRaw : 0
                const projectedService = existingToday + additionalService
                const currentCountRaw =
                  row.currentCount != null && row.currentCount !== ''
                    ? Number(row.currentCount)
                    : null
                const hasCurrentCount = Number.isFinite(currentCountRaw)
                const remainingCount = hasCurrentCount ? currentCountRaw - projectedService : null
                const remainingDisplay =
                  remainingCount != null && Number.isFinite(remainingCount)
                    ? Math.max(remainingCount, 0)
                    : 0
                const exceedsCurrent =
                  hasCurrentCount && remainingCount !== null && remainingCount < 0
                const fullyCovered =
                  hasCurrentCount &&
                  !exceedsCurrent &&
                  currentCountRaw !== null &&
                  currentCountRaw > 0 &&
                  projectedService >= currentCountRaw
                const warningId = exceedsCurrent ? `service-warning-${row.key}` : undefined
                const serviceInputClasses = [
                  'w-full rounded border p-2',
                  exceedsCurrent
                    ? 'border-red-400 bg-red-50 focus:border-red-500 focus:ring-red-200'
                    : '',
                  !exceedsCurrent && fullyCovered
                    ? 'border-emerald-400 bg-emerald-50 focus:border-emerald-500 focus:ring-emerald-200'
                    : '',
                ]
                  .filter(Boolean)
                  .join(' ')
                const badgeBaseClass =
                  'inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600'
                const remainingBadgeClass = `${badgeBaseClass}${
                  hasCurrentCount && remainingCount !== null && remainingCount <= 0
                    ? ' bg-emerald-100 text-emerald-700'
                    : ''
                }`
                const lifetimeTotalRaw =
                  row.lifetimeServiceTotal != null
                    ? Number(row.lifetimeServiceTotal)
                    : Number(lifetimeStats.totalServiced || 0)
                const lifetimeTotal = Number.isFinite(lifetimeTotalRaw) ? lifetimeTotalRaw : 0
                const latestDate =
                  latestEntry?.activity_date ||
                  latestEntry?.recorded_at ||
                  periodStats.lastServiceDate ||
                  lifetimeStats.lastServiceDate ||
                  null
                const latestDateFormatted = formatDateOnly(latestDate)
                const latestCountLabel =
                  latestEntry && latestEntry.service_count != null
                    ? formatNumber(latestEntry.service_count)
                    : '-'
                const latestScopeValue =
                  latestEntry?.service_scope || latestEntry?.service_type || null
                const latestTypeLabel = latestScopeValue
                  ? SERVICE_SCOPE_LABEL_MAP[latestScopeValue] || latestScopeValue
                  : '-'
                const latestRecordedBy = latestEntry?.recorded_by_name || ''
                return (
                  <div key={row.key} className="space-y-3 rounded border bg-white p-3 shadow-sm">
                    <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                      <div>
                        <div className="font-semibold text-slate-800">
                          {row.varietyName || TEXT.tree.serviceVariety}
                        </div>
                        <div className="text-xs text-slate-500">
                          {hasCurrentCount
                            ? `${TEXT.tree.serviceCurrent}: ${formatNumber(currentCountRaw)}`
                            : TEXT.tree.serviceCurrent}
                        </div>
                        {row.status && (
                          <div className="text-[11px] text-slate-500">{row.status}</div>
                        )}
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-600">
                          <span className={badgeBaseClass}>
                            {TEXT.tree.serviceExistingToday(formatNumber(existingToday))}
                          </span>
                          <span className={badgeBaseClass}>
                            {TEXT.tree.serviceProjected(formatNumber(projectedService))}
                          </span>
                          <span className={badgeBaseClass}>
                            {TEXT.tree.serviceCoverageToday(
                              formatPercent(periodStats.coverageRatio),
                            )}
                          </span>
                          <span className={badgeBaseClass}>
                            {TEXT.tree.serviceCoverageLifetime(
                              formatPercent(lifetimeStats.coverageRatio),
                            )}
                          </span>
                          {hasCurrentCount && (
                            <span className={remainingBadgeClass}>
                              {TEXT.tree.serviceRemaining(formatNumber(remainingDisplay))}
                            </span>
                          )}
                          <span className={badgeBaseClass}>
                            {TEXT.tree.serviceLifetimeTotal(formatNumber(lifetimeTotal))}
                          </span>
                        </div>
                        {latestDate || latestEntry?.service_count != null || latestRecordedBy ? (
                          <div className="mt-2 space-y-1 text-[11px] text-slate-500">
                            <div>
                              {TEXT.tree.serviceLastRecorded(
                                latestDateFormatted,
                                latestCountLabel,
                                latestTypeLabel,
                              )}
                            </div>
                            {latestRecordedBy && (
                              <div>{TEXT.tree.serviceLatestBy(latestRecordedBy)}</div>
                            )}
                          </div>
                        ) : (
                          <div className="mt-2 text-[11px] text-slate-400">
                            {TEXT.tree.serviceLatestMissing}
                          </div>
                        )}
                      </div>
                      <button
                        type="button"
                        className="self-start text-xs text-red-600 hover:underline"
                        onClick={() => handleRemoveServiceRow(row.key)}
                      >
                        {TEXT.tree.serviceRemove}
                      </button>
                    </div>
                    <div className="grid gap-3 md:grid-cols-4">
                      <div className="space-y-1">
                        <label className="block text-xs text-gray-600">
                          {TEXT.tree.serviceCount}
                        </label>
                        <input
                          type="number"
                          min="0"
                          step="1"
                          className={serviceInputClasses}
                          value={row.serviceCount}
                          onChange={handleServiceRowChange(row.key, 'serviceCount')}
                          aria-describedby={warningId}
                          aria-invalid={exceedsCurrent}
                        />
                      </div>
                      {!row.varietyId && (
                        <div className="space-y-1">
                          <label className="block text-xs text-gray-600">
                            {TEXT.tree.serviceScope}
                          </label>
                          <select
                            className="w-full rounded border p-2"
                            value={row.serviceScope || DEFAULT_SERVICE_SCOPE}
                            onChange={handleServiceRowChange(row.key, 'serviceScope')}
                          >
                            {SERVICE_SCOPE_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                      <div className="space-y-1">
                        <label className="block text-xs text-gray-600">
                          {TEXT.tree.serviceCurrent}
                        </label>
                        <input
                          type="number"
                          className="w-full rounded border p-2"
                          value={row.totalBefore}
                          placeholder={TEXT.tree.serviceCurrent}
                          onChange={handleServiceRowChange(row.key, 'totalBefore')}
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="block text-xs text-gray-600">
                          {TEXT.tree.serviceAfter}
                        </label>
                        <input
                          type="number"
                          className="w-full rounded border p-2"
                          value={row.totalAfter}
                          placeholder={TEXT.tree.serviceAfter}
                          onChange={handleServiceRowChange(row.key, 'totalAfter')}
                        />
                      </div>
                    </div>
                    <div className="space-y-1">
                      <label className="block text-xs text-gray-600">
                        {TEXT.tree.serviceNotes}
                      </label>
                      <textarea
                        className="w-full rounded border p-2 text-xs"
                        rows="2"
                        value={row.notes}
                        placeholder={TEXT.tree.serviceNotesPlaceholder}
                        onChange={handleServiceRowChange(row.key, 'notes')}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CollapsibleCard>
      )}
    </>
  )
}

DailyLogForm.propTypes = {
  form: PropTypes.object.isRequired,
  setForm: PropTypes.func.isRequired,
  isEditingActivity: PropTypes.bool.isRequired,
  onFarmChange: PropTypes.func.isRequired,
  onLocationChange: PropTypes.func.isRequired,
  onCropChange: PropTypes.func.isRequired,
  onTaskChange: PropTypes.func.isRequired,
  farms: PropTypes.array.isRequired,
  locations: PropTypes.array.isRequired,
  crops: PropTypes.array.isRequired,
  tasks: PropTypes.array.isRequired,
  taskMeta: PropTypes.object.isRequired,
  selectedCrop: PropTypes.object,
  isTreeActivity: PropTypes.bool.isRequired,
  summary: PropTypes.object,
  summaryLoading: PropTypes.bool,
  summaryError: PropTypes.string,
  treeSummary: PropTypes.object,
  hasTreeSummary: PropTypes.bool,
  treeSummaryEntries: PropTypes.array,
  criticalMessages: PropTypes.array,
  collapsedSections: PropTypes.object.isRequired,
  toggleSection: PropTypes.func.isRequired,
  teamOptions: PropTypes.array,
  teamLoading: PropTypes.bool,
  formErrors: PropTypes.object,
  clearFieldError: PropTypes.func.isRequired,
  setTeamSearchTerm: PropTypes.func.isRequired,
  serviceProviders: PropTypes.array.isRequired,
  availableWells: PropTypes.array.isRequired,
  canSkipWellReading: PropTypes.bool,
  treeSnapshot: PropTypes.object.isRequired,
  treeSnapshotMeta: PropTypes.object.isRequired,
  varieties: PropTypes.array.isRequired,
  selectedLocation: PropTypes.object,
  selectedVariety: PropTypes.object,
  helpers: PropTypes.shape({
    formatNumber: PropTypes.func.isRequired,
    toDateInputValue: PropTypes.func.isRequired,
    formatDateTime: PropTypes.func.isRequired,
    formatOptionalNumber: PropTypes.func,
  }).isRequired,
  treeLossReasons: PropTypes.array,
  locationSummaryMeta: PropTypes.object,
  existingServiceCountTotal: PropTypes.number,
  totalServiceCount: PropTypes.number,
  projectedServiceCount: PropTypes.number,
  locationServiceTotals: PropTypes.object,
  serviceRows: PropTypes.array,
  serviceRowsLoading: PropTypes.bool,
  serviceRowsError: PropTypes.string,
  handleRemoveServiceRow: PropTypes.func,
  handleServiceRowChange: PropTypes.func,
}
