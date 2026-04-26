import { Filter, RotateCcw, Loader2 } from 'lucide-react'

const DIMENSION_META = {
  farm: { label: 'المزرعة', icon: '🏠', placeholder: 'كل المزارع' },
  location: { label: 'الموقع', icon: '📍', placeholder: 'كل المواقع' },
  costCenter: { label: 'مركز التكلفة', icon: '🏷️', placeholder: 'كل المراكز' },
  crop_plan: { label: 'خطة المحصول', icon: '🌾', placeholder: 'كل الخطط' },
  activity: { label: 'النشاط', icon: '🧭', placeholder: 'كل الأنشطة' },
  crop: { label: 'المحصول', icon: '🌿', placeholder: 'كل المحاصيل' },
  period: { label: 'الفترة', icon: '📅', placeholder: 'كل الفترات' },
}

const PARENT_DIMENSIONS = {
  location: 'farm',
  costCenter: 'farm',
  crop_plan: 'farm',
  activity: 'crop_plan',
  crop: 'farm',
  period: 'farm',
}

export default function FinancialFilterBar({
  filters = {},
  options = {},
  loading = {},
  setFilter,
  onReset,
  dimensions = ['farm'],
  className = '',
}) {
  const hasActiveFilters = Object.values(filters).some(Boolean)

  return (
    <div
      dir="rtl"
      className={`flex flex-wrap items-center gap-2 rounded-xl border border-gray-200/80 bg-white/90 px-3 py-2.5 shadow-sm backdrop-blur dark:border-slate-700/60 dark:bg-slate-800/80 ${className}`}
      data-testid="financial-filter-bar"
    >
      <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 dark:text-slate-400">
        <Filter className="h-3.5 w-3.5" />
        <span>فلترة</span>
      </div>

      {dimensions.map((dim) => {
        const meta = DIMENSION_META[dim] || { label: dim, icon: '🔹', placeholder: 'الكل' }
        const dimOptions = options[dim] || []
        const isLoading = loading[dim]
        const value = filters[dim] || ''
        const parentDimension = PARENT_DIMENSIONS[dim]
        const isDisabled = Boolean(parentDimension && !filters[parentDimension])

        return (
          <div key={dim} className="relative">
            <select
              value={value}
              onChange={(e) => setFilter(dim, e.target.value)}
              disabled={isDisabled || isLoading}
              className={
                `appearance-none rounded-lg border px-3 py-1.5 pr-7 text-xs font-medium transition-all ` +
                (value
                  ? 'border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-300 '
                  : 'border-gray-200 bg-gray-50 text-gray-600 dark:border-slate-600 dark:bg-slate-700/50 dark:text-slate-300 ') +
                (isDisabled
                  ? 'cursor-not-allowed opacity-50 '
                  : 'cursor-pointer hover:border-emerald-400 dark:hover:border-emerald-500 ') +
                'focus:outline-none focus:ring-2 focus:ring-emerald-400/40'
              }
              data-testid={`filter-${dim}`}
            >
              <option value="">
                {meta.icon} {meta.placeholder}
              </option>
              {dimOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            {isLoading && (
              <Loader2 className="absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 animate-spin text-emerald-500" />
            )}
          </div>
        )
      })}

      {hasActiveFilters && onReset && (
        <button
          onClick={onReset}
          className="flex items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs font-medium text-red-600 transition-colors hover:bg-red-100 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/40"
          data-testid="filter-reset"
        >
          <RotateCcw className="h-3 w-3" />
          مسح
        </button>
      )}
    </div>
  )
}
