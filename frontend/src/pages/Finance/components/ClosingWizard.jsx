import { useMemo, useState } from 'react'
import PropTypes from 'prop-types'
import { api } from '../../../api/client'
import { toast } from 'react-hot-toast'
import { AlertTriangle, CheckCircle2, Lock, Calculator, X } from 'lucide-react'
import { useSettings } from '../../../contexts/SettingsContext'

const parseApiErrorMessage = (error, fallback = 'تعذر إتمام العملية.') => {
  const payload = error?.response?.data
  if (!payload) return error?.message || fallback
  if (typeof payload === 'string' && payload.trim()) return payload
  const detail = payload?.detail
  if (Array.isArray(detail)) return detail.join(' - ')
  if (typeof detail === 'string' && detail.trim()) return detail
  return fallback
}

const StepBadge = ({ label, active, done, index }) => (
  <div className="flex items-center gap-2">
    <div
      className={`h-8 w-8 rounded-full border flex items-center justify-center text-xs font-bold ${
        done
          ? 'bg-emerald-600 border-emerald-600 text-white'
          : active
            ? 'border-blue-600 text-blue-600 bg-blue-50'
            : 'border-gray-300 text-gray-400 bg-white'
      }`}
    >
      {done ? <CheckCircle2 className="w-4 h-4" /> : index}
    </div>
    <span className={`text-xs ${active ? 'text-blue-700 font-bold' : 'text-gray-500'}`}>
      {label}
    </span>
  </div>
)

StepBadge.propTypes = {
  label: PropTypes.string.isRequired,
  active: PropTypes.bool,
  done: PropTypes.bool,
  index: PropTypes.number.isRequired,
}

StepBadge.defaultProps = {
  active: false,
  done: false,
}

export default function ClosingWizard({ period, canHardClose, onClose, onComplete }) {
  const [step, setStep] = useState(1)
  const [busy, setBusy] = useState(false)
  const [softClosed, setSoftClosed] = useState(period?.status === 'soft_close')
  const [acceptZakatPosting, setAcceptZakatPosting] = useState(false)
  const { isZakatEnabled } = useSettings()

  const periodTitle = useMemo(() => {
    if (!period) return ''
    return `الفترة ${period.month}/${period.fiscal_year || ''}`.trim()
  }, [period])

  const doSoftClose = async () => {
    if (!period?.id) return
    setBusy(true)
    try {
      await api.post(`/finance/fiscal-periods/${period.id}/soft-close/`)
      setSoftClosed(true)
      setStep(isZakatEnabled ? 2 : 3)
      toast.success('تم تنفيذ الإغلاق المبدئي للفترة')
    } catch (error) {
      toast.error(parseApiErrorMessage(error, 'تعذر تنفيذ الإغلاق المبدئي'))
    } finally {
      setBusy(false)
    }
  }

  const goNextToHardClose = () => {
    if (isZakatEnabled && !acceptZakatPosting) {
      toast.error('يجب تأكيد مراجعة الزكاة قبل المتابعة.')
      return
    }
    if (!canHardClose) {
      toast.error('لا تملك صلاحية الإغلاق النهائي للفترة.')
      return
    }
    setStep(3)
  }

  const doHardClose = async () => {
    if (!period?.id) return
    if (!canHardClose) {
      toast.error('لا تملك صلاحية الإغلاق النهائي للفترة.')
      return
    }
    setBusy(true)
    try {
      await api.post(`/finance/fiscal-periods/${period.id}/hard-close/`)
      toast.success('تم الإغلاق النهائي بنجاح')
      onComplete?.()
      onClose?.()
    } catch (error) {
      toast.error(parseApiErrorMessage(error, 'تعذر تنفيذ الإغلاق النهائي'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      dir="rtl"
    >
      <div className="w-full max-w-2xl rounded-3xl bg-white dark:bg-zinc-900 border border-gray-200 dark:border-white/10 shadow-2xl p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-black text-gray-900 dark:text-white flex items-center gap-2">
              <Lock className="w-5 h-5 text-red-600" /> معالج الإغلاق الثلاثي
            </h2>
            <p className="text-sm text-gray-500 dark:text-white/60 mt-1">{periodTitle}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-white/10"
            aria-label="إغلاق"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex gap-3 flex-wrap">
          <StepBadge
            index={1}
            label="الإغلاق المبدئي"
            active={step === 1}
            done={step > 1 || softClosed}
          />
          {isZakatEnabled && (
            <StepBadge index={2} label="مراجعة الزكاة" active={step === 2} done={step > 2} />
          )}
          <StepBadge
            index={isZakatEnabled ? 3 : 2}
            label="الإغلاق النهائي"
            active={step === 3}
            done={false}
          />
        </div>

        {step === 1 && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-800 text-sm">
              <div className="flex items-center gap-2 font-bold mb-1">
                <AlertTriangle className="w-4 h-4" />
                مراجعة ما قبل الإغلاق
              </div>
              <p>سيتم تنفيذ Soft Close أولاً. لا يمكن الانتقال إلى Hard Close مباشرة.</p>
            </div>
            <button
              type="button"
              onClick={doSoftClose}
              disabled={busy || softClosed}
              className="w-full rounded-xl bg-blue-600 hover:bg-blue-700 text-white py-3 font-bold disabled:opacity-50"
            >
              {softClosed
                ? 'تم الإغلاق المبدئي'
                : busy
                  ? 'جاري التنفيذ...'
                  : 'تنفيذ الإغلاق المبدئي'}
            </button>
          </div>
        )}

        {isZakatEnabled && step === 2 && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-900 text-sm">
              <div className="flex items-center gap-2 font-bold mb-1">
                <Calculator className="w-4 h-4" />
                مراجعة الزكاة
              </div>
              <p>
                راجع قيد الزكاة المولد من الخادم (5% أو 10% وفق سياسة الري) قبل الإغلاق النهائي.
              </p>
            </div>

            <label className="flex items-start gap-3 text-sm text-gray-700 dark:text-white/80">
              <input
                type="checkbox"
                className="mt-1"
                checked={acceptZakatPosting}
                onChange={(e) => setAcceptZakatPosting(e.target.checked)}
              />
              أؤكد مراجعة احتساب الزكاة ومطابقته قبل الإغلاق النهائي.
            </label>

            <button
              type="button"
              onClick={goNextToHardClose}
              className="w-full rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white py-3 font-bold"
            >
              متابعة إلى الإغلاق النهائي
            </button>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-red-800 text-sm">
              <div className="font-bold mb-1">تحذير نهائي</div>
              <p>
                هذه العملية غير قابلة للتراجع. أي تصحيح لاحق يجب أن يكون بقيد عكسي في فترة مفتوحة.
              </p>
            </div>
            <button
              type="button"
              onClick={doHardClose}
              disabled={busy}
              className="w-full rounded-xl bg-red-700 hover:bg-red-800 text-white py-3 font-bold disabled:opacity-50"
            >
              {busy ? 'جاري الإغلاق...' : 'تنفيذ الإغلاق النهائي (Hard Close)'}
            </button>
          </div>
        )}
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
  }),
  canHardClose: PropTypes.bool,
  onClose: PropTypes.func,
  onComplete: PropTypes.func,
}

ClosingWizard.defaultProps = {
  period: null,
  canHardClose: false,
  onClose: null,
  onComplete: null,
}
