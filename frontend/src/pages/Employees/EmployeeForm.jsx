import { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import { safeRequest } from '../../api/client'
import { toast } from 'react-hot-toast'
import { X, RefreshCw, Save } from 'lucide-react'

export default function EmployeeForm({ employee, onClose, onSave, farmId }) {
  const [form, setForm] = useState({
    name: '',
    job_title: '',
    phone: '',
    email: '',
    daily_rate: '',
    is_active: true,
    farm: farmId,
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (employee) {
      setForm({
        name: employee.name || '',
        job_title: employee.job_title || '',
        phone: employee.phone || '',
        email: employee.email || '',
        daily_rate: employee.daily_rate || '',
        is_active: employee.is_active ?? true,
        farm: farmId,
      })
    }
  }, [employee, farmId])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name) {
      toast.error('اسم الموظف مطلوب')
      return
    }
    setSaving(true)
    try {
      if (employee?.id) {
        const result = await safeRequest('patch', `/employees/${employee.id}/`, form)
        toast.success(
          result?.queued
            ? 'تم حفظ التعديل في قائمة الإرسال، وسيتم مزامنته عند عودة الاتصال'
            : 'تم تحديث بيانات الموظف بنجاح'
        )
      } else {
        const result = await safeRequest('post', '/employees/', form)
        toast.success(
          result?.queued
            ? 'تم حفظ الإضافة في قائمة الإرسال، وسيتم مزامنته عند عودة الاتصال'
            : 'تم إضافة الموظف بنجاح'
        )
      }
      onSave()
    } catch (err) {
      console.error(err)
      toast.error(err.response?.data?.detail || 'فشل حفظ البيانات')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
      <div className="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-white/10 rounded-3xl w-full max-w-lg p-6 shadow-2xl scale-100 animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            {employee?.id ? 'تعديل بيانات الموظف' : 'إضافة موظف جديد'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-white/10 transition-colors"
            aria-label="إغلاق"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-white/60" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-gray-600 dark:text-white/60 text-sm font-medium mb-1.5">
              الاسم الكامل *
            </label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all"
              placeholder="اسم الموظف"
              aria-label="اسم الموظف"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-gray-600 dark:text-white/60 text-sm font-medium mb-1.5">
              المسمى الوظيفي
            </label>
            <input
              type="text"
              value={form.job_title}
              onChange={(e) => setForm({ ...form, job_title: e.target.value })}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all"
              placeholder="مثال: عامل زراعي، مشرف..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-gray-600 dark:text-white/60 text-sm font-medium mb-1.5">
                رقم الهاتف
              </label>
              <input
                type="tel"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all"
                placeholder="00967..."
              />
            </div>
            <div>
              <label className="block text-gray-600 dark:text-white/60 text-sm font-medium mb-1.5">
                البريد الإلكتروني
              </label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all"
                placeholder="email@example.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-gray-600 dark:text-white/60 text-sm font-medium mb-1.5">
              الأجر اليومي (ريال)
            </label>
            <input
              type="number"
              step="0.01"
              value={form.daily_rate}
              onChange={(e) => setForm({ ...form, daily_rate: e.target.value })}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl text-gray-900 dark:text-white focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all"
              placeholder="0.00"
            />
          </div>

          <div className="flex items-center gap-3 p-3 rounded-xl bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10">
            <input
              type="checkbox"
              id="is_active"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              className="w-5 h-5 rounded border-gray-300 dark:border-white/10 text-emerald-600 focus:ring-emerald-500 dark:bg-white/10"
            />
            <label
              htmlFor="is_active"
              className="text-gray-700 dark:text-white/90 font-medium cursor-pointer"
            >
              الموظف نشط حالياً
            </label>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 rounded-xl bg-gray-100 dark:bg-white/5 text-gray-700 dark:text-white/60 font-bold hover:bg-gray-200 dark:hover:bg-white/10 transition-all"
            >
              إلغاء
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold hover:from-blue-500 hover:to-indigo-500 transition-all flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {saving ? (
                <RefreshCw className="w-5 h-5 animate-spin" />
              ) : (
                <Save className="w-5 h-5" />
              )}
              {saving ? 'جاري الحفظ...' : 'حفظ البيانات'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

EmployeeForm.propTypes = {
  employee: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    name: PropTypes.string,
    job_title: PropTypes.string,
    phone: PropTypes.string,
    email: PropTypes.string,
    daily_rate: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    is_active: PropTypes.bool,
  }),
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  farmId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
}
