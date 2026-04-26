import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, ClipboardCheck, FileStack, HandCoins, Tractor } from 'lucide-react'

import { SharecroppingContracts } from '../api/client'
import { useFarmContext } from '../api/farmContext'
import { useSettings } from '../contexts/SettingsContext'
import { useToast } from '../components/ToastProvider'
import { useAuth } from '../auth/AuthContext'
import { extractApiError } from '../utils/errorUtils'

const safeArray = (payload) =>
  Array.isArray(payload) ? payload : Array.isArray(payload?.results) ? payload.results : []

function PolicyBanner({ isStrictMode, contractMode, visibilityLevel, costVisibility }) {
  return (
    <div
      className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"
      data-testid="contract-operations-policy-banner"
    >
      <div className="font-semibold">سياسة العمليات التعاقدية</div>
      <div className="mt-1">
        {isStrictMode
          ? 'الوضع الصارم يعرض مسار التسويات، موقف الترحيل المالي، وحالة المطابقة.'
          : 'الوضع المبسط يُبقي العمليات مبسطة وميدانية عبر عرض الجولات الميدانية، ومخاطر التأخير والفروقات فقط.'}
      </div>
      <div className="mt-1">
        وضع التعاقد: {contractMode} | الرؤية: {visibilityLevel} | مستوى التكلفة: {costVisibility}
      </div>
    </div>
  )
}

function SummaryCard({ icon: Icon, title, value, tone = 'slate' }) {
  const toneClass = {
    amber: 'border-amber-200 bg-amber-50 text-amber-900',
    rose: 'border-rose-200 bg-rose-50 text-rose-900',
    sky: 'border-sky-200 bg-sky-50 text-sky-900',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-900',
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

function SmartCard({ contract, isStrictMode, showAmounts }) {
  if (!contract) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">
        Select a contract row to inspect the smart card.
      </div>
    )
  }

  return (
    <div
      className="rounded-2xl border border-slate-200 bg-white p-5"
      data-testid="contract-operations-smart-card"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Contract smart card
          </div>
          <h2 className="mt-1 text-xl font-bold text-slate-900">
            {contract.farmer_name} · {contract.contract_type}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {contract.farm_name} · {contract.crop_name || 'No crop'} ·{' '}
            {contract.season_name || 'No season'}
          </p>
        </div>
        <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
          <div>Status: {contract.status}</div>
          <div>Touring: {contract.touring_state}</div>
          <div>Settlement: {contract.settlement_state}</div>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            التشغيل والمشاركة
          </div>
          {showAmounts ? (
            <>
              <div className="mt-2 text-sm text-slate-800">
                المتوقع للمؤسسة: {contract.expected_institution_share}
              </div>
              <div className="mt-1 text-sm text-slate-800">
                الفعلي للمؤسسة: {contract.actual_institution_share}
              </div>
              <div className="mt-1 text-sm text-slate-800">
                الفجوة: {contract.expected_vs_actual_gap}
              </div>
            </>
          ) : (
            <>
              <div className="mt-2 text-sm text-slate-800">
                الموقف الاقتصادي: {contract.economic_posture || contract.settlement_state}
              </div>
              <div className="mt-1 text-sm text-slate-800">
                يتم عرض مخاطر العقود بناءً على السياسة في الوضع المبسط.
              </div>
            </>
          )}
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            الجاهزية والاعتماد
          </div>
          <div className="mt-2 text-sm text-slate-800">الاعتماد: {contract.approval_state}</div>
          <div className="mt-1 text-sm text-slate-800">الاستلام: {contract.receipt_state}</div>
          <div className="mt-1 text-sm text-slate-800">
            المطابقة: {contract.reconciliation_state}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">المخاطر</div>
          <div className="mt-2 text-sm text-slate-800">التباين: {contract.variance_severity}</div>
          <div className="mt-1 text-sm text-slate-800">
            المؤشرات: {contract.flags.length ? contract.flags.join(', ') : 'طبيعي'}
          </div>
          <div className="mt-1 text-sm text-slate-800">السياسة: {contract.contract_mode}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            التسوية والإيجار
          </div>
          <div className="mt-2 text-sm text-slate-800">
            النمط: {contract.sharecropping_mode || contract.contract_mode}
          </div>
          <div className="mt-1 text-sm text-slate-800">
            {showAmounts || isStrictMode
              ? `الإيجار السنوي: ${contract.annual_rent_amount}`
              : 'القيم المالية ملخصة بالسياسة'}
          </div>
          <div className="mt-1 text-sm text-slate-800">
            {contract.last_rent_payment?.payment_period
              ? `آخر فترة مسددة: ${contract.last_rent_payment.payment_period}`
              : 'لا توجد دفعات إيجار مرحّلة'}
          </div>
        </div>
      </div>
    </div>
  )
}

function TouringModal({ open, onClose, onSubmit, contract }) {
  const [form, setForm] = useState({ estimated_kg: '', committee_members: 'عضو 1, عضو 2, عضو 3' })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) {
      setForm({ estimated_kg: '', committee_members: 'عضو 1, عضو 2, عضو 3' })
    }
  }, [open])

  if (!open || !contract) return null

  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      await onSubmit(contract.id, {
        estimated_kg: form.estimated_kg,
        committee_members: form.committee_members
          .split(',')
          .map((entry) => entry.trim())
          .filter(Boolean),
      })
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <form onSubmit={submit} className="w-full max-w-lg rounded-2xl bg-white px-6 py-5 shadow-2xl">
        <h2 className="text-lg font-semibold text-slate-900">تسجيل الجولة الميدانية والتخمين</h2>
        <p className="mt-1 text-sm text-slate-500">{contract.farmer_name}</p>
        <div className="mt-4">
          <label className="block text-sm font-medium text-slate-700">الكمية التقديرية (كجم)</label>
          <input
            aria-label="Estimated KG"
            type="number"
            min="0"
            step="0.0001"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.estimated_kg}
            onChange={(event) =>
              setForm((current) => ({ ...current, estimated_kg: event.target.value }))
            }
          />
        </div>
        <div className="mt-4">
          <label className="block text-sm font-medium text-slate-700">أعضاء لجنة الجولة (مفصولين بفاصلة)</label>
          <input
            aria-label="Committee members"
            type="text"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.committee_members}
            onChange={(event) =>
              setForm((current) => ({ ...current, committee_members: event.target.value }))
            }
          />
        </div>
        <div className="mt-5 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
          >
            إلغاء
          </button>
          <button
            type="submit"
            disabled={!form.estimated_kg || saving}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? 'جاري الحفظ...' : 'حفظ الجولة'}
          </button>
        </div>
      </form>
    </div>
  )
}

function HarvestModal({ open, onClose, onSubmit, contract }) {
  const [form, setForm] = useState({
    actual_kg: '',
    yield_type: 'CASH',
    committee_members: 'عضو 1, عضو 2, عضو 3',
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) {
      setForm({ actual_kg: '', yield_type: 'CASH', committee_members: 'عضو 1, عضو 2, عضو 3' })
    }
  }, [open])

  if (!open || !contract) return null

  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      await onSubmit(contract.id, {
        actual_kg: form.actual_kg,
        yield_type: form.yield_type,
        committee_members: form.committee_members
          .split(',')
          .map((entry) => entry.trim())
          .filter(Boolean),
      })
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <form onSubmit={submit} className="w-full max-w-lg rounded-2xl bg-white px-6 py-5 shadow-2xl">
        <h2 className="text-lg font-semibold text-slate-900">تسوية ومعالجة الحصاد</h2>
        <p className="mt-1 text-sm text-slate-500">{contract.farmer_name}</p>
        <div className="mt-4">
          <label className="block text-sm font-medium text-slate-700">الكمية الفعلية الموردة (كجم)</label>
          <input
            aria-label="Actual KG"
            type="number"
            min="0"
            step="0.0001"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.actual_kg}
            onChange={(event) =>
              setForm((current) => ({ ...current, actual_kg: event.target.value }))
            }
          />
        </div>
        <div className="mt-4">
          <label className="block text-sm font-medium text-slate-700">نوع التسوية للمحصول</label>
          <select
            aria-label="Settlement type"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.yield_type}
            onChange={(event) =>
              setForm((current) => ({ ...current, yield_type: event.target.value }))
            }
          >
            <option value="CASH">نقدي (CASH)</option>
            <option value="IN_KIND">عيني (IN_KIND)</option>
          </select>
        </div>
        <div className="mt-4">
          <label className="block text-sm font-medium text-slate-700">أعضاء لجنة الحصاد والفحص</label>
          <input
            aria-label="Harvest committee members"
            type="text"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.committee_members}
            onChange={(event) =>
              setForm((current) => ({ ...current, committee_members: event.target.value }))
            }
          />
        </div>
        <div className="mt-5 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
          >
            إلغاء
          </button>
          <button
            type="submit"
            disabled={!form.actual_kg || saving}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? 'جاري الترحيل...' : 'تنفيذ وتقييد'}
          </button>
        </div>
      </form>
    </div>
  )
}

function RentPaymentModal({ open, onClose, onSubmit, contract }) {
  const [form, setForm] = useState({ amount: '', payment_period: '', notes: '' })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) {
      setForm({ amount: '', payment_period: '', notes: '' })
    }
  }, [open])

  if (!open || !contract) return null

  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      await onSubmit(contract.id, form)
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <form onSubmit={submit} className="w-full max-w-lg rounded-2xl bg-white px-6 py-5 shadow-2xl">
        <h2 className="text-lg font-semibold text-slate-900">تسجيل دفعة إيجار</h2>
        <p className="mt-1 text-sm text-slate-500">{contract.farmer_name}</p>
        <div className="mt-4">
          <label className="block text-sm font-medium text-slate-700">المبلغ</label>
          <input
            aria-label="Amount"
            type="number"
            min="0"
            step="0.0001"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.amount}
            onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))}
          />
        </div>
        <div className="mt-4">
          <label className="block text-sm font-medium text-slate-700">عن فترة سداد / موسم</label>
          <input
            aria-label="Payment period"
            type="text"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.payment_period}
            onChange={(event) =>
              setForm((current) => ({ ...current, payment_period: event.target.value }))
            }
          />
        </div>
        <div className="mt-4">
          <label className="block text-sm font-medium text-slate-700">ملاحظات التحصيل والمرجع</label>
          <input
            aria-label="Notes"
            type="text"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.notes}
            onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
          />
        </div>
        <div className="mt-5 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
          >
            إلغاء
          </button>
          <button
            type="submit"
            disabled={!form.amount || !form.payment_period || saving}
            className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? 'جاري الترحيل...' : 'ترحيل الدفعة النقدية'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default function ContractOperationsDashboard() {
  const { selectedFarmId } = useFarmContext()
  const { isStrictMode, costVisibility, visibilityLevel, contractMode } = useSettings()
  const { isAdmin, is_superuser: isSuperuser, hasFarmRole, hasPermission } = useAuth()
  const toast = useToast()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [rows, setRows] = useState([])
  const [summary, setSummary] = useState({})
  const [filterType, setFilterType] = useState('ALL')
  const [selectedId, setSelectedId] = useState(null)
  const [touringTarget, setTouringTarget] = useState(null)
  const [harvestTarget, setHarvestTarget] = useState(null)
  const [rentTarget, setRentTarget] = useState(null)

  const canManageOperational =
    isStrictMode &&
    (isAdmin ||
      isSuperuser ||
      hasPermission?.('core.change_sharecroppingcontract') ||
      hasFarmRole?.('manager') ||
      hasFarmRole?.('admin') ||
      hasFarmRole?.('مدير المزرعة'))

  const canManageStrict =
    isStrictMode &&
    (isAdmin ||
      isSuperuser ||
      hasPermission?.('finance.can_post_treasury') ||
      hasPermission?.('finance.can_approve_finance_request') ||
      hasFarmRole?.('المدير المالي لقطاع المزارع') ||
      hasFarmRole?.('رئيس حسابات القطاع') ||
      hasFarmRole?.('مدير القطاع') ||
      hasFarmRole?.('المدير المالي للمزرعة') ||
      hasFarmRole?.('رئيس الحسابات'))

  const load = useCallback(async () => {
    if (!selectedFarmId) {
      setRows([])
      setSummary({})
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await SharecroppingContracts.dashboard({ farm: selectedFarmId })
      setRows(safeArray(response.data))
      setSummary(response.data?.summary ?? {})
    } catch (loadError) {
      setError(extractApiError(loadError, 'Failed to load contract operations board.'))
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!rows.length) {
      setSelectedId(null)
      return
    }
    if (!selectedId || !rows.some((entry) => entry.id === selectedId)) {
      setSelectedId(rows[0].id)
    }
  }, [rows, selectedId])

  const filteredRows = useMemo(
    () =>
      filterType === 'ALL' ? rows : rows.filter((entry) => entry.contract_type === filterType),
    [rows, filterType],
  )

  const selectedContract = useMemo(
    () => filteredRows.find((entry) => entry.id === selectedId) ?? filteredRows[0] ?? null,
    [filteredRows, selectedId],
  )

  const showAmounts = isStrictMode && visibilityLevel === 'full_erp' && costVisibility !== 'ratios_only'

  const runAction = async (fn, successMessage) => {
    try {
      await fn()
      toast.success(successMessage)
      await load()
    } catch (actionError) {
      toast.error(extractApiError(actionError, 'Failed to update contract workflow.'))
      throw actionError
    }
  }

  if (!selectedFarmId) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-amber-900">
        Select a farm first to open contract operations control.
      </div>
    )
  }

  return (
    <div className="app-page mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">العمليات التعاقدية</h1>
          <p className="mt-1 text-sm text-slate-500">
            موقف العمليات التعاقدية والجولات الميدانية والإيجارات الموحد للفئتين (SIMPLE) و (STRICT).
          </p>
        </div>
        <PolicyBanner
          isStrictMode={isStrictMode}
          contractMode={contractMode}
          visibilityLevel={visibilityLevel}
          costVisibility={costVisibility}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          icon={Tractor}
          title="بانتظار الجولات الميدانية"
          value={summary.awaiting_touring ?? 0}
          tone="amber"
        />
        <SummaryCard
          icon={ClipboardCheck}
          title="جولات غير مسواة"
          value={summary.touring_completed_unsettled ?? 0}
          tone="sky"
        />
        <SummaryCard
          icon={HandCoins}
          title="إيجارات متأخرة"
          value={summary.overdue_rentals ?? 0}
          tone="rose"
        />
        <SummaryCard
          icon={AlertTriangle}
          title="فروقات مفتوحة"
          value={summary.unresolved_contract_variances ?? 0}
          tone="emerald"
        />
      </div>

      <SmartCard
        contract={selectedContract}
        isStrictMode={isStrictMode}
        showAmounts={showAmounts}
      />

      {!isStrictMode ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          وضع (SIMPLE) يقوم بعرض الحالة التشغيلية للعقد فقط. صلاحيات الجدولة واعتمادات الحصاد والمبالغ المالية لا زالت تخضع للصلاحية بالوضع (STRICT).
        </div>
      ) : null}

      <div className="rounded-xl border border-slate-200 bg-white">
        <div className="flex flex-col gap-3 border-b px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="font-semibold text-slate-900">العقود</div>
            <div className="text-xs text-slate-500">
              الحالة التشغيلية، الجولات الميدانية، التسوية المادية والتفاوت المالي.
            </div>
          </div>
          <div className="flex items-center gap-2">
            <select
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={filterType}
              onChange={(event) => setFilterType(event.target.value)}
              data-testid="contract-operations-filter"
            >
              <option value="ALL">كل العقود</option>
              <option value="SHARECROPPING">مشاركة المحصول</option>
              <option value="RENTAL">تأجير أراضي</option>
            </select>
          </div>
        </div>

        {loading ? <div className="p-4 text-sm text-slate-500">جاري تحميل العقود...</div> : null}
        {error ? (
          <div className="m-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <div className="overflow-x-auto">
          <table
            className="min-w-full divide-y divide-slate-200"
            data-testid="contract-operations-table"
          >
            <thead className="bg-slate-50">
              <tr className="text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                <th className="px-4 py-3">المقاول / المزارع</th>
                <th className="px-4 py-3">نوع العقد</th>
                <th className="px-4 py-3">الحالة</th>
                <th className="px-4 py-3">الجولة</th>
                <th className="px-4 py-3">التسوية</th>
                <th className="px-4 py-3">الفروق</th>
                {showAmounts ? (
                  <th className="px-4 py-3" data-testid="contract-operations-amount-column">
                    المتوقع / الفعلي
                  </th>
                ) : null}
                <th className="px-4 py-3">الإجراءات</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {filteredRows.map((entry) => (
                <tr
                  key={entry.id}
                  className={`cursor-pointer hover:bg-slate-50 ${selectedContract?.id === entry.id ? 'bg-emerald-50/40' : ''}`}
                  onClick={() => setSelectedId(entry.id)}
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{entry.farmer_name}</div>
                    <div className="text-xs text-slate-500">
                      {entry.farm_name} · {entry.crop_name || 'No crop'}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-700">{entry.contract_type}</td>
                  <td className="px-4 py-3 text-sm text-slate-700">{entry.status}</td>
                  <td className="px-4 py-3 text-sm text-slate-700">{entry.touring_state}</td>
                  <td className="px-4 py-3 text-sm text-slate-700">{entry.settlement_state}</td>
                  <td className="px-4 py-3 text-sm text-slate-700">{entry.variance_severity}</td>
                  {showAmounts ? (
                    <td className="px-4 py-3 text-sm text-slate-700">
                      {entry.expected_institution_share} / {entry.actual_institution_share}
                    </td>
                  ) : null}
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {entry.contract_type === 'SHARECROPPING' ? (
                        <>
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation()
                              setTouringTarget(entry)
                            }}
                            disabled={!canManageOperational}
                            className="rounded-lg border border-emerald-300 px-3 py-1 text-xs font-medium text-emerald-700 disabled:opacity-50"
                          >
                            جولة تقدير
                          </button>
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation()
                              setHarvestTarget(entry)
                            }}
                            disabled={!canManageOperational}
                            className="rounded-lg border border-sky-300 px-3 py-1 text-xs font-medium text-sky-700 disabled:opacity-50"
                          >
                            حصاد / استلام
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation()
                            setRentTarget(entry)
                          }}
                          disabled={!canManageStrict}
                          className="rounded-lg border border-amber-300 px-3 py-1 text-xs font-medium text-amber-700 disabled:opacity-50"
                        >
                          سداد إيجار
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2 text-slate-900">
          <FileStack className="h-5 w-5" />
          <div className="font-semibold">تقارير مندمجة</div>
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4 text-sm text-slate-700">
          <div>عقود بانتظار الجولات الميدانية: {summary.awaiting_touring ?? 0}</div>
          <div>جولات تمت وغير مسواة: {summary.touring_completed_unsettled ?? 0}</div>
          <div>إيجارات متأخرة: {summary.overdue_rentals ?? 0}</div>
          <div>تسويات غير متطابقة: {summary.mismatched_settlements ?? 0}</div>
        </div>
      </div>

      <TouringModal
        open={Boolean(touringTarget)}
        contract={touringTarget}
        onClose={() => setTouringTarget(null)}
        onSubmit={(contractId, payload) =>
          runAction(
            () => SharecroppingContracts.registerTouring(contractId, payload),
            'تم تسجيل جولة التقييم.'
          )
        }
      />
      <HarvestModal
        open={Boolean(harvestTarget)}
        contract={harvestTarget}
        onClose={() => setHarvestTarget(null)}
        onSubmit={(contractId, payload) =>
          runAction(
            () => SharecroppingContracts.processHarvest(contractId, payload),
            'تم تنفيذ الاستلام والتسوية.'
          )
        }
      />
      <RentPaymentModal
        open={Boolean(rentTarget)}
        contract={rentTarget}
        onClose={() => setRentTarget(null)}
        onSubmit={(contractId, payload) =>
          runAction(
            () => SharecroppingContracts.recordRentPayment(contractId, payload),
            'تم ترحيل دفعة الإيجار.'
          )
        }
      />
    </div>
  )
}
