import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  BanknotesIcon,
  CheckCircleIcon,
  ClipboardDocumentCheckIcon,
  ExclamationTriangleIcon,
  PlusCircleIcon,
} from '@heroicons/react/24/outline'

import api, { safeRequest } from '../../api/client'
import { useFarmContext } from '../../api/farmContext'
import { useSettings } from '../../contexts/SettingsContext'
import { useToast } from '../../components/ToastProvider'
import { useAuth } from '../../auth/AuthContext'
import { extractApiError } from '../../utils/errorUtils'

const safeArray = (payload) =>
  Array.isArray(payload) ? payload : Array.isArray(payload?.results) ? payload.results : []

const STATUS_META = {
  PENDING: { label: 'بانتظار الاعتماد', className: 'bg-amber-100 text-amber-800' },
  APPROVED: { label: 'معتمد', className: 'bg-blue-100 text-blue-800' },
  DISBURSED: { label: 'مصروفة للموظف', className: 'bg-emerald-100 text-emerald-800' },
  SETTLED: { label: 'مغلقة / مُسواة', className: 'bg-slate-100 text-slate-800' },
  CANCELLED: { label: 'ملغاة', className: 'bg-rose-100 text-rose-800' },
  REJECTED: { label: 'مرفوضة', className: 'bg-rose-100 text-rose-800' },
}

const SETTLEMENT_META = {
  PENDING: { label: 'بانتظار المراجعة', className: 'bg-amber-100 text-amber-800' },
  APPROVED: { label: 'مُرحّلة للقيود', className: 'bg-emerald-100 text-emerald-800' },
  REJECTED: { label: 'مرفوضة', className: 'bg-rose-100 text-rose-800' },
}

function formatMoney(value) {
  if (value === null || value === undefined || value === '') {
    return '0.0000'
  }
  return String(value)
}

function formatDateTime(value) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('en-GB', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch (_error) {
    return String(value)
  }
}

function StatusBadge({ status, settlement = false }) {
  const meta = settlement ? SETTLEMENT_META[status] : STATUS_META[status]
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${meta?.className || 'bg-slate-100 text-slate-700'}`}
    >
      {meta?.label || status}
    </span>
  )
}

function PolicyHint({ isStrictMode, costVisibility }) {
  const message = isStrictMode
    ? 'الوضع الحازم (STRICT) يعرض دورة العمل الكاملة للسلفة، الإجراءات المحاسبية، ومأمولية الخزانة.'
    : 'الوضع المبسط (SIMPLE) يبقي الرؤية التشغيلية فقط: حالة الطلب، الإجمالي، والمخاطر أو الاستثناءات.'

  const costMessage =
    costVisibility === 'ratios_only'
      ? 'رؤية التكاليف: نسب فقط.'
      : costVisibility === 'summarized_amounts'
        ? 'رؤية التكاليف: إجماليات ملخصة.'
        : 'رؤية التكاليف: كامل للمسؤول المالي.'

  return (
    <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
      <div className="font-semibold">سياسة الحوكمة</div>
      <div className="mt-1">{message}</div>
      <div className="mt-1">{costMessage}</div>
    </div>
  )
}

function RequestModal({ open, onClose, onCreated, farmId, isStrictMode, costCenters, canManage }) {
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    amount: '',
    description: '',
    cost_center: '',
  })

  const canSubmit = farmId && form.amount && Number(form.amount) > 0 && form.description.trim()

  const reset = useCallback(() => {
    setForm({
      amount: '',
      description: '',
      cost_center: '',
    })
  }, [])

  const submit = async (event) => {
    event.preventDefault()
    if (!canSubmit) return

    setSaving(true)
    try {
      const payload = {
        farm: farmId,
        amount: form.amount,
        description: form.description.trim(),
      }
      if (form.cost_center) {
        payload.cost_center = form.cost_center
      }

      await safeRequest('post', '/finance/petty-cash-requests/', payload)
      toast.success('Petty cash request created.')
      reset()
      onCreated?.()
      onClose?.()
    } catch (error) {
      toast.error(extractApiError(error, 'Failed to create petty cash request.'))
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl">
        <div className="border-b border-slate-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-slate-900">طلب سلفة تمويل نثري (جديدة)</h2>
          <p className="mt-1 text-sm text-slate-500">
            {isStrictMode
              ? 'توجيه الطلبات بوضوح للأبعاد التحليلية للترحيلات اللاحقة.'
              : 'التقاط البيانات التشغيلية الأولية لتسهيل الإشراف.'}
          </p>
        </div>
        <form onSubmit={submit} className="space-y-4 px-6 py-5">
          <div>
            <label className="block text-sm font-medium text-slate-700">المبلغ</label>
            <input
              type="number"
              step="0.0001"
              min="0"
              value={form.amount}
              onChange={(event) =>
                setForm((current) => ({ ...current, amount: event.target.value }))
              }
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">البيان / الغرض</label>
            <textarea
              rows={3}
              value={form.description}
              onChange={(event) =>
                setForm((current) => ({ ...current, description: event.target.value }))
              }
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              required
            />
          </div>
          {(isStrictMode || canManage) && (
            <div>
              <label className="block text-sm font-medium text-slate-700">مركز التكلفة</label>
              <select
                value={form.cost_center}
                onChange={(event) =>
                  setForm((current) => ({ ...current, cost_center: event.target.value }))
                }
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              >
                <option value="">غير مخصص (مركزي)</option>
                {costCenters.map((entry) => (
                  <option key={entry.id} value={entry.id}>
                    {entry.code ? `${entry.code} - ${entry.name}` : entry.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => {
                reset()
                onClose?.()
              }}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            >
              إلغاء
            </button>
            <button
              type="submit"
              disabled={!canSubmit || saving}
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {saving ? 'جاري الإنشاء...' : 'إنشاء الطلب'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function SettlementModal({
  open,
  onClose,
  settlement,
  onUpdated,
  canManage,
  isStrictMode,
  costVisibility,
}) {
  const toast = useToast()
  const [form, setForm] = useState({
    amount: '',
    description: '',
  })
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) {
      setForm({ amount: '', description: '' })
    }
  }, [open])

  if (!open || !settlement) return null

  const addLine = async (event) => {
    event.preventDefault()
    if (!form.amount || Number(form.amount) <= 0 || !form.description.trim()) {
      return
    }

    setSubmitting(true)
    try {
      await safeRequest('post', `/finance/petty-cash-settlements/${settlement.id}/add_line/`, {
        amount: form.amount,
        description: form.description.trim(),
      })
      toast.success('Settlement line added.')
      setForm({ amount: '', description: '' })
      onUpdated?.()
    } catch (error) {
      toast.error(extractApiError(error, 'Failed to add settlement line.'))
    } finally {
      setSubmitting(false)
    }
  }

  const postSettlement = async () => {
    setSubmitting(true)
    try {
      await safeRequest(
        'post',
        `/finance/petty-cash-settlements/${settlement.id}/post_settlement/`,
        {},
      )
      toast.success('Settlement posted.')
      onUpdated?.()
      onClose?.()
    } catch (error) {
      toast.error(extractApiError(error, 'Failed to post settlement.'))
    } finally {
      setSubmitting(false)
    }
  }

  const canEdit = settlement.status === 'PENDING' && canManage
  const showAmounts = costVisibility !== 'ratios_only'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <div className="w-full max-w-3xl rounded-2xl bg-white shadow-2xl">
        <div className="border-b border-slate-200 px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">مرفقات التسوية #{settlement.id}</h2>
              <p className="mt-1 text-sm text-slate-500">
                {isStrictMode
                  ? 'مراجعة بنود المصروفات، احتساب المرتجع نقداً، وتأكيد الترحيل.'
                  : 'مراجعة التسوية والتحقق من المخاطر قبل الإغلاق النهائي للموظف.'}
              </p>
            </div>
            <StatusBadge settlement status={settlement.status} />
          </div>
        </div>

        <div className="grid gap-6 px-6 py-5 lg:grid-cols-[1.4fr_0.9fr]">
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200">
              <div className="border-b border-slate-200 px-4 py-3 font-semibold text-slate-900">
                بنود المصروفات
              </div>
              {settlement.lines?.length ? (
                <div className="divide-y divide-slate-100">
                  {settlement.lines.map((line) => (
                    <div
                      key={line.id}
                      className="flex items-start justify-between gap-4 px-4 py-3 text-sm"
                    >
                      <div>
                        <div className="font-medium text-slate-900">{line.description}</div>
                        <div className="text-slate-500">{line.date || '-'}</div>
                      </div>
                      <div className="font-semibold text-emerald-700" dir="ltr">
                        {showAmounts ? formatMoney(line.amount) : 'يُرى بالوضع المالي'}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="px-4 py-6 text-sm text-slate-500">
                  لا توجد بنود مصروفة مسجلة لهذه السلفة.
                </div>
              )}
            </div>

            {canEdit && (
              <form onSubmit={addLine} className="rounded-xl border border-slate-200 p-4">
                <div className="text-sm font-semibold text-slate-900">إضافة بند مصروفات</div>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium text-slate-700">المبلغ</label>
                    <input
                      type="number"
                      step="0.0001"
                      min="0"
                      value={form.amount}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, amount: event.target.value }))
                      }
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                      required
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-medium text-slate-700">التفاصيل / البيان</label>
                    <input
                      value={form.description}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          description: event.target.value,
                        }))
                      }
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                      required
                    />
                  </div>
                </div>
                <div className="mt-4 flex justify-end">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                  >
                    {submitting ? 'حفظ...' : 'إضافة إلى القائمة'}
                  </button>
                </div>
              </form>
            )}
          </div>

          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200 p-4">
              <div className="text-sm font-semibold text-slate-900">خلاصة التسوية</div>
              <div className="mt-3 space-y-2 text-sm text-slate-600">
                <div className="flex items-center justify-between gap-4">
                  <span>تاريخ الإنشاء</span>
                  <span>{formatDateTime(settlement.created_at)}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>إجمالي المصروفات</span>
                  <span dir="ltr">
                    {showAmounts ? formatMoney(settlement.total_expenses) : 'محجوب بحسب الصلاحية'}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>المبلغ المسترد للمتبقي</span>
                  <span dir="ltr">
                    {showAmounts ? formatMoney(settlement.refund_amount) : 'محجوب بحسب الصلاحية'}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>الحالة التنظيمية</span>
                  <span>
                    {settlement.status === 'PENDING'
                      ? 'بانتظار المراجعة'
                      : settlement.status === 'APPROVED'
                        ? 'مغلقة'
                        : 'تحتاج معالجة'}
                  </span>
                </div>
              </div>
            </div>

            {canEdit && (
              <button
                type="button"
                onClick={postSettlement}
                disabled={submitting || !settlement.lines?.length}
                className="w-full rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50"
              >
                {submitting ? 'Posting...' : 'Post settlement'}
              </button>
            )}

            <button
              type="button"
              onClick={onClose}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm font-medium text-slate-700"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function SummaryCards({ requests, settlements, costVisibility }) {
  const pendingRequests = requests.filter((entry) => entry.status === 'PENDING').length
  const activeCustody = requests.filter((entry) => entry.status === 'DISBURSED').length
  const pendingSettlements = settlements.filter((entry) => entry.status === 'PENDING').length
  const disbursedAmount = requests
    .filter((entry) => entry.status === 'DISBURSED')
    .reduce((sum, entry) => sum + Number(entry.amount || 0), 0)

  const cards = [
    {
      title: 'بانتظار الاعتماد',
      value: String(pendingRequests),
      icon: CheckCircleIcon,
      className: 'text-amber-700 bg-amber-50 border-amber-200',
    },
    {
      title: 'السلف المُعلقة',
      value: String(activeCustody),
      icon: BanknotesIcon,
      className: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    },
    {
      title: 'تسويات معلقة',
      value: String(pendingSettlements),
      icon: ClipboardDocumentCheckIcon,
      className: 'text-sky-700 bg-sky-50 border-sky-200',
    },
    {
      title: 'المبالغ المصروفة للعهدة',
      value:
        costVisibility === 'ratios_only'
          ? activeCustody > 0
            ? 'نَشِط'
            : 'لا يوجد'
          : formatMoney(disbursedAmount.toFixed(4)),
      icon: ExclamationTriangleIcon,
      className: 'text-slate-700 bg-slate-50 border-slate-200',
    },
  ]

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => {
        const Icon = card.icon
        return (
          <div key={card.title} className={`rounded-xl border p-4 ${card.className}`}>
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-sm font-medium">{card.title}</div>
                <div className="mt-2 text-2xl font-bold" dir="ltr">
                  {card.value}
                </div>
              </div>
              <Icon className="h-7 w-7" />
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default function PettyCashDashboard() {
  const { selectedFarmId } = useFarmContext()
  const { isStrictMode, isPettyCashEnabled, costVisibility, visibilityLevel } = useSettings()
  const { isAdmin, is_superuser: isSuperuser, hasPermission, hasFarmRole } = useAuth()
  const toast = useToast()

  const [activeTab, setActiveTab] = useState('requests')
  const [requests, setRequests] = useState([])
  const [settlements, setSettlements] = useState([])
  const [cashBoxes, setCashBoxes] = useState([])
  const [costCenters, setCostCenters] = useState([])
  const [loading, setLoading] = useState(false)
  const [requestModalOpen, setRequestModalOpen] = useState(false)
  const [settlementModal, setSettlementModal] = useState(null)
  const [disbursementBoxes, setDisbursementBoxes] = useState({})

  const canManage =
    isAdmin ||
    isSuperuser ||
    hasPermission('change_pettycashrequest') ||
    hasPermission('add_pettycashrequest') ||
    hasFarmRole('manager') ||
    hasFarmRole('admin')

  const settlementByRequestId = useMemo(() => {
    const mapping = new Map()
    settlements.forEach((entry) => {
      const requestId = entry.request?.id || entry.request
      if (requestId) {
        mapping.set(requestId, entry)
      }
    })
    return mapping
  }, [settlements])

  const loadData = useCallback(async () => {
    if (!selectedFarmId || !isPettyCashEnabled) return

    setLoading(true)
    try {
      const [requestResponse, settlementResponse, cashBoxResponse, costCenterResponse] =
        await Promise.all([
          api.get('/finance/petty-cash-requests/', { params: { farm_id: selectedFarmId } }),
          api.get('/finance/petty-cash-settlements/', { params: { farm_id: selectedFarmId } }),
          api.get('/finance/cashboxes/', { params: { farm_id: selectedFarmId } }),
          api.get('/finance/cost-centers/', { params: { farm_id: selectedFarmId } }),
        ])

      const nextRequests = safeArray(requestResponse.data)
      const nextSettlements = safeArray(settlementResponse.data)
      const nextCashBoxes = safeArray(cashBoxResponse.data)
      const nextCostCenters = safeArray(costCenterResponse.data)

      setRequests(nextRequests)
      setSettlements(nextSettlements)
      setCashBoxes(nextCashBoxes)
      setCostCenters(nextCostCenters)
      setDisbursementBoxes((current) => {
        const updated = { ...current }
        nextRequests.forEach((entry) => {
          if (!updated[entry.id] && nextCashBoxes[0]?.id) {
            updated[entry.id] = String(nextCashBoxes[0].id)
          }
        })
        return updated
      })
    } catch (error) {
      console.error(error)
      toast.error(extractApiError(error, 'Failed to load petty cash data.'))
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId, isPettyCashEnabled, toast])

  useEffect(() => {
    loadData()
  }, [loadData])

  const runAction = async (callback, successMessage, afterSuccess) => {
    try {
      const response = await callback()
      toast.success(successMessage)
      await loadData()
      afterSuccess?.(response)
    } catch (error) {
      toast.error(extractApiError(error, 'Action failed.'))
    }
  }

  const approveRequest = (requestId) =>
    runAction(
      () => safeRequest('post', `/finance/petty-cash-requests/${requestId}/approve/`, {}),
      'Petty cash request approved.',
    )

  const disburseRequest = (requestId) => {
    const cashBoxId = disbursementBoxes[requestId]
    if (!cashBoxId) {
      toast.error('Select a cash box before disbursement.')
      return
    }
    return runAction(
      () =>
        safeRequest('post', `/finance/petty-cash-requests/${requestId}/disburse/`, {
          cash_box_id: cashBoxId,
        }),
      'Petty cash request disbursed.',
    )
  }

  const createSettlement = (requestId) =>
    runAction(
      () =>
        safeRequest('post', '/finance/petty-cash-settlements/', {
          request: requestId,
        }),
      'Settlement shell created.',
      (response) => setSettlementModal(response?.data || null),
    )

  const openSettlement = (requestId) => {
    const settlement = settlementByRequestId.get(requestId)
    if (settlement) {
      setSettlementModal(settlement)
    }
  }

  if (!isPettyCashEnabled) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-slate-500">
        <BanknotesIcon className="mx-auto mb-4 h-12 w-12 text-slate-300" />
        <div className="text-xl font-semibold text-slate-900">نظام السلف النثرية معطل</div>
        <div className="mt-2 max-w-xl mx-auto">
          يجب تفعيل السلف النثرية من خصائص المزرعة (الضبط المالي) قبل إعداد طلبات عهدة جديدة.
        </div>
      </div>
    )
  }

  return (
    <div className="app-page max-w-7xl mx-auto space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <BanknotesIcon className="h-7 w-7 text-emerald-600" />
            <h1 className="text-2xl font-bold text-slate-900">نظام السلف النثرية والعهد</h1>
          </div>
          <p className="mt-2 text-sm text-slate-500">
            متابعة لعهد الموظفين التشغيلية من طلب السلفة إلى الاعتماد، والدفع، وختامًا تسوية العهد.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setRequestModalOpen(true)}
          className="inline-flex items-center gap-2 rounded-xl bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white"
        >
          <PlusCircleIcon className="h-5 w-5" />
          طلب سلفة جديد
        </button>
      </div>

      <PolicyHint isStrictMode={isStrictMode} costVisibility={costVisibility} />

      <div
        className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600"
        data-testid="petty-cash-visibility-banner"
      >
        <span className="font-semibold text-slate-900">مستوى الرؤية:</span> {visibilityLevel} |{' '}
        <span className="font-semibold text-slate-900">المالية المحجبة:</span> {costVisibility}
      </div>

      <SummaryCards requests={requests} settlements={settlements} costVisibility={costVisibility} />

      <div className="rounded-xl border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4">
          <nav className="flex gap-6">
            {[
              { id: 'requests', label: 'الطلبات' },
              { id: 'settlements', label: 'التسويات' },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`border-b-2 px-1 py-4 text-sm font-semibold ${activeTab === tab.id
                  ? 'border-sky-500 text-sky-600'
                  : 'border-transparent text-slate-500'
                  }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-4">
          {loading ? (
            <div className="py-10 text-center text-sm text-slate-500">
              جارٍ تحميل بيانات السلف النثرية...
            </div>
          ) : activeTab === 'requests' ? (
            requests.length === 0 ? (
              <div className="py-10 text-center text-sm text-slate-500">
                لا توجد طلبات سلفة نثرية لهذه المزرعة بعد.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table
                  className="min-w-full divide-y divide-slate-200"
                  data-testid="petty-cash-requests-table"
                >
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                        الطلب
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                        الغرض / البيان
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                        الحالة
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                        المتابعة التشغيلية
                      </th>
                      {isStrictMode && (
                        <th
                          className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
                          data-testid="petty-cash-cost-center-column"
                        >
                          مركز التكلفة
                        </th>
                      )}
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                        الإجراءات
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {requests.map((entry) => {
                      const settlement = settlementByRequestId.get(entry.id)
                      const canApprove = canManage && entry.status === 'PENDING'
                      const canDisburse = canManage && entry.status === 'APPROVED'
                      const canSettle = canManage && entry.status === 'DISBURSED' && !settlement
                      const hasSettlement = Boolean(settlement)
                      const showAmounts = costVisibility !== 'ratios_only'

                      return (
                        <tr key={entry.id}>
                          <td className="px-4 py-4 text-sm">
                            <div className="font-semibold text-slate-900">#{entry.id}</div>
                            <div className="mt-1 text-slate-500">
                              {formatDateTime(entry.created_at)}
                            </div>
                            <div className="mt-1 text-emerald-700" dir="ltr">
                              {showAmounts ? formatMoney(entry.amount) : 'رؤية محجوبة (صلاحية)'}
                            </div>
                          </td>
                          <td className="px-4 py-4 text-sm text-slate-700">{entry.description}</td>
                          <td className="px-4 py-4 text-sm">
                            <StatusBadge status={entry.status} />
                          </td>
                          <td className="px-4 py-4 text-sm text-slate-600">
                            {entry.status === 'DISBURSED'
                              ? 'السلفة في حوزة الموظف (يجب التسوية).'
                              : entry.status === 'SETTLED'
                                ? 'تم اعتماد تسوية السلفة وإغلاقها.'
                                : entry.status === 'APPROVED'
                                  ? 'معتمدة وتشريعية الصرف، بانتظار صرف الخزينة.'
                                  : 'جديدة - في انتظار المراجعة.'}
                          </td>
                          {isStrictMode && (
                            <td className="px-4 py-4 text-sm text-slate-600">
                              {entry.cost_center || 'بدون مركز تكلفة'}
                            </td>
                          )}
                          <td className="px-4 py-4 text-sm">
                            <div className="flex flex-col gap-2">
                              {canApprove && (
                                <button
                                  type="button"
                                  onClick={() => approveRequest(entry.id)}
                                  className="rounded-lg border border-sky-200 px-3 py-2 text-left font-medium text-sky-700"
                                >
                                  اعتماد الطلب
                                </button>
                              )}
                              {canDisburse && (
                                <div className="flex flex-col gap-2 sm:flex-row">
                                  <select
                                    aria-label={`خزينة الصرف للطلب ${entry.id}`}
                                    value={disbursementBoxes[entry.id] || ''}
                                    onChange={(event) =>
                                      setDisbursementBoxes((current) => ({
                                        ...current,
                                        [entry.id]: event.target.value,
                                      }))
                                    }
                                    className="rounded-lg border border-slate-300 px-3 py-2"
                                  >
                                    <option value="">اختر الخزينة المدفוע منها</option>
                                    {cashBoxes.map((box) => (
                                      <option key={box.id} value={box.id}>
                                        {box.name}
                                      </option>
                                    ))}
                                  </select>
                                  <button
                                    type="button"
                                    onClick={() => disburseRequest(entry.id)}
                                    className="rounded-lg border border-emerald-200 px-3 py-2 font-medium text-emerald-700"
                                  >
                                    صرف النقدية
                                  </button>
                                </div>
                              )}
                              {canSettle && (
                                <button
                                  type="button"
                                  onClick={() => createSettlement(entry.id)}
                                  className="rounded-lg border border-indigo-200 px-3 py-2 text-left font-medium text-indigo-700"
                                >
                                  إنشاء تسوية
                                </button>
                              )}
                              {hasSettlement && (
                                <button
                                  type="button"
                                  onClick={() => openSettlement(entry.id)}
                                  className="rounded-lg border border-slate-300 px-3 py-2 text-left font-medium text-slate-700"
                                >
                                  {settlement.status === 'PENDING'
                                    ? 'إدارة التسوية'
                                    : 'عرض التسوية'}
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )
          ) : settlements.length === 0 ? (
            <div className="py-10 text-center text-sm text-slate-500">
              لا تسويات مسجلة لهذه المزرعة حتى الآن.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table
                className="min-w-full divide-y divide-slate-200"
                data-testid="petty-cash-settlements-table"
              >
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      التسوية
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      الطلب
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      الحالة
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      الملخص المالي
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      الإجراءات
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {settlements.map((entry) => (
                    <tr key={entry.id}>
                      <td className="px-4 py-4 text-sm font-semibold text-slate-900">
                        #{entry.id}
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-600">#{entry.request}</td>
                      <td className="px-4 py-4 text-sm">
                        <StatusBadge settlement status={entry.status} />
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-600">
                        {costVisibility === 'ratios_only' ? (
                          <span>
                            التسوية قيد المراجعة. افتح التفاصيل للاطلاع على المبالغ.
                          </span>
                        ) : (
                          <span dir="ltr">
                            مصروفات {formatMoney(entry.total_expenses)} | مسترد{' '}
                            {formatMoney(entry.refund_amount)}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-4 text-sm">
                        <button
                          type="button"
                          onClick={() => setSettlementModal(entry)}
                          className="rounded-lg border border-slate-300 px-3 py-2 font-medium text-slate-700"
                        >
                          فتح التفاصيل
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <RequestModal
        open={requestModalOpen}
        onClose={() => setRequestModalOpen(false)}
        onCreated={loadData}
        farmId={selectedFarmId}
        isStrictMode={isStrictMode}
        costCenters={costCenters}
        canManage={canManage}
      />

      <SettlementModal
        open={Boolean(settlementModal)}
        onClose={() => setSettlementModal(null)}
        settlement={settlementModal}
        onUpdated={loadData}
        canManage={canManage}
        isStrictMode={isStrictMode}
        costVisibility={costVisibility}
      />
    </div>
  )
}
