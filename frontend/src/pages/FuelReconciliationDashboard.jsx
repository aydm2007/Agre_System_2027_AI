import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Fuel, ShieldAlert, Waves } from 'lucide-react'

import { api } from '../api/client'
import { useFarmContext } from '../api/farmContext'
import { useSettings } from '../contexts/SettingsContext'
import { useAuth } from '../auth/AuthContext'
import { extractApiError } from '../utils/errorUtils'

const safeArray = (payload) =>
  Array.isArray(payload) ? payload : Array.isArray(payload?.results) ? payload.results : []

function SummaryCard({ icon: Icon, title, value, tone = 'slate' }) {
  const toneClass = {
    amber: 'border-amber-200 bg-amber-50 text-amber-900',
    rose: 'border-rose-200 bg-rose-50 text-rose-900',
    sky: 'border-sky-200 bg-sky-50 text-sky-900',
    slate: 'border-slate-200 bg-white text-slate-900',
  }[tone]

  return (
    <div className={`rounded-xl border p-4 ${toneClass}`}>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium">{title}</div>
          <div className="mt-2 text-2xl font-bold">{value}</div>
        </div>
        <Icon className="h-5 w-5" />
      </div>
    </div>
  )
}

function formatLiters(value) {
  const numeric = Number(value || 0)
  if (Number.isNaN(numeric)) return String(value || '0.0000')
  return numeric.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
}

function PolicyBanner({ isStrictMode, visibilityLevel, costVisibility, varianceBehavior }) {
  return (
    <div
      className="rounded-xl border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-900"
      data-testid="fuel-reconciliation-policy-banner"
    >
      <div className="font-semibold">سياسة مطابقة المحروقات</div>
      <div className="mt-1">
        {isStrictMode
          ? 'الوضع الحازم (STRICT) يعرض مسار المطابقة الكامل لدورة المحروقات، وحالة الاعتماد المالي والتسعير.'
          : 'الوضع المبسط (SIMPLE) يبقى مخصصاً للعمليات: موقف الآلات، الفعلي مقابل المتوقع، وحالات الشذوذ مع إخفاء التكاليف التفصيلية.'}
      </div>
      <div className="mt-1">
        مستوى الرؤية: {visibilityLevel} | التكاليف: {costVisibility} | سلوك الفروقات:{' '}
        {varianceBehavior}
      </div>
    </div>
  )
}

function SeverityBadge({ severity }) {
  const className =
    {
      critical: 'bg-rose-100 text-rose-800',
      warning: 'bg-amber-100 text-amber-800',
      normal: 'bg-emerald-100 text-emerald-800',
    }[severity] || 'bg-slate-100 text-slate-800'
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${className}`}>
      {severity}
    </span>
  )
}

function FuelSmartCard({ row, showAmounts, strictTrace }) {
  if (!row) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">
        اختر سجل خزان لمطالعة بطاقة مطابقة المحروقات الذكية.
      </div>
    )
  }

  const flags = Object.entries(row.flags || {}).filter(([, active]) => Boolean(active))

  return (
    <div
      className="rounded-2xl border border-slate-200 bg-white p-5"
      data-testid="fuel-reconciliation-smart-card"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            بطاقة مطابقة المحروقات الذكية
          </div>
          <h2 className="mt-1 text-xl font-bold text-slate-900">{row.tank}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {row.farm_name} · {row.measurement_method} · {row.supervisor}
          </p>
        </div>
        <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
          <div>تنبيه الوقود: {row.fuel_alert_status}</div>
          <div>الحالة: {row.reconciliation_state}</div>
          <div>الرؤية: {row.visibility_level}</div>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            موقف الخزان (Tank posture)
          </div>
          <div className="mt-2 text-sm text-slate-800">رمز الخزان: {row.tank_code || 'N/A'}</div>
          <div className="mt-1 text-sm text-slate-800">الطريقة: {row.measurement_method}</div>
          <div className="mt-1 text-sm text-slate-800">
            تاريخ القراءة: {row.reading_date || 'N/A'}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            المتوقع مقابل الفعلي
          </div>
          <div className="mt-2 text-sm text-slate-800">
            الفعلي: {showAmounts ? `${formatLiters(row.actual_liters)} لتر` : 'ملخص حسب السياسة'}
          </div>
          <div className="mt-1 text-sm text-slate-800">
            المتوقع: {showAmounts ? `${formatLiters(row.expected_liters)} لتر` : 'مسار محكوم'}
          </div>
          <div className="mt-1 text-sm text-slate-800">
            الفارق (Variance): {formatLiters(row.variance_liters)} لتر
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            المخاطر والإنذارات
          </div>
          <div className="mt-2 text-sm text-slate-800">الخطورة: {row.variance_severity}</div>
          <div className="mt-1 text-sm text-slate-800">
            المؤشرات: {flags.length ? flags.map(([name]) => name).join(', ') : 'لا يوجد'}
          </div>
          <div className="mt-1 text-sm text-slate-800 break-all">
            سجل الآلة: {row.matching_daily_log_id || 'غير مرتبط بآلة'}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            أثر المسار المالي
          </div>
          <div className="mt-2 text-sm text-slate-800">السياسة: {row.cost_display_mode}</div>
          <div className="mt-1 text-sm text-slate-800">عدد التنبيهات: {row.alerts_count}</div>
          <div className="mt-1 text-sm text-slate-800">
            {strictTrace
              ? 'تتبع الخزينة والمخزون ظاهر للمالية (Governed mode).'
              : 'مسار الخزينة مخفي في الوضع المبسط.'}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function FuelReconciliationDashboard() {
  const { selectedFarmId } = useFarmContext()
  const { isStrictMode, costVisibility, visibilityLevel, varianceBehavior, treasuryVisibility } =
    useSettings()
  const { isAdmin, is_superuser: isSuperuser, hasPermission, hasFarmRole } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [rows, setRows] = useState([])
  const [summary, setSummary] = useState(null)
  const [selectedId, setSelectedId] = useState(null)

  const strictTrace =
    isStrictMode &&
    (treasuryVisibility !== 'hidden' ||
      isAdmin ||
      isSuperuser ||
      hasPermission?.('finance.can_post_treasury') ||
      hasPermission?.('finance.can_approve_finance_request') ||
      hasFarmRole?.('محاسب المزرعة') ||
      hasFarmRole?.('المدير المالي للمزرعة') ||
      hasFarmRole?.('رئيس الحسابات') ||
      hasFarmRole?.('محاسب القطاع') ||
      hasFarmRole?.('رئيس حسابات القطاع'))

  const load = useCallback(async () => {
    if (!selectedFarmId) {
      setRows([])
      setSummary(null)
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await api.get('/fuel-reconciliation/', {
        params: { farm_id: selectedFarmId },
      })
      const nextRows = safeArray(response.data)
      setRows(nextRows)
      setSummary(response.data.summary || null)
      setSelectedId((current) => current || nextRows[0]?.id || null)
    } catch (loadError) {
      setError(extractApiError(loadError, 'Failed to load fuel reconciliation dashboard.'))
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId])

  useEffect(() => {
    load()
  }, [load])

  const selectedRow = useMemo(
    () => rows.find((entry) => entry.id === selectedId) || rows[0] || null,
    [rows, selectedId],
  )

  const showAmounts = costVisibility !== 'ratios_only'

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-slate-900">مطابقة المحروقات (Fuel Reconciliation)</h1>
        <p className="text-sm text-slate-500">
          مسار واحد للحقيقة عبر الوضعين `SIMPLE` و `STRICT`: إظهار الشذوذ التشغيلي بالحقل،
          وظهور أثر المطابقة الكلي والتكاليف للمالية.
        </p>
      </div>

      <PolicyBanner
        isStrictMode={isStrictMode}
        visibilityLevel={visibilityLevel}
        costVisibility={costVisibility}
        varianceBehavior={varianceBehavior}
      />

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div
          className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500"
          data-testid="fuel-reconciliation-loading"
        >
          جاري تحميل لوحة مطابقة المحروقات...
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard icon={Fuel} title="سجلات المحروقات" value={summary?.logs_count || 0} />
        <SummaryCard
          icon={AlertTriangle}
          title="شذوذ مفتوح"
          value={summary?.open_anomalies || 0}
          tone="amber"
        />
        <SummaryCard
          icon={ShieldAlert}
          title="سجلات حرجة"
          value={summary?.critical_logs || 0}
          tone="rose"
        />
        <SummaryCard
          icon={Waves}
          title="معايرة مفقودة"
          value={summary?.missing_calibration_logs || 0}
          tone="sky"
        />
      </div>

      {!loading ? <FuelSmartCard row={selectedRow} showAmounts={showAmounts} strictTrace={strictTrace} /> : null}

      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              سجلات المحروقات وموقف المطابقة
            </h2>
            <p className="text-sm text-slate-500">
              موقف الاستهلاك المربوط بالآلات، قراءات العداد أو العصا المترية، والتفاوت على مستوى المزرعة.
            </p>
          </div>
          <div className="text-sm text-slate-500">
            بانتظار المراجعة: {summary?.pending_reconciliation_logs || 0}
          </div>
        </div>

        {!loading ? (
          <div className="overflow-x-auto">
          <table
            className="min-w-full divide-y divide-slate-200"
            data-testid="fuel-reconciliation-table"
          >
            <thead>
              <tr className="text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">الخزان / المستودع</th>
                <th className="px-3 py-2">الطريقة</th>
                <th className="px-3 py-2">الخطورة</th>
                <th className="px-3 py-2">الحالة</th>
                {showAmounts ? (
                  <th className="px-3 py-2" data-testid="fuel-reconciliation-amount-column">
                    المتوقع مقابل الفعلي
                  </th>
                ) : null}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
              {rows.map((row) => (
                <tr
                  key={row.id}
                  className={`cursor-pointer ${selectedRow?.id === row.id ? 'bg-orange-50' : 'hover:bg-slate-50'}`}
                  onClick={() => setSelectedId(row.id)}
                >
                  <td className="px-3 py-3">
                    <div className="font-medium text-slate-900">{row.tank}</div>
                    <div className="text-xs text-slate-500">{row.farm_name}</div>
                  </td>
                  <td className="px-3 py-3">{row.measurement_method}</td>
                  <td className="px-3 py-3">
                    <SeverityBadge severity={row.variance_severity} />
                  </td>
                  <td className="px-3 py-3">
                    <div>{row.reconciliation_state}</div>
                    <div className="text-xs text-slate-500">{row.fuel_alert_status}</div>
                  </td>
                  {showAmounts ? (
                    <td className="px-3 py-3 font-mono text-xs">
                      <div>المتوقع: {formatLiters(row.expected_liters)} لتر</div>
                      <div className="text-slate-500">
                        الفعلي: {formatLiters(row.actual_liters)} لتر
                      </div>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        ) : null}

        {!loading && rows.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
            لا توجد سجلات محروقات متاحة للمزرعة المحددة.
          </div>
        ) : null}

        {!loading ? (
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
            <div className="font-semibold">تلميحات التقرير</div>
            <div className="mt-2 grid gap-2 md:grid-cols-3">
              <div className="rounded-lg bg-white px-3 py-2">
                سجلات تحذيرية: {summary?.warning_logs || 0}
              </div>
              <div className="rounded-lg bg-white px-3 py-2">
                سجلات حرجة: {summary?.critical_logs || 0}
              </div>
              <div className="rounded-lg bg-white px-3 py-2">عرض التكاليف: {costVisibility}</div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
