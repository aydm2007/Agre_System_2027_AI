import { useMemo, useState } from 'react'
import PropTypes from 'prop-types'
import { api } from '../../../api/client'
import { toast } from 'react-hot-toast'
import { AlertTriangle, Calculator, Lock, RotateCcw, Shield, X } from 'lucide-react'
import { useSettings } from '../../../contexts/SettingsContext'

const parseApiErrorMessage = (error, fallback = 'تعذر إتمام العملية.') => {
  const payload = error?.response?.data
  if (!payload) return error?.message || fallback
  if (typeof payload === 'string' && payload.trim()) return payload
  const detail = payload?.detail
  if (Array.isArray(detail)) return detail.join(' - ')
  if (typeof detail === 'string' && detail.trim()) return detail
  if (typeof payload?.error === 'string' && payload.error.trim()) return payload.error
  return fallback
}

const normalizePeriodStatus = (status) => String(status || 'open').toLowerCase().replace(/-/g, '_')

export default function ClosingWizard({
  period,
  canHardClose,
  canReopen,
  onClose,
  onComplete,
}) {
  const { isZakatEnabled } = useSettings()
  const [busyAction, setBusyAction] = useState('')
  const [acceptZakatPosting, setAcceptZakatPosting] = useState(false)
  const [reopenReason, setReopenReason] = useState('')
  const [currentStatus, setCurrentStatus] = useState(normalizePeriodStatus(period?.status))

  const periodTitle = useMemo(() => {
    if (!period) return ''
    return `الفترة ${period.month}/${period.fiscal_year_display || period.fiscal_year || ''}`.trim()
  }, [period])

  const isOpen = currentStatus === 'open'
  const isSoftClosed = currentStatus === 'soft_close'
  const isHardClosed = currentStatus === 'hard_close'

  const doSoftClose = async () => {
    if (!period?.id) return
    setBusyAction('soft-close')
    try {
      await api.post(`/finance/fiscal-periods/${period.id}/soft-close/`)
      setCurrentStatus('soft_close')
      toast.success('تم تنفيذ الإغلاق المبدئي للفترة')
      onComplete?.()
    } catch (error) {
      toast.error(parseApiErrorMessage(error, 'تعذر تنفيذ الإغلاق المبدئي'))
    } finally {
      setBusyAction('')
    }
  }

  const doHardClose = async () => {
    if (!period?.id || !canHardClose) {
      toast.error('لا تملك صلاحية الإغلاق النهائي للفترة.')
      return
    }
    if (isZakatEnabled && !acceptZakatPosting) {
      toast.error('يجب تأكيد مراجعة الزكاة قبل الإغلاق النهائي.')
      return
    }

    setBusyAction('hard-close')
    try {
      await api.post(`/finance/fiscal-periods/${period.id}/hard-close/`)
      toast.success('تم الإغلاق النهائي بنجاح')
      onComplete?.()
      onClose?.()
    } catch (error) {
      toast.error(parseApiErrorMessage(error, 'تعذر تنفيذ الإغلاق النهائي'))
    } finally {
      setBusyAction('')
    }
  }

  const doReopen = async () => {
    if (!period?.id || !canReopen) {
      toast.error('لا تملك صلاحية إعادة فتح الفترة.')
      return
    }
    if (!reopenReason.trim()) {
      toast.error('أدخل سبب إعادة فتح الفترة المالية.')
      return
    }

    setBusyAction('reopen')
    try {
      await api.post(`/finance/fiscal-periods/${period.id}/reopen/`, {
        reason: reopenReason.trim(),
      })
      toast.success('تمت إعادة فتح الفترة المالية')
      onComplete?.()
      onClose?.()
    } catch (error) {
      toast.error(parseApiErrorMessage(error, 'تعذر إعادة فتح الفترة المالية'))
    } finally {
      setBusyAction('')
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      dir="rtl"
    >
      <div className="w-full max-w-2xl space-y-5 rounded-3xl border border-gray-200 bg-white p-6 shadow-2xl dark:border-white/10 dark:bg-zinc-900">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-xl font-black text-gray-900 dark:text-white">
              <Lock className="h-5 w-5 text-red-600" />
              إدارة الفترة المالية
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-white/60">{periodTitle}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl p-2 hover:bg-gray-100 dark:hover:bg-white/10"
            aria-label="إغلاق"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        {isOpen ? (
          <div className="space-y-4">
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <div className="mb-1 flex items-center gap-2 font-bold">
                <AlertTriangle className="h-4 w-4" />
                الإغلاق المبدئي
              </div>
              <p>يتم نقل الفترة إلى وضع المراجعة قبل السماح بالإغلاق النهائي أو إعادة الفتح المحكومة.</p>
            </div>
            <button
              type="button"
              onClick={doSoftClose}
              disabled={busyAction === 'soft-close'}
              className="w-full rounded-xl bg-blue-600 py-3 font-bold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {busyAction === 'soft-close' ? 'جاري التنفيذ...' : 'تنفيذ الإغلاق المبدئي'}
            </button>
          </div>
        ) : null}

        {isSoftClosed ? (
          <div className="space-y-4">
            <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
              <div className="mb-1 flex items-center gap-2 font-bold">
                <Shield className="h-4 w-4" />
                الفترة في وضع الإغلاق المبدئي
              </div>
              <p>يمكن الآن إما الإغلاق النهائي وفق الصلاحيات أو إعادة فتح الفترة بسبب محكوم مع أثر تدقيقي.</p>
            </div>

            {isZakatEnabled ? (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
                <div className="mb-2 flex items-center gap-2 font-bold">
                  <Calculator className="h-4 w-4" />
                  مراجعة الزكاة
                </div>
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={acceptZakatPosting}
                    onChange={(event) => setAcceptZakatPosting(event.target.checked)}
                  />
                  أؤكد مراجعة احتساب الزكاة ومطابقته قبل الإغلاق النهائي.
                </label>
              </div>
            ) : null}

            <button
              type="button"
              onClick={doHardClose}
              disabled={busyAction === 'hard-close' || !canHardClose}
              className="w-full rounded-xl bg-red-700 py-3 font-bold text-white hover:bg-red-800 disabled:opacity-50"
            >
              {busyAction === 'hard-close' ? 'جاري الإغلاق...' : 'تنفيذ الإغلاق النهائي (Hard Close)'}
            </button>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/60">
              <div className="mb-2 flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-slate-100">
                <RotateCcw className="h-4 w-4" />
                إعادة فتح الفترة
              </div>
              <textarea
                value={reopenReason}
                onChange={(event) => setReopenReason(event.target.value)}
                rows={3}
                placeholder="اذكر سبب إعادة الفتح وأثره المحاسبي أو التشغيلي."
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
              />
              <button
                type="button"
                onClick={doReopen}
                disabled={busyAction === 'reopen' || !canReopen}
                className="mt-3 w-full rounded-xl border border-slate-300 py-3 font-bold text-slate-800 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-600 dark:text-slate-100 dark:hover:bg-slate-700"
              >
                {busyAction === 'reopen' ? 'جاري إعادة الفتح...' : 'إعادة فتح الفترة'}
              </button>
            </div>
          </div>
        ) : null}

        {isHardClosed ? (
          <div className="space-y-4">
            <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">
              <div className="mb-1 font-bold">الفترة مغلقة نهائياً</div>
              <p>أي إعادة فتح تتطلب سبباً واضحاً واعتماداً قطاعياً، وتبقى مسجلة في سجل التدقيق.</p>
            </div>

            <textarea
              value={reopenReason}
              onChange={(event) => setReopenReason(event.target.value)}
              rows={4}
              placeholder="سبب إعادة فتح الفترة المالية."
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
            />

            <button
              type="button"
              onClick={doReopen}
              disabled={busyAction === 'reopen' || !canReopen}
              className="w-full rounded-xl bg-slate-800 py-3 font-bold text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {busyAction === 'reopen' ? 'جاري إعادة الفتح...' : 'إعادة فتح الفترة'}
            </button>
          </div>
        ) : null}
      </div>
    </div>
  )
}

ClosingWizard.propTypes = {
  period: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    status: PropTypes.string,
    month: PropTypes.number,
    fiscal_year: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    fiscal_year_display: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  }),
  canHardClose: PropTypes.bool,
  canReopen: PropTypes.bool,
  onClose: PropTypes.func,
  onComplete: PropTypes.func,
}

ClosingWizard.defaultProps = {
  period: null,
  canHardClose: false,
  canReopen: false,
  onClose: null,
  onComplete: null,
}
