import { useEffect, useState, useMemo } from 'react'
import PropTypes from 'prop-types' // [AGRI-GUARDIAN] Enforce strict typing
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Crops, Farms, api } from '../api/client'
import FarmCropLinkModal from '../components/Crops/FarmCropLinkModal'
import { useToast } from '../components/ToastProvider'

const TEXT = {
  title: 'المحاصيل والعمليات',
  subtitle: 'إدارة المحاصيل والعمليات الزراعية المعتمدة لكل مزرعة',
  loading: 'جاري تحميل البيانات...',
  noFarms: 'لا توجد مزارع مسجلة',
  selectFarm: 'اختر مزرعة لعرض محاصيلها',
  farm: {
    cropsCount: (n) => `${n} محاصيل`,
    area: (n) => `${n} هكتار`,
  },
  crop: {
    perennial: 'أشجار (معمر)',
    seasonal: 'موسمي',
    varieties: 'الأصناف',
    tasks: 'إدارة المهام',
    plans: 'الخطط النشطة',
    noCropInfo: 'لا توجد تفاصيل',
  },
  tabs: {
    myFarms: 'مزارعي',
    catalog: 'دليل المحاصيل (عام)',
  },
  actions: {
    addCropToFarm: 'إضافة محصول للمزرعة',
    manageTasks: 'العمليات والمهام',
    viewDetails: 'التفاصيل',
    delete: 'حذف',
    configure: 'إعدادات',
  },
}

const normalizeFarm = (farm) => {
  const rawArea = farm?.area
  if (rawArea === null || rawArea === undefined || rawArea === '') {
    return { ...farm, area: null }
  }
  const normalizedArea = Number(rawArea)
  return {
    ...farm,
    area: Number.isFinite(normalizedArea) ? normalizedArea : null,
  }
}

// 🎨 Premium UI Components
const LoadingSkeleton = () => (
  <div className="min-h-screen bg-gray-50 dark:bg-slate-900 p-8 space-y-8 animate-pulse">
    <div className="h-20 w-1/3 bg-gray-200 dark:bg-white/5 rounded-2xl" />
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-48 bg-gray-200 dark:bg-white/5 rounded-3xl" />
      ))}
    </div>
  </div>
)

const FarmCard = ({ farm, isSelected, onClick }) => (
  <button
    onClick={onClick}
    className={`group relative overflow-hidden rounded-3xl p-6 text-end transition-all duration-300 w-full
      ${
        isSelected
          ? 'bg-emerald-600 shadow-2xl shadow-emerald-900/50 scale-[1.02] border-2 border-emerald-400'
          : 'bg-white dark:bg-zinc-900/60 hover:bg-gray-50 dark:hover:bg-zinc-800 border border-gray-200 dark:border-white/5 hover:border-emerald-500/30'
      }`}
    aria-label={`عرض محاصيل المزرعة: ${farm.name}`}
    aria-pressed={isSelected}
  >
    <div className="flex justify-between items-start mb-4">
      <div
        className={`p-3 rounded-xl text-2xl ${isSelected ? 'bg-white/20' : 'bg-emerald-500/10'}`}
      >
        🏡
      </div>
      {farm.area !== null && farm.area !== undefined && (
        <span
          className={`text-xs font-bold px-3 py-1 rounded-full ${isSelected ? 'bg-black/20 text-white' : 'bg-zinc-800 text-zinc-400'}`}
        >
          {TEXT.farm.area(farm.area)}
        </span>
      )}
    </div>
    <h3 className={`text-xl font-bold mb-1 ${isSelected ? 'text-white' : 'text-zinc-200'}`}>
      {farm.name}
    </h3>
    <p className={`text-sm ${isSelected ? 'text-emerald-100' : 'text-zinc-500'}`}>
      {farm.region || 'موقع غير محدد'}
    </p>
  </button>
)

FarmCard.propTypes = {
  farm: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    area: PropTypes.number,
    region: PropTypes.string,
  }).isRequired,
  isSelected: PropTypes.bool,
  onClick: PropTypes.func.isRequired,
}

const CropCard = ({ crop, onTasksClick, onVarietiesClick, activePlanCount }) => {
  const isPerennial = crop.is_perennial || crop.crop?.is_perennial
  const cropName = crop.name || crop.crop?.name
  const cropId = crop.crop?.id || crop.id // Handle both FarmCrop and direct Crop objects

  return (
    <article className="group relative bg-white dark:bg-[#131615] rounded-3xl p-1 border border-gray-200 dark:border-white/5 transition-all hover:bg-gray-50 dark:hover:bg-[#1a1e1c] hover:border-emerald-500/20">
      <div className="p-5 h-full flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-start mb-4">
          <div className="flex gap-4">
            <div
              className={`w-14 h-14 rounded-2xl flex items-center justify-center text-3xl shadow-lg
              ${isPerennial ? 'bg-gradient-to-br from-emerald-500/20 to-teal-500/20 text-emerald-400' : 'bg-gradient-to-br from-amber-500/20 to-orange-500/20 text-amber-400'}
            `}
            >
              {isPerennial ? '🌳' : '🌱'}
            </div>
            <div>
              <h4 className="text-xl font-bold text-gray-800 dark:text-white mb-1">{cropName}</h4>
              <span
                className={`text-xs px-2 py-0.5 rounded-md border ${
                  isPerennial
                    ? 'border-emerald-500/30 text-emerald-400'
                    : 'border-amber-500/30 text-amber-400'
                }`}
              >
                {isPerennial ? TEXT.crop.perennial : TEXT.crop.seasonal}
              </span>
            </div>
          </div>
        </div>

        {/* Stats / Info */}
        <div className="flex-1 space-y-3">
          {activePlanCount > 0 && (
            <div className="flex items-center gap-2 text-sm text-emerald-300 bg-emerald-500/10 px-3 py-2 rounded-xl">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              {activePlanCount} {TEXT.crop.plans}
            </div>
          )}
        </div>

        {/* Action Button */}
        <div className="mt-6 pt-4 border-t border-white/5 flex gap-2">
          {isPerennial && (
            <button
              onClick={() => onVarietiesClick && onVarietiesClick(cropId, cropName)}
              className="flex flex-1 flex-col sm:flex-row items-center justify-center gap-1 sm:gap-2 bg-emerald-50 dark:bg-emerald-900/20 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300 py-2 sm:py-3 rounded-xl font-medium transition-all text-sm border border-emerald-100 dark:border-emerald-800/30"
              aria-label={`إدارة أصناف ${cropName}`}
            >
              <span className="text-lg">🌿</span>
              <span>{TEXT.crop.varieties}</span>
            </button>
          )}
          <button
            onClick={() => onTasksClick(cropId)}
            className="flex-[1.5] flex items-center justify-center gap-2 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-700 text-gray-800 dark:text-white py-2 sm:py-3 rounded-xl font-medium transition-all group-hover:bg-emerald-600/90 group-hover:text-white group-hover:shadow-lg group-hover:shadow-emerald-900/20 text-sm"
            aria-label={`إدارة مهام وعمليات ${cropName}`}
          >
            <span>📋</span>
            <span>{TEXT.actions.manageTasks}</span>
          </button>
        </div>
      </div>
    </article>
  )
}

CropCard.propTypes = {
  crop: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string,
    is_perennial: PropTypes.bool,
    active_plan_count: PropTypes.number,
    crop: PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      is_perennial: PropTypes.bool,
    }),
  }).isRequired,
  onTasksClick: PropTypes.func.isRequired,
  onVarietiesClick: PropTypes.func,
  activePlanCount: PropTypes.number,
}

// 🌿 Varieties Modal Component
const CropVarietiesModal = ({ cropId, cropName, onClose }) => {
  const [varieties, setVarieties] = useState([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const toast = useToast()

  useEffect(() => {
    if (!cropId) return
    const fetchVars = async () => {
      try {
        const res = await api.get('/crop-varieties/', { params: { crop_id: cropId } })
        setVarieties(res.data?.results || res.data || [])
      } catch (err) {
        toast.error('تعذر تحميل الأصناف')
      } finally {
        setLoading(false)
      }
    }
    fetchVars()
  }, [cropId, toast])

  const handleAdd = async (e) => {
    e.preventDefault()
    if (!name.trim()) return
    setSaving(true)
    try {
      const res = await api.post('/crop-varieties/', { crop: cropId, name, notes })
      setVarieties((prev) => [...prev, res.data])
      setName('')
      setNotes('')
      toast.success('تمت إضافة الصنف بنجاح')
    } catch (err) {
      toast.error('حدث خطأ أثناء إضافة الصنف')
    } finally {
      setSaving(false)
    }
  }

  if (!cropId) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200" dir="rtl">
      <div className="bg-white dark:bg-slate-800 w-full max-w-lg rounded-3xl shadow-2xl border border-gray-100 dark:border-slate-700 flex flex-col overflow-hidden max-h-[90vh]">
        
        {/* Header */}
        <div className="p-5 border-b border-gray-100 dark:border-slate-700 flex justify-between items-center bg-emerald-50/50 dark:bg-emerald-900/10">
          <div>
            <h2 className="text-lg font-bold text-emerald-800 dark:text-emerald-400">إدارة أصناف: {cropName}</h2>
            <p className="text-xs text-gray-500 dark:text-slate-400">سجل الأصناف المعمرة المعتمدة لتسهيل الجرد</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-white bg-white dark:bg-slate-700 rounded-full p-2 shadow-sm border border-gray-100 dark:border-slate-600"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* List Body */}
        <div className="p-5 overflow-y-auto flex-1 bg-gray-50/30 dark:bg-slate-900/20">
          {loading ? (
            <div className="py-8 text-center text-gray-500 dark:text-slate-400 animate-pulse">جاري تحميل الأصناف...</div>
          ) : varieties.length === 0 ? (
            <div className="py-8 text-center border-2 border-dashed border-gray-200 dark:border-slate-600 rounded-xl text-gray-500 dark:text-slate-400 bg-white dark:bg-slate-800 text-sm">
              لا توجد أصناف مسجلة لهذا المحصول حتى الآن.
            </div>
          ) : (
            <div className="grid gap-3">
              {varieties.map((v) => (
                <div key={v.id} className="flex justify-between items-center p-3 sm:p-4 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm">
                  <div>
                    <h4 className="font-bold text-gray-800 dark:text-white">{v.name}</h4>
                    {v.notes && <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{v.notes}</p>}
                  </div>
                  <div className="text-[10px] text-gray-400 font-mono bg-gray-50 dark:bg-slate-900 px-2 py-1 rounded">#{v.id}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Add Form Footer */}
        <form onSubmit={handleAdd} className="p-5 border-t border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800">
          <h4 className="text-sm font-bold text-gray-800 dark:text-white mb-3">إضافة صنف جديد</h4>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="اسم الصنف (مثال: سكري، بلدي...)"
              className="flex-1 rounded-xl border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-700 text-gray-900 dark:text-white px-4 py-2.5 text-sm focus:ring-emerald-500"
            />
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="ملاحظات (اختياري)"
              className="flex-1 rounded-xl border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-700 text-gray-900 dark:text-white px-4 py-2.5 text-sm focus:ring-emerald-500"
            />
            <button
              type="submit"
              disabled={saving || !name.trim()}
              className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold rounded-xl shadow-md transition-all disabled:opacity-50 whitespace-nowrap"
            >
              {saving ? 'جاري الحفظ...' : '+ إضافة'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

CropVarietiesModal.propTypes = {
  cropId: PropTypes.number,
  cropName: PropTypes.string,
  onClose: PropTypes.func.isRequired,
}

export default function CropsPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const toast = useToast()

  // State
  const [loading, setLoading] = useState(true)
  const [farms, setFarms] = useState([])
  const [selectedFarmId, setSelectedFarmId] = useState(null)
  const [farmCrops, setFarmCrops] = useState({}) // Cache: { farmId: [crops] }
  const [cropsLoading, setCropsLoading] = useState(false)
  const [isLinkModalOpen, setIsLinkModalOpen] = useState(false)
  
  // Varieties Modal State
  const [varietiesModal, setVarietiesModal] = useState({ isOpen: false, cropId: null, cropName: '' })

  // Initial Load: Fetch Farms
  useEffect(() => {
    async function init() {
      try {
        const { data } = await Farms.list()
        const farmList = (data.results || data || []).map(normalizeFarm)
        setFarms(farmList)
        
        // [PHASE 11] Priority Selection: URL Param > First Farm
        const urlFarmId = searchParams.get('farmId')
        if (urlFarmId) {
          setSelectedFarmId(Number(urlFarmId))
          
          // Trigger add modal if flag is present
          if (searchParams.get('addCrop') === 'true') {
            setIsLinkModalOpen(true)
          }
        } else if (farmList.length > 0) {
          setSelectedFarmId(farmList[0].id)
        }
      } catch (error) {
        console.error('Failed to load farms', error)
        toast({ title: 'خطأ', message: 'تعذر تحميل المزارع', intent: 'error' })
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [toast, searchParams])

  // Fetch Crops when Farm changes
  useEffect(() => {
    if (!selectedFarmId) return
    if (farmCrops[selectedFarmId]) return // Use Cache

    async function loadFarmContext() {
      setCropsLoading(true)
      try {
        // We use Crops.list({ farm_id }) to get crops available/active for this farm
        // Alternatively, FarmCrops.list if specific "Plantings" are needed.
        // Based on current API client, Crops.list handles farm_id aggregation nicely.
        const { data } = await Crops.list({ farm_id: selectedFarmId })
        const crops = data.results || data || []

        setFarmCrops((prev) => ({ ...prev, [selectedFarmId]: crops }))
      } catch (error) {
        console.error('Failed to load crops', error)
      } finally {
        setCropsLoading(false)
      }
    }
    loadFarmContext()
  }, [farmCrops, selectedFarmId])

  const handleCropAdded = () => {
    // Invalidate cache for this farm to reload
    setFarmCrops((prev) => {
      const next = { ...prev }
      delete next[selectedFarmId]
      return next
    })
    // Re-trigger effect will handle load
    // But effect depends on [selectedFarmId], we just cleared cache.
    // We need to manually trigger load or just set farmCrops to null to trigger loading state?
    // Actually, simply clearing cache + the dependency array logic requires a bit of care.
    // The effect runs on 'selectedFarmId'. It won't re-run just because we cleared cache unless we trigger it.
    // Better: Helper function
  }

  // Reload helper
  useEffect(() => {
    if (selectedFarmId && !farmCrops[selectedFarmId]) {
      // This effect will catch the cache invalidation
      const reload = async () => {
        setCropsLoading(true)
        try {
          const { data } = await Crops.list({ farm_id: selectedFarmId })
          const crops = data.results || data || []
          setFarmCrops((prev) => ({ ...prev, [selectedFarmId]: crops }))
        } catch (e) {
          console.error(e)
        } finally {
          setCropsLoading(false)
        }
      }
      reload()
    }
  }, [farmCrops, selectedFarmId])

  const currentCrops = useMemo(() => {
    return selectedFarmId ? farmCrops[selectedFarmId] || [] : []
  }, [selectedFarmId, farmCrops])

  if (loading) return <LoadingSkeleton />

  return (
    <div
      dir="rtl"
      className="min-h-screen bg-gray-50 dark:bg-slate-900 text-gray-800 dark:text-white font-sans selection:bg-emerald-500/30"
    >
      {/* Header Area */}
      <header className="relative pt-12 pb-20 px-8 bg-gradient-to-b from-gray-100 dark:from-[#131615] to-gray-50 dark:to-slate-900">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
            <div>
              <h1 className="text-5xl font-black tracking-tight mb-2 bg-gradient-to-r from-emerald-600 dark:from-emerald-400 via-teal-400 dark:via-teal-200 to-amber-500 dark:to-amber-200 bg-clip-text text-transparent">
                {TEXT.title}
              </h1>
              <p className="text-gray-500 dark:text-zinc-500 text-lg max-w-2xl">{TEXT.subtitle}</p>
            </div>

            {/* Quick Stats or Actions could here */}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-8 -mt-12 space-y-12">
        {/* 1. Farm Selection Strip */}
        <section>
          <div className="flex items-center gap-3 overflow-x-auto pb-4 scrollbar-hide snap-x">
            {farms.length > 0 ? (
              farms.map((farm) => (
                <div key={farm.id} className="min-w-[280px] snap-start">
                  <FarmCard
                    farm={farm}
                    isSelected={selectedFarmId === farm.id}
                    onClick={() => setSelectedFarmId(farm.id)}
                  />
                </div>
              ))
            ) : (
              <div className="w-full text-center py-10 bg-gray-100 dark:bg-white/5 rounded-3xl border border-dashed border-gray-300 dark:border-white/10">
                <p className="text-gray-500 dark:text-zinc-500">{TEXT.noFarms}</p>
              </div>
            )}
          </div>
        </section>

        {/* 2. Selected Farm Context */}
        {selectedFarmId && (
          <section className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold flex items-center gap-3">
                <span className="w-2 h-8 bg-emerald-500 rounded-full" />
                محاصيل المزرعة
                {cropsLoading && (
                  <span className="text-xs font-normal text-zinc-500 animate-pulse">
                    {TEXT.loading}
                  </span>
                )}
              </h2>
              {/* <button className="text-emerald-400 hover:text-emerald-300 text-sm font-bold opacity-0 hover:opacity-100 transition-opacity">
                + إضافة محصول جديد
              </button> */}
              <button
                onClick={() => setIsLinkModalOpen(true)}
                className="text-emerald-600 dark:text-emerald-400 hover:text-emerald-500 text-sm font-bold flex items-center gap-1 bg-emerald-500/10 hover:bg-emerald-500/20 px-4 py-2 rounded-xl transition-all"
              >
                <span>+</span> {TEXT.actions.addCropToFarm}
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {!cropsLoading && currentCrops.length === 0 ? (
                <div className="col-span-full py-20 text-center bg-white dark:bg-[#131615] rounded-3xl border border-gray-200 dark:border-white/5 border-dashed">
                  <span className="text-6xl mb-4 block opacity-20 grayscale">🌱</span>
                  <p className="text-gray-500 dark:text-zinc-500 mb-4">
                    لا توجد محاصيل مرتبطة بهذه المزرعة
                  </p>
                  <button
                    className="px-6 py-2 bg-gray-100 dark:bg-white/5 hover:bg-gray-200 dark:hover:bg-white/10 rounded-full text-gray-600 dark:text-white/60 transition-colors"
                    aria-label="إضافة محصول جديد لهذه المزرعة"
                    onClick={() => setIsLinkModalOpen(true)}
                  >
                    {TEXT.actions.addCropToFarm}
                  </button>
                </div>
              ) : (
                currentCrops.map((crop) => (
                  <CropCard
                    key={crop.id}
                    crop={crop}
                    activePlanCount={crop.active_plan_count || 0}
                    onTasksClick={(id) => navigate(`/crops/${id}/tasks`)}
                    onVarietiesClick={(id, name) => setVarietiesModal({ isOpen: true, cropId: id, cropName: name })}
                  />
                ))
              )}

              {/* Add New Skeleton Card */}
              {/* <button className="group relative min-h-[250px] rounded-3xl border-2 border-dashed border-white/10 hover:border-emerald-500/50 flex flex-col items-center justify-center gap-4 text-zinc-600 hover:text-emerald-400 transition-all hover:bg-white/5">
                <span className="text-4xl group-hover:scale-110 transition-transform duration-300">+</span>
                <span className="font-bold">{TEXT.actions.addCropToFarm}</span>
              </button> */}
            </div>
          </section>
        )}

        <FarmCropLinkModal
          isOpen={isLinkModalOpen}
          onClose={() => setIsLinkModalOpen(false)}
          farmId={selectedFarmId}
          onSuccess={handleCropAdded}
        />

        {varietiesModal.isOpen && (
          <CropVarietiesModal
            cropId={varietiesModal.cropId}
            cropName={varietiesModal.cropName}
            onClose={() => setVarietiesModal({ isOpen: false, cropId: null, cropName: '' })}
          />
        )}
      </main>
    </div>
  )
}
