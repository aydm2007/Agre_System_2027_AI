import React, { useState, useEffect } from 'react'
import {
  Zap as BoltIcon,
  AlertTriangle as ExclamationTriangleIcon,
  AlertCircle as ExclamationCircleIcon,
  ShieldCheck as ShieldCheckIcon,
} from 'lucide-react'
import { formatCurrency } from '../utils/decimal'
import { api } from '../api/client'
import { useFarmContext } from '../api/farmContext.jsx'
import LoadingSkeleton from '../components/ui/LoadingSkeleton'
import ErrorState from '../components/ui/ErrorState'

const HealthBadge = ({ status }) => {
  switch (status) {
    case 'GREEN':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20 dark:bg-green-500/10 dark:text-green-400 dark:ring-green-500/20">
          <ShieldCheckIcon className="h-3.5 w-3.5" />
          جيدة
        </span>
      )
    case 'WARNING':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20 dark:bg-yellow-500/10 dark:text-yellow-400 dark:ring-yellow-500/20">
          <ExclamationTriangleIcon className="h-3.5 w-3.5" />
          إنذار صيانة
        </span>
      )
    case 'CRITICAL':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-1 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/10 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20">
          <ExclamationCircleIcon className="h-3.5 w-3.5" />
          استبدال فوري
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

  return (
    <div className="mt-2 w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
      <div
        className={`h-2.5 rounded-full transition-all duration-500 ${colorClass}`}
        style={{ width: `${Math.min(100, percentage)}%` }}
      ></div>
    </div>
  )
}

export default function SolarFleetMonitor() {

  const { selectedFarmId } = useFarmContext()
  const [assets, setAssets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!selectedFarmId) {
      setAssets([])
      setLoading(false)
      return
    }
    const fetchFleet = async () => {
      try {
        setLoading(true)
        const response = await api.get('/solar-fleet/', { params: { farm_id: selectedFarmId } })
        setAssets(response.data.results || [])
        setError(null)
      } catch (err) {
        console.error('Failed to fetch solar fleet:', err)
        setError('تعذر جُلب بيانات أسطول الطاقة. يرجى المحاولة لاحقاً.')
      } finally {
        setLoading(false)
      }
    }
    fetchFleet()
  }, [selectedFarmId])

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
            <BoltIcon className="h-7 w-7 text-amber-500" />
            شاشة الرقابة على الأصول الشمسية
          </h1>
          <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">
            مراقبة حية لاستهلاك منظومات الطاقة وتراكم مخصصات الإهلاك (صندوق الاستبدال).
          </p>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {assets.map((asset) => (
          <div
            key={asset.id}
            className="overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-gray-900/5 dark:bg-slate-800 dark:ring-white/10 transition-all hover:shadow-md"
          >
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold leading-6 text-gray-900 dark:text-white">
                    {asset.name}
                  </h3>
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    المزرعة: {asset.farm_name}
                  </p>
                </div>
                <HealthBadge status={asset.health_status} />
              </div>

              <dl className="mt-6 flex flex-col gap-y-4">
                <div>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    صندوق الاستبدال (الاحتياطي المتراكم)
                  </dt>
                  <dd className="mt-1 text-2xl font-bold tracking-tight text-gray-900 dark:text-white">
                    {formatCurrency(asset.accumulated_depreciation, 2)}
                  </dd>
                </div>

                <div>
                  <div className="flex justify-between items-center mt-2">
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      معدل الاستهلاك
                    </dt>
                    <dd className="text-sm font-semibold text-gray-900 dark:text-white">
                      {asset.depreciation_percentage}%
                    </dd>
                  </div>
                  <ProgressBar
                    percentage={asset.depreciation_percentage}
                    status={asset.health_status}
                  />
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-left" dir="ltr">
                    Hours: {formatCurrency(asset.useful_life_hours, 0)} | Years:{' '}
                    {asset.useful_life_years}
                  </p>
                </div>

                <div className="flex justify-between border-t border-gray-100 pt-4 dark:border-white/10">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    تكلفة الشراء الأصلية
                  </dt>
                  <dd className="text-sm font-semibold text-gray-900 dark:text-white">
                    {formatCurrency(asset.purchase_value, 2)}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        ))}
      </div>

      {assets.length === 0 && (
        <div className="mt-8 text-center bg-white dark:bg-slate-800 p-12 rounded-xl ring-1 ring-gray-900/5 dark:ring-white/10">
          <BoltIcon className="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600" />
          <h3 className="mt-2 text-sm font-semibold text-gray-900 dark:text-white">
            لا توجد أصول شمسية
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            لم يتم تسجيل أي أصول طاقة شمسية في المزارع المتاحة لك.
          </p>
        </div>
      )}
    </div>
  )
}
