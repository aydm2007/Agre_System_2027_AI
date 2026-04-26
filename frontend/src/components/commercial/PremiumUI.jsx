export const PremiumCard = ({ title, value, icon, trend, subValue, color = 'emerald' }) => {
  const colorMap = {
    emerald: 'from-emerald-500/10 to-emerald-900/10 border-emerald-500/20 text-emerald-400',
    gold: 'from-amber-400/10 to-amber-900/10 border-amber-400/20 text-amber-400',
    blue: 'from-blue-500/10 to-blue-900/10 border-blue-500/20 text-blue-400',
    rose: 'from-rose-500/10 to-rose-900/10 border-rose-500/20 text-rose-400',
  }

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border bg-gradient-to-br p-6 backdrop-blur-xl shadow-lg dark:shadow-2xl transition-all hover:scale-[1.02] hover:shadow-emerald-500/10 ${colorMap[color]}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gray-100 dark:bg-black/40 backdrop-blur-md border border-gray-200 dark:border-white/5">
          {icon}
        </div>
        {trend && (
          <div
            className={`text-xs font-semibold px-2.5 py-1 rounded-full bg-gray-100 dark:bg-black/40 border border-gray-200 dark:border-white/5 ${trend > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}
          >
            {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
          </div>
        )}
      </div>

      <div className="mt-4">
        <p className="text-sm font-medium text-gray-500 dark:text-white/50 uppercase tracking-widest">
          {title}
        </p>
        <h3 className="mt-1 text-3xl font-extrabold text-gray-800 dark:text-white tracking-tight">
          {value}
        </h3>
        {subValue && (
          <p className="mt-1 text-xs text-gray-400 dark:text-white/40 italic font-light">
            {subValue}
          </p>
        )}
      </div>

      {/* Decorative Light Glow */}
      <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-emerald-500/10 blur-[50px]"></div>
    </div>
  )
}

export const GlassContainer = ({ children, title, action }) => (
  <div className="rounded-3xl border border-gray-200 dark:border-white/5 bg-white dark:bg-zinc-900/40 p-6 backdrop-blur-2xl shadow-lg dark:shadow-2xl">
    <div className="mb-6 flex items-center justify-between">
      <h2 className="text-xl font-bold text-gray-800 dark:text-white/90">{title}</h2>
      {action && <div>{action}</div>}
    </div>
    {children}
  </div>
)
