import { useEffect, useMemo, useState } from 'react'

import { Farms, ResourceAnalytics } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useToast } from '../components/ToastProvider'

const TEXT = {
  title: 'لوحة استهلاك التكاليف والخامات',
  farmLabel: 'المزرعة',
  cropLabel: 'المحصول',
  startLabel: 'من تاريخ',
  endLabel: 'إلى تاريخ',
  filter: 'تحديث البيانات',
  recommendedCost: 'التكلفة الموصى بها',
  actualCost: 'التكلفة الفعلية',
  variance: 'الانحراف',
  materialsTitle: 'تفاصيل الخامات',
  materialHeader: 'الخامة',
  recommendedQty: 'الكمية الموصى بها',
  actualQty: 'الكمية الفعلية',
  unit: 'الوحدة',
}

const formatNumber = (value) => {
  if (value === null || value === undefined) return '-'
  const number = Number(value)
  if (Number.isNaN(number)) return '-'
  return number.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function ResourceAnalyticsPage() {
  const auth = useAuth()
  const addToast = useToast()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [farms, setFarms] = useState([])
  const [metrics, setMetrics] = useState([])
  const [filters, setFilters] = useState({ farm: '', crop: '', start: '', end: '' })

  useEffect(() => {
    let isMounted = true
    ;(async () => {
      setLoading(true)
      setError('')
      try {
        const response = await Farms.list()
        if (!isMounted) return
        const list = response.data?.results ?? response.data ?? []
        const accessible = list.filter(
          (farm) => auth.isSuperuser || auth.isAdmin || auth.hasFarmAccess(farm.id),
        )
        setFarms(accessible)
        if (accessible.length && !filters.farm) {
          setFilters((prev) => ({ ...prev, farm: String(accessible[0].id) }))
        }
      } catch (err) {
        console.error('Failed to load farms', err)
        if (isMounted) setError('تعذر تحميل قائمة المزارع.')
      } finally {
        if (isMounted) setLoading(false)
      }
    })()
    return () => {
      isMounted = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth])

  const loadAnalytics = async () => {
    setLoading(true)
    setError('')
    try {
      const params = {
        farm: filters.farm || undefined,
        crop: filters.crop || undefined,
        start: filters.start || undefined,
        end: filters.end || undefined,
      }
      const response = await ResourceAnalytics.list(params)
      setMetrics(response.data?.results ?? response.data ?? [])
    } catch (err) {
      console.error('Failed to load resource analytics', err)
      setError('تعذر تحميل لوحة الموارد. حاول مرة أخرى.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (filters.farm) {
      loadAnalytics()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.farm])

  const farmOptions = useMemo(
    () => farms.map((farm) => ({ id: String(farm.id), name: farm.name })),
    [farms],
  )

  if (loading && !metrics.length) {
    return (
      <div className="rounded-xl border border-primary/20 bg-primary/5 dark:bg-primary/10 px-4 py-3 text-primary-700 dark:text-primary-400">
        جارٍ تحميل البيانات التحليلية...
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/30 px-4 py-3 text-red-700 dark:text-red-400">
        {error}
      </div>
    )
  }

  const totals = metrics.reduce(
    (acc, entry) => {
      acc.recommended += entry.totals?.recommended_cost ?? 0
      acc.actual += entry.totals?.actual_cost ?? 0
      return acc
    },
    { recommended: 0, actual: 0 },
  )
  const variance = totals.actual - totals.recommended

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm p-6 space-y-4">
        <h1 className="text-xl font-semibold text-gray-800 dark:text-white">{TEXT.title}</h1>
        <form
          className="grid gap-3 md:grid-cols-4"
          onSubmit={(event) => {
            event.preventDefault()
            loadAnalytics().catch((err) => {
              console.error(err)
              addToast({ intent: 'error', message: 'تعذر تحديث البيانات.' })
            })
          }}
        >
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {TEXT.farmLabel}
            </label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={filters.farm}
              onChange={(event) => setFilters((prev) => ({ ...prev, farm: event.target.value }))}
              required
            >
              <option value="">اختر المزرعة</option>
              {farmOptions.map((farm) => (
                <option key={farm.id} value={farm.id}>
                  {farm.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {TEXT.cropLabel}
            </label>
            <input
              type="number"
              min="1"
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={filters.crop}
              onChange={(event) => setFilters((prev) => ({ ...prev, crop: event.target.value }))}
              placeholder="معرّف المحصول (اختياري)"
            />
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {TEXT.startLabel}
            </label>
            <input
              type="date"
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={filters.start}
              onChange={(event) => setFilters((prev) => ({ ...prev, start: event.target.value }))}
            />
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {TEXT.endLabel}
            </label>
            <input
              type="date"
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={filters.end}
              onChange={(event) => setFilters((prev) => ({ ...prev, end: event.target.value }))}
            />
          </div>
          <div className="md:col-span-4">
            <button
              type="submit"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90"
            >
              {TEXT.filter}
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm p-6 space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-primary/20 bg-primary/5 dark:bg-primary/10 p-4">
            <p className="text-sm text-primary-600 dark:text-primary-400">{TEXT.recommendedCost}</p>
            <p className="text-2xl font-semibold text-primary-800 dark:text-primary-300">
              {formatNumber(totals.recommended)} ر.س
            </p>
          </div>
          <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/30 p-4">
            <p className="text-sm text-emerald-600 dark:text-emerald-400">{TEXT.actualCost}</p>
            <p className="text-2xl font-semibold text-emerald-800 dark:text-emerald-300">
              {formatNumber(totals.actual)} ر.س
            </p>
          </div>
          <div
            className={`rounded-xl border p-4 ${variance >= 0 ? 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400' : 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'}`}
          >
            <p className="text-sm">{TEXT.variance}</p>
            <p className="text-2xl font-semibold">{formatNumber(variance)} ر.س</p>
          </div>
        </div>

        {metrics.map((entry) => (
          <div
            key={entry.crop.id}
            className="space-y-3 rounded-xl border border-gray-200 dark:border-slate-700 p-4"
          >
            <div className="flex flex-col gap-1">
              <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
                {entry.crop.name}
              </h3>
              <p className="text-sm text-gray-500 dark:text-slate-400">
                المحصلة: {formatNumber(entry.totals?.actual_cost)} ر.س
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-600 text-sm">
                <thead className="bg-gray-50 dark:bg-slate-700 text-gray-600 dark:text-slate-300">
                  <tr>
                    <th className="px-3 py-2 text-end font-medium">{TEXT.materialHeader}</th>
                    <th className="px-3 py-2 text-end font-medium">{TEXT.recommendedQty}</th>
                    <th className="px-3 py-2 text-end font-medium">{TEXT.actualQty}</th>
                    <th className="px-3 py-2 text-end font-medium">{TEXT.unit}</th>
                    <th className="px-3 py-2 text-end font-medium">{TEXT.recommendedCost}</th>
                    <th className="px-3 py-2 text-end font-medium">{TEXT.actualCost}</th>
                    <th className="px-3 py-2 text-end font-medium">{TEXT.variance}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-slate-600">
                  {entry.materials.map((material) => (
                    <tr key={material.item_id} className="hover:bg-gray-50 dark:hover:bg-slate-700">
                      <td className="px-3 py-2 text-gray-800 dark:text-slate-200">
                        {material.item_name}
                      </td>
                      <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                        {formatNumber(material.recommended_qty)}
                      </td>
                      <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                        {formatNumber(material.actual_qty)}
                      </td>
                      <td className="px-3 py-2 text-gray-500 dark:text-slate-400">
                        {material.unit_symbol || '-'}
                      </td>
                      <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                        {formatNumber(material.recommended_cost)}
                      </td>
                      <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                        {formatNumber(material.actual_cost)}
                      </td>
                      <td
                        className={`px-3 py-2 font-semibold ${material.variance_cost > 0 ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}`}
                      >
                        {formatNumber(material.variance_cost)}
                      </td>
                    </tr>
                  ))}
                  {!entry.materials.length && (
                    <tr>
                      <td
                        className="px-3 py-3 text-center text-gray-500 dark:text-slate-400"
                        colSpan={7}
                      >
                        لا توجد بيانات خامات لهذا القالب.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ))}

        {!metrics.length && (
          <div className="rounded-xl border border-dashed border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700 px-4 py-3 text-sm text-gray-500 dark:text-slate-400">
            لا توجد بيانات متاحة ضمن نطاق التصفية الحالي.
          </div>
        )}
      </section>
    </div>
  )
}
