import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CropCards, CropProducts, Farms, Items } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useToast } from '../components/ToastProvider'

const TEXT = {
  title: 'بطاقات أداء المحاصيل',
  subtitle: 'إدارة ذكية للمحاصيل والإنتاجية',
  farmLabel: 'اختر المزرعة',
  services: 'الخدمات الزراعية',
  products: 'المنتجات المرتبطة',
  addProductPlaceholder: 'اختر منتجاً لإضافته',
  addProductAction: 'ربط المنتج',
  primaryBadge: 'أساسي',
  makePrimary: 'تعيين كأساسي',
  removeLink: 'إزالة',
  summaryServices: 'إجمالي الخدمات',
  summaryMachinery: 'خدمات تتطلب أصولاً',
  summaryProducts: 'المنتجات المرتبطة',
  assetTagsLabel: 'أنواع الأصول المطلوبة',
  statusReady: 'المحصول جاهز',
  statusNeedsServices: 'يحتاج خدمات',
  statusNeedsProducts: 'يحتاج منتجات',
  timelineTitle: 'أحدث الأنشطة',
  timelineEmpty: 'لا توجد أنشطة مسجلة',
  timelineScope: 'نوع الخدمة',
  timelineTaskFallback: 'خدمة بدون مهمة',
  productCategoryLabel: 'التصنيف',
  cardEmptyServices: 'لا توجد خدمات مرتبطة',
  cardEmptyProducts: 'لم يتم ربط أي منتجات',
  loading: 'جاري التحميل...',
  error: 'تعذر تحميل البيانات',
  successLinked: 'تم ربط المنتج بنجاح',
  successPrimary: 'تم تحديث المنتج الأساسي',
  successRemoved: 'تم إزالة الربط',
  confirmRemove: 'هل أنت متأكد من إزالة الربط؟',
  noFarms: 'لا توجد مزارع متاحة',
  ROI: 'مؤشر العائد (ROI)',
  TotalCost: 'إجمالي المصروفات',
  ExpectedRevenue: 'الإيراد المتوقع',
  activePlans: 'خطط نشطة',
  logActivity: 'تسجيل نشاط',
  newPlan: 'خطة جديدة',
}

// Premium Loading Skeleton
const LoadingSkeleton = () => (
  <div className="min-h-screen bg-gray-50 dark:bg-slate-900 p-8">
    <div className="animate-pulse space-y-6">
      <div className="h-12 w-64 bg-gray-200 dark:bg-slate-700 rounded-xl" />
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="h-96 bg-gray-200 dark:bg-slate-800 rounded-3xl" />
        ))}
      </div>
    </div>
  </div>
)

// Premium Card Component
const PremiumCropCard = ({
  card,
  selectedFarm,
  availableItems,
  productSelection,
  setProductSelection,
  onAddProduct,
  onMarkPrimary,
  onRemoveLink,
  navigate,
  formatTimelineDate,
}) => {
  const servicesTotal = card.metrics?.services_total ?? card.services?.length ?? 0
  const productsTotal = card.metrics?.products_total ?? card.products?.length ?? 0
  const roiValue = card.roi_percentage || 0
  const isPositiveROI = roiValue >= 0

  // Status determination
  let statusConfig = { label: TEXT.statusReady, color: 'emerald' }
  if (!servicesTotal) {
    statusConfig = { label: TEXT.statusNeedsServices, color: 'amber' }
  } else if (!productsTotal) {
    statusConfig = { label: TEXT.statusNeedsProducts, color: 'amber' }
  }

  return (
    <article className="group relative overflow-hidden rounded-3xl border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 shadow-lg dark:shadow-2xl transition-all duration-500 hover:shadow-emerald-500/10 hover:border-emerald-500/30 hover:-translate-y-1">
      {/* Card Header with Image */}
      <div className="h-48 relative overflow-hidden">
        {card.image_url ? (
          <img
            src={card.image_url}
            alt={card.name}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-emerald-100 dark:from-emerald-900/40 to-gray-100 dark:to-slate-800 flex items-center justify-center">
            <span className="text-7xl opacity-30 group-hover:scale-125 transition-transform duration-500">
              {card.is_perennial ? '🌳' : '🌱'}
            </span>
          </div>
        )}

        {/* Overlay gradient */}
        <div className="absolute inset-0 bg-gradient-to-t from-white dark:from-slate-800 via-transparent to-transparent" />

        {/* Code Badge */}
        <div className="absolute top-4 left-4 px-3 py-1.5 rounded-xl bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border border-gray-200 dark:border-slate-600 text-[11px] font-bold text-gray-800 dark:text-slate-200">
          {card.code}
        </div>

        {/* Status Badge */}
        <div
          className={`absolute top-4 right-4 px-3 py-1.5 rounded-xl text-[11px] font-bold backdrop-blur-md border ${
            statusConfig.color === 'emerald'
              ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
              : 'bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30'
          }`}
        >
          {statusConfig.label}
        </div>

        {/* Crop Name */}
        <div className="absolute bottom-4 left-4 right-4">
          <h2 className="text-2xl font-black text-gray-800 dark:text-white drop-shadow-lg">
            {card.name}
          </h2>
          <p className="text-sm text-gray-600 dark:text-slate-400 mt-1">
            {card.active_plan_count || 0} {TEXT.activePlans}
          </p>
        </div>
      </div>

      {/* Card Body */}
      <div className="p-5 space-y-5">
        {/* Financial Metrics */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-4 rounded-2xl bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600">
            <p className="text-[10px] font-bold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {TEXT.TotalCost}
            </p>
            <p className="text-xl font-black text-gray-800 dark:text-white mt-1">
              {(card.total_cost || 0).toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
              <span className="text-xs text-gray-400 dark:text-slate-400 me-1">ر.ي</span>
            </p>
          </div>
          <div className="p-4 rounded-2xl bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600">
            <p className="text-[10px] font-bold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {TEXT.ROI}
            </p>
            <p
              className={`text-xl font-black mt-1 ${isPositiveROI ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}
            >
              {isPositiveROI ? '+' : ''}
              {roiValue}%
            </p>
          </div>
        </div>

        {/* ROI Progress Bar */}
        <div className="space-y-2">
          <div className="h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-1000 ${isPositiveROI ? 'bg-gradient-to-r from-emerald-500 to-teal-400' : 'bg-gradient-to-r from-rose-500 to-orange-400'}`}
              style={{ width: `${Math.min(Math.abs(roiValue), 100)}%` }}
            />
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => {
              const params = new URLSearchParams()
              params.set('farm', selectedFarm)
              params.set('crop', card.id)
              navigate?.(`/daily-log?${params.toString()}`)
            }}
            className="flex-1 py-3 rounded-xl bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400 text-sm font-bold hover:bg-emerald-200 dark:hover:bg-emerald-900/60 transition-colors border border-emerald-200 dark:border-emerald-700"
          >
            📝 {TEXT.logActivity}
          </button>
          <button
            onClick={() => navigate?.(`/plans/new?crop_id=${card.id}&farm_id=${selectedFarm}`)}
            className="flex-1 py-3 rounded-xl bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300 text-sm font-bold hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors border border-gray-200 dark:border-slate-600"
          >
            📅 {TEXT.newPlan}
          </button>
        </div>

        {/* Timeline Section */}
        <div className="space-y-3">
          <h3 className="text-sm font-bold text-gray-700 dark:text-slate-300">
            {TEXT.timelineTitle}
          </h3>
          {Array.isArray(card.service_timeline) && card.service_timeline.length ? (
            <div className="space-y-2 max-h-32 overflow-y-auto custom-scrollbar">
              {card.service_timeline.slice(0, 3).map((event, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 rounded-xl bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 dark:bg-emerald-400" />
                    <span className="text-xs text-gray-700 dark:text-slate-300">
                      {event.task_name || TEXT.timelineTaskFallback}
                    </span>
                  </div>
                  <span className="text-[10px] text-gray-400 dark:text-slate-500 font-mono">
                    {formatTimelineDate(event.date)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-400 dark:text-slate-500 italic">{TEXT.timelineEmpty}</p>
          )}
        </div>

        {/* Products Section */}
        <div className="space-y-3">
          <h3 className="text-sm font-bold text-gray-700 dark:text-slate-300">{TEXT.products}</h3>
          {card.products?.length > 0 ? (
            <div className="space-y-2 max-h-24 overflow-y-auto custom-scrollbar">
              {card.products.map((product) => (
                <div
                  key={product.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-800 dark:text-white font-medium">
                      {product.name}
                    </span>
                    {product.is_primary && (
                      <span className="px-2 py-0.5 text-[9px] font-bold bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 rounded-full">
                        {TEXT.primaryBadge}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-1">
                    {!product.is_primary && (
                      <button
                        onClick={() => onMarkPrimary(product.id)}
                        className="text-[10px] px-2 py-1 rounded-lg bg-gray-100 dark:bg-slate-700 text-amber-600 dark:text-amber-400 hover:bg-gray-200 dark:hover:bg-slate-600"
                      >
                        {TEXT.makePrimary}
                      </button>
                    )}
                    <button
                      onClick={() => onRemoveLink(product.id)}
                      className="text-[10px] px-2 py-1 rounded-lg bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400 hover:bg-rose-200 dark:hover:bg-rose-900/50"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-400 dark:text-slate-500 italic">
              {TEXT.cardEmptyProducts}
            </p>
          )}

          {/* Add Product */}
          <div className="flex gap-2">
            <select
              className="flex-1 px-3 py-2 rounded-xl bg-gray-100 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 text-sm text-gray-800 dark:text-white appearance-none cursor-pointer hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
              value={productSelection[card.id] || ''}
              onChange={(e) =>
                setProductSelection((prev) => ({ ...prev, [card.id]: e.target.value }))
              }
            >
              <option value="">{TEXT.addProductPlaceholder}</option>
              {availableItems.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => onAddProduct(card.id)}
              disabled={!productSelection[card.id]}
              className="px-4 py-2 rounded-xl bg-emerald-500 text-white text-sm font-bold hover:bg-emerald-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              +
            </button>
          </div>
        </div>
      </div>

      {/* Decorative glow */}
      <div className="absolute -bottom-20 -right-20 w-40 h-40 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
    </article>
  )
}

export default function CropCardsPage() {
  const auth = useAuth()
  const addToast = useToast()
  const navigate = useNavigate()

  const [farms, setFarms] = useState([])
  const [selectedFarm, setSelectedFarm] = useState('')
  const [cards, setCards] = useState([])
  const [itemOptions, setItemOptions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [productSelection, setProductSelection] = useState({})

  const loadCards = useCallback(async (farmId) => {
    if (!farmId) {
      setCards([])
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await CropCards.list({ farm_id: farmId })
      setCards(response.data ?? [])
    } catch (err) {
      console.error('Failed to load crop cards', err)
      setError(TEXT.error)
      setCards([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void (async () => {
      try {
        const [farmsResponse, itemsResponse] = await Promise.all([
          Farms.list(),
          Items.list({ group: 'Harvested Product' }),
        ])

        const allFarms = farmsResponse.data?.results ?? farmsResponse.data ?? []
        const accessible = allFarms.filter(
          (farm) => auth.hasFarmAccess(farm.id) || auth.isAdmin || auth.isSuperuser,
        )
        setFarms(accessible)
        if (accessible.length > 0) {
          const firstId = String(accessible[0].id)
          setSelectedFarm(firstId)
          loadCards(firstId)
        } else {
          setLoading(false)
        }

        const rawProducts = itemsResponse.data?.results ?? itemsResponse.data ?? []
        const normalisedProducts = rawProducts.map((item) => ({
          ...item,
          uom: item.unit_detail?.symbol || item.uom || '',
        }))
        setItemOptions(normalisedProducts)
      } catch (err) {
        console.error('Failed to bootstrap crop cards page', err)
        setError(TEXT.error)
        setLoading(false)
      }
    })()
  }, [auth, loadCards])

  useEffect(() => {
    if (selectedFarm) {
      loadCards(selectedFarm)
    }
  }, [selectedFarm, loadCards])

  const unusedItemsByCrop = useMemo(() => {
    const map = {}
    cards.forEach((card) => {
      const usedIds = new Set(card.products?.map((product) => product.item_id) || [])
      map[card.id] = itemOptions.filter(
        (item) => item.group === 'Harvested Product' && !usedIds.has(item.id),
      )
    })
    return map
  }, [cards, itemOptions])

  const formatTimelineDate = useCallback((value) => {
    if (!value) return '—'
    try {
      return new Date(value).toLocaleDateString('ar-SA')
    } catch {
      return String(value)
    }
  }, [])

  const handleAddProduct = useCallback(
    async (cropId) => {
      const itemId = productSelection[cropId]
      if (!itemId || !selectedFarm) return
      try {
        await CropProducts.create({ crop: cropId, item: itemId, farm: selectedFarm })
        addToast({ intent: 'success', message: TEXT.successLinked })
        setProductSelection((prev) => ({ ...prev, [cropId]: '' }))
        loadCards(selectedFarm)
      } catch (err) {
        console.error('Failed to link product', err)
        addToast({ intent: 'error', message: TEXT.error })
      }
    },
    [addToast, loadCards, productSelection, selectedFarm],
  )

  const handleMarkPrimary = useCallback(
    async (linkId) => {
      try {
        await CropProducts.update(linkId, { is_primary: true })
        addToast({ intent: 'success', message: TEXT.successPrimary })
        loadCards(selectedFarm)
      } catch (err) {
        console.error('Failed to mark primary product', err)
        addToast({ intent: 'error', message: TEXT.error })
      }
    },
    [addToast, loadCards, selectedFarm],
  )

  const handleRemoveLink = useCallback(
    async (linkId) => {
      if (!window.confirm(TEXT.confirmRemove)) return
      try {
        await CropProducts.remove(linkId)
        addToast({ intent: 'success', message: TEXT.successRemoved })
        loadCards(selectedFarm)
      } catch (err) {
        console.error('Failed to remove product link', err)
        addToast({ intent: 'error', message: TEXT.error })
      }
    },
    [addToast, loadCards, selectedFarm],
  )

  if (loading) return <LoadingSkeleton />

  if (!farms.length) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 p-8 flex items-center justify-center">
        <div className="text-center">
          <span className="text-6xl mb-4 block">🌾</span>
          <h1 className="text-2xl font-bold text-gray-800 dark:text-white">{TEXT.title}</h1>
          <p className="text-gray-500 dark:text-white/50 mt-2">{TEXT.noFarms}</p>
        </div>
      </div>
    )
  }

  return (
    <div dir="rtl" className="min-h-screen bg-gray-50 dark:bg-slate-900 p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-black tracking-tight bg-gradient-to-r from-emerald-600 dark:from-emerald-400 to-amber-500 dark:to-amber-200 bg-clip-text text-transparent">
            {TEXT.title}
          </h1>
          <p className="text-gray-500 dark:text-slate-400 font-medium mt-1">{TEXT.subtitle}</p>
        </div>

        {/* Farm Selector */}
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-500 dark:text-slate-400">{TEXT.farmLabel}</label>
          <select
            value={selectedFarm}
            onChange={(e) => setSelectedFarm(e.target.value)}
            className="px-4 py-2.5 rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 text-gray-800 dark:text-white appearance-none cursor-pointer hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors min-w-[200px]"
          >
            {farms.map((farm) => (
              <option key={farm.id} value={String(farm.id)}>
                {farm.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-6 py-4 text-rose-400">
          {error}
        </div>
      )}

      {/* Cards Grid */}
      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((card) => (
          <PremiumCropCard
            key={card.id}
            card={card}
            selectedFarm={selectedFarm}
            availableItems={unusedItemsByCrop[card.id] || []}
            productSelection={productSelection}
            setProductSelection={setProductSelection}
            onAddProduct={handleAddProduct}
            onMarkPrimary={handleMarkPrimary}
            onRemoveLink={handleRemoveLink}
            navigate={navigate}
            formatTimelineDate={formatTimelineDate}
          />
        ))}
      </div>

      {/* Empty State */}
      {cards.length === 0 && !loading && (
        <div className="text-center py-20">
          <span className="text-6xl mb-4 block opacity-30">🌱</span>
          <p className="text-gray-400 dark:text-slate-500">لا توجد بطاقات محاصيل لهذه المزرعة</p>
        </div>
      )}

      {/* Custom scrollbar styles */}
      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: rgb(51 65 85 / 0.5); border-radius: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgb(100 116 139); border-radius: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgb(148 163 184); }
      `}</style>
    </div>
  )
}
