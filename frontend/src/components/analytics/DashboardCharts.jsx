import {
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

/**
 * DashboardCharts - Visual Insight Component
 *
 * Features:
 * - Cost Breakdown (Donut Chart)
 * - Activity Trend (Area Chart)
 * - Dark Mode Support
 * - RTL Ready
 * - Loading States
 */

const COLORS = {
  labor: '#10b981', // emerald-500
  material: '#3b82f6', // blue-500
  machinery: '#f59e0b', // amber-500
  overhead: '#8b5cf6', // violet-500
}

// Skeleton Loader
const ChartSkeleton = () => (
  <div className="animate-pulse">
    <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
  </div>
)

export function DashboardCharts({ costData, activityTrend, isLoading = false }) {
  // Default data for demonstration
  const defaultCostData = [
    { name: 'العمالة', value: 35, key: 'labor' },
    { name: 'المواد', value: 40, key: 'material' },
    { name: 'الآلات', value: 15, key: 'machinery' },
    { name: 'أخرى', value: 10, key: 'overhead' },
  ]

  const defaultTrendData = [
    { day: 'السبت', activities: 12 },
    { day: 'الأحد', activities: 19 },
    { day: 'الإثنين', activities: 15 },
    { day: 'الثلاثاء', activities: 22 },
    { day: 'الأربعاء', activities: 18 },
    { day: 'الخميس', activities: 25 },
    { day: 'الجمعة', activities: 8 },
  ]

  const costs = costData || defaultCostData
  const trends = activityTrend || defaultTrendData

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8" dir="rtl">
      {/* Cost Breakdown - Donut Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 transition-colors">
        <h3 className="text-lg font-bold text-gray-800 dark:text-white mb-4 text-end">
          توزيع التكاليف
        </h3>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={costs}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={2}
              dataKey="value"
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            >
              {costs.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[entry.key] || COLORS.overhead}
                  className="transition-all hover:opacity-80"
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--tooltip-bg, #fff)',
                border: 'none',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Activity Trend - Area Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 transition-colors">
        <h3 className="text-lg font-bold text-gray-800 dark:text-white mb-4 text-end">
          نشاط الأسبوع
        </h3>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={trends}>
            <defs>
              <linearGradient id="colorActivities" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis
              dataKey="day"
              tick={{ fill: 'currentColor' }}
              className="text-gray-600 dark:text-gray-400"
            />
            <YAxis tick={{ fill: 'currentColor' }} className="text-gray-600 dark:text-gray-400" />
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--tooltip-bg, #fff)',
                border: 'none',
                borderRadius: '8px',
              }}
            />
            <Area
              type="monotone"
              dataKey="activities"
              stroke="#10b981"
              strokeWidth={2}
              fill="url(#colorActivities)"
              name="الأنشطة"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default DashboardCharts
