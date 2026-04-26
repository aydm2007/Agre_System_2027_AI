import { useState, useEffect } from 'react'
import {
  Presentation as PresentationChartLineIcon,
  Flame as FireIcon,
  AlertCircle as ExclamationCircleIcon,
  AlertTriangle as ExclamationTriangleIcon,
  ShieldCheck as ShieldCheckIcon,
} from 'lucide-react'
import { formatCurrency } from '../utils/decimal'
import { api } from '../api/client'
import { useTranslation } from 'react-i18next'
import LoadingSkeleton from '../components/ui/LoadingSkeleton'
import ErrorState from '../components/ui/ErrorState'
import useFinancialFilters from '../hooks/useFinancialFilters'
import FinancialFilterBar from '../components/filters/FinancialFilterBar'

const HealthBadge = ({ status }) => {
  switch (status) {
    case 'GREEN':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20 dark:bg-green-500/10 dark:text-green-400 dark:ring-green-500/20">
          <ShieldCheckIcon className="h-3.5 w-3.5" />
          مستقر
        </span>
      )
    case 'WARNING':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20 dark:bg-yellow-500/10 dark:text-yellow-400 dark:ring-yellow-500/20">
          <ExclamationTriangleIcon className="h-3.5 w-3.5" />
          تجاوز محتمل
        </span>
      )
    case 'CRITICAL':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-1 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/10 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20">
          <ExclamationCircleIcon className="h-3.5 w-3.5" />
          عجز مالي مؤكد
        </span>
      )
    default:
      return null
  }
}

const ProgressBar = ({ percentage, status }) => {
  let colorClass = 'bg-green-500 dark:bg-green-400'
  if (status === 'WARNING') colorClass = 'bg-yellow-500 dark:bg-yellow-400'
  if (status === 'CRITICAL') colorClass = 'bg-red-500 dark:bg-red-400'

  // Cap the progress bar width visually to 100% so it doesn't break layout
  const visualPercentage = Math.min(100, Math.max(0, percentage))

  return (
    <div className="mt-2 w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
      <div
        className={`h-2.5 rounded-full transition-all duration-500 ${colorClass}`}
        style={{ width: `${visualPercentage}%` }}
      ></div>
    </div>
  )
}

export default function PredictiveVariance() {
  // eslint-disable-next-line no-unused-vars
  const { t } = useTranslation()
  const [metrics, setMetrics] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // [AGRI-GUARDIAN Axis 6] Multi-level cascading filters
  const {
    filters,
    options,
    loading: filterLoading,
    setFilter,
    resetFilters,
    filterParams,
  } = useFinancialFilters({ dimensions: ['farm', 'crop_plan', 'crop'] })

  useEffect(() => {
    const fetchPredictiveData = async () => {
      try {
        setLoading(true)
        const response = await api.get('/predictive-variance/', { params: filterParams })
        setMetrics(response.data.results || [])
        setError(null)
      } catch (err) {
        console.error('Failed to fetch predictive variance:', err)
        setError('تعذر جُلب مؤشرات الانحرافات التنبؤية. يرجى المحاولة لاحقاً.')
      } finally {
        setLoading(false)
      }
    }
    fetchPredictiveData()
  }, [filterParams])

  if (loading) {
    return (
      <div className="p-4 sm:p-6 lg:p-8">
        <LoadingSkeleton count={3} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 sm:p-6 lg:p-8">
        <ErrorState message={error} />
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-bold leading-6 text-gray-900 dark:text-white flex items-center gap-2">
            <PresentationChartLineIcon className="h-7 w-7 text-indigo-500" />
            لوحة الانحرافات التنبؤية (استهلاك الموازنة)
          </h1>
          <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">
            توقع الانحراف المالي عند نهاية الموسم الزراعي بناءً على معدل حرق الموارد وتكاليف المواد
            الفعلية حالياً.
          </p>
        </div>
      </div>

      {/* [AGRI-GUARDIAN] Multi-level filter bar */}
      <FinancialFilterBar
        filters={filters}
        options={options}
        loading={filterLoading}
        setFilter={setFilter}
        onReset={resetFilters}
        dimensions={['farm', 'crop_plan', 'crop']}
        className="mt-6"
      />

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {metrics.map((metric) => (
          <div
            key={metric.plan_id}
            className={`overflow-hidden rounded-xl bg-white shadow-sm ring-1 dark:bg-slate-800 transition-all hover:shadow-md
              ${
                metric.health_status === 'CRITICAL'
                  ? 'ring-red-500/50 dark:ring-red-500/30'
                  : metric.health_status === 'WARNING'
                    ? 'ring-yellow-500/50 dark:ring-yellow-500/30'
                    : 'ring-gray-900/5 dark:ring-white/10'
              }`}
          >
            <div className="p-6">
              <div className="flex items-center justify-between border-b border-gray-100 pb-4 dark:border-slate-700">
                <div>
                  <h3 className="text-lg font-semibold leading-6 text-gray-900 dark:text-white flex items-center gap-2">
                    {metric.plan_name}
                    {metric.health_status === 'CRITICAL' && (
                      <FireIcon className="h-5 w-5 text-red-500 animate-pulse" />
                    )}
                  </h3>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {metric.farm_name} • محصول: {metric.crop_name}
                  </p>
                </div>
                <HealthBadge status={metric.health_status} />
              </div>

              <dl className="mt-6 flex flex-col gap-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 dark:bg-slate-900 rounded-lg p-3 border border-gray-100 dark:border-slate-700 text-center">
                    <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">
                      الموازنة الكلية (مواد)
                    </dt>
                    <dd className="mt-1 text-lg font-bold tracking-tight text-gray-900 dark:text-white">
                      {formatCurrency(metric.total_material_budget, 0)}
                    </dd>
                  </div>
                  <div className="bg-gray-50 dark:bg-slate-900 rounded-lg p-3 border border-gray-100 dark:border-slate-700 text-center">
                    <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">
                      التوقع النهائي (Burn Extrapolation)
                    </dt>
                    <dd
                      className={`mt-1 text-lg font-bold tracking-tight ${
                        metric.health_status === 'CRITICAL'
                          ? 'text-red-600 dark:text-red-400'
                          : metric.health_status === 'WARNING'
                            ? 'text-yellow-600 dark:text-yellow-400'
                            : 'text-green-600 dark:text-green-400'
                      }`}
                    >
                      {formatCurrency(metric.projected_total_cost, 0)}
                    </dd>
                  </div>
                </div>

                <div className="mt-2">
                  <div className="flex justify-between items-center mt-2">
                    <dt className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      نسبة الانحراف المتوقعة من الموازنة
                    </dt>
                    <dd className="text-sm font-bold text-gray-900 dark:text-white" dir="ltr">
                      {formatCurrency(metric.variance_ratio, 1)}%
                    </dd>
                  </div>
                  <ProgressBar percentage={metric.variance_ratio} status={metric.health_status} />
                  <p
                    className="mt-2 text-xs text-center text-gray-500 dark:text-gray-400"
                    dir="ltr"
                  >
                    Season Progress: {metric.elapsed_days} / {metric.total_days} Days (
                    {formatCurrency(metric.time_elapsed_ratio, 1)}%)
                  </p>
                </div>

                <div className="flex justify-between border-t border-gray-100 pt-3 dark:border-slate-700">
                  <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">
                    الاستهلاك الفعلي حتى اليوم الطارئ
                  </dt>
                  <dd className="text-sm font-semibold text-gray-900 dark:text-white">
                    {formatCurrency(metric.actual_material_cost, 2)}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        ))}
      </div>

      {metrics.length === 0 && (
        <div className="mt-8 text-center bg-white dark:bg-slate-800 p-12 rounded-xl ring-1 ring-gray-900/5 dark:ring-white/10">
          <PresentationChartLineIcon className="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600" />
          <h3 className="mt-2 text-sm font-semibold text-gray-900 dark:text-white">
            جاهزية التنبؤات مغطاة
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            لا توجد خطط زراعية نشطة حالياً لتوليد تنبؤات الانحراف.
          </p>
        </div>
      )}
    </div>
  )
}
