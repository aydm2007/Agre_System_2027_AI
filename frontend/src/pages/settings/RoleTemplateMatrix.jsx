import { useEffect, useState, useCallback } from 'react'
import api from '../../api/client'
import { useAuth } from '../../auth/AuthContext'

export default function RoleTemplateMatrix() {
  const { isSuperuser, isAdmin } = useAuth()
  const [permissionTemplates, setPermissionTemplates] = useState([])
  const [raciTemplates, setRaciTemplates] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [newTemplate, setNewTemplate] = useState({
    name: '',
    slug: '',
    description: '',
  })

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [permRes, raciRes] = await Promise.all([
        api.get('/governance/permission-templates/'),
        api.get('/governance/raci-templates/'),
      ])
      setPermissionTemplates(permRes.data?.results || permRes.data || [])
      setRaciTemplates(raciRes.data?.results || raciRes.data || [])
    } catch (err) {
      console.error(err)
      setError('تعذر تحميل بيانات القوالب.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const createTemplate = async (e) => {
    e.preventDefault()
    try {
      await api.post('/governance/permission-templates/', newTemplate)
      setNewTemplate({ name: '', slug: '', description: '' })
      setMessage('تم إنشاء قالب الصلاحيات بنجاح.')
      setError('')
      loadData()
    } catch (err) {
      console.error(err)
      setError('فشل في إنشاء قالب الصلاحيات.')
      setMessage('')
    }
  }

  const deleteTemplate = async (id) => {
    if (!window.confirm('هل أنت متأكد من حذف هذا القالب؟')) return
    try {
      await api.delete(`/governance/permission-templates/${id}/`)
      loadData()
    } catch (err) {
      console.error(err)
      setError('فشل حذف القالب.')
    }
  }

  if (!isSuperuser && !isAdmin) {
    return <div className="p-4 text-rose-600">غير مصرح بدخول هذه الصفحة.</div>
  }

  return (
    <div data-testid="role-template-matrix-page" className="space-y-8 animate-in fade-in duration-500">
      {loading && <div className="text-sm text-gray-500">جاري التحميل...</div>}

      {message && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-xl text-sm">
          {message}
        </div>
      )}

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-sm">
          {error}
        </div>
      )}

      {/* Permission Templates Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold">قوالب الصلاحيات</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {permissionTemplates.map((tpl) => (
            <div
              key={tpl.id}
              data-testid={`role-template-card-${tpl.id}`}
              className="p-4 border rounded-2xl bg-white dark:bg-slate-900 shadow-sm space-y-2 relative group"
            >
              <div className="flex justify-between">
                <span data-testid={`role-template-name-${tpl.id}`} className="font-bold text-primary">{tpl.name}</span>
                {tpl.is_system && (
                  <span className="text-[10px] bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-full">
                    نظامي
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 line-clamp-2">
                {tpl.description || 'لا يوجد وصف.'}
              </p>
              <div className="text-[11px] text-gray-400 mt-2">
                عدد المستخدمين: {tpl.user_count || 0}
              </div>
              {!tpl.is_system && (
                <button
                  onClick={() => deleteTemplate(tpl.id)}
                  className="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity text-rose-500 hover:text-rose-700"
                >
                  <span className="sr-only">حذف</span>
                  🗑️
                </button>
              )}
            </div>
          ))}

          {/* Create Form Card */}
          <form
            onSubmit={createTemplate}
            className="p-4 border-2 border-dashed border-gray-200 dark:border-slate-800 rounded-2xl bg-gray-50/50 dark:bg-slate-900/30 space-y-3"
          >
            <div className="text-sm font-semibold text-gray-600 dark:text-gray-400">
              إضافة قالب جديد
            </div>
            <input
              className="w-full text-xs p-2 border rounded-lg bg-white dark:bg-slate-800"
              placeholder="اسم القالب (مثلاً: محاسب مزرعة)"
              value={newTemplate.name}
              onChange={(e) => setNewTemplate((s) => ({ ...s, name: e.target.value }))}
              required
            />
            <input
              className="w-full text-xs p-2 border rounded-lg bg-white dark:bg-slate-800 font-mono"
              placeholder="role-template-slug"
              value={newTemplate.slug}
              onChange={(e) => setNewTemplate((s) => ({ ...s, slug: e.target.value }))}
              required
            />
            <p className="text-[11px] text-gray-500 dark:text-slate-400">
              يُستخدم هذا الحقل داخليًا فقط كمُعرّف تقني، ولا يظهر في بطاقات العرض الأساسية للمستخدم.
            </p>
            <textarea
              className="w-full text-xs p-2 border rounded-lg bg-white dark:bg-slate-800"
              placeholder="وصف القالب..."
              rows="2"
              value={newTemplate.description}
              onChange={(e) => setNewTemplate((s) => ({ ...s, description: e.target.value }))}
            />
            <button
              type="submit"
              className="w-full py-2 bg-primary text-white rounded-xl text-xs font-bold hover:bg-primary-dark transition-colors"
            >
              إضافة القالب
            </button>
          </form>
        </div>
      </section>

      {/* RACI Matrix Overview */}
      <section className="space-y-4 pt-6 border-t dark:border-slate-800">
        <h3 className="text-lg font-bold">ملخص قوالب الحوكمة RACI</h3>
        <div className="overflow-x-auto rounded-2xl border dark:border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-slate-800 text-right">
              <tr>
                <th className="p-3">اسم القالب</th>
                <th className="p-3">المستوى (Tier)</th>
                <th className="p-3">الإصدار</th>
                <th className="p-3">الحالة</th>
              </tr>
            </thead>
            <tbody>
              {raciTemplates.map((rt) => (
                <tr
                  key={rt.id}
                  className="border-t dark:border-slate-800 hover:bg-gray-50/50 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <td className="p-3 font-semibold">{rt.name}</td>
                  <td className="p-3 text-gray-500">{rt.tier}</td>
                  <td className="p-3 text-xs font-mono">{rt.version}</td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] ${rt.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'}`}
                    >
                      {rt.is_active ? 'نشط' : 'معطل'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-gray-400 italic">
          * يتم التحكم في مصفوفة RACI التفصيلية من خلال نظام الحوكمة في تبويب &quot;الحوكمة
          والسياسات&quot;.
        </p>
      </section>
    </div>
  )
}
