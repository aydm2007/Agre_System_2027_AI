import { useState, useEffect, useMemo, useCallback } from 'react'
import { api } from '../../api/client'
import { toast } from 'react-hot-toast'
import { useFarmContext } from '../../api/farmContext.jsx'
import { Calendar, Lock, Unlock, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react'

// ─────────────────────────────────────────────────────────────────────────────
// LOADING SKELETON
// ─────────────────────────────────────────────────────────────────────────────
const LoadingSkeleton = () => (
  <div className="app-page">
    <div className="animate-pulse space-y-6 max-w-7xl mx-auto">
      <div className="h-16 bg-gray-200 dark:bg-white/5 rounded-2xl" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-28 bg-gray-200 dark:bg-white/5 rounded-2xl" />
        ))}
      </div>
      <div className="h-64 bg-gray-200 dark:bg-white/5 rounded-xl" />
    </div>
  </div>
)

// ─────────────────────────────────────────────────────────────────────────────
// ERROR STATE
// ─────────────────────────────────────────────────────────────────────────────
const ErrorState = ({ error, onRetry }) => (
  <div className="app-page flex items-center justify-center">
    <div className="text-center space-y-4">
      <div className="w-16 h-16 rounded-full bg-rose-500/20 flex items-center justify-center mx-auto">
        <AlertCircle className="w-8 h-8 text-rose-400" />
      </div>
      <h2 className="text-xl font-bold text-slate-900 dark:text-white">
        حدث خطأ أثناء تحميل البيانات
      </h2>
      <p className="text-slate-600 dark:text-white/50">{error}</p>
      <button
        onClick={onRetry}
        className="px-6 py-3 rounded-xl bg-emerald-600 text-white font-bold hover:bg-emerald-500 transition-all flex items-center gap-2 mx-auto"
      >
        <RefreshCw className="w-4 h-4" />
        إعادة المحاولة
      </button>
    </div>
  </div>
)

// ─────────────────────────────────────────────────────────────────────────────
// STAT CARD
// ─────────────────────────────────────────────────────────────────────────────
const StatCard = ({ title, value, icon: Icon, color }) => (
  <div
    className={`rounded-2xl border border-${color}-500/30 bg-gradient-to-br from-${color}-500/20 to-${color}-500/5 backdrop-blur-xl p-5`}
  >
    <div className="flex items-center gap-3">
      <div className={`p-2.5 bg-${color}-500/20 rounded-xl border border-${color}-500/30`}>
        <Icon className={`w-6 h-6 text-${color}-400`} />
      </div>
      <div>
        <p className={`text-${color}-400/70 text-sm font-medium`}>{title}</p>
        <h2 className="text-2xl font-black text-slate-900 dark:text-white mt-0.5">{value}</h2>
      </div>
    </div>
  </div>
)

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
export default function FiscalYearList() {
  const { selectedFarmId, farms } = useFarmContext()
  const [fiscalYears, setFiscalYears] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchFiscalYears = useCallback(async () => {
    if (!selectedFarmId) {
      setLoading(false)
      return
    }
    try {
      setLoading(true)
      setError(null)
      const res = await api.get('/finance/fiscal-years/', {
        params: { farm: selectedFarmId },
      })
      setFiscalYears(res.data.results || res.data || [])
    } catch (err) {
      console.error('FiscalYear fetch error:', err)
      setError('تعذر تحميل السنوات المالية')
      toast.error('فشل تحميل السنوات المالية')
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId])

  useEffect(() => {
    fetchFiscalYears()
  }, [fetchFiscalYears])

  // Stats
  const stats = useMemo(() => {
    const open = fiscalYears.filter((fy) => !fy.is_closed).length
    const closed = fiscalYears.filter((fy) => fy.is_closed).length
    return { open, closed, total: fiscalYears.length }
  }, [fiscalYears])

  const selectedFarm = farms?.find((f) => String(f.id) === String(selectedFarmId))

  if (!selectedFarmId) {
    return (
      <div dir="rtl" className="app-page">
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-8 text-center max-w-lg mx-auto mt-20">
          <AlertCircle className="w-16 h-16 text-amber-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-amber-900 dark:text-white mb-2">اختر مزرعة</h2>
          <p className="text-slate-700 dark:text-white/60">
            يرجى اختيار مزرعة من الشريط العلوي لعرض السنوات المالية
          </p>
        </div>
      </div>
    )
  }

  if (loading) return <LoadingSkeleton />
  if (error) return <ErrorState error={error} onRetry={fetchFiscalYears} />

  return (
    <div data-testid="finance-fiscal-years-page" dir="rtl" className="app-page space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-black tracking-tight bg-gradient-to-r from-indigo-600 dark:from-indigo-400 to-purple-500 dark:to-purple-200 bg-clip-text text-transparent">
            السنوات المالية
          </h1>
          <p className="text-gray-500 dark:text-zinc-500 font-medium mt-1">
            إدارة السنوات المالية - {selectedFarm?.name || 'المزرعة'}
          </p>
        </div>
        <button
          onClick={fetchFiscalYears}
          className="p-3 rounded-xl bg-white/80 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-700 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-white dark:hover:bg-white/10 transition-all"
          aria-label="تحديث البيانات"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard title="سنوات مفتوحة" value={stats.open} icon={Unlock} color="emerald" />
        <StatCard title="سنوات مغلقة" value={stats.closed} icon={Lock} color="rose" />
        <StatCard title="إجمالي السنوات" value={stats.total} icon={Calendar} color="blue" />
      </div>

      {/* Fiscal Years Table */}
      <div className="app-panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-end">
            <thead className="bg-slate-100/90 dark:bg-white/5 text-slate-600 dark:text-white/40 font-bold border-b border-slate-200 dark:border-white/10">
              <tr>
                <th className="px-6 py-4">السنة</th>
                <th className="px-6 py-4">تاريخ البدء</th>
                <th className="px-6 py-4">تاريخ الانتهاء</th>
                <th className="px-6 py-4">الحالة</th>
              </tr>
            </thead>
            <tbody>
              {fiscalYears.length === 0 ? (
                <tr>
                  <td colSpan="4" className="py-16 text-center text-slate-500 dark:text-white/30">
                    <Calendar className="w-12 h-12 mx-auto mb-4 opacity-30" />
                    لا توجد سنوات مالية مسجلة لهذه المزرعة
                    <div className="mt-3 text-xs text-slate-500 dark:text-white/40">
                      يتم إنشاء السنوات المالية تلقائياً عند تسجيل أول معاملة مالية.
                    </div>
                  </td>
                </tr>
              ) : (
                fiscalYears.map((fy) => (
                  <tr
                    key={fy.id}
                    className="border-t border-slate-200/70 dark:border-white/5 hover:bg-slate-100/70 dark:hover:bg-white/5 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <span className="text-lg font-bold text-slate-900 dark:text-white">
                        {fy.year}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-600 dark:text-white/50">
                      {fy.start_date
                        ? new Date(fy.start_date).toLocaleDateString('ar-SA', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                          })
                        : '-'}
                    </td>
                    <td className="px-6 py-4 text-slate-600 dark:text-white/50">
                      {fy.end_date
                        ? new Date(fy.end_date).toLocaleDateString('ar-SA', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                          })
                        : '-'}
                    </td>
                    <td className="px-6 py-4">
                      {fy.is_closed ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                          <Lock className="w-3.5 h-3.5" />
                          مغلقة
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          <CheckCircle className="w-3.5 h-3.5" />
                          مفتوحة
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Info Notice — Fiscal Close Doctrine */}
      <div className="rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-indigo-500/20 rounded-xl">
            <AlertCircle className="w-6 h-6 text-indigo-400" />
          </div>
          <div>
            <h3 className="font-bold text-indigo-400 mb-1">دورة الإغلاق المالي</h3>
            <p className="text-slate-700 dark:text-white/60 text-sm leading-relaxed">
              وفقاً لمعايير Agri-Guardian، دورة الإغلاق تمر بثلاث مراحل: مفتوح ← إغلاق مبدئي ← إغلاق
              نهائي. بعد الإغلاق النهائي لا يمكن إضافة أي معاملات، ويتم أي تصحيح عبر قيود عكسية في
              فترة مفتوحة.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
