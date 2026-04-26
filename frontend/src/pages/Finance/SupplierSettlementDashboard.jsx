import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, BadgeDollarSign, Landmark, PlusCircle, Wallet } from 'lucide-react'

import { PurchaseOrders, SupplierSettlements, api } from '../../api/client'
import { useFarmContext } from '../../api/farmContext'
import { useSettings } from '../../contexts/SettingsContext'
import { useToast } from '../../components/ToastProvider'
import { useAuth } from '../../auth/AuthContext'
import { extractApiError } from '../../utils/errorUtils'

const safeArray = (payload) =>
  Array.isArray(payload) ? payload : Array.isArray(payload?.results) ? payload.results : []

const STATUS_META = {
  DRAFT: 'bg-slate-100 text-slate-800',
  UNDER_REVIEW: 'bg-amber-100 text-amber-800',
  APPROVED: 'bg-sky-100 text-sky-800',
  PARTIALLY_PAID: 'bg-orange-100 text-orange-800',
  PAID: 'bg-emerald-100 text-emerald-800',
  REJECTED: 'bg-rose-100 text-rose-800',
  REOPENED: 'bg-violet-100 text-violet-800',
}

function formatMoney(value) {
  const numeric = Number(value || 0)
  if (Number.isNaN(numeric)) return String(value || '0.00')
  return numeric.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function StatusBadge({ status }) {
  const labelMap = {
    DRAFT: 'مسودة',
    UNDER_REVIEW: 'قيد المراجعة',
    APPROVED: 'معتمد',
    PARTIALLY_PAID: 'مدفوع جزئياً',
    PAID: 'مدفوع',
    REJECTED: 'مرفوض',
    REOPENED: 'معاد فتحه'
  }
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_META[status] || STATUS_META.DRAFT}`}
    >
      {labelMap[status] || status}
    </span>
  )
}

function PolicyBanner({ isStrictMode, costVisibility, visibilityLevel }) {
  return (
    <div
      className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900"
      data-testid="supplier-settlement-policy-banner"
    >
      <div className="font-semibold">سياسة الحوكمة</div>
      <div className="mt-1">
        {isStrictMode
          ? 'الوضع الحازم (STRICT) يعرض دورة الاعتماد، الدفع، والمطابقة بشكل إلزامي.'
          : 'الوضع المبسط (SIMPLE) يبقي العمليات المالية مبسطة دون تعقيدات تخطيط الموارد (ERP).'}
      </div>
      <div className="mt-1">
        مستوى الرؤية: {visibilityLevel} | التكاليف: {costVisibility}
      </div>
    </div>
  )
}

function CreateSettlementCard({ approvedOrders, onCreate, canManage, isStrictMode }) {
  const [purchaseOrder, setPurchaseOrder] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    if (!purchaseOrder) return
    setSaving(true)
    await onCreate(purchaseOrder).finally(() => setSaving(false))
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2 text-slate-900">
        <PlusCircle className="h-5 w-5" />
        <div className="font-semibold">إنشاء تسوية مورد</div>
      </div>
      <p className="mt-2 text-sm text-slate-500">
        {isStrictMode
          ? 'بدء تسوية محكومة من أمر شراء معتمد.'
          : 'يمكن للمستخدم المالي تسجيل الاستحقاق بينما يتابع المستخدم التشغيلي حالة الطلب فقط.'}
      </p>
      <div className="mt-4 flex flex-col gap-3 md:flex-row">
        <select
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={purchaseOrder}
          onChange={(event) => setPurchaseOrder(event.target.value)}
          disabled={!canManage}
          data-testid="supplier-settlement-create-select"
        >
          <option value="">اختر أمر شراء معتمد</option>
          {approvedOrders.map((order) => (
            <option key={order.id} value={order.id}>
              {order.vendor_name} / PO-{order.id}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={!purchaseOrder || !canManage || saving}
          onClick={submit}
          className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {saving ? 'جاري الإنشاء...' : 'إنشاء'}
        </button>
      </div>
    </div>
  )
}

function PaymentModal({ open, onClose, settlement, cashBoxes, onSubmit }) {
  const [form, setForm] = useState({ cash_box_id: '', amount: '', reference: '' })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) {
      setForm({ cash_box_id: '', amount: '', reference: '' })
    }
  }, [open])

  if (!open || !settlement) return null

  const submit = async (event) => {
    event.preventDefault()
    if (!form.cash_box_id || !form.amount) return
    setSaving(true)
    try {
      await onSubmit(settlement.id, form)
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl">
        <div className="border-b border-slate-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-slate-900">تسجيل دفعة مورد</h2>
          <p className="mt-1 text-sm text-slate-500">
            {settlement.vendor_name} | المتبقي {formatMoney(settlement.remaining_balance)}
          </p>
        </div>
        <form onSubmit={submit} className="space-y-4 px-6 py-5">
          <div>
            <label className="block text-sm font-medium text-slate-700">الخزينة</label>
            <select
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              value={form.cash_box_id}
              onChange={(event) =>
                setForm((current) => ({ ...current, cash_box_id: event.target.value }))
              }
            >
              <option value="">اختر الخزينة</option>
              {cashBoxes.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {entry.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">المبلغ</label>
            <input
              type="number"
              min="0"
              step="0.0001"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              value={form.amount}
              onChange={(event) =>
                setForm((current) => ({ ...current, amount: event.target.value }))
              }
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">البيان/المرجع</label>
            <input
              type="text"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              value={form.reference}
              onChange={(event) =>
                setForm((current) => ({ ...current, reference: event.target.value }))
              }
            />
          </div>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            >
              إلغاء
            </button>
            <button
              type="submit"
              disabled={!form.cash_box_id || !form.amount || saving}
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {saving ? 'جاري الترحيل...' : 'ترحيل الدفعة'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function SupplierSettlementDashboard() {
  const { selectedFarmId } = useFarmContext()
  const { isStrictMode, costVisibility, visibilityLevel } = useSettings()
  const { isAdmin, is_superuser: isSuperuser, hasPermission, hasFarmRole } = useAuth()
  const toast = useToast()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [settlements, setSettlements] = useState([])
  const [purchaseOrders, setPurchaseOrders] = useState([])
  const [cashBoxes, setCashBoxes] = useState([])
  const [paymentTarget, setPaymentTarget] = useState(null)

  const canManage =
    isAdmin ||
    isSuperuser ||
    hasPermission('finance.can_post_treasury') ||
    hasPermission('finance.can_approve_finance_request') ||
    hasFarmRole('manager') ||
    hasFarmRole('admin') ||
    hasFarmRole('المدير المالي لقطاع المزارع') ||
    hasFarmRole('رئيس حسابات القطاع') ||
    hasFarmRole('المدير المالي للمزرعة') ||
    hasFarmRole('رئيس الحسابات')

  const load = useCallback(async () => {
    if (!selectedFarmId) {
      setSettlements([])
      setPurchaseOrders([])
      setCashBoxes([])
      return
    }
    setLoading(true)
    setError('')
    try {
      const [settlementsResponse, purchaseOrdersResponse, cashBoxesResponse] = await Promise.all([
        SupplierSettlements.list({ farm_id: selectedFarmId }),
        PurchaseOrders.list({ farm_id: selectedFarmId }),
        api.get('/finance/cashboxes/', { params: { farm_id: selectedFarmId } }),
      ])

      setSettlements(safeArray(settlementsResponse.data))
      setPurchaseOrders(safeArray(purchaseOrdersResponse.data))
      setCashBoxes(safeArray(cashBoxesResponse.data))
    } catch (loadError) {
      setError(extractApiError(loadError, 'Failed to load supplier settlement board.'))
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId])

  useEffect(() => {
    load()
  }, [load])

  const approvedOrders = useMemo(
    () =>
      purchaseOrders.filter(
        (entry) =>
          ['APPROVED', 'RECEIVED'].includes(entry.status) &&
          !settlements.some((settlement) => settlement.purchase_order === entry.id),
      ),
    [purchaseOrders, settlements],
  )

  const report = useMemo(() => {
    const overdue = settlements.filter(
      (entry) => entry.variance_severity === 'warning' && Number(entry.remaining_balance || 0) > 0,
    ).length
    const partial = settlements.filter((entry) => entry.status === 'PARTIALLY_PAID').length
    const blocked = settlements.filter((entry) => entry.status === 'REJECTED').length
    const unresolved = settlements.filter((entry) => entry.variance_severity !== 'normal').length
    return { overdue, partial, blocked, unresolved }
  }, [settlements])

  const showAmounts = costVisibility !== 'ratios_only'

  const createSettlement = async (purchaseOrderId) => {
    try {
      await SupplierSettlements.create({ purchase_order: purchaseOrderId })
      toast.success('تم إنشاء تسوية المورد.')
      await load()
    } catch (createError) {
      toast.error(extractApiError(createError, 'فشل إنشاء تسوية المورد.'))
    }
  }

  const transition = async (action, settlementId, payload = {}) => {
    try {
      await action(settlementId, payload)
      toast.success('تم تحديث حالة التسوية بنجاح.')
      await load()
    } catch (actionError) {
      toast.error(extractApiError(actionError, 'فشل تحديث حالة التسوية.'))
    }
  }

  const recordPayment = async (settlementId, payload) => {
    try {
      await SupplierSettlements.recordPayment(settlementId, payload)
      toast.success('تم ترحيل الدفعة بنجاح.')
      await load()
    } catch (actionError) {
      toast.error(extractApiError(actionError, 'فشل ترحيل الدفعة.'))
      throw actionError
    }
  }

  if (!selectedFarmId) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-amber-900">
        الرجاء اختيار المزرعة أولاً لعرض تسجيلات الموردين.
      </div>
    )
  }

  return (
    <div className="app-page max-w-7xl mx-auto space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">تسويات الموردين (الذمم الدائنة)</h1>
          <p className="mt-1 text-sm text-slate-500">
            نافذة موحدة للمراجعة، الاعتماد، الدفع، والمطابقة للالتزامات تجاه الموردين.
          </p>
        </div>
        <PolicyBanner
          isStrictMode={isStrictMode}
          costVisibility={costVisibility}
          visibilityLevel={visibilityLevel}
        />
      </div>

      <CreateSettlementCard
        approvedOrders={approvedOrders}
        onCreate={createSettlement}
        canManage={canManage}
        isStrictMode={isStrictMode}
      />

      {loading ? (
        <div className="text-sm text-slate-500">جاري تحميل البيانات...</div>
      ) : null}
      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-amber-900">متأخرات (Overdue)</div>
              <div className="mt-2 text-2xl font-bold text-amber-900">{report.overdue}</div>
            </div>
            <AlertTriangle className="h-5 w-5 text-amber-700" />
          </div>
        </div>
        <div className="rounded-xl border border-orange-200 bg-orange-50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-orange-900">دفع جزئي</div>
              <div className="mt-2 text-2xl font-bold text-orange-900">{report.partial}</div>
            </div>
            <Wallet className="h-5 w-5 text-orange-700" />
          </div>
        </div>
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-rose-900">مرفوض (محجوب)</div>
              <div className="mt-2 text-2xl font-bold text-rose-900">{report.blocked}</div>
            </div>
            <Landmark className="h-5 w-5 text-rose-700" />
          </div>
        </div>
        <div className="rounded-xl border border-sky-200 bg-sky-50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-sky-900">فروقات غير محلولة</div>
              <div className="mt-2 text-2xl font-bold text-sky-900">{report.unresolved}</div>
            </div>
            <BadgeDollarSign className="h-5 w-5 text-sky-700" />
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div>
            <div className="font-semibold text-slate-900">سجل تسويات الموردين</div>
            <div className="text-xs text-slate-500">
              مراجعة الحالات، تقدم الدفعات، والمسار المحاسبي (Reconciliation).
            </div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table
            className="min-w-full divide-y divide-slate-200"
            data-testid="supplier-settlement-table"
          >
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                  المورد
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                  الأمر (PO)
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                  الحالة
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                  الفروقات
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                  المطابقة
                </th>
                {isStrictMode && (
                  <th
                    className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500"
                    data-testid="supplier-settlement-amount-column"
                  >
                    المبالغ
                  </th>
                )}
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                  الإجراءات
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {settlements.length === 0 ? (
                <tr>
                  <td
                    colSpan={isStrictMode ? 7 : 6}
                    className="px-4 py-10 text-center text-sm text-slate-500"
                  >
                    لا توجد تسويات موردين مسجلة للمزرعة الحالية.
                  </td>
                </tr>
              ) : (
                settlements.map((entry) => (
                  <tr key={entry.id}>
                    <td className="px-4 py-4 text-sm font-semibold text-slate-900">
                      {entry.vendor_name}
                    </td>
                    <td className="px-4 py-4 text-sm text-slate-700">PO-{entry.purchase_order}</td>
                    <td className="px-4 py-4 text-sm text-slate-700">
                      <StatusBadge status={entry.status} />
                    </td>
                    <td className="px-4 py-4 text-sm text-slate-700">{entry.variance_severity}</td>
                    <td className="px-4 py-4 text-sm text-slate-700">
                      {entry.reconciliation_state}
                    </td>
                    {isStrictMode && (
                      <td className="px-4 py-4 text-sm text-slate-700" dir="ltr">
                        {showAmounts
                          ? `${formatMoney(entry.paid_amount)} / ${formatMoney(entry.payable_amount)}`
                          : 'محجوب بحسب الصلاحية'}
                      </td>
                    )}
                    <td className="px-4 py-4 text-sm text-slate-700">
                      <div className="flex flex-wrap gap-2">
                        {canManage && entry.status === 'DRAFT' ? (
                          <button
                            type="button"
                            onClick={() => transition(SupplierSettlements.submitReview, entry.id)}
                            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700"
                          >
                            طلب مراجعة
                          </button>
                        ) : null}
                        {canManage && entry.status === 'UNDER_REVIEW' ? (
                          <button
                            type="button"
                            onClick={() => transition(SupplierSettlements.approve, entry.id)}
                            className="rounded-lg border border-sky-300 px-3 py-1.5 text-xs font-medium text-sky-700"
                          >
                            موافقة
                          </button>
                        ) : null}
                        {canManage && entry.status === 'REJECTED' ? (
                          <button
                            type="button"
                            onClick={() => transition(SupplierSettlements.reopen, entry.id)}
                            className="rounded-lg border border-violet-300 px-3 py-1.5 text-xs font-medium text-violet-700"
                          >
                            إعادة فتح
                          </button>
                        ) : null}
                        {canManage && ['APPROVED', 'PARTIALLY_PAID'].includes(entry.status) ? (
                          <button
                            type="button"
                            onClick={() => setPaymentTarget(entry)}
                            className="rounded-lg border border-emerald-300 px-3 py-1.5 text-xs font-medium text-emerald-700"
                          >
                            تسجيل دفعة
                          </button>
                        ) : null}
                        {!isStrictMode && !showAmounts ? (
                          <span className="text-xs text-slate-500">حسب الصلاحية</span>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <PaymentModal
        open={Boolean(paymentTarget)}
        settlement={paymentTarget}
        cashBoxes={cashBoxes}
        onClose={() => setPaymentTarget(null)}
        onSubmit={recordPayment}
      />
    </div>
  )
}
