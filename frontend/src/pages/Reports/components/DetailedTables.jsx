import React, { useMemo } from 'react'

import { TEXT, formatDate, formatNumber } from '../constants'

const STATUS_STYLES = {
  pending: 'bg-amber-100 text-amber-700',
  processing: 'bg-amber-100 text-amber-700',
  running: 'bg-amber-100 text-amber-700',
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
}

const REPORT_GROUP_LABELS = {
  advanced: 'التقرير المتقدم',
  execution: 'تقارير التنفيذ اليومي',
  variance: 'تقارير الخطة والانحراف',
  perennial: 'تقارير الأشجار والمعمّرات',
  readiness: 'تقارير الجاهزية التشغيلية',
  inventory: 'تقارير المخزون',
  fuel: 'تقارير الوقود',
  assets: 'تقارير الأصول الثابتة',
  contracts: 'تقارير العقود الزراعية',
  petty_cash: 'تقارير السلف والعهد',
  settlements: 'تقارير الموردين والتسويات',
  receipts: 'تقارير التحصيل والإيداع',
  governance: 'تقارير الحوكمة والموافقات',
}

const MODE_SCOPE_LABELS = {
  all: 'SIMPLE / STRICT',
  simple_only: 'SIMPLE فقط',
  strict_only: 'STRICT فقط',
}

const groupExportTemplates = (templates = []) => {
  const grouped = new Map()
  templates.forEach((template) => {
    const groupKey = template.report_group || 'advanced'
    const bucket = grouped.get(groupKey) || []
    bucket.push(template)
    grouped.set(groupKey, bucket)
  })
  return Array.from(grouped.entries()).map(([groupKey, items]) => ({
    groupKey,
    title: REPORT_GROUP_LABELS[groupKey] || groupKey,
    items,
  }))
}

const renderJobStatus = (job) => {
  if (job.status === 'completed') return TEXT.export.completed
  if (job.status === 'failed') return TEXT.export.failedLabel
  return TEXT.export.inProgress
}

export default function DetailedTables({
  summary,
  activities,
  loading,
  handleExport,
  exporting,
  exportJobs = [],
  exportTemplates = [],
  reportPendingMessage = '',
  reportRefreshing = false,
  selectedSections = ['summary'],
  sectionStatusMap = {},
  canUseJsonExports = false,
}) {
  const groupedTemplates = useMemo(() => groupExportTemplates(exportTemplates), [exportTemplates])
  const showDetailedTables = selectedSections.includes('detailed_tables')
  const showActivitiesTable = selectedSections.includes('activities') || showDetailedTables
  const activitiesStatus = sectionStatusMap.activities || sectionStatusMap.detailed_tables || 'idle'
  const hasJsonExports = groupedTemplates.some((group) =>
    group.items.some((template) => (template.formats || []).includes('json')),
  )

  return (
    <>
      {reportPendingMessage ? (
        <div
          data-testid="detailed-report-pending-banner"
          className="rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200"
        >
          {reportPendingMessage}
        </div>
      ) : null}

      {showDetailedTables ? (
        <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
            {TEXT.table.locationBreakdown}
          </h2>
          <div className="overflow-x-auto">
            {summary?.locations?.length ? (
              <table className="w-full text-sm text-end">
                <thead className="bg-gray-50 dark:bg-slate-700 text-xs text-gray-600 dark:text-slate-300">
                  <tr>
                    <th className="px-3 py-2">{TEXT.table.location}</th>
                    <th className="px-3 py-2 text-center">{TEXT.summary.totalHours}</th>
                    <th className="px-3 py-2 text-center">{TEXT.summary.harvestQty}</th>
                  </tr>
                </thead>
                <tbody className="text-gray-700 dark:text-slate-300">
                  {summary.locations.map((loc) => (
                    <tr
                      key={loc.id}
                      className="border-t dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700/50"
                    >
                      <td className="px-3 py-2">{loc.name}</td>
                      <td className="px-3 py-2 text-center">{formatNumber(loc.total_hours)}</td>
                      <td className="px-3 py-2 text-center">{formatNumber(loc.harvest_total_qty)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-gray-500 dark:text-slate-400 text-sm">{TEXT.charts.noData}</p>
            )}
          </div>
        </div>
      ) : null}

      <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow space-y-4">
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <h2 className="text-xl font-semibold text-gray-800 dark:text-white">{TEXT.table.title}</h2>
            <span className="inline-flex w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-100">
              {hasJsonExports && canUseJsonExports ? 'XLSX أساسي • JSON إداري' : 'XLSX أساسي'}
            </span>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            جميع عمليات التصدير تعتمد الأقسام المحددة حاليًا داخل الصفحة.
          </p>
        </div>

        {!!groupedTemplates.length && (
          <div className="space-y-4" data-testid="report-export-catalog">
            {groupedTemplates.map((group) => (
              <section
                key={group.groupKey}
                className="rounded-2xl border border-slate-200 dark:border-slate-700 p-4"
              >
                <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">
                    {group.title}
                  </h3>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                    <span>{group.items.length} تقرير</span>
                    {reportRefreshing ? (
                      <span className="rounded-full bg-amber-100 px-2 py-1 font-semibold text-amber-700 dark:bg-amber-500/10 dark:text-amber-200">
                        جاري تجهيز تقرير جديد
                      </span>
                    ) : null}
                  </div>
                </div>
                <div className="grid gap-3 xl:grid-cols-2">
                  {group.items.map((template) => (
                    <article
                      key={template.export_type}
                      className="rounded-xl bg-slate-50 dark:bg-slate-900/40 p-4 space-y-3"
                    >
                      <div className="space-y-1">
                        <h4 className="font-semibold text-slate-800 dark:text-slate-100">
                          {template.title}
                        </h4>
                        {template.description ? (
                          <p className="text-sm text-slate-500 dark:text-slate-400">
                            {template.description}
                          </p>
                        ) : null}
                      </div>
                      <div className="flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                        <span className="rounded-full bg-white/80 dark:bg-slate-800 px-2 py-1">
                          {MODE_SCOPE_LABELS[template.mode_scope] || template.mode_scope}
                        </span>
                        <span className="rounded-full bg-white/80 dark:bg-slate-800 px-2 py-1">
                          {template.sensitivity_level || 'normal'}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {(template.formats || []).includes('xlsx') ? (
                          <button
                            type="button"
                            onClick={() =>
                              handleExport({
                                exportType: template.export_type,
                                format: 'xlsx',
                              })
                            }
                            className="px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-60"
                            disabled={loading || exporting}
                          >
                            تصدير Excel للأقسام المختارة
                          </button>
                        ) : null}
                        {(template.formats || []).includes('json') && canUseJsonExports ? (
                          <button
                            type="button"
                            onClick={() =>
                              handleExport({
                                exportType: template.export_type,
                                format: 'json',
                              })
                            }
                            className="px-3 py-2 border border-slate-300 text-slate-700 rounded hover:bg-slate-50 disabled:opacity-60 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
                            disabled={loading || exporting}
                          >
                            تصدير JSON للأقسام المختارة
                          </button>
                        ) : null}
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}

        {!!exportJobs.length && (
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">
              {TEXT.export.jobsTitle}
            </h3>
            <div className="space-y-2" data-testid="report-export-jobs">
              {exportJobs.map((job) => (
                <div
                  key={job.id}
                  className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between rounded-lg bg-slate-50 dark:bg-slate-900/40 px-3 py-2"
                >
                  <div className="text-sm text-slate-700 dark:text-slate-200">
                    <span className="font-semibold">
                      {job.output_filename || job.metadata?.export_type || `job-${job.id}`}
                    </span>
                    <span className="mx-2 text-slate-400">•</span>
                    <span>{String(job.format || '').toUpperCase()}</span>
                    {job.metadata?.report_group ? (
                      <>
                        <span className="mx-2 text-slate-400">•</span>
                        <span>
                          {REPORT_GROUP_LABELS[job.metadata.report_group] || job.metadata.report_group}
                        </span>
                      </>
                    ) : null}
                  </div>
                  <span
                    className={`inline-flex w-fit rounded-full px-3 py-1 text-xs font-semibold ${
                      STATUS_STYLES[job.status] || 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {renderJobStatus(job)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {showActivitiesTable ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-end">
              <thead className="bg-gray-50 dark:bg-slate-700 text-xs text-gray-600 dark:text-slate-300">
                <tr>
                  <th className="px-3 py-2">{TEXT.table.date}</th>
                  <th className="px-3 py-2">{TEXT.table.location}</th>
                  <th className="px-3 py-2">{TEXT.table.crop}</th>
                  <th className="px-3 py-2">{TEXT.table.task}</th>
                  <th className="px-3 py-2 text-center">{TEXT.table.hours}</th>
                  <th className="px-3 py-2 text-center">{TEXT.table.machineHours}</th>
                  <th className="px-3 py-2 text-center">{TEXT.table.wellReading}</th>
                </tr>
              </thead>
              <tbody className="text-gray-700 dark:text-slate-300">
                {activitiesStatus === 'loading' ? (
                  <tr>
                    <td className="px-3 py-4 text-center text-gray-500 dark:text-slate-400" colSpan={7}>
                      جارٍ تحميل بيانات الأنشطة...
                    </td>
                  </tr>
                ) : activities.length ? (
                  activities.map((act) => (
                    <tr
                      key={act.id}
                      className="border-t dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700/50"
                    >
                      <td className="px-3 py-2">{formatDate(act.log_date)}</td>
                      <td className="px-3 py-2">{act.location?.name || '-'}</td>
                      <td className="px-3 py-2">{act.crop?.name || '-'}</td>
                      <td className="px-3 py-2">{act.task?.name || '-'}</td>
                      <td className="px-3 py-2 text-center">{formatNumber(act.hours)}</td>
                      <td className="px-3 py-2 text-center">{formatNumber(act.machine_hours)}</td>
                      <td className="px-3 py-2 text-center">{formatNumber(act.well_reading)}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="px-3 py-4 text-center text-gray-500 dark:text-slate-400" colSpan={7}>
                      {TEXT.table.empty}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            اختر قسمي &quot;الأنشطة&quot; أو &quot;الجداول التفصيلية&quot; لعرض الجداول داخل الصفحة.
          </p>
        )}
      </div>
    </>
  )
}
