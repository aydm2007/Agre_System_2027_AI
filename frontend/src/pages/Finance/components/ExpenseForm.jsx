import { useState } from 'react'
import PropTypes from 'prop-types'
import { api } from '../../../api/client'
import { toast } from 'react-hot-toast'
import { X, RefreshCw, Save } from 'lucide-react'
import { ACCOUNT_CODES } from '../constants'
import { toDecimal } from '../../../utils/decimal'

const parseApiErrorMessage = (error, fallback = 'تعذر إتمام العملية.') => {
  const payload = error?.response?.data
  if (!payload) return error?.message || fallback
  if (typeof payload === 'string' && payload.trim()) return payload
  const detail = payload?.detail
  if (Array.isArray(detail)) return detail.join(' - ')
  if (typeof detail === 'string' && detail.trim()) return detail
  return fallback
}

export default function ExpenseForm({ expense, onSave, onClose, farmId }) {
  const [form, setForm] = useState({
    farm: farmId,
    date: expense?.date || new Date().toISOString().slice(0, 10),
    amount: expense?.amount || '',
    description: expense?.description || '',
    account_code: expense?.account_code || '4000-OVERHEAD',
    currency: expense?.currency || 'YER',
    exchange_rate: expense?.exchange_rate || 1,
    budget_classification: expense?.budget_classification || '',
    replenishment_reference: expense?.replenishment_reference || '',
    period_start: expense?.period_start || '',
    period_end: expense?.period_end || '',
  })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.amount || !form.description) {
      toast.error('يرجى ملء جميع الحقول المطلوبة')
      return
    }

    // [Agri-Guardian] Budget Classification and Replenishment Reference are mandatory
    if (!form.budget_classification) {
      toast.error('يرجى اختيار بند الموازنة')
      return
    }
    if (!form.replenishment_reference) {
      toast.error('يرجى إدخال مرجع التغذية المعتمد')
      return
    }

    const amountVal = toDecimal(form.amount, 2)
    // [Agri-Guardian] Financial Physics: Expense cannot be negative (must be > 0)
    if (amountVal <= 0) {
      toast.error('المبلغ يجب أن يكون أكبر من صفر. للمرتجعات استخدم نموذج "إيراد متفرقات".')
      return
    }

    // Force absolute just in case logic slips through (e.g. if we remove the check later)
    const finalForm = { ...form, amount: Math.abs(amountVal) }
    setSaving(true)
    try {
      if (expense?.id) {
        await api.patch(`/finance/expenses/${expense.id}/`, finalForm)
        toast.success('تم تحديث المصروف بنجاح')
      } else {
        await api.post('/finance/expenses/', finalForm)
        toast.success('تم إضافة المصروف بنجاح')
      }
      onSave()
    } catch (err) {
      console.error(err)
      toast.error(`تعذر حفظ المصروف: ${parseApiErrorMessage(err, 'فشل حفظ المصروف.')}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-white/10 rounded-3xl p-6 w-full max-w-lg shadow-2xl scale-100 animate-in zoom-in-95 duration-200">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            {expense?.id ? 'تعديل المصروف' : 'إضافة مصروف جديد'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-white/10 rounded-xl transition-colors"
            aria-label="إغلاق النافذة"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-white/60" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-white/60 mb-2">
              التاريخ *
            </label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-emerald-500/50 focus:outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-white/60 mb-2">
              المبلغ *
            </label>
            <input
              type="number"
              step="0.001"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-emerald-500/50 focus:outline-none"
              placeholder="أدخل المبلغ"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-white/60 mb-2">
              الوصف *
            </label>
            <input
              type="text"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-emerald-500/50 focus:outline-none"
              placeholder="وصف المصروف"
              required
            />
          </div>

          {/* [Agri-Guardian] Budget Classification - Mandatory */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-white/60 mb-2">
              بند الموازنة *
            </label>
            <input
              type="text"
              value={form.budget_classification}
              onChange={(e) => setForm({ ...form, budget_classification: e.target.value })}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-emerald-500/50 focus:outline-none"
              placeholder="مثال: 2111 (وقود) أو 3112 (صيانة)"
              required
            />
          </div>

          {/* [Agri-Guardian] Replenishment Reference - Mandatory */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-white/60 mb-2">
              مرجع التغذية المعتمد *
            </label>
            <input
              type="text"
              value={form.replenishment_reference}
              onChange={(e) => setForm({ ...form, replenishment_reference: e.target.value })}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-emerald-500/50 focus:outline-none"
              placeholder="رقم طلب التغذية المعتمد"
              required
            />
          </div>

          {/* [Agri-Guardian] Expense Period */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-white/60 mb-2">
                بداية الفترة
              </label>
              <input
                type="date"
                value={form.period_start}
                onChange={(e) => setForm({ ...form, period_start: e.target.value })}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-emerald-500/50 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-white/60 mb-2">
                نهاية الفترة
              </label>
              <input
                type="date"
                value={form.period_end}
                onChange={(e) => setForm({ ...form, period_end: e.target.value })}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-emerald-500/50 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-white/60 mb-2">
              الحساب
            </label>
            <select
              value={form.account_code}
              onChange={(e) => setForm({ ...form, account_code: e.target.value })}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-emerald-500/50 focus:outline-none"
            >
              {ACCOUNT_CODES.map((acc) => (
                <option key={acc.code} value={acc.code}>
                  {acc.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-white/60 mb-2">
                العملة
              </label>
              <select
                value={form.currency}
                onChange={(e) => setForm({ ...form, currency: e.target.value })}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-emerald-500/50 focus:outline-none"
              >
                <option value="YER">ريال يمني</option>
                <option value="SAR">ريال سعودي</option>
                <option value="USD">دولار أمريكي</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-white/60 mb-2">
                سعر الصرف
              </label>
              <input
                type="number"
                step="0.0001"
                value={form.exchange_rate}
                onChange={(e) => setForm({ ...form, exchange_rate: e.target.value })}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-emerald-500/50 focus:outline-none"
              />
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 rounded-xl bg-gray-100 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-gray-700 dark:text-white font-medium hover:bg-gray-200 dark:hover:bg-white/10 transition-colors"
            >
              إلغاء
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-bold hover:from-emerald-500 hover:to-teal-500 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg shadow-emerald-500/20"
            >
              {saving ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              {saving ? 'جاري الحفظ...' : 'حفظ'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

ExpenseForm.propTypes = {
  expense: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    date: PropTypes.string,
    amount: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    description: PropTypes.string,
    account_code: PropTypes.string,
    currency: PropTypes.string,
    exchange_rate: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    budget_classification: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    replenishment_reference: PropTypes.string,
    period_start: PropTypes.string,
    period_end: PropTypes.string,
  }),
  onSave: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired,
  farmId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
}
