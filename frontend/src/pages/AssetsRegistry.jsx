import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Assets } from '../api/client'
import { useFarmContext } from '../api/farmContext'
import { Plus, Search, Edit2, Compass } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function AssetsRegistry() {
  const navigate = useNavigate()
  const { selectedFarmId } = useFarmContext()
  const [assets, setAssets] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  const fetchAssets = useCallback(async () => {
    if (!selectedFarmId) return
    try {
      setLoading(true)
      const res = await Assets.list({ farm_id: selectedFarmId })
      setAssets(res.data.results || res.data || [])
    } catch (err) {
      toast.error('فشل تحميل قائمة الأصول')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId])

  useEffect(() => {
    if (selectedFarmId) {
      fetchAssets()
    } else {
      setAssets([])
    }
  }, [fetchAssets, selectedFarmId])

  const filtered = assets.filter(a => a.name.includes(searchTerm) || a.code?.includes(searchTerm))

  if (!selectedFarmId) {
    return (
      <div dir="rtl" className="app-page flex items-center justify-center">
        <div className="text-center space-y-4 max-w-md">
          <div className="p-4 bg-teal-100 dark:bg-teal-900/20 text-teal-600 dark:text-teal-400 rounded-full w-fit mx-auto">
            <Compass className="w-12 h-12" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">حدد المزرعة أولاً</h2>
          <p className="text-gray-500 dark:text-gray-400">لإدارة وتقديم الأصول الثابتة وتسجيلها.</p>
        </div>
      </div>
    )
  }

  const categoryMap = {
    Machinery: 'آليات', Vehicle: 'سيارات', Solar: 'طاقة', Well: 'بئر', Facility: 'مرافق', Irrigation: 'نظام ري'
  }

  return (
    <div dir="rtl" className="app-page space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-black bg-gradient-to-r from-teal-600 dark:from-teal-400 to-emerald-500 dark:to-emerald-300 bg-clip-text text-transparent">
            سجل الأصول المدخلة
          </h1>
          <p className="text-slate-500 font-medium mt-1">إدخال وإدارة أصول المزرعة الفردية</p>
        </div>
        <button
          onClick={() => navigate('/assets/new')}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-teal-600 text-white font-bold shadow-lg shadow-teal-500/20 hover:bg-teal-500 transition-all"
        >
          <Plus className="w-5 h-5" /> بناء أصل جديد
        </button>
      </div>

      <div className="app-panel p-4 flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="relative w-full md:w-80">
          <Search className="absolute right-4 top-3 w-5 h-5 text-slate-400" />
          <input
            type="text"
            placeholder="بحث بالاسم أو الكود..."
            className="app-input pl-4 pr-12"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="app-panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-end">
            <thead className="bg-slate-100/90 dark:bg-white/5 text-slate-600 dark:text-white/40 font-bold border-b border-slate-200 dark:border-white/10">
              <tr>
                <th className="px-6 py-4">اسم الأصل</th>
                <th className="px-6 py-4">التصنيف</th>
                <th className="px-6 py-4">الكود</th>
                <th className="px-6 py-4">القيمة الشرائية</th>
                <th className="px-6 py-4">العمر</th>
                <th className="px-6 py-4">إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="6" className="py-16 text-center text-slate-500">جاري التحميل...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan="6" className="py-16 text-center text-slate-500">لا توجد أصول مسجلة بهذه المطابقة</td></tr>
              ) : (
                filtered.map(a => (
                  <tr key={a.id} className="border-t border-slate-200 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/5 group">
                    <td className="px-6 py-4 font-bold text-slate-800 dark:text-white">{a.name}</td>
                    <td className="px-6 py-4 text-slate-600 dark:text-white/60 text-xs">
                      <span className="bg-teal-50 text-teal-600 border border-teal-200 px-2 py-1 rounded-md">{categoryMap[a.category] || a.category}</span>
                    </td>
                    <td className="px-6 py-4 font-mono text-slate-500 dark:text-white/50">{a.code || '-'}</td>
                    <td className="px-6 py-4 font-bold text-amber-500">{Number(a.purchase_value).toLocaleString()}</td>
                    <td className="px-6 py-4 text-slate-500 dark:text-white/50">{a.useful_life_years} سنوات</td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => navigate(`/assets/${a.id}`)}
                        className="p-2 text-slate-500 hover:text-teal-500 hover:bg-teal-50 rounded-lg transition-colors"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
