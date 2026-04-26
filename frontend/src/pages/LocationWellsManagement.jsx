import React, { useCallback, useEffect, useMemo, useReducer, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { Assets, Farms, LocationWells, Locations } from '../api/client'

const initialSelection = {
  farmId: '',
  locationId: '',
  wellId: '',
}

const STATUS_OPTIONS = [
  {
    value: 'active',
    label: 'نشط',
    badgeClass:
      'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800',
  },
  {
    value: 'maintenance',
    label: 'صيانة',
    badgeClass:
      'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800',
  },
  {
    value: 'inactive',
    label: 'متوقف',
    badgeClass:
      'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-400 border border-gray-200 dark:border-slate-600',
  },
]

const STATUS_LABELS = STATUS_OPTIONS.reduce((map, option) => {
  map[option.value] = option.label
  return map
}, {})

const defaultOperationalForm = {
  depth_meters: '',
  water_level_meters: '',
  discharge_rate_lps: '',
  status: 'active',
  last_serviced_at: '',
  notes: '',
}

const numberFormatter = new Intl.NumberFormat('ar-SA', { maximumFractionDigits: 2 })

function selectionReducer(state, action) {
  switch (action.type) {
    case 'setFarm':
      return { farmId: action.value, locationId: '', wellId: '' }
    case 'setLocation':
      return { ...state, locationId: action.value }
    case 'setWell':
      return { ...state, wellId: action.value }
    case 'reset':
      return initialSelection
    default:
      return state
  }
}

const StepIndicator = ({ currentStep }) => {
  const steps = [
    { id: 1, label: 'اختيار المزرعة' },
    { id: 2, label: 'تحديد الموقع' },
    { id: 3, label: 'ربط البئر' },
  ]

  return (
    <ol className="flex flex-wrap items-center gap-4 text-sm">
      {steps.map((step) => {
        const active = step.id === currentStep
        const completed = step.id < currentStep
        return (
          <li key={step.id} className="flex items-center gap-2">
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
                completed
                  ? 'bg-green-500 text-white'
                  : active
                    ? 'bg-primary text-white'
                    : 'bg-gray-200 dark:bg-slate-700 text-gray-600 dark:text-slate-400'
              }`}
            >
              {step.id}
            </span>
            <span
              className={
                completed
                  ? 'text-green-700 dark:text-green-400'
                  : 'text-gray-700 dark:text-slate-300'
              }
            >
              {step.label}
            </span>
          </li>
        )
      })}
    </ol>
  )
}

const SelectorField = ({ label, placeholder, options, value, onChange, disabled }) => (
  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
    <span>{label}</span>
    <select
      className="mt-1 w-full rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white p-2 text-base focus:border-primary focus:outline-none transition-colors"
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="" disabled>
        {placeholder}
      </option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  </label>
)

function InlineAlert({ feedback }) {
  if (!feedback?.message) {
    return null
  }
  const intentClasses =
    feedback.type === 'error'
      ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800'
      : 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800'
  return <div className={`rounded px-4 py-3 text-sm ${intentClasses}`}>{feedback.message}</div>
}

const formatMetric = (value, unitSuffix = '') => {
  if (value === null || value === undefined || value === '') {
    return '—'
  }
  const numeric = Number(value)
  if (Number.isNaN(numeric)) {
    return value
  }
  const rendered = numberFormatter.format(numeric)
  return unitSuffix ? `${rendered} ${unitSuffix}` : rendered
}

const formatDate = (value) => {
  if (!value) {
    return '—'
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return parsed.toLocaleDateString('ar-SA')
}

function SummaryPanel({ summary, onRefresh, loading }) {
  if (!summary) {
    return null
  }

  const total = summary.total ?? 0
  const topLocations = (summary.by_location || []).slice(0, 5)

  return (
    <section className="rounded border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-widest text-primary">نظرة تشغيلية</p>
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white dark:text-white">
            إجمالي الروابط: {total}
          </h2>
        </div>
        <button
          type="button"
          className="rounded border border-primary px-4 py-2 text-sm font-semibold text-primary hover:bg-primary/10 disabled:opacity-60 transition-colors"
          onClick={onRefresh}
          disabled={loading}
        >
          تحديث الملخص
        </button>
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-600 dark:text-slate-400">حسب الحالة</h3>
          <ul className="mt-3 space-y-2">
            {STATUS_OPTIONS.map((option) => {
              const match = summary.by_status?.find((entry) => entry.status === option.value)
              return (
                <li
                  key={option.value}
                  className="flex items-center justify-between rounded border border-gray-100 dark:border-slate-700 px-3 py-2 bg-gray-50/50 dark:bg-slate-700/30"
                >
                  <span className="flex items-center gap-2 text-sm">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-semibold ${option.badgeClass}`}
                    >
                      {option.label}
                    </span>
                  </span>
                  <span className="text-base font-bold text-gray-900 dark:text-white">
                    {match?.count ?? 0}
                  </span>
                </li>
              )
            })}
          </ul>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-600 dark:text-slate-400">
            أعلى المواقع ارتباطاً
          </h3>
          <ul className="mt-3 space-y-2">
            {topLocations.length === 0 && (
              <li className="rounded border border-dashed border-gray-200 dark:border-slate-600 px-3 py-2 text-sm text-gray-500 dark:text-slate-400">
                لا توجد بيانات كافية بعد.
              </li>
            )}
            {topLocations.map((location) => (
              <li
                key={location.location_id}
                className="flex items-center justify-between rounded border border-gray-100 dark:border-slate-700 px-3 py-2 bg-gray-50/50 dark:bg-slate-700/30"
              >
                <span className="text-sm text-gray-700 dark:text-slate-300">
                  {location.location_name || `موقع #${location.location_id}`}
                </span>
                <span className="text-base font-bold text-gray-900 dark:text-white">
                  {location.well_count}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

function FieldInput({ label, type = 'text', value, onChange, min, step, placeholder }) {
  return (
    <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
      <span>{label}</span>
      <input
        type={type}
        value={value}
        min={min}
        step={step}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white p-2 text-base focus:border-primary focus:outline-none transition-colors placeholder:text-gray-400 dark:placeholder:text-slate-500"
      />
    </label>
  )
}

function StatusSelect({ value, onChange, disabled }) {
  return (
    <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
      <span>حالة البئر</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        className="mt-1 w-full rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white p-2 text-base focus:border-primary focus:outline-none transition-colors"
      >
        {STATUS_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

function OperationalEditor({ link, form, onChange, onCancel, onSubmit, busy }) {
  if (!link) {
    return null
  }

  return (
    <section className="rounded border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm uppercase tracking-widest text-primary">بيانات تشغيلية</p>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white dark:text-white">
            {link.asset_name || 'بئر'} - {link.location_name || 'موقع'}
          </h3>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded border border-gray-300 dark:border-slate-600 px-4 py-2 text-sm text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700"
            onClick={onCancel}
            disabled={busy}
          >
            إلغاء
          </button>
          <button
            type="button"
            className="rounded bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-dark disabled:opacity-60"
            onClick={onSubmit}
            disabled={busy}
          >
            حفظ التعديلات
          </button>
        </div>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <FieldInput
          label="عمق البئر (متر)"
          type="number"
          value={form.depth_meters}
          step="0.1"
          min="0"
          placeholder="مثال: 150"
          onChange={(value) => onChange('depth_meters', value)}
        />
        <FieldInput
          label="منسوب الماء (متر)"
          type="number"
          value={form.water_level_meters}
          step="0.1"
          min="0"
          placeholder="مثال: 45"
          onChange={(value) => onChange('water_level_meters', value)}
        />
        <FieldInput
          label="غزارة التصريف (لتر/ثانية)"
          type="number"
          value={form.discharge_rate_lps}
          step="0.1"
          min="0"
          placeholder="مثال: 12"
          onChange={(value) => onChange('discharge_rate_lps', value)}
        />
        <StatusSelect
          value={form.status}
          onChange={(value) => onChange('status', value)}
          disabled={busy}
        />
        <FieldInput
          label="آخر صيانة"
          type="date"
          value={form.last_serviced_at}
          onChange={(value) => onChange('last_serviced_at', value)}
        />
      </div>

      <label className="mt-4 block text-sm font-medium text-gray-700 dark:text-slate-300">
        <span>ملاحظات</span>
        <textarea
          rows={3}
          value={form.notes}
          onChange={(event) => onChange('notes', event.target.value)}
          className="mt-1 w-full rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white p-2 text-base focus:border-primary focus:outline-none transition-colors placeholder:text-gray-400 dark:placeholder:text-slate-500"
          placeholder="سجل أي ملاحظات تشغيلية أو فنية"
        />
      </label>
    </section>
  )
}

function LocationWellTable({
  links,
  locationsById,
  wellsById,
  onRemove,
  onEdit,
  canDelete,
  isBusy,
}) {
  if (!links.length) {
    return (
      <div className="rounded border border-dashed border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-4 py-10 text-center text-sm text-gray-500 dark:text-slate-400">
        لا يوجد أي روابط محفوظة. أضف ارتباطاً جديداً من خلال النموذج أعلاه.
      </div>
    )
  }

  const sortedLinks = [...links].sort((a, b) => {
    const locationNameA = (
      a.location_name ||
      locationsById.get(a.location_id)?.name ||
      ''
    ).toString()
    const locationNameB = (
      b.location_name ||
      locationsById.get(b.location_id)?.name ||
      ''
    ).toString()
    const compareLocation = locationNameA.localeCompare(locationNameB, 'ar')
    if (compareLocation !== 0) {
      return compareLocation
    }
    return (a.asset_name || '').localeCompare(b.asset_name || '', 'ar')
  })

  return (
    <div className="grid gap-4">
      {sortedLinks.map((link) => {
        const location = locationsById.get(link.location_id)
        const well = wellsById.get(link.asset_id)
        const locationName = link.location_name || location?.name || `موقع #${link.location_id}`
        const wellName = link.asset_name || well?.name || `بئر #${link.asset_id}`
        const wellCode = link.asset_code || well?.code
        const badgeClass =
          STATUS_OPTIONS.find((option) => option.value === link.status)?.badgeClass ||
          'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300 border border-gray-200 dark:border-slate-600'

        return (
          <article
            key={link.id}
            className="rounded border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 shadow-sm"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-widest text-gray-500 dark:text-slate-400">
                  الموقع
                </p>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white dark:text-white">
                  {locationName}
                </h3>
              </div>
              <div className="text-end">
                <p className="text-xs uppercase tracking-widest text-gray-500 dark:text-slate-400">
                  البئر
                </p>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white dark:text-white">
                  {wellName}
                  {wellCode ? (
                    <span className="ms-2 text-sm text-gray-500 dark:text-slate-400">
                      ({wellCode})
                    </span>
                  ) : null}
                </h3>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${badgeClass}`}>
                {STATUS_LABELS[link.status] || link.status}
              </span>
            </div>

            <dl className="mt-4 grid gap-4 text-sm md:grid-cols-4">
              <div>
                <dt className="text-gray-500 dark:text-slate-400">عمق البئر</dt>
                <dd className="font-semibold text-gray-900 dark:text-white">
                  {formatMetric(link.depth_meters, 'م')}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500 dark:text-slate-400">منسوب الماء</dt>
                <dd className="font-semibold text-gray-900 dark:text-white">
                  {formatMetric(link.water_level_meters, 'م')}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500 dark:text-slate-400">معدل التصريف</dt>
                <dd className="font-semibold text-gray-900 dark:text-white">
                  {formatMetric(link.discharge_rate_lps, 'لتر/ث')}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500 dark:text-slate-400">آخر صيانة</dt>
                <dd className="font-semibold text-gray-900 dark:text-white">
                  {formatDate(link.last_serviced_at)}
                </dd>
              </div>
            </dl>

            {link.notes ? (
              <p className="mt-3 text-sm text-gray-600 dark:text-slate-300">{link.notes}</p>
            ) : null}

            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                className="rounded border border-primary px-3 py-1.5 text-xs font-semibold text-primary hover:bg-primary/10 disabled:opacity-60"
                disabled={isBusy}
                onClick={() => onEdit(link)}
              >
                تحرير البيانات التشغيلية
              </button>
              {canDelete && (
                <button
                  type="button"
                  className="rounded border border-red-200 dark:border-red-800 px-3 py-1.5 text-xs font-semibold text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-60"
                  disabled={isBusy}
                  onClick={() => onRemove(link)}
                >
                  حذف الرابط
                </button>
              )}
            </div>
          </article>
        )
      })}
    </div>
  )
}

export default function LocationWellsManagement() {
  const { hasFarmAccess, canAddModel, canDeleteModel } = useAuth()
  const [farms, setFarms] = useState([])
  const [locations, setLocations] = useState([])
  const [wells, setWells] = useState([])
  const [links, setLinks] = useState([])
  const [selection, dispatch] = useReducer(selectionReducer, initialSelection)
  const [feedback, setFeedback] = useState(null)
  const [dataLoading, setDataLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [summary, setSummary] = useState(null)
  const [editingLink, setEditingLink] = useState(null)
  const [operationalForm, setOperationalForm] = useState(defaultOperationalForm)

  const canManageLinks = canAddModel('locationwell')
  const canRemoveLinks = canDeleteModel('locationwell')

  const currentStep = useMemo(() => {
    if (!selection.farmId) return 1
    if (!selection.locationId || !selection.wellId) return 2
    return 3
  }, [selection])

  const locationsById = useMemo(() => {
    const map = new Map()
    locations.forEach((location) => {
      map.set(location.id, location)
    })
    return map
  }, [locations])

  const wellsById = useMemo(() => {
    const map = new Map()
    wells.forEach((well) => {
      map.set(well.id, well)
    })
    return map
  }, [wells])

  const handleFeedback = useCallback((type, message) => {
    setFeedback({ type, message })
    if (type === 'success') {
      setTimeout(() => setFeedback(null), 4000)
    }
  }, [])

  const fetchFarms = useCallback(async () => {
    try {
      const response = await Farms.list()
      setFarms(response.data.results || response.data || [])
    } catch (error) {
      console.error('Failed to load farms', error)
      handleFeedback('error', 'تعذر تحميل قائمة المزارع، تأكد من الاتصال ثم أعد المحاولة.')
    }
  }, [handleFeedback])

  const resetDatasets = useCallback(() => {
    setLocations([])
    setWells([])
    setLinks([])
    setSummary(null)
    setEditingLink(null)
    setOperationalForm(defaultOperationalForm)
  }, [])

  const refreshSummary = useCallback(async (farmId) => {
    if (!farmId) {
      setSummary(null)
      return
    }
    try {
      const response = await LocationWells.summary({ farm_id: farmId })
      setSummary(response.data)
    } catch (error) {
      console.error('Failed to load summary', error)
    }
  }, [])

  const loadFarmData = useCallback(
    async (farmId) => {
      if (!farmId) {
        resetDatasets()
        return
      }

      if (!hasFarmAccess(farmId)) {
        handleFeedback('error', 'ليس لديك صلاحية لإدارة هذه المزرعة.')
        dispatch({ type: 'reset' })
        return
      }

      setDataLoading(true)
      try {
        setEditingLink(null)
        setOperationalForm(defaultOperationalForm)
        const [locationsResponse, wellsResponse, linksResponse, summaryResponse] =
          await Promise.all([
            Locations.list({ farm_id: farmId, page_size: 500 }),
            Assets.list({ farm_id: farmId, category: 'Well', page_size: 500 }),
            LocationWells.list({ farm_id: farmId, page_size: 500 }),
            LocationWells.summary({ farm_id: farmId }),
          ])
        setLocations(locationsResponse.data.results || locationsResponse.data || [])
        setWells(wellsResponse.data.results || wellsResponse.data || [])
        setLinks(linksResponse.data.results || linksResponse.data || [])
        setSummary(summaryResponse.data || null)
      } catch (error) {
        console.error('Failed to load farm data', error)
        handleFeedback('error', 'تعذر تحميل بيانات المزرعة المحددة.')
      } finally {
        setDataLoading(false)
      }
    },
    [handleFeedback, hasFarmAccess, resetDatasets],
  )

  useEffect(() => {
    fetchFarms()
  }, [fetchFarms])

  useEffect(() => {
    loadFarmData(selection.farmId)
  }, [loadFarmData, selection.farmId])

  const handleCreateLink = useCallback(async () => {
    if (!selection.locationId || !selection.wellId) {
      handleFeedback('error', 'يرجى اختيار الموقع والبئر قبل المتابعة.')
      return
    }
    if (!canManageLinks) {
      handleFeedback('error', 'ليست لديك صلاحية لإدارة روابط الآبار.')
      return
    }

    setActionLoading(true)
    try {
      const payload = {
        location_id: Number(selection.locationId),
        asset_id: Number(selection.wellId),
      }
      const response = await LocationWells.create(payload)
      setLinks((prev) => [...prev, response.data])
      dispatch({ type: 'setLocation', value: '' })
      dispatch({ type: 'setWell', value: '' })
      handleFeedback('success', 'تم ربط الموقع بالبئر.')
      refreshSummary(selection.farmId)
    } catch (error) {
      console.error('Failed to create link', error)
      const message =
        error?.response?.data?.detail || 'تعذر إنشاء الربط، تحقق من البيانات وحاول مجدداً.'
      handleFeedback('error', message)
    } finally {
      setActionLoading(false)
    }
  }, [
    canManageLinks,
    handleFeedback,
    refreshSummary,
    selection.farmId,
    selection.locationId,
    selection.wellId,
  ])

  const handleRemoveLink = useCallback(
    async (link) => {
      if (!canRemoveLinks) {
        handleFeedback('error', 'لا تملك صلاحية حذف الروابط.')
        return
      }
      const confirmed = window.confirm('هل تريد حذف هذا الربط بشكل نهائي؟')
      if (!confirmed) {
        return
      }

      setActionLoading(true)
      try {
        await LocationWells.delete(link.id)
        setLinks((prev) => prev.filter((item) => item.id !== link.id))
        handleFeedback('success', 'تم حذف الرابط.')
        refreshSummary(selection.farmId)
      } catch (error) {
        console.error('Failed to delete link', error)
        handleFeedback('error', 'تعذر حذف الرابط، حاول مرة أخرى.')
      } finally {
        setActionLoading(false)
      }
    },
    [canRemoveLinks, handleFeedback, refreshSummary, selection.farmId],
  )

  const handleStartEdit = useCallback((link) => {
    setEditingLink(link)
    setOperationalForm({
      depth_meters: link?.depth_meters ?? '',
      water_level_meters: link?.water_level_meters ?? '',
      discharge_rate_lps: link?.discharge_rate_lps ?? '',
      status: link?.status || 'active',
      last_serviced_at: link?.last_serviced_at || '',
      notes: link?.notes || '',
    })
  }, [])

  const handleOperationalChange = useCallback((field, value) => {
    setOperationalForm((prev) => ({ ...prev, [field]: value }))
  }, [])

  const resetOperationalEditor = useCallback(() => {
    setEditingLink(null)
    setOperationalForm(defaultOperationalForm)
  }, [])

  const toNullableNumber = (value) => {
    if (value === '' || value === null || value === undefined) {
      return null
    }
    const parsed = Number(value)
    return Number.isNaN(parsed) ? null : parsed
  }

  const handleSubmitOperational = useCallback(async () => {
    if (!editingLink) {
      return
    }

    setActionLoading(true)
    try {
      const payload = {
        depth_meters: toNullableNumber(operationalForm.depth_meters),
        water_level_meters: toNullableNumber(operationalForm.water_level_meters),
        discharge_rate_lps: toNullableNumber(operationalForm.discharge_rate_lps),
        status: operationalForm.status,
        last_serviced_at: operationalForm.last_serviced_at || null,
        notes: operationalForm.notes || '',
      }
      const response = await LocationWells.update(editingLink.id, payload)
      setLinks((prev) => prev.map((item) => (item.id === response.data.id ? response.data : item)))
      handleFeedback('success', 'تم تحديث بيانات البئر.')
      refreshSummary(selection.farmId)
      resetOperationalEditor()
    } catch (error) {
      console.error('Failed to update operational data', error)
      const message = error?.response?.data?.detail || 'تعذر تحديث بيانات البئر.'
      handleFeedback('error', message)
    } finally {
      setActionLoading(false)
    }
  }, [
    editingLink,
    handleFeedback,
    operationalForm,
    refreshSummary,
    resetOperationalEditor,
    selection.farmId,
  ])

  const farmOptions = useMemo(
    () =>
      farms.map((farm) => ({
        value: String(farm.id),
        label: farm.name,
      })),
    [farms],
  )

  const locationOptions = useMemo(
    () =>
      locations.map((location) => ({
        value: String(location.id),
        label: location.name,
      })),
    [locations],
  )

  const wellOptions = useMemo(
    () =>
      wells.map((well) => ({
        value: String(well.id),
        label: well.code ? `${well.name} (${well.code})` : well.name,
      })),
    [wells],
  )

  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-widest text-primary">إدارة الربط</p>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">ربط المواقع بالآبار</h1>
        <p className="text-gray-600 dark:text-slate-300">
          استخدم هذه الواجهة لاختيار المزرعة والموقع وربطهما بالبئر المناسب مع تحديث بيانات التشغيل.
        </p>
      </header>

      <div className="rounded border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 shadow-sm">
        <StepIndicator currentStep={currentStep} />
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <SelectorField
            label="المزرعة"
            placeholder="اختر المزرعة"
            options={farmOptions}
            value={selection.farmId}
            onChange={(value) => dispatch({ type: 'setFarm', value })}
            disabled={dataLoading || actionLoading}
          />
          <SelectorField
            label="الموقع"
            placeholder="اختر الموقع"
            options={locationOptions}
            value={selection.locationId}
            onChange={(value) => dispatch({ type: 'setLocation', value })}
            disabled={!selection.farmId || dataLoading || actionLoading}
          />
          <SelectorField
            label="البئر"
            placeholder="اختر البئر"
            options={wellOptions}
            value={selection.wellId}
            onChange={(value) => dispatch({ type: 'setWell', value })}
            disabled={!selection.farmId || dataLoading || actionLoading}
          />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-4">
          <button
            type="button"
            className="rounded bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-dark disabled:opacity-60"
            onClick={handleCreateLink}
            disabled={
              !canManageLinks ||
              !selection.farmId ||
              !selection.locationId ||
              !selection.wellId ||
              actionLoading
            }
          >
            ربط الموقع بالبئر
          </button>
          {dataLoading && (
            <span className="text-sm text-gray-500 dark:text-slate-400">
              جارٍ تحميل البيانات المحدثة…
            </span>
          )}
        </div>
      </div>

      <InlineAlert feedback={feedback} />

      {selection.farmId ? (
        <SummaryPanel
          summary={summary}
          onRefresh={() => refreshSummary(selection.farmId)}
          loading={dataLoading}
        />
      ) : null}

      <LocationWellTable
        links={links}
        locationsById={locationsById}
        wellsById={wellsById}
        canDelete={canRemoveLinks}
        isBusy={actionLoading}
        onRemove={handleRemoveLink}
        onEdit={handleStartEdit}
      />

      <OperationalEditor
        link={editingLink}
        form={operationalForm}
        onChange={handleOperationalChange}
        onCancel={resetOperationalEditor}
        onSubmit={handleSubmitOperational}
        busy={actionLoading}
      />
    </section>
  )
}
