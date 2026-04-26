import { useEffect, useState } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { api, TreeCensusVarianceAlerts, BiologicalAssetCohorts } from '../api/client'
import { useToast } from '../components/ToastProvider'
import { useTreeCensusOffline, IDB_KEYS } from '../hooks/useTreeCensusOffline'

const formatNumber = (num, decimals = 0) => {
  if (num == null) return '-'
  return Number(num).toLocaleString('ar-EG', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

const formatDate = (dateString, withTime = false) => {
  if (!dateString) return '-'
  const d = new Date(dateString)
  if (isNaN(d)) return dateString
  const options = { year: 'numeric', month: 'short', day: 'numeric' }
  if (withTime) {
    options.hour = '2-digit'
    options.minute = '2-digit'
  }
  return new Intl.DateTimeFormat('ar-EG', options).format(d)
}

export default function TreeVarianceAlertsPage() {
  const toast = useToast()

  // [Agri-Guardian] Offline-First Infrastructure (AGENTS.md §18)
  const { isOnline, isOffline, fetchWithCache } = useTreeCensusOffline()

  const [farms, setFarms] = useState([])
  const [locations, setLocations] = useState([])

  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [filters, setFilters] = useState({
    farm: '',
    location_id: '',
    status: 'PENDING',
  })

  // [AGRI-GUARDIAN] Resolve Modal State
  const [resolveModal, setResolveModal] = useState({
    isOpen: false,
    alert: null,
    cohorts: [],
    loadingCohorts: false,
    form: {
      cohort_id: '',
      create_ratoon: false,
      notes: '',
    },
    submitting: false,
    error: '',
  })

  // [Offline-First] Cache farms with IndexedDB fallback
  useEffect(() => {
    const fetchBaseData = async () => {
      const result = await fetchWithCache(IDB_KEYS.FARMS, async () => {
        const res = await api.get('/farms/')
        return res.data?.results || res.data || []
      })
      if (result.data) setFarms(result.data)
    }
    fetchBaseData()
  }, [fetchWithCache])

  // [Offline-First] Cache locations per farm with IndexedDB fallback
  useEffect(() => {
    const fetchDependencies = async () => {
      if (!filters.farm) {
        setLocations([])
        return
      }
      const cacheKey = `${IDB_KEYS.LOCATIONS_PREFIX}${filters.farm}`
      const result = await fetchWithCache(cacheKey, async () => {
        const res = await api.get('/locations/', { params: { farm_id: filters.farm } })
        return res.data?.results || res.data || []
      })
      if (result.data) setLocations(result.data)
      else setLocations([])
    }
    fetchDependencies()
  }, [filters.farm, fetchWithCache])

  // [Offline-First] Cache alerts with IndexedDB fallback
  const fetchAlerts = async () => {
    setLoading(true)
    setError('')
    const cacheKey = `${IDB_KEYS.ALERTS_PREFIX}${filters.farm}-${filters.location_id}-${filters.status}`

    const result = await fetchWithCache(cacheKey, async () => {
      const resp = await TreeCensusVarianceAlerts.list(filters)
      return resp.data?.results || resp.data || []
    })

    if (result.data) setAlerts(result.data)
    else setAlerts([])
    if (result.error) setError(result.error)
    setLoading(false)
  }

  useEffect(() => {
    fetchAlerts()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters])

  const handleFilterChange = (e) => {
    const { name, value } = e.target
    setFilters((prev) => ({ ...prev, [name]: value }))
  }

  // [AGENTS.md §5] Financial mutations MUST NOT be queued offline.
  // Resolve = asset write-off = financial mutation → live server required.
  const openResolveModal = async (alert) => {
    if (!isOnline) {
      toast.error('تسوية الفاقد تتطلب اتصالاً بالخادم. لا يمكن اعتماد الإعدام في وضع عدم الاتصال.')
      return
    }

    setResolveModal({
      isOpen: true,
      alert,
      cohorts: [],
      loadingCohorts: true,
      form: { cohort_id: '', create_ratoon: false, notes: '' },
      submitting: false,
      error: '',
    })

    try {
      // Fetch cohorts for this specific farm + location + crop
      const res = await BiologicalAssetCohorts.list({
        farm: alert.farm || alert.farm_id,
        location: alert.location || alert.location_id,
        crop: alert.crop || alert.crop_id,
        status: 'ACTIVE', // Ideally we only deduct from ACTIVE or RENEWING
      })
      const foundCohorts = res.data?.results || res.data || []

      setResolveModal((prev) => ({
        ...prev,
        cohorts: foundCohorts,
        loadingCohorts: false,
        // Auto-select if only 1 active cohort exists
        form: {
          ...prev.form,
          cohort_id: foundCohorts.length === 1 ? foundCohorts[0].id : '',
        },
      }))
    } catch (err) {
      setResolveModal((prev) => ({
        ...prev,
        loadingCohorts: false,
        error: 'فشل في جلب الدفعات الشجرية المتاحة.',
      }))
    }
  }

  const closeResolveModal = () => {
    setResolveModal((prev) => ({ ...prev, isOpen: false, alert: null }))
  }

  const submitResolve = async () => {
    if (!resolveModal.form.cohort_id) {
      setResolveModal((prev) => ({ ...prev, error: 'يجب اختيار الدفعة الشجرية أولاً.' }))
      return
    }

    if (
      !window.confirm('هل أنت متأكد من اعتماد الفاقد؟ سيتم خصم الأشجار من الدفعة المختارة إدارياً.')
    )
      return

    setResolveModal((prev) => ({ ...prev, submitting: true, error: '' }))
    try {
      const idempotencyKey = uuidv4()
      await TreeCensusVarianceAlerts.resolve(
        resolveModal.alert.id,
        resolveModal.form,
        idempotencyKey,
      )
      toast.success('تمت الموافقة واعتماد التسوية بنجاح')
      closeResolveModal()
      fetchAlerts()
    } catch (err) {
      setResolveModal((prev) => ({
        ...prev,
        submitting: false,
        error: err.response?.data?.detail || 'فشل في اعتماد التسوية',
      }))
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-red-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 p-6 space-y-6">
      {/* [Offline-First] Offline alert banner */}
      {isOffline && (
        <div className="bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-xl p-4 flex items-center gap-3">
          <span className="w-3 h-3 rounded-full bg-amber-500 animate-pulse flex-shrink-0"></span>
          <div>
            <p className="text-sm font-bold text-amber-800 dark:text-amber-300">
              وضع عدم الاتصال (Offline Mode)
            </p>
            <p className="text-xs text-amber-600 dark:text-amber-400">
              يتم عرض البيانات المخبأة. اعتماد الإعدام يتطلب اتصالاً بالخادم.
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-col gap-2">
          <h1 className="text-4xl font-extrabold bg-gradient-to-r from-red-600 via-orange-600 to-amber-500 bg-clip-text text-transparent flex items-center gap-3">
            <svg
              className="w-10 h-10 text-red-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            الرقابة: تنبيهات العجز والفقد الشجري
            {isOffline && (
              <span className="text-xs px-2.5 py-1 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-400 rounded-full font-bold flex items-center gap-2 border border-amber-200 dark:border-amber-800">
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
                Offline
              </span>
            )}
          </h1>
          <p className="text-gray-500 dark:text-slate-400">
            مراجعة تناقضات أعداد الأشجار المرفوعة من الميدان في السجلات اليومية (يُتطلب اعتماد إداري
            لتسويتها كإعدامات رسمية).
          </p>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-gray-100 dark:border-slate-700 p-5">
        <div className="grid gap-4 md:grid-cols-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-600 dark:text-slate-400">
              المزرعة
            </label>
            <select
              name="farm"
              value={filters.farm}
              onChange={handleFilterChange}
              className="rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-3 py-2 text-sm focus:ring-red-500"
            >
              <option value="">-- الكل --</option>
              {farms.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-600 dark:text-slate-400">
              الموقع الميداني
            </label>
            <select
              name="location_id"
              value={filters.location_id}
              onChange={handleFilterChange}
              disabled={!filters.farm}
              className="rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-3 py-2 text-sm disabled:opacity-50 focus:ring-red-500"
            >
              <option value="">-- الكل --</option>
              {locations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-600 dark:text-slate-400">
              حالة التنبيه
            </label>
            <select
              name="status"
              value={filters.status}
              onChange={handleFilterChange}
              className="rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-3 py-2 text-sm focus:ring-red-500"
            >
              <option value="">-- جميع الحالات --</option>
              <option value="PENDING">معلق - بانتظار مراجعة الإدارة</option>
              <option value="RESOLVED">مغلق - تم اعتماد التسوية</option>
            </select>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 shadow-sm overflow-hidden min-h-[300px]">
        {loading ? (
          <div className="p-8 flex justify-center text-red-600 pt-20">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-red-600"></div>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">{error}</div>
        ) : alerts.length === 0 ? (
          <div className="p-16 flex flex-col items-center justify-center text-gray-400 dark:text-slate-500">
            <svg
              className="w-16 h-16 mb-4 opacity-70"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.5"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-lg font-medium">الدفتر مطابق ميدانياً. لا توجد تنبيهات فاقد شجري.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-right text-sm">
              <thead className="bg-red-50 dark:bg-red-900/10 text-red-800 dark:text-red-300 border-b border-red-100 dark:border-red-900/30">
                <tr>
                  <th className="px-5 py-4 font-semibold">تاريخ السجل اليومي</th>
                  <th className="px-5 py-4 font-semibold">الموقع والمحصول</th>
                  <th className="px-5 py-4 font-semibold">كمية العجز (أشجار)</th>
                  <th className="px-5 py-4 font-semibold">السبب الميداني المذكور</th>
                  <th className="px-5 py-4 font-semibold">الحالة</th>
                  <th className="px-5 py-4 font-semibold text-center">الإجراء</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-slate-700/60">
                {alerts.map((alert) => (
                  <tr
                    key={alert.id}
                    className="hover:bg-red-50/20 dark:hover:bg-slate-700/30 transition-colors"
                  >
                    <td className="px-5 py-4 text-gray-600 dark:text-slate-400">
                      {formatDate(alert.log_date)}
                      <div className="text-[10px] text-gray-400 mt-1">
                        أُنشئ: {formatDate(alert.created_at, true)}
                      </div>
                    </td>
                    <td className="px-5 py-4 text-gray-900 dark:text-white">
                      <div className="font-semibold">{alert.location_name || '-'}</div>
                      <div className="text-xs text-slate-500">{alert.crop_name || '-'}</div>
                    </td>
                    <td className="px-5 py-4">
                      <span className="font-bold text-red-600 bg-red-100 dark:bg-red-900/30 px-2.5 py-1 rounded-full text-base">
                        - {formatNumber(alert.missing_quantity)}
                      </span>
                    </td>
                    <td
                      className="px-5 py-4 max-w-[200px] truncate text-gray-600 dark:text-slate-400"
                      title={alert.reason}
                    >
                      {alert.reason || 'بدون سبب'}
                    </td>
                    <td className="px-5 py-4">
                      {alert.status === 'PENDING' ? (
                        <span className="text-xs bg-amber-100 text-amber-800 border border-amber-200 px-2 py-1 rounded-full font-semibold">
                          بانتظار المراجعة
                        </span>
                      ) : (
                        <span
                          className="text-xs bg-emerald-100 text-emerald-800 border border-emerald-200 px-2 py-1 rounded-full font-semibold"
                          title={`بواسطة ${alert.resolved_by_name} في ${formatDate(alert.resolved_at, true)}`}
                        >
                          إعدام معتمد
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-4 flex justify-center">
                      {alert.status === 'PENDING' && (
                        <button
                          onClick={() => openResolveModal(alert)}
                          disabled={isOffline}
                          title={isOffline ? 'يتطلب اتصالاً بالخادم' : 'اعتماد تسوية الفاقد'}
                          className={`px-4 py-2 rounded-lg text-xs font-bold transition-transform active:scale-95 shadow-lg ${
                            isOffline
                              ? 'bg-gray-400 text-gray-200 cursor-not-allowed shadow-none'
                              : 'text-white bg-red-600 hover:bg-red-700 shadow-red-500/20'
                          }`}
                        >
                          {isOffline ? '⛔ يتطلب اتصالاً' : 'اعتماد الإعدام'}
                        </button>
                      )}
                      {alert.status === 'RESOLVED' && (
                        <span className="text-emerald-600">
                          <svg
                            className="w-6 h-6"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth="2"
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* --- Resolve Modal --- */}
      {resolveModal.isOpen && resolveModal.alert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm rtl">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-lg border border-gray-100 dark:border-slate-700 overflow-hidden transform transition-all">
            <div className="px-6 py-4 border-b border-gray-100 dark:border-slate-700 flex justify-between items-center bg-gray-50 dark:bg-slate-800/50">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <svg
                  className="w-5 h-5 text-red-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                اعتماد إعدام أشجار
              </h3>
              <button
                onClick={closeResolveModal}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-5">
              {/* Alert Summary */}
              <div className="bg-red-50 dark:bg-red-900/10 p-4 rounded-xl border border-red-100 dark:border-red-900/30 flex gap-4">
                <div className="flex-1">
                  <div className="text-sm text-gray-500 dark:text-gray-400">التنبيه</div>
                  <div className="font-semibold text-gray-900 dark:text-white mt-1">
                    {resolveModal.alert.location_name} - {resolveModal.alert.crop_name}
                  </div>
                </div>
                <div className="text-left">
                  <div className="text-sm text-gray-500 dark:text-gray-400">الكمية המُعدمة</div>
                  <div className="font-bold text-red-600 text-xl font-mono">
                    {formatNumber(resolveModal.alert.missing_quantity)} شجرة
                  </div>
                </div>
              </div>

              {/* Form Areas */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1.5">
                    الدفعة الشجرية المستهدفة بالخصم <span className="text-red-500">*</span>
                  </label>
                  {resolveModal.loadingCohorts ? (
                    <div className="animate-pulse h-10 bg-gray-100 dark:bg-slate-700 rounded-lg"></div>
                  ) : (
                    <select
                      value={resolveModal.form.cohort_id}
                      onChange={(e) =>
                        setResolveModal((prev) => ({
                          ...prev,
                          form: { ...prev.form, cohort_id: e.target.value },
                        }))
                      }
                      className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-3 py-2 text-sm focus:ring-red-500"
                    >
                      <option value="">-- اختر الدفعة --</option>
                      {resolveModal.cohorts.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.batch_name} ({formatNumber(c.quantity)} شجرة متوفرة)
                        </option>
                      ))}
                    </select>
                  )}
                  {resolveModal.cohorts.length === 0 && !resolveModal.loadingCohorts && (
                    <p className="mt-1.5 text-xs text-amber-600 dark:text-amber-400 font-medium">
                      ⚠️ لا توجد دفعات نشطة متاحة لهذا المحصول في هذا الموقع.
                    </p>
                  )}
                </div>

                {/* Banner: Banana Ratooning check based on crop metadata - here we show it globally for any perennial or just show the toggle */}
                <div className="pt-2 border-t border-gray-100 dark:border-slate-700">
                  <label className="flex items-start gap-3 cursor-pointer p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors border border-transparent hover:border-gray-200 dark:hover:border-slate-600">
                    <div className="relative flex items-center mt-0.5">
                      <input
                        type="checkbox"
                        checked={resolveModal.form.create_ratoon}
                        onChange={(e) =>
                          setResolveModal((prev) => ({
                            ...prev,
                            form: { ...prev.form, create_ratoon: e.target.checked },
                          }))
                        }
                        className="peer sr-only"
                      />
                      <div className="block w-10 h-6 bg-gray-200 dark:bg-slate-600 rounded-full peer-checked:bg-emerald-500 transition-colors"></div>
                      <div className="absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform peer-checked:translate-x-4"></div>
                    </div>
                    <div>
                      <span className="block text-sm font-semibold text-gray-900 dark:text-white">
                        إنشاء دفعة خلفة (Ratoon)
                      </span>
                      <span className="block text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                        سيتم تخصيص عدد {formatNumber(resolveModal.alert.missing_quantity)} كشجرة
                        مجَدّدة (خلفة) تابعة للدفعة الأصلية تلقائياً.
                      </span>
                    </div>
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1.5">
                    ملاحظات مراجعة (اختياري)
                  </label>
                  <textarea
                    value={resolveModal.form.notes}
                    onChange={(e) =>
                      setResolveModal((prev) => ({
                        ...prev,
                        form: { ...prev.form, notes: e.target.value },
                      }))
                    }
                    className="w-full rounded-lg border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 dark:text-white px-3 py-2 text-sm focus:ring-red-500 min-h-[80px]"
                    placeholder="سبب القبول، أو ملاحظات مدقق الحسابات..."
                  />
                </div>
              </div>

              {resolveModal.error && (
                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm border border-red-200 dark:border-red-900/50">
                  {resolveModal.error}
                </div>
              )}
            </div>

            <div className="px-6 py-4 bg-gray-50 dark:bg-slate-800/50 border-t border-gray-100 dark:border-slate-700 flex justify-end gap-3">
              <button
                type="button"
                onClick={closeResolveModal}
                disabled={resolveModal.submitting}
                className="px-4 py-2 text-sm font-semibold text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 transition-colors"
              >
                إلغاء
              </button>
              <button
                type="button"
                onClick={submitResolve}
                disabled={resolveModal.submitting || !resolveModal.form.cohort_id}
                className="px-5 py-2 text-sm font-semibold text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
              >
                {resolveModal.submitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    جاري الاعتماد...
                  </>
                ) : (
                  'تأكيد الخصم والإعدام'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
