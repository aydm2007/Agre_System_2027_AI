import { useCallback, useEffect, useState } from 'react'
import { Audit } from '../api/client'

export default function AuditPage() {
  const [rows, setRows] = useState([])
  const [q, setQ] = useState({ action: '', user: '', model: '' })
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    const params = {}
    if (q.action) params.action = q.action
    if (q.user) params.user = q.user
    if (q.model) params.model = q.model

    try {
      const { data } = await Audit.list(params)
      setRows(data.results || data)
    } catch (error) {
      console.error('Error loading audit logs:', error)
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [q])

  useEffect(() => {
    load()
  }, [load])

  const getUserName = (row) => {
    if (row.user_details && row.user_details.full_name) {
      return row.user_details.full_name
    }
    if (!row.user) return '-'
    return `User ${row.user}`
  }

  const getActionName = (action) => {
    const actions = {
      create: 'إنشاء',
      update: 'تحديث',
      delete: 'حذف',
      view: 'عرض',
      login: 'دخول',
      logout: 'خروج',
      add: 'إضافة',
      edit: 'تعديل',
      remove: 'إزالة',
    }
    return actions[action] || action
  }

  const getActionBadge = (action) => {
    const styles = {
      create:
        'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800',
      update:
        'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800',
      delete:
        'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800',
      view: 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300 border-gray-200 dark:border-slate-600',
      login:
        'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 border-purple-200 dark:border-purple-800',
      logout:
        'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800',
    }
    return styles[action] || 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300'
  }

  const getModelName = (model) => {
    const models = {
      Farm: 'مزرعة',
      Crop: 'محصول',
      Location: 'موقع',
      Asset: 'أصل',
      Task: 'مهمة',
      User: 'مستخدم',
      DailyLog: 'سجل يومي',
      Activity: 'نشاط',
      AuditLog: 'سجل تدقيق',
    }
    return models[model] || model
  }

  return (
    <section className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">سجل التدقيق</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            تتبع جميع العمليات والتغييرات في النظام
          </p>
        </div>
        <div className="text-sm text-gray-500 dark:text-slate-400">{rows.length} سجل</div>
      </div>

      {/* Filters Card */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[150px]">
            <label className="block text-xs font-medium text-gray-600 dark:text-slate-400 mb-1">
              العملية
            </label>
            <select
              className="w-full border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
              value={q.action}
              onChange={(e) => setQ({ ...q, action: e.target.value })}
            >
              <option value="">كل العمليات</option>
              <option value="create">إنشاء</option>
              <option value="update">تحديث</option>
              <option value="delete">حذف</option>
              <option value="view">عرض</option>
              <option value="login">دخول</option>
              <option value="logout">خروج</option>
            </select>
          </div>

          <div className="flex-1 min-w-[150px]">
            <label className="block text-xs font-medium text-gray-600 dark:text-slate-400 mb-1">
              المستخدم
            </label>
            <input
              className="w-full border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white rounded-lg p-2.5 text-sm placeholder:text-gray-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
              placeholder="معرف المستخدم"
              value={q.user}
              onChange={(e) => setQ({ ...q, user: e.target.value })}
            />
          </div>

          <div className="flex-1 min-w-[150px]">
            <label className="block text-xs font-medium text-gray-600 dark:text-slate-400 mb-1">
              الموديل
            </label>
            <select
              className="w-full border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
              value={q.model}
              onChange={(e) => setQ({ ...q, model: e.target.value })}
            >
              <option value="">كل الموديلات</option>
              <option value="Farm">مزرعة</option>
              <option value="Crop">محصول</option>
              <option value="Location">موقع</option>
              <option value="Asset">أصل</option>
              <option value="Task">مهمة</option>
              <option value="User">مستخدم</option>
              <option value="DailyLog">سجل يومي</option>
              <option value="Activity">نشاط</option>
            </select>
          </div>

          <button
            className="px-5 py-2.5 bg-primary hover:bg-primary/90 text-white rounded-lg font-medium shadow-sm transition-all disabled:opacity-60"
            onClick={load}
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                جاري...
              </span>
            ) : (
              'تطبيق'
            )}
          </button>
        </div>
      </div>

      {/* Table Card */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-slate-700/50 text-end border-b border-gray-200 dark:border-slate-700">
                <th className="px-4 py-3 font-semibold text-gray-600 dark:text-slate-300">الوقت</th>
                <th className="px-4 py-3 font-semibold text-gray-600 dark:text-slate-300">
                  المستخدم
                </th>
                <th className="px-4 py-3 font-semibold text-gray-600 dark:text-slate-300">
                  العملية
                </th>
                <th className="px-4 py-3 font-semibold text-gray-600 dark:text-slate-300">
                  الموديل
                </th>
                <th className="px-4 py-3 font-semibold text-gray-600 dark:text-slate-300">
                  التفاصيل
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
              {rows.map((r, i) => (
                <tr
                  key={i}
                  className="hover:bg-gray-50/50 dark:hover:bg-slate-700/30 transition-colors"
                >
                  <td className="px-4 py-3 text-gray-700 dark:text-slate-300 whitespace-nowrap">
                    <span className="font-mono text-xs">
                      {new Date(r.timestamp).toLocaleString('ar-SA')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-900 dark:text-white font-medium">
                    {getUserName(r)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${getActionBadge(r.action)}`}
                    >
                      {getActionName(r.action)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-700 dark:text-slate-300">
                    {getModelName(r.model)}
                  </td>
                  <td className="px-4 py-3">
                    {r.changes && (
                      <div
                        className="text-xs text-gray-500 dark:text-slate-400 max-w-xs truncate font-mono"
                        title={r.changes}
                      >
                        {r.changes}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan="5" className="px-4 py-12 text-center">
                    <div className="text-gray-400 dark:text-slate-500 text-lg mb-2">📋</div>
                    <p className="text-gray-500 dark:text-slate-400">
                      {loading ? 'جاري التحميل...' : 'لا توجد سجلات'}
                    </p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
