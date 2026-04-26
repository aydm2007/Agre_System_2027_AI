import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Assets } from '../api/client'
import { useFarmContext } from '../api/farmContext'
import { ArrowLeft, Save, Shield, Compass } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function AssetForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { selectedFarmId } = useFarmContext()
  const [loading, setLoading] = useState(false)

  const [formData, setFormData] = useState({
    name: '',
    category: 'Machinery',
    code: '',
    asset_type: 'general',
    purchase_value: 0,
    salvage_value: 0,
    useful_life_years: 5,
    depreciation_method: 'SL',
    operational_cost_per_hour: 0,
    status: 'ACTIVE'
  })

  useEffect(() => {
    if (id) {
      const fetchAsset = async () => {
        try {
          const { data } = await Assets.retrieve(id)
          setFormData({
            name: data.name || '',
            category: data.category || 'Machinery',
            code: data.code || '',
            asset_type: data.asset_type || 'general',
            purchase_value: data.purchase_value || 0,
            salvage_value: data.salvage_value || 0,
            useful_life_years: data.useful_life_years || 5,
            depreciation_method: data.depreciation_method || 'SL',
            operational_cost_per_hour: data.operational_cost_per_hour || 0,
            status: data.status || 'ACTIVE'
          })
        } catch (err) {
          toast.error('فشل تحميل الأصل')
          navigate('/assets')
        }
      }
      fetchAsset()
    }
  }, [id, navigate])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selectedFarmId) return toast.error('يرجى اختيار مزرعة أولاً')
    setLoading(true)

    try {
      const p = {
        ...formData,
        farm: selectedFarmId
      }
      if (id) {
        await Assets.update(id, p)
        toast.success('تم تحديث الأصل بنجاح')
      } else {
        await Assets.create(p)
        toast.success('تم تسجيل الأصل بنجاح')
      }
      navigate('/assets')
    } catch (err) {
      toast.error('حدث خطأ أثناء حفظ الأصل')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div dir="rtl" className="min-h-screen bg-gray-50 dark:bg-slate-900 p-8">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => navigate('/assets')}
              className="p-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl hover:bg-slate-50 dark:hover:bg-white/10 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-slate-600 dark:text-white/60" />
            </button>
            <div>
              <h1 className="text-3xl font-black bg-gradient-to-r from-teal-600 dark:from-teal-400 to-emerald-500 dark:to-emerald-300 bg-clip-text text-transparent">
                {id ? 'تعديل الأصل الثابت' : 'تسجيل أصل جديد'}
              </h1>
              <p className="text-slate-500 dark:text-zinc-500 font-medium text-sm mt-1">توجيه النظام لفتح بطاقة أصل مالي وحساب إهلاكه</p>
            </div>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-8 py-3 rounded-xl bg-teal-600 text-white font-bold shadow-lg shadow-teal-500/20 hover:bg-teal-500 transition-all"
          >
            <Save className="w-5 h-5" />
            {loading ? 'جاري الحفظ...' : 'حفظ وسجل الأصل'}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-zinc-900/80 p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
              <Compass className="w-5 h-5 text-teal-500" />
              البيانات الأساسية
            </h3>
            
            <div>
              <label className="block text-sm font-bold text-slate-500 dark:text-white/50 mb-2">اسم الأصل</label>
              <input
                required
                className="w-full bg-slate-50 border border-slate-200 dark:bg-white/5 dark:border-white/10 rounded-xl p-3 text-slate-800 dark:text-white focus:border-teal-500/50 focus:outline-none"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-bold text-slate-500 dark:text-white/50 mb-2">التصنيف المحاسبي</label>
                <select
                  className="w-full bg-slate-50 border border-slate-200 dark:bg-white/5 dark:border-white/10 rounded-xl p-3 text-slate-800 dark:text-white focus:border-teal-500/50"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                >
                  <option value="Machinery">آليات زراعية</option>
                  <option value="Vehicle">سيارات وشاحنات</option>
                  <option value="Solar">طاقة شمسية</option>
                  <option value="Irrigation">أنظمة ري</option>
                  <option value="Well">آبار مياه</option>
                  <option value="Facility">مباني ومرافق</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-500 dark:text-white/50 mb-2">كود الأصل (اختياري)</label>
                <input
                  className="w-full bg-slate-50 border border-slate-200 dark:bg-white/5 dark:border-white/10 rounded-xl p-3 text-slate-800 dark:text-white focus:border-teal-500/50"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                />
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-zinc-900/80 p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5 text-amber-500" />
              الاستهلاك والإهلاك المالي
            </h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-bold text-slate-500 dark:text-white/50 mb-2">القيمة الشرائية</label>
                <input
                  type="number"
                  step="0.01"
                  className="w-full bg-slate-50 border border-slate-200 dark:bg-white/5 dark:border-white/10 rounded-xl p-3 text-slate-800 dark:text-white focus:border-teal-500/50"
                  value={formData.purchase_value}
                  onChange={(e) => setFormData({ ...formData, purchase_value: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-500 dark:text-white/50 mb-2">القيمة التخريدية</label>
                <input
                  type="number"
                  step="0.01"
                  className="w-full bg-slate-50 border border-slate-200 dark:bg-white/5 dark:border-white/10 rounded-xl p-3 text-slate-800 dark:text-white focus:border-teal-500/50"
                  value={formData.salvage_value}
                  onChange={(e) => setFormData({ ...formData, salvage_value: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-bold text-slate-500 dark:text-white/50 mb-2">طريقة الإهلاك</label>
                <select
                  className="w-full bg-slate-50 border border-slate-200 dark:bg-white/5 dark:border-white/10 rounded-xl p-3 text-slate-800 dark:text-white focus:border-teal-500/50"
                  value={formData.depreciation_method}
                  onChange={(e) => setFormData({ ...formData, depreciation_method: e.target.value })}
                >
                  <option value="SL">القسط الثابت (SL)</option>
                  <option value="DB">القسط المتناقص (DB)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-500 dark:text-white/50 mb-2">العمر الافتراضي (سنوات)</label>
                <input
                  type="number"
                  className="w-full bg-slate-50 border border-slate-200 dark:bg-white/5 dark:border-white/10 rounded-xl p-3 text-slate-800 dark:text-white focus:border-teal-500/50"
                  value={formData.useful_life_years}
                  onChange={(e) => setFormData({ ...formData, useful_life_years: parseInt(e.target.value) || 5 })}
                />
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-white/10">
              <label className="block text-sm font-bold text-slate-500 dark:text-white/50 mb-2">تكلفة التشغيل التقديرية (للساعة)</label>
              <input
                type="number"
                step="0.01"
                className="w-full bg-slate-50 border border-slate-200 dark:bg-white/5 dark:border-white/10 rounded-xl p-3 text-slate-800 dark:text-white focus:border-teal-500/50"
                value={formData.operational_cost_per_hour}
                onChange={(e) => setFormData({ ...formData, operational_cost_per_hour: parseFloat(e.target.value) || 0 })}
              />
            </div>
          </div>
        </div>
      </form>
    </div>
  )
}
