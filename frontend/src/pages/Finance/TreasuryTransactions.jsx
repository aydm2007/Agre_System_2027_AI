import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft,
  Plus,
  RefreshCw,
  ReceiptText,
  HandCoins,
  BadgeDollarSign,
  Send,
} from 'lucide-react'

import api, { safeRequest } from '../../api/client'
import { useFarmContext } from '../../api/farmContext'
import { useToast } from '../../components/ToastProvider'
import { useAuth } from '../../auth/AuthContext'
import { extractApiError } from '../../utils/errorUtils'

const safeArray = (d) => (Array.isArray(d) ? d : Array.isArray(d?.results) ? d.results : [])

const TYPE_LABELS = {
  RECEIPT: 'استلام',
  PAYMENT: 'دفع',
  EXPENSE: 'مصروف',
  REMITTANCE: 'حوالة',
}

const TYPE_ICONS = {
  RECEIPT: ReceiptText,
  PAYMENT: HandCoins,
  EXPENSE: BadgeDollarSign,
  REMITTANCE: Send,
}

function formatMoney(v) {
  if (v === null || v === undefined || v === '') return '0.00'
  const n = Number(v)
  if (Number.isNaN(n)) return String(v)
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function TransactionForm({ open, onClose, cashBoxes, onCreated, farmId }) {
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [loadingParties, setLoadingParties] = useState(false)
  const [employees, setEmployees] = useState([])
  const [customers, setCustomers] = useState([])

  const [form, setForm] = useState({
    cash_box: '',
    transaction_type: 'RECEIPT',
    amount: '',
    exchange_rate: '1.0',
    reference: '',
    note: '',
    party_model: '',
    party_id: '',
  })

  const canSubmit = useMemo(() => {
    if (!farmId) return false
    if (!form.cash_box) return false
    if (!form.transaction_type) return false
    if (!form.amount || Number(form.amount) <= 0) return false
    return true
  }, [form, farmId])

  useEffect(() => {
    if (!open) return
    // Lazy-load parties to keep the page fast.
    const load = async () => {
      setLoadingParties(true)
      try {
        const [eRes, cRes] = await Promise.all([api.get('/employees/'), api.get('/customers/')])
        setEmployees(safeArray(eRes.data))
        setCustomers(safeArray(cRes.data))
      } catch (e) {
        // Parties are optional, so we don't fail the form.
        console.warn('party preload failed', e)
      } finally {
        setLoadingParties(false)
      }
    }
    load()
  }, [open])

  const parties = useMemo(() => {
    if (form.party_model === 'employee') return employees
    if (form.party_model === 'customer') return customers
    return []
  }, [form.party_model, employees, customers])

  const submit = async (e) => {
    e.preventDefault()
    if (!canSubmit) return

    setSaving(true)
    try {
      const payload = {
        cash_box: form.cash_box,
        transaction_type: form.transaction_type,
        amount: form.amount,
        exchange_rate: form.exchange_rate || '1.0',
        reference: form.reference || null,
        note: form.note || null,
      }

      if (form.party_model && form.party_id) {
        payload.party_model = form.party_model
        payload.party_id = String(form.party_id)
      }

      const result = await safeRequest('post', '/finance/treasury-transactions/', payload, {
        headers: {
          'X-Farm-Id': String(farmId),
        },
      })

      if (result?.queued) {
        toast.info('تم حفظ الحركة في قائمة الإرسال (Offline). سيتم إرسالها عند عودة الاتصال.')
      } else {
        toast.success('تم تسجيل الحركة بنجاح')
      }
      setForm({
        cash_box: '',
        transaction_type: 'RECEIPT',
        amount: '',
        exchange_rate: '1.0',
        reference: '',
        note: '',
        party_model: '',
        party_id: '',
      })
      onCreated?.()
      onClose?.()
    } catch (err) {
      toast.error(extractApiError(err, 'فشل تسجيل الحركة'))
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="fixed inset-0 bg-black/50" onClick={onClose} />
        <div className="relative w-full max-w-2xl rounded-lg bg-white shadow-lg">
          <div className="flex items-center justify-between border-b px-6 py-4">
            <h2 className="text-lg font-semibold">إضافة حركة خزينة</h2>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
              ✕
            </button>
          </div>

          <form onSubmit={submit} className="p-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700">الصندوق *</label>
                <select
                  value={form.cash_box}
                  onChange={(e) => setForm((f) => ({ ...f, cash_box: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                  required
                >
                  <option value="">اختر صندوقاً</option>
                  {cashBoxes.map((cb) => (
                    <option key={cb.id} value={cb.id}>
                      {cb.name} ({cb.currency})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">نوع الحركة *</label>
                <select
                  value={form.transaction_type}
                  onChange={(e) => setForm((f) => ({ ...f, transaction_type: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                >
                  <option value="RECEIPT">استلام</option>
                  <option value="PAYMENT">دفع</option>
                  <option value="EXPENSE">مصروف</option>
                  <option value="REMITTANCE">حوالة</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">المبلغ *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={form.amount}
                  onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">سعر الصرف</label>
                <input
                  type="number"
                  step="0.0001"
                  min="0"
                  value={form.exchange_rate}
                  onChange={(e) => setForm((f) => ({ ...f, exchange_rate: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                />
                <p className="mt-1 text-xs text-gray-500">اتركه 1.0 إذا كانت نفس عملة الصندوق.</p>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700">مرجع</label>
                <input
                  value={form.reference}
                  onChange={(e) => setForm((f) => ({ ...f, reference: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                  placeholder="مثال: رقم إيصال / رقم حوالة"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700">ملاحظة</label>
                <textarea
                  rows={3}
                  value={form.note}
                  onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                />
              </div>

              <div className="sm:col-span-2">
                <div className="flex items-center justify-between">
                  <label className="block text-sm font-medium text-gray-700">
                    طرف الحركة (اختياري)
                  </label>
                  {loadingParties ? <span className="text-xs text-gray-500">تحميل...</span> : null}
                </div>
                <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <select
                    value={form.party_model}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, party_model: e.target.value, party_id: '' }))
                    }
                    className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                  >
                    <option value="">بدون</option>
                    <option value="customer">عميل</option>
                    <option value="employee">موظف</option>
                  </select>

                  <select
                    value={form.party_id}
                    onChange={(e) => setForm((f) => ({ ...f, party_id: e.target.value }))}
                    disabled={!form.party_model}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500 disabled:bg-gray-100"
                  >
                    <option value="">اختر</option>
                    {parties.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name || p.full_name || `#${p.id}`}
                      </option>
                    ))}
                  </select>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  سيتم ربط الطرف بالسجل لأغراض التقارير والتحليل (إن وجد).
                </p>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50"
              >
                إلغاء
              </button>
              <button
                type="submit"
                disabled={!canSubmit || saving}
                className="rounded-md bg-green-600 px-4 py-2 text-white hover:bg-green-700 disabled:opacity-50"
              >
                {saving ? 'جارٍ الحفظ...' : 'حفظ'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default function TreasuryTransactions() {
  const toast = useToast()
  const { selectedFarmId } = useFarmContext()
  const { hasPermission, hasFarmRole, isAdmin, isSuperuser } = useAuth()
  const [loading, setLoading] = useState(true)
  const [cashBoxes, setCashBoxes] = useState([])
  const [transactions, setTransactions] = useState([])
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const canPostTreasury =
    isAdmin ||
    isSuperuser ||
    hasPermission('can_post_treasury') ||
    hasFarmRole('manager') ||
    hasFarmRole('admin')

  const cashBoxById = useMemo(() => {
    const m = new Map()
    cashBoxes.forEach((c) => m.set(c.id, c))
    return m
  }, [cashBoxes])

  const load = useCallback(async () => {
    if (!selectedFarmId) {
      setLoading(false)
      setCashBoxes([])
      setTransactions([])
      return
    }

    setLoading(true)
    setError(null)
    try {
      const [cbRes, txRes] = await Promise.all([
        api.get('/finance/cashboxes/', { params: { farm_id: selectedFarmId } }),
        api.get('/finance/treasury-transactions/', { params: { farm_id: selectedFarmId } }),
      ])
      setCashBoxes(safeArray(cbRes.data))
      setTransactions(safeArray(txRes.data))
    } catch (e) {
      console.error(e)
      setError('تعذر تحميل بيانات الخزينة')
      toast.error('تعذر تحميل بيانات الخزينة')
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId, toast])

  useEffect(() => {
    load()
  }, [load])

  const totalsByType = useMemo(() => {
    const t = { RECEIPT: 0, PAYMENT: 0, EXPENSE: 0, REMITTANCE: 0 }
    transactions.forEach((tx) => {
      const amount = Number(tx.amount || 0)
      if (!Number.isNaN(amount) && t[tx.transaction_type] !== undefined) {
        t[tx.transaction_type] += amount
      }
    })
    return t
  }, [transactions])

  if (!selectedFarmId) {
    return (
      <div className="app-page">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-yellow-800">اختر مزرعة أولاً</h2>
            <p className="mt-2 text-yellow-700">
              الخزينة مرتبطة بمزرعة محددة. اختر المزرعة من أعلى الصفحة ثم أعد المحاولة.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="app-page">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Link
              to="/finance/treasury"
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
              title="رجوع"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">حركات الخزينة</h1>
              <p className="text-gray-600">
                عرض وإضافة الحركات المالية (مع دعم idempotency تلقائياً)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => load()}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
              title="تحديث"
            >
              <RefreshCw className="h-5 w-5" />
            </button>
            <button
              onClick={() => {
                if (!canPostTreasury) {
                  toast.error('لا تملك صلاحية تسجيل حركة خزينة.')
                  return
                }
                setModalOpen(true)
              }}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              <Plus className="h-4 w-4" />
              إضافة حركة
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
          {Object.keys(TYPE_LABELS).map((k) => {
            const Icon = TYPE_ICONS[k] || ReceiptText
            return (
              <div key={k} className="bg-white rounded-lg shadow p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">{TYPE_LABELS[k]}</p>
                    <p className="text-xl font-bold text-gray-900">
                      {formatMoney(totalsByType[k])}
                    </p>
                  </div>
                  <Icon className="h-6 w-6 text-green-600" />
                </div>
              </div>
            )
          })}
        </div>

        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b">
            <h2 className="text-lg font-semibold">السجل</h2>
          </div>

          {error ? (
            <div className="p-6 text-red-600">{error}</div>
          ) : loading ? (
            <div className="p-6 text-gray-500">جارٍ التحميل...</div>
          ) : transactions.length === 0 ? (
            <div className="p-6 text-gray-500">لا توجد حركات مسجلة لهذه المزرعة بعد.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      التاريخ
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      الصندوق
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      النوع
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      المبلغ
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      مرجع
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      ملاحظة
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {transactions.map((tx) => {
                    const cb = cashBoxById.get(tx.cash_box)
                    const isIncoming = tx.transaction_type === 'RECEIPT'
                    const amountColor = isIncoming ? 'text-green-600' : 'text-red-600'
                    const amountSign = isIncoming ? '+' : '-'
                    const badgeBg = isIncoming
                      ? 'bg-green-100 text-green-800 border-green-200'
                      : 'bg-red-100 text-red-800 border-red-200'
                    return (
                      <tr key={tx.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {tx.created_at
                            ? new Date(tx.created_at).toLocaleString('ar-YE', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 border-r-4 border-l-transparent border-r-transparent hover:border-r-blue-500 transition-all">
                          {cb ? cb.name : `#${tx.cash_box}`}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <span
                            className={`px-2.5 py-1 rounded-full text-xs font-semibold border flex w-max items-center justify-center gap-1 ${badgeBg}`}
                          >
                            {isIncoming ? '⬇️' : '⬆️'}{' '}
                            {TYPE_LABELS[tx.transaction_type] || tx.transaction_type}
                          </span>
                        </td>
                        <td
                          className={`px-6 py-4 whitespace-nowrap text-sm font-bold ${amountColor}`}
                          dir="ltr"
                        >
                          <span className="opacity-70 ml-1">{amountSign}</span>
                          {formatMoney(tx.amount)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                          {tx.reference ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                              {tx.reference}
                            </span>
                          ) : (
                            '-'
                          )}
                        </td>
                        <td
                          className="px-6 py-4 text-sm text-gray-700 truncate max-w-xs"
                          title={tx.note}
                        >
                          {tx.note || '-'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {canPostTreasury && (
          <TransactionForm
            open={modalOpen}
            onClose={() => setModalOpen(false)}
            cashBoxes={cashBoxes}
            onCreated={load}
            farmId={selectedFarmId}
          />
        )}
      </div>
    </div>
  )
}
