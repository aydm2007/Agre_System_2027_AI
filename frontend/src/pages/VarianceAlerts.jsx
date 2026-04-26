import { useState, useEffect } from 'react'
import { VarianceAlerts as VarianceAlertsAPI } from '../api/client'
import {
  AlertCircle,
  AlertTriangle,
  Search,
  Filter,
  Briefcase,
  Activity as ActivityIcon,
  Sprout,
  CheckCircle2,
} from 'lucide-react'
import ErrorBoundary from '../components/ErrorBoundary'
import { useFarmContext } from '../api/farmContext'
import useFinancialFilters from '../hooks/useFinancialFilters'
import FinancialFilterBar from '../components/filters/FinancialFilterBar'

const FILTER_DIMENSIONS = ['farm', 'location', 'crop']

function VarianceAlertsPage() {
  const { farms } = useFarmContext()
  const hasFarms = farms.length > 0
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [filter, setFilter] = useState('ALL') // ALL, WARNING, CRITICAL
  const [search, setSearch] = useState('')

  // [AGRI-GUARDIAN Axis 6] Multi-level cascading filters
  const {
    filters: financialFilters,
    options: filterOptions,
    loading: filterLoading,
    setFilter: setFinancialFilter,
    resetFilters,
    filterParams,
  } = useFinancialFilters({ dimensions: FILTER_DIMENSIONS })

  useEffect(() => {
    if (hasFarms) {
      fetchAlerts()
    } else {
      setLoading(false)
    }
  }, [hasFarms, filterParams]) // eslint-disable-line react-hooks/exhaustive-deps

  const fetchAlerts = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await VarianceAlertsAPI.list(filterParams)
      setAlerts(res.data?.results || res.data || [])
    } catch (err) {
      console.error(err)
      setError('تعذر استرداد بيانات انحراف المواد (Variance).')
    } finally {
      setLoading(false)
    }
  }

  const filteredAlerts = alerts.filter((a) => {
    if (filter !== 'ALL' && a.status !== filter) return false
    if (search) {
      const q = search.toLowerCase()
      const matName = a.item_name?.toLowerCase() || ''
      const planName = a.crop_plan_name?.toLowerCase() || ''
      if (!matName.includes(q) && !planName.includes(q)) return false
    }
    return true
  })

  const getStatusStyle = (status) => {
    switch (status) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800'
      case 'WARNING':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 border border-yellow-200 dark:border-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'CRITICAL':
        return <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
      case 'WARNING':
        return <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
      default:
        return <ActivityIcon className="w-5 h-5 text-gray-500" />
    }
  }

  if (!hasFarms) {
    return (
      <div className="p-12 text-center bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-dashed border-gray-300 dark:border-slate-700">
        <Sprout className="w-16 h-16 text-gray-300 dark:text-slate-600 mx-auto mb-4" />
        <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">لا توجد مزرعة نشطة</h3>
        <p className="text-gray-500 dark:text-slate-400">
          الرجاء اختيار مزرعة لعرض تنبيهات الانحرافات
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-slate-700">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <ActivityIcon className="w-6 h-6 text-primary" />
            لوحة انحراف التكاليف (Variance Alerts)
          </h1>
          <p className="text-gray-500 dark:text-slate-400 mt-1">
            مراقبة وتتبع التجاوزات الحية للمواد المستهلكة مقابل المعيار الزراعي (BOM)
          </p>
        </div>
        <div className="bg-primary/10 text-primary px-4 py-2 rounded-lg font-bold text-lg border border-primary/20">
          {alerts.filter((a) => a.status === 'CRITICAL').length} تنبيهات حرجة
        </div>
      </div>

      {/* [AGRI-GUARDIAN] Multi-level filter bar */}
      <FinancialFilterBar
        filters={financialFilters}
        options={filterOptions}
        loading={filterLoading}
        setFilter={setFinancialFilter}
        onReset={resetFilters}
        dimensions={FILTER_DIMENSIONS}
      />

      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute right-3 top-3.5 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="البحث باسم المادة أو خطة المحصول..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-4 pr-10 py-3 rounded-xl border border-gray-200 dark:border-slate-700 focus:ring-2 focus:ring-primary focus:border-transparent outline-none bg-white dark:bg-slate-800 dark:text-white shadow-sm"
          />
        </div>
        <div className="flex items-center gap-2 bg-white dark:bg-slate-800 rounded-xl p-1.5 border border-gray-200 dark:border-slate-700 shadow-sm">
          <Filter className="w-5 h-5 text-gray-400 mr-2" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-transparent border-none outline-none text-gray-700 dark:text-slate-200 font-medium py-1.5 pr-2 focus:ring-0 cursor-pointer"
          >
            <option value="ALL">جميع التنبيهات</option>
            <option value="CRITICAL">حرجة فقط</option>
            <option value="WARNING">تحذيرات فقط</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-pulse">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="bg-white dark:bg-slate-800 rounded-2xl h-48 border border-gray-100 dark:border-slate-700"
            ></div>
          ))}
        </div>
      ) : error ? (
        <div className="p-8 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-700 dark:text-red-400 font-medium">{error}</p>
          <button
            onClick={fetchAlerts}
            className="mt-4 px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
          >
            إعادة المحاولة
          </button>
        </div>
      ) : filteredAlerts.length === 0 ? (
        <div className="p-16 text-center bg-white dark:bg-slate-800 border border-dashed border-gray-300 dark:border-slate-700 rounded-3xl shadow-sm">
          <div className="w-20 h-20 bg-green-50 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-10 h-10 text-green-500" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
            لا توجد انحرافات مسجلة
          </h3>
          <p className="text-gray-500 dark:text-slate-400 max-w-sm mx-auto">
            جميع العمليات الزراعية تتم ضمن النطاق المعياري المحدد. أداء ممتاز!
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {filteredAlerts.map((alert) => (
            <div
              key={alert.id}
              className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-slate-700 hover:shadow-md transition-shadow relative overflow-hidden group"
            >
              <div
                className={`absolute left-0 top-0 bottom-0 w-1.5 ${alert.status === 'CRITICAL' ? 'bg-red-500' : 'bg-yellow-500'}`}
              ></div>

              <div className="flex justify-between items-start mb-4">
                <div className="flex gap-3">
                  <div
                    className={`p-3 rounded-xl shrink-0 ${alert.status === 'CRITICAL' ? 'bg-red-50 dark:bg-red-900/20' : 'bg-yellow-50 dark:bg-yellow-900/20'}`}
                  >
                    {getStatusIcon(alert.status)}
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900 dark:text-white text-lg leading-tight">
                      {alert.item_name}
                    </h3>
                    <p className="text-gray-500 dark:text-slate-400 text-sm mt-1">
                      {alert.crop_plan_name}
                    </p>
                  </div>
                </div>
                <div
                  className={`px-3 py-1 rounded-full text-xs font-bold tracking-wide ${getStatusStyle(alert.status)}`}
                >
                  {alert.status === 'CRITICAL' ? 'حرج' : 'تحذير'}
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-4 mb-4 grid grid-cols-2 gap-4 border border-gray-100 dark:border-slate-700">
                <div>
                  <div className="text-xs text-gray-500 dark:text-slate-400 font-medium mb-1">
                    الكمية المستهلكة (الفعلي)
                  </div>
                  <div className="text-lg font-bold text-gray-900 dark:text-white font-mono ltr">
                    {Number(alert.actual_qty).toLocaleString()}{' '}
                    <span className="text-sm font-normal text-gray-500">{alert.item_uom}</span>
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 dark:text-slate-400 font-medium mb-1">
                    الكمية القياسية (BOM)
                  </div>
                  <div className="text-lg font-bold text-gray-600 dark:text-slate-300 font-mono ltr">
                    {Number(alert.expected_qty).toLocaleString()}{' '}
                    <span className="text-sm font-normal text-gray-500">{alert.item_uom}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-100 dark:border-slate-700">
                <div className="flex flex-col">
                  <span className="text-xs text-gray-500 dark:text-slate-400">نسبة الانحراف</span>
                  <span
                    className={`font-bold font-mono text-lg ${alert.deviation_pct >= 20 ? 'text-red-600 dark:text-red-400' : 'text-yellow-600 dark:text-yellow-400'} ltr`}
                  >
                    +{alert.deviation_pct}%
                  </span>
                </div>

                <div className="flex items-center gap-6">
                  <div className="text-right hidden sm:block">
                    <div className="text-sm font-medium text-gray-700 dark:text-slate-300">
                      {alert.supervisor_name}
                    </div>
                    <div className="text-xs text-gray-400 dark:text-slate-500">
                      {alert.log_date} • {alert.farm_name}
                    </div>
                  </div>
                  {alert.status === 'CRITICAL' ? (
                    <button
                      title="هذا الانحراف يتجاوز الحد المسموح به، يتطلب اعتماد مالي"
                      className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 shadow-sm transition hover:-translate-y-0.5"
                    >
                      <Briefcase className="w-4 h-4" />
                      طلب اعتماد مالي
                    </button>
                  ) : (
                    <button className="bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-4 py-2 rounded-lg text-sm font-bold transition">
                      تخطِ
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function VarianceAlerts() {
  return (
    <ErrorBoundary>
      <VarianceAlertsPage />
    </ErrorBoundary>
  )
}
