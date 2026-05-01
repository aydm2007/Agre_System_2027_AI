import React, { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import {
  FileBarChart,
  Download,
  Calendar,
  Filter,
  ChevronDown,
  PieChart as PieIcon,
  BarChart3,
  LineChart as LineIcon,
  Printer,
  Lock,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../auth/AuthContext'
import { useSettings } from '../../contexts/SettingsContext'
import { usePageFarmFilter } from '../../hooks/usePageFarmFilter'
import { useOfflineQueue } from '../../offline/OfflineQueueProvider'
import ReportFilters from './components/ReportFilters'
import ReportSectionSelector from './components/ReportSectionSelector'
import KeyMetricsCard from './components/KeyMetricsCard'
import ActivityCharts from './components/ActivityCharts'
import TreeInsights from './components/TreeInsights'
import FinancialRiskZone from './components/FinancialRiskZone'
import DetailedTables from './components/DetailedTables'
import { useReportFilters } from './hooks/useReportFilters'
import { useReportData } from './hooks/useReportData'

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444']

const formatDateTime = (value) => {
  if (!value) return 'لا توجد'
  try {
    return new Date(value).toLocaleString('ar-YE')
  } catch {
    return String(value)
  }
}

export default function ReportsPage() {
  const { isStrictMode, showAdvancedReports } = useSettings()
  const { isAdmin, isSuperuser } = useAuth()
  const navigate = useNavigate()
  const { farmId, canUseAll } = usePageFarmFilter({
    storageKey: 'reports:farm',
    allowAllForAdmin: true,
  })
  const {
    filters,
    handleFilterChange,
    seasons,
    farms,
    locations,
    crops,
    tasks,
    varieties,
    treeStatuses,
  } = useReportFilters(farmId)
  const {
    summary,
    activities,
    treeSummary,
    treeEvents,
    loading,
    treeLoading,
    treeError,
    riskData,
    exporting,
    fetchReport,
    handleExport,
    exportJobs,
    exportTemplates,
    treeTotals,
    materialChart,
    machineryChart,
    reportPendingMessage,
    reportRefreshing,
    selectedSections,
    setSelectedSections,
    sectionStatusMap,
    hasStaleSections,
    toggleSection,
  } = useReportData(filters)
  const {
    isOnline,
    queuedRequests,
    queuedHarvests,
    queuedDailyLogs,
    queuedCustody,
    failedRequests,
    failedHarvests,
    failedDailyLogs,
    failedCustody,
    syncing,
    lastSync,
  } = useOfflineQueue()

  const productiveTreeCount = useMemo(
    () =>
      treeSummary.reduce((total, item) => {
        const code = item?.productivity_status?.code || item?.productivity_status_code || ''
        if (code === 'productive' || code === 'PRODUCTIVE') {
          return total + Number(item?.current_tree_count || 0)
        }
        return total
      }, 0),
    [treeSummary],
  )

  const pendingOffline = queuedRequests + queuedHarvests + queuedDailyLogs + queuedCustody
  const failedOffline = failedRequests + failedHarvests + failedDailyLogs + failedCustody
  const canUseJsonExports = isAdmin || isSuperuser

  const chartData = useMemo(() => {
    const grouped = new Map()
    activities.forEach((activity) => {
      const rawDate = activity?.log_date || activity?.created_at
      if (!rawDate) return
      const date = new Date(rawDate)
      if (Number.isNaN(date.getTime())) return
      const label = date.toLocaleString('ar-YE', { month: 'short' })
      const current = grouped.get(label) || { name: label, cost: 0, revenue: 0, trend: 0 }
      current.cost +=
        Number(activity?.hours || 0) +
        Number(activity?.machine_hours || 0) +
        Number(activity?.fuel_consumed || 0) +
        Number(activity?.water_volume || 0)
      current.revenue +=
        Number(activity?.harvest_quantity || 0) +
        Number(activity?.harvested_qty || 0) +
        Number(activity?.achievement_qty || 0)
      grouped.set(label, current)
    })
    return Array.from(grouped.values()).map((entry) => ({
      ...entry,
      cost: Number(entry.cost.toFixed(2)),
      revenue: Number(entry.revenue.toFixed(2)),
      trend: Number((entry.cost > 0 ? (entry.revenue / entry.cost) * 100 : 0).toFixed(1)),
    }))
  }, [activities])

  const resourceMix = useMemo(() => {
    const materialsValue = Array.isArray(summary?.materials)
      ? summary.materials.reduce((total, item) => total + Number(item?.total_qty || 0), 0)
      : 0
    const laborValue = activities.reduce((total, activity) => total + Number(activity?.hours || 0), 0)
    const fuelValue = activities.reduce(
      (total, activity) => total + Number(activity?.fuel_consumed || 0),
      0,
    )
    const waterValue = activities.reduce(
      (total, activity) => total + Number(activity?.water_volume || 0),
      0,
    )
    return [
      { name: 'المواد', value: materialsValue },
      { name: 'العمالة', value: laborValue },
      { name: 'الوقود', value: fuelValue },
      { name: 'الري', value: waterValue },
    ].filter((entry) => entry.value > 0)
  }, [activities, summary])

  const resourceMixTotal = useMemo(
    () => resourceMix.reduce((total, entry) => total + Number(entry.value || 0), 0),
    [resourceMix],
  )

  const growthMetric = useMemo(() => {
    if (!chartData.length) return 0
    return Number(chartData[chartData.length - 1]?.trend || 0)
  }, [chartData])

  const applySimplePreset = (sections) => {
    if (typeof setSelectedSections === 'function') {
      setSelectedSections(sections)
    }
  }

  return (
    <div className="app-page bg-slate-50 p-6 text-slate-900 dark:bg-slate-900 dark:text-slate-50 rtl" dir="rtl">
      <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="mb-2 flex items-center gap-3 text-3xl font-black">
            <span className="rounded-xl bg-emerald-600 p-2 text-white shadow-lg shadow-emerald-600/20">
              <FileBarChart size={28} />
            </span>
            مركز التقارير والذكاء الاصطناعي (BI)
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            {isStrictMode
              ? 'تحليل البيانات التشغيلية والمالية مع تصدير التقارير الرسمية'
              : 'تقارير تشغيلية وجداول تفصيلية للمود البسيط دون كشف قيم مالية محظورة'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {isStrictMode ? (
            <>
              <button
                type="button"
                onClick={() => navigate('/reports/advanced')}
                className="flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-6 py-3 font-bold shadow-sm transition-all hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-800"
              >
                <Download size={18} /> التقارير المتقدمة (XLSX)
              </button>
              <button
                type="button"
                onClick={() => window.print()}
                className="flex items-center justify-center gap-2 rounded-2xl bg-emerald-600 px-6 py-3 font-bold text-white shadow-lg shadow-emerald-600/20 transition-all hover:bg-emerald-500"
              >
                <Printer size={18} /> طباعة
              </button>
            </>
          ) : showAdvancedReports ? (
            <button
              onClick={() => navigate('/reports/advanced')}
              className="flex items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-6 py-3 font-bold text-white shadow-lg shadow-indigo-600/20 transition-all hover:bg-indigo-500"
              title="تصدير تقارير مخصصة (XLSX)"
            >
              <Download size={18} /> التقارير المتقدمة (XLSX)
            </button>
          ) : null}
        </div>
      </div>

      <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-100">
        التقارير تعمل عبر خادم AgriAsset الداخلي ولا تحتاج اشتراكاً خارجياً. عرض الرسوم والتصدير يعتمد على اتصال الواجهة بالخادم وخط التقارير غير المتزامن.
      </div>

      <div className="mb-8 flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-800">
        <div className="flex items-center gap-2 rounded-xl bg-slate-100 px-4 py-2 dark:bg-slate-900">
          <Calendar size={18} className="text-slate-400" />
          <span className="text-sm font-bold">آخر 30 يوم</span>
          <ChevronDown size={14} className="text-slate-400" />
        </div>
        <div className="h-8 w-px bg-slate-200 dark:bg-slate-700" />
        <div className="flex flex-1 flex-wrap items-center gap-4">
          {['ملخص التشغيل', 'تحليل الموارد', 'إنتاجية المحاصيل', 'كفاءة العمالة'].map((tab, index) => (
            <button
              key={tab}
              className={`text-sm font-bold transition-colors ${
                index === 0 ? 'text-emerald-500' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        <button className="rounded-xl bg-slate-100 p-2 transition-all hover:bg-slate-200 dark:bg-slate-900 dark:hover:bg-slate-700">
          <Filter size={20} className="text-slate-500" />
        </button>
      </div>

      {!isStrictMode ? (
        <div className="mb-8 flex items-center justify-between rounded-2xl border border-blue-200 bg-blue-100 p-4 text-sm font-bold text-blue-700 dark:border-blue-900/40 dark:bg-blue-900/20 dark:text-blue-500">
          <div className="flex items-center gap-3">
            <Lock size={18} /> وضع الاستعراض التشغيلي نشط: القيم النقدية المطلقة مخفية، والتقارير تعرض مؤشرات تشغيلية وجداول مراجعة.
          </div>
          <span className="rounded-full bg-blue-600 px-3 py-1 text-[10px] uppercase text-white">Simple Mode</span>
        </div>
      ) : null}

      {!isStrictMode ? (
        <div
          data-testid="simple-report-presets-panel"
          className="mb-8 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-800"
        >
          <div className="mb-3">
            <h2 className="text-base font-black text-slate-900 dark:text-white">تقارير SIMPLE التشغيلية</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              اختصارات قراءة لا تفتح تأليفًا ماليًا، وتعرض الجداول التفصيلية بجانب BI.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              data-testid="simple-report-preset-daily_execution"
              onClick={() => applySimplePreset(['summary', 'activities', 'charts', 'detailed_tables'])}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-emerald-500"
            >
              التنفيذ اليومي
            </button>
            <button
              type="button"
              data-testid="simple-report-preset-custody_materials"
              onClick={() => applySimplePreset(['summary', 'activities', 'charts', 'detailed_tables'])}
              className="rounded-xl bg-sky-600 px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-sky-500"
            >
              عهدة المواد
            </button>
            <button
              type="button"
              data-testid="simple-report-preset-tree_inventory"
              onClick={() => applySimplePreset(['summary', 'tree_summary', 'tree_events', 'detailed_tables'])}
              className="rounded-xl bg-amber-600 px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-amber-500"
            >
              الأشجار والمعمرات
            </button>
            <button
              type="button"
              data-testid="simple-report-preset-offline_readiness"
              onClick={() => applySimplePreset(['summary', 'activities', 'detailed_tables'])}
              className="rounded-xl bg-slate-700 px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-slate-600"
            >
              جاهزية offline
            </button>
          </div>
        </div>
      ) : null}

      <div data-testid="reports-offline-readiness-panel" className="mb-8 grid gap-3 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-800">
          <div className="text-xs font-bold text-slate-500 dark:text-slate-400">حالة الشبكة</div>
          <div className={`mt-2 text-lg font-black ${isOnline ? 'text-emerald-600' : 'text-amber-600'}`}>
            {isOnline ? 'متصل' : 'Offline'}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-800">
          <div className="text-xs font-bold text-slate-500 dark:text-slate-400">بانتظار الإرسال</div>
          <div className="mt-2 text-lg font-black text-slate-900 dark:text-white">{pendingOffline}</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-800">
          <div className="text-xs font-bold text-slate-500 dark:text-slate-400">تحتاج معالجة</div>
          <div className={`mt-2 text-lg font-black ${failedOffline ? 'text-rose-600' : 'text-emerald-600'}`}>
            {failedOffline}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-800">
          <div className="text-xs font-bold text-slate-500 dark:text-slate-400">آخر مزامنة</div>
          <div className="mt-2 text-sm font-bold text-slate-900 dark:text-white">
            {syncing ? 'جاري المزامنة' : formatDateTime(lastSync)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="app-panel p-6 lg:col-span-2">
          <div className="mb-8 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-lg font-black">
              <BarChart3 size={20} className="text-emerald-500" />
              الاتجاه التشغيلي الشهري
            </h2>
          </div>
          <div className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(value) => [Number(value || 0).toLocaleString('ar-YE'), '']}
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                />
                <Legend iconType="circle" />
                <Bar dataKey="revenue" fill="#10b981" radius={[4, 4, 0, 0]} name="الإنجاز" />
                <Bar dataKey="cost" fill="#3b82f6" radius={[4, 4, 0, 0]} name="استهلاك الموارد" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="space-y-8 lg:col-span-1">
          <div className="app-panel p-6">
            <h2 className="mb-6 flex items-center gap-2 text-lg font-black">
              <PieIcon size={20} className="text-amber-500" /> نسب توزيع الموارد
            </h2>
            <div className="h-[250px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={resourceMix} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                    {resourceMix.map((entry, index) => (
                      <Cell key={`cell-${entry.name}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) =>
                      resourceMixTotal > 0
                        ? `${((Number(value || 0) / resourceMixTotal) * 100).toFixed(1)}%`
                        : '0%'
                    }
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {resourceMix.map((entry, index) => (
                <div key={entry.name} className="flex items-center gap-2 text-xs">
                  <div className="h-2 w-2 rounded-full" style={{ backgroundColor: COLORS[index] }} />
                  <span className="truncate text-slate-500">{entry.name}</span>
                  <span className="font-bold">
                    {resourceMixTotal > 0 ? ((entry.value / resourceMixTotal) * 100).toFixed(1) : '0.0'}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="app-panel border-none bg-emerald-600 p-6 text-white shadow-emerald-600/20">
            <div className="mb-4 flex items-start justify-between">
              <LineIcon size={24} className="opacity-50" />
              <span className="rounded-full bg-white/20 px-2 py-1 text-xs font-bold">مؤشر حقيقي</span>
            </div>
            <p className="mb-1 text-sm opacity-80">معدل التحسن التشغيلي</p>
            <h3 className="mb-4 text-3xl font-black">
              {growthMetric > 0 ? '+' : ''}
              {growthMetric.toFixed(1)}%
            </h3>
            <div className="h-[60px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <Line type="monotone" dataKey="trend" stroke="#fff" strokeWidth={3} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      <section data-testid="reports-detailed-workspace" className="mt-8 space-y-6">
        <div>
          <h2 className="text-2xl font-black text-slate-900 dark:text-white">التقارير التفصيلية التشغيلية</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            نفس مصدر الحقيقة المستخدم في DailyLog والتقارير، مع تحميل أقسام انتقائي يناسب الشبكات الضعيفة.
          </p>
        </div>

        <ReportFilters
          filters={filters}
          handleFilterChange={handleFilterChange}
          fetchReport={fetchReport}
          seasons={seasons}
          farms={farms}
          canUseAll={canUseAll}
          locations={locations}
          crops={crops}
          tasks={tasks}
          varieties={varieties}
          treeStatuses={treeStatuses}
        />

        <ReportSectionSelector
          filters={filters}
          selectedSections={selectedSections}
          sectionStatusMap={sectionStatusMap}
          hasStaleSections={hasStaleSections}
          onToggleSection={toggleSection}
        />

        {selectedSections.includes('summary') ? <KeyMetricsCard summary={summary} /> : null}

        {selectedSections.includes('charts') ? (
          <ActivityCharts
            materialChart={materialChart}
            machineryChart={machineryChart}
            status={sectionStatusMap.charts}
          />
        ) : null}

        {selectedSections.includes('tree_summary') || selectedSections.includes('tree_events') ? (
          <TreeInsights
            treeLoading={treeLoading}
            treeSummary={treeSummary}
            treeTotals={treeTotals}
            treeEvents={treeEvents}
            treeError={treeError}
            productiveTreeCount={productiveTreeCount}
            showSummary={selectedSections.includes('tree_summary')}
            showEvents={selectedSections.includes('tree_events')}
            summaryStatus={sectionStatusMap.tree_summary}
            eventsStatus={sectionStatusMap.tree_events}
          />
        ) : null}

        {isStrictMode && selectedSections.includes('risk_zone') ? (
          <FinancialRiskZone filters={filters} riskData={riskData} status={sectionStatusMap.risk_zone} />
        ) : null}

        <DetailedTables
          summary={summary}
          activities={activities}
          loading={loading}
          handleExport={handleExport}
          exporting={exporting}
          exportJobs={exportJobs}
          exportTemplates={exportTemplates}
          canUseJsonExports={canUseJsonExports}
          reportPendingMessage={reportPendingMessage}
          reportRefreshing={reportRefreshing}
          selectedSections={selectedSections}
          sectionStatusMap={sectionStatusMap}
        />
      </section>
    </div>
  )
}
