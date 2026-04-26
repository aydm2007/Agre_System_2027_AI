import { useState, useCallback, useEffect } from 'react'
import { api } from '../../api/client'
import { toast } from 'react-hot-toast'
import { useFarmContext } from '../../api/farmContext.jsx'
import { formatMoney, toDecimal } from '../../utils/decimal'
import {
  Banknote,
  AlertCircle,
  RefreshCw,
  Calendar,
  CreditCard,
  FileText,
  Save,
  Info,
} from 'lucide-react'
import { v4 as uuidv4 } from 'uuid'
import { ACCOUNT_LABELS } from './constants'

export default function PayrollSettlement() {
  const { selectedFarmId } = useFarmContext()
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [salariesPayable, setSalariesPayable] = useState(0)
  const [cashAccounts, setCashAccounts] = useState([])

  const [formData, setFormData] = useState({
    payment_date: new Date().toISOString().slice(0, 10),
    credit_account: '',
    ref_id: '',
    description: 'تصفية رواتب العاملين عن الشهر',
    advances_recovery_amount: '0',
  })

  // Fetch current 2000-PAY-SAL balance and available cash accounts
  const fetchPayrollData = useCallback(async () => {
    if (!selectedFarmId) return
    try {
      setLoading(true)
      const res = await api.get('/finance/ledger/balances/', {
        params: { farm_id: selectedFarmId },
      })

      const balances = res.data.balances || {}
      setSalariesPayable(balances['2000-PAY-SAL'] || 0)

      // Get Cash and Bank accounts
      const accounts = Object.entries(balances)
        .filter(([code]) => code.startsWith('1000') || code.startsWith('1100'))
        .map(([code, balance]) => ({ code, balance }))

      setCashAccounts(accounts)

      if (accounts.length > 0) {
        setFormData((prev) => ({ ...prev, credit_account: accounts[0].code }))
      }
    } catch (err) {
      console.error('Fetch payroll data error:', err)
      toast.error('تعذر جلب أرصدة الرواتب المستحقة')
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId])

  useEffect(() => {
    fetchPayrollData()
  }, [fetchPayrollData])

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleLiquidate = async (e) => {
    e.preventDefault()
    if (!selectedFarmId) return

    if (!formData.credit_account) {
      toast.error('الرجاء اختيار الحساب الدائن (الصندوق/البنك)')
      return
    }

    if (salariesPayable <= 0) {
      toast.error('لا يوجد رصيد رواتب مستحق للتصفية')
      return
    }

    const advances = toDecimal(formData.advances_recovery_amount, 2)
    if (advances > salariesPayable) {
      toast.error('قيمة استرداد السلف لا يمكن أن تتجاوز إجمالي الرواتب المستحقة')
      return
    }

    if (
      !window.confirm(
        'هل أنت متأكد من تنفيذ تصفية الرواتب؟ سيتم إصدار سند صرف نهائي ولا يمكن التراجع.',
      )
    ) {
      return
    }

    try {
      setSubmitting(true)
      const idempotencyKey = uuidv4()
      const payload = {
        farm_id: selectedFarmId,
        payment_date: formData.payment_date,
        credit_account: formData.credit_account,
        ref_id: formData.ref_id,
        description: formData.description,
        advances_recovery_amount: formData.advances_recovery_amount,
      }

      const res = await api.post('/finance/ledger/liquidate-payroll/', payload, {
        headers: { 'X-Idempotency-Key': idempotencyKey },
      })

      toast.success(res.data.message || 'تم تصفية الرواتب بنجاح')
      // Reset after success
      setFormData((prev) => ({ ...prev, advances_recovery_amount: '0', ref_id: '' }))
      fetchPayrollData()
    } catch (err) {
      console.error('Liquidation error:', err)
      toast.error(err.response?.data?.error || 'فشل عملية الصرف')
    } finally {
      setSubmitting(false)
    }
  }

  const advances = toDecimal(formData.advances_recovery_amount, 2)
  const netCashPayout = Math.max(0, salariesPayable - advances)

  if (!selectedFarmId) {
    return (
      <div dir="rtl" className="app-page">
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-8 text-center max-w-lg mx-auto mt-20">
          <AlertCircle className="w-16 h-16 text-amber-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-amber-900 dark:text-white mb-2">اختر مزرعة</h2>
          <p className="text-slate-700 dark:text-white/60">
            يرجى اختيار مزرعة لفحص وتصفية مستحقات الرواتب
          </p>
        </div>
      </div>
    )
  }

  return (
    <div
      data-testid="payroll-settlement-page"
      dir="rtl"
      className="app-page space-y-6 max-w-5xl mx-auto"
    >
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-black text-slate-900 dark:text-white flex items-center gap-3">
            <Banknote className="w-8 h-8 text-indigo-500" />
            تصفية رواتب العمليات الزراعية
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            صرف الرواتب المستحقة للأنشطة الميدانية واستقطاع السلف
          </p>
        </div>
        <button
          onClick={fetchPayrollData}
          className="p-2 rounded-xl border border-slate-200 dark:border-white/10 text-slate-500 hover:text-indigo-600 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
          disabled={loading}
        >
          <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-3xl border border-amber-500/30 bg-gradient-to-br from-amber-500/10 to-transparent p-6 shadow-sm">
          <p className="text-amber-600 dark:text-amber-400/80 text-sm font-bold mb-1">
            إجمالي الرواتب والأجور المستحقة (2000-PAY-SAL)
          </p>
          <h2 className="text-4xl font-black text-amber-500" dir="ltr">
            {formatMoney(salariesPayable)}
          </h2>
          {salariesPayable <= 0 && (
            <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
              <Info className="w-4 h-4" /> رصيد مستحق الصرف صفر
            </p>
          )}
        </div>

        <div className="rounded-3xl border border-rose-500/30 bg-gradient-to-br from-rose-500/10 to-transparent p-6 shadow-sm">
          <p className="text-rose-600 dark:text-rose-400/80 text-sm font-bold mb-1">
            إجمالي السلف المستردة (خصم)
          </p>
          <h2 className="text-4xl font-black text-rose-500" dir="ltr">
            {formatMoney(advances)}
          </h2>
        </div>

        <div className="rounded-3xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-transparent p-6 shadow-sm">
          <p className="text-emerald-600 dark:text-emerald-400/80 text-sm font-bold mb-1">
            صافي النقد الواجب صرفه
          </p>
          <h2 className="text-4xl font-black text-emerald-500" dir="ltr">
            {formatMoney(netCashPayout)}
          </h2>
        </div>
      </div>

      <form onSubmit={handleLiquidate} className="app-panel p-6 space-y-6">
        <h3 className="text-xl font-bold text-slate-800 dark:text-white border-b border-slate-200 dark:border-white/10 pb-4">
          تفاصيل الصرف
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700 dark:text-slate-300 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-slate-400" /> تاريخ الدفع
            </label>
            <input
              type="date"
              name="payment_date"
              value={formData.payment_date}
              onChange={handleInputChange}
              required
              className="app-input w-full"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700 dark:text-slate-300 flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-slate-400" /> حساب الدفع (النقد/البنك)
            </label>
            <select
              name="credit_account"
              value={formData.credit_account}
              onChange={handleInputChange}
              required
              className="app-input w-full"
            >
              {cashAccounts.length === 0 && <option value="">لا توجد أرصدة صناديق</option>}
              {cashAccounts.map((acc) => (
                <option key={acc.code} value={acc.code}>
                  {acc.code} - {ACCOUNT_LABELS[acc.code]?.name || acc.code} (رصيد:{' '}
                  {formatMoney(acc.balance)})
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700 dark:text-slate-300 flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-400" /> إجمالي السلف المطلوب استردادها (ريال)
            </label>
            <input
              type="number"
              name="advances_recovery_amount"
              step="0.0001"
              min="0"
              max={salariesPayable}
              value={formData.advances_recovery_amount}
              onChange={handleInputChange}
              className="app-input w-full text-left"
              dir="ltr"
              placeholder="0.00"
            />
            <p className="text-xs text-slate-500">
              يتم قيد هذا المبلغ بحساب 1200-RECEIVABLE كاسترداد ذمم المدينة
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700 dark:text-slate-300">
              رقم المرجع الخارجي (اختياري)
            </label>
            <input
              type="text"
              name="ref_id"
              value={formData.ref_id}
              onChange={handleInputChange}
              className="app-input w-full"
              placeholder="رقم الشيك أو الحوالة البنكية..."
            />
          </div>

          <div className="md:col-span-2 space-y-2">
            <label className="text-sm font-bold text-slate-700 dark:text-slate-300">
              البيان الوصفي لسند الصرف
            </label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              required
              rows="2"
              className="app-input w-full"
              placeholder="تفاصيل التصفية..."
            />
          </div>
        </div>

        <div className="pt-4 border-t border-slate-200 dark:border-white/10 flex justify-end">
          <button
            type="submit"
            disabled={submitting || salariesPayable <= 0}
            className="flex items-center gap-2 px-8 py-3 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md"
          >
            {submitting ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <Save className="w-5 h-5" />
            )}
            تنفيذ سند الصرف وتصفية الرواتب
          </button>
        </div>
      </form>
    </div>
  )
}
