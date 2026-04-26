import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Boxes, Landmark, SunMedium } from 'lucide-react'

import { api } from '../api/client'
import { useFarmContext } from '../api/farmContext'
import { useSettings } from '../contexts/SettingsContext'
import { useAuth } from '../auth/AuthContext'
import { extractApiError } from '../utils/errorUtils'

const safeArray = (payload) =>
  Array.isArray(payload) ? payload : Array.isArray(payload?.results) ? payload.results : []

function formatMoney(value) {
  const numeric = Number(value || 0)
  if (Number.isNaN(numeric)) return String(value || '0.00')
  return numeric.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function SummaryCard({ icon: Icon, title, value, tone = 'slate' }) {
  const toneClass = {
    amber: 'border-amber-200 bg-amber-50 text-amber-900',
    rose: 'border-rose-200 bg-rose-50 text-rose-900',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-900',
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

function HealthBadge({ status }) {
  const className =
    {
      GREEN: 'bg-emerald-100 text-emerald-800',
      WARNING: 'bg-amber-100 text-amber-800',
      CRITICAL: 'bg-rose-100 text-rose-800',
    }[status] || 'bg-slate-100 text-slate-800'
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${className}`}>
      {status}
    </span>
  )
}

function PolicyBanner({ fixedAssetMode, isStrictMode, visibilityLevel, costVisibility }) {
  return (
    <div
      className="rounded-xl border border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-900"
      data-testid="fixed-assets-policy-banner"
    >
      <div className="font-semibold">سياسة الأصول الثابتة</div>
      <div className="mt-1">
        {fixedAssetMode === 'tracking_only'
          ? 'وضع (تتبع فقط) يُبقي الأصول مرئية تشغيلياً دون فرض دورة رسملة مالية كاملة.'
          : 'وضع الرسملة الكاملة يعرض القيمة الدفترية، موقف الإهلاك، وضوابط الرسملة للأصل المعني.'}
      </div>
      <div className="mt-1">
        الوضع: {isStrictMode ? 'صارم (STRICT)' : 'مبسط (SIMPLE)'} | الرؤية: {visibilityLevel} | مستوى التكاليف:{' '}
        {costVisibility}
      </div>
    </div>
  )
}

function AssetSmartCard({ asset, showAmounts, canSeeCapitalization }) {
  if (!asset) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">
        Select an asset row to inspect the fixed-asset smart card.
      </div>
    )
  }

  return (
    <div
      className="rounded-2xl border border-slate-200 bg-white p-5"
      data-testid="fixed-assets-smart-card"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Fixed asset smart card
          </div>
          <h2 className="mt-1 text-xl font-bold text-slate-900">{asset.name}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {asset.farm_name} · {asset.category} · {asset.asset_type}
          </p>
        </div>
        <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
          <div>Status: {asset.status}</div>
          <div>Capitalization: {asset.capitalization_state}</div>
          <div>Health: {asset.health_status}</div>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            التتبع
          </div>
          <div className="mt-2 text-sm text-slate-800">الكود: {asset.code || 'N/A'}</div>
          <div className="mt-1 text-sm text-slate-800">
            تاريخ الشراء: {asset.purchase_date || 'N/A'}
          </div>
          <div className="mt-1 text-sm text-slate-800">
            العمر التقديري: {asset.useful_life_years} سنوات
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            التشغيل
          </div>
          <div className="mt-2 text-sm text-slate-800">الصحة: {asset.health_status}</div>
          <div className="mt-1 text-sm text-slate-800">
            معدل الإهلاك: {asset.depreciation_percentage}%
          </div>
          <div className="mt-1 text-sm text-slate-800">
            تكلفة التشغيل (ساعة):{' '}
            {showAmounts ? formatMoney(asset.operational_cost_per_hour) : 'ملخص حسب السياسة'}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            سجل الأصل
          </div>
          <div className="mt-2 text-sm text-slate-800">الوضع: {asset.fixed_asset_mode}</div>
          <div className="mt-1 text-sm text-slate-800">الرؤية: {asset.visibility_level}</div>
          <div className="mt-1 text-sm text-slate-800">سياسة التكلفة: {asset.cost_display_mode}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            الرسملة المالية
          </div>
          <div className="mt-2 text-sm text-slate-800">
            {canSeeCapitalization && showAmounts
              ? `قيمة الشراء: ${formatMoney(asset.purchase_value)}`
              : 'قيم مالية محجوبة وملخصة'}
          </div>
          <div className="mt-1 text-sm text-slate-800">
            {canSeeCapitalization && showAmounts
              ? `مجمع الإهلاك: ${formatMoney(asset.accumulated_depreciation)}`
              : 'مسار الرسملة ظاهر للصرامة المالية'}
          </div>
          <div className="mt-1 text-sm text-slate-800">
            {canSeeCapitalization && showAmounts
              ? `القيمة الدفترية: ${formatMoney(asset.book_value)}`
              : 'الوضع المبسط لا يعرض القيم الدفترية'}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function FixedAssetsDashboard() {
  const { selectedFarmId } = useFarmContext()
  const { isStrictMode, costVisibility, visibilityLevel, fixedAssetMode } = useSettings()
  const { isAdmin, is_superuser: isSuperuser, hasPermission, hasFarmRole } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [assets, setAssets] = useState([])
  const [summary, setSummary] = useState(null)
  const [selectedAssetId, setSelectedAssetId] = useState(null)

  const canSeeCapitalization =
    isStrictMode &&
    fixedAssetMode === 'full_capitalization' &&
    (isAdmin ||
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
      setAssets([])
      setSummary(null)
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await api.get('/fixed-assets/', { params: { farm_id: selectedFarmId } })
      const rows = safeArray(response.data)
      setAssets(rows)
      setSummary(response.data.summary || null)
      setSelectedAssetId((current) => current || rows[0]?.id || null)
    } catch (loadError) {
      setError(extractApiError(loadError, 'Failed to load fixed asset dashboard.'))
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId])

  useEffect(() => {
    load()
  }, [load])

  const selectedAsset = useMemo(
    () => assets.find((entry) => entry.id === selectedAssetId) || assets[0] || null,
    [assets, selectedAssetId],
  )

  const showAmounts = costVisibility !== 'ratios_only'

  if (loading) {
    return <div className="p-6 text-sm text-slate-500">جاري تحميل سجل الأصول الثابتة...</div>
  }

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-slate-900">الأصول الثابتة و الممتلكات</h1>
        <p className="text-sm text-slate-500">
          سجل الأصول المركزية لدعم التشغيل في وضع (SIMPLE) والدورات المحاسبية للأصول في وضع (STRICT).
        </p>
      </div>

      <PolicyBanner
        fixedAssetMode={fixedAssetMode}
        isStrictMode={isStrictMode}
        visibilityLevel={visibilityLevel}
        costVisibility={costVisibility}
      />

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard icon={Boxes} title="أصول مسجلة" value={summary?.assets_count || 0} />
        <SummaryCard
          icon={AlertTriangle}
          title="أصول بإنذار"
          value={summary?.warning_assets || 0}
          tone="amber"
        />
        <SummaryCard
          icon={SunMedium}
          title="أصول حرجة"
          value={summary?.critical_assets || 0}
          tone="rose"
        />
        <SummaryCard
          icon={Landmark}
          title="قيمة الشراء التقديرية"
          value={showAmounts ? formatMoney(summary?.total_purchase_value || 0) : 'ملخص ومدار'}
          tone="sky"
        />
      </div>

      <AssetSmartCard
        asset={selectedAsset}
        showAmounts={showAmounts}
        canSeeCapitalization={canSeeCapitalization}
      />

      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">سجل إحصاء الأصول</h2>
            <p className="text-sm text-slate-500">
              سجل إحصائي ودفتري يدعم الحالة السليمة للأصل (Health) وحالة رسملته إذا توفرت الصلاحية.
            </p>
          </div>
          <div className="text-sm text-slate-500">
            الفئات: {summary?.categories?.join(', ') || 'N/A'}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200" data-testid="fixed-assets-table">
            <thead>
              <tr className="text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">الأصل</th>
                <th className="px-3 py-2">التصنيف</th>
                <th className="px-3 py-2">الصحة</th>
                <th className="px-3 py-2">الرسملة</th>
                {showAmounts ? (
                  <th className="px-3 py-2" data-testid="fixed-assets-amount-column">
                    القيم الدفترية
                  </th>
                ) : null}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
              {assets.map((asset) => (
                <tr
                  key={asset.id}
                  className={`cursor-pointer ${selectedAsset?.id === asset.id ? 'bg-sky-50' : 'hover:bg-slate-50'}`}
                  onClick={() => setSelectedAssetId(asset.id)}
                >
                  <td className="px-3 py-3">
                    <div className="font-medium text-slate-900">{asset.name}</div>
                    <div className="text-xs text-slate-500">{asset.farm_name}</div>
                  </td>
                  <td className="px-3 py-3">{asset.category}</td>
                  <td className="px-3 py-3">
                    <HealthBadge status={asset.health_status} />
                  </td>
                  <td className="px-3 py-3">{asset.capitalization_state}</td>
                  {showAmounts ? (
                    <td className="px-3 py-3 font-mono text-xs">
                      {canSeeCapitalization ? (
                        <div>
                          <div>الدفترية: {formatMoney(asset.book_value)}</div>
                          <div className="text-slate-500">
                            مجمع الإهلاك: {formatMoney(asset.accumulated_depreciation)}
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-500">محجوبة وملخصة</span>
                      )}
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {assets.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
            لا توجد أصول مسجلة في منصة المزرعة المحددة.
          </div>
        ) : null}

        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
          <div className="font-semibold">تلميحات التقرير</div>
          <div className="mt-2 grid gap-2 md:grid-cols-3">
            <div className="rounded-lg bg-white px-3 py-2">
              وضع التتبع فقط: {summary?.report_flags?.tracking_only ? 'نعم' : 'لا'}
            </div>
            <div className="rounded-lg bg-white px-3 py-2">
              ضوابط الرسملة:{' '}
              {summary?.report_flags?.requires_capitalization_controls ? 'مرتبطة' : 'غير مطلوبة'}
            </div>
            <div className="rounded-lg bg-white px-3 py-2">عرض التكاليف: {costVisibility}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
