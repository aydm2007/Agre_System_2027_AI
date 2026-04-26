import { useEffect, useMemo, useState } from 'react'

import { ImportJobs } from '../../api/client'

const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

const JOB_STATUS_LABELS = {
  draft: 'مسودة',
  uploaded: 'مرفوع',
  validated: 'تم التحقق',
  preview_ready: 'جاهز للمعاينة',
  approved_for_apply: 'جاهز للتطبيق',
  applied: 'تم التطبيق',
  partially_rejected: 'مرفوض جزئيًا',
  failed: 'فاشل',
}

const MODE_SCOPE_LABELS = {
  mode_aware_operational: 'تشغيلي بحسب المود',
  strict_only: 'STRICT فقط',
}

export default function PlanningImportCenter({
  farmId,
  cropPlanId = null,
  templateCode,
  title,
  description,
  onClose,
  onApplied,
  addToast,
}) {
  const [loading, setLoading] = useState(false)
  const [templates, setTemplates] = useState([])
  const [importJobs, setImportJobs] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [importJob, setImportJob] = useState(null)

  useEffect(() => {
    let active = true
    ;(async () => {
      if (!farmId) return
      try {
        const [templatesRes, importJobsRes] = await Promise.all([
          ImportJobs.templates({ farm_id: farmId, module: 'planning' }),
          ImportJobs.list({ farm_id: farmId, module: 'planning', limit: 8 }),
        ])
        if (!active) return
        setTemplates(templatesRes?.data?.results || [])
        setImportJobs(importJobsRes?.data?.results || [])
      } catch (error) {
        if (active) {
          addToast?.('تعذر تحميل مركز استيراد التخطيط.', 'error')
        }
      }
    })()
    return () => {
      active = false
    }
  }, [addToast, farmId])

  const activeTemplate = useMemo(
    () => templates.find((entry) => entry.code === templateCode) || null,
    [templateCode, templates],
  )

  const scopedJobs = useMemo(() => {
    const rows = cropPlanId
      ? importJobs.filter(
          (job) => String(job.metadata?.crop_plan_id || '') === String(cropPlanId),
        )
      : importJobs.filter((job) => !job.metadata?.crop_plan_id)
    return rows.slice(0, 6)
  }, [cropPlanId, importJobs])

  const handleTemplateDownload = async () => {
    if (!farmId) {
      addToast?.('اختر المزرعة أولًا قبل تنزيل القالب.', 'error')
      return
    }
    setLoading(true)
    try {
      const response = await ImportJobs.downloadTemplate(templateCode, {
        farm_id: farmId,
        crop_plan_id: cropPlanId || '',
      })
      downloadBlob(response.data, `${templateCode}-${farmId}.xlsx`)
      addToast?.('تم تنزيل القالب بنجاح.', 'success')
    } catch (error) {
      addToast?.('تعذر تنزيل القالب.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async () => {
    if (!farmId || !selectedFile) {
      addToast?.('اختر ملف Excel أولًا.', 'error')
      return
    }
    setLoading(true)
    try {
      const { data } = await ImportJobs.upload({
        template_code: templateCode,
        farm_id: farmId,
        crop_plan_id: cropPlanId,
        file: selectedFile,
      })
      setImportJob(data)
      setImportJobs((prev) => [data, ...prev.filter((entry) => entry.id !== data.id)].slice(0, 8))
      addToast?.('تم رفع الملف بنجاح. نفذ التحقق الآن.', 'success')
    } catch (error) {
      addToast?.(error?.response?.data?.detail || 'تعذر رفع الملف.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleValidate = async () => {
    if (!importJob?.id) {
      addToast?.('ارفع ملف Excel أولًا.', 'error')
      return
    }
    setLoading(true)
    try {
      const { data } = await ImportJobs.validate(importJob.id)
      setImportJob(data)
      setImportJobs((prev) => [data, ...prev.filter((entry) => entry.id !== data.id)].slice(0, 8))
      addToast?.('تم التحقق من الملف وبناء المعاينة.', 'success')
    } catch (error) {
      addToast?.(error?.response?.data?.detail || 'تعذر التحقق من الملف.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleApply = async () => {
    if (!importJob?.id) {
      addToast?.('لا توجد مهمة جاهزة للتطبيق.', 'error')
      return
    }
    setLoading(true)
    try {
      const { data } = await ImportJobs.apply(importJob.id)
      setImportJob(data)
      setImportJobs((prev) => [data, ...prev.filter((entry) => entry.id !== data.id)].slice(0, 8))
      addToast?.('تم تطبيق ملف التخطيط بنجاح.', 'success')
      onApplied?.(data)
    } catch (error) {
      addToast?.(error?.response?.data?.detail || 'تعذر تطبيق الملف.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadErrors = async () => {
    if (!importJob?.id) return
    try {
      const response = await ImportJobs.downloadErrors(importJob.id)
      downloadBlob(response.data, `planning-import-errors-${importJob.id}.xlsx`)
    } catch (error) {
      addToast?.('لا يوجد ملف أخطاء قابل للتنزيل.', 'error')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" dir="rtl">
      <div className="flex max-h-[90vh] w-full max-w-5xl flex-col rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-800">
        <div className="mb-4 flex items-start justify-between gap-4 border-b border-slate-200 pb-4 dark:border-slate-700">
          <div className="space-y-2">
            <h3 className="text-xl font-bold text-slate-900 dark:text-white">{title}</h3>
            <p className="text-sm text-slate-600 dark:text-slate-300">{description}</p>
            {activeTemplate ? (
              <div className="flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span className="rounded-full bg-slate-100 px-2 py-1 dark:bg-slate-700">
                  {MODE_SCOPE_LABELS[activeTemplate.mode_scope] || activeTemplate.mode_scope}
                </span>
                <span className="rounded-full bg-slate-100 px-2 py-1 dark:bg-slate-700">
                  إصدار {activeTemplate.template_version}
                </span>
                {activeTemplate.requires_crop_plan && (
                  <span className="rounded-full bg-amber-100 px-2 py-1 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                    يتطلب خطة زراعية
                  </span>
                )}
              </div>
            ) : (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-300">
                هذا القالب غير متاح للمزرعة أو المود الحالي.
              </div>
            )}
          </div>
          <button
            type="button"
            className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
            onClick={onClose}
          >
            إغلاق
          </button>
        </div>

        <div className="grid gap-5 lg:grid-cols-[1.1fr_1.4fr]">
          <div className="space-y-4 rounded-xl border border-slate-200 p-4 dark:border-slate-700">
            <h4 className="font-semibold text-slate-800 dark:text-white">خطوات الاستيراد</h4>
            <div className="space-y-3">
              <button
                type="button"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 disabled:opacity-60 dark:border-slate-600 dark:text-slate-200"
                onClick={handleTemplateDownload}
                disabled={loading || !activeTemplate}
              >
                تنزيل القالب
              </button>
              <input
                type="file"
                accept=".xlsx"
                className="block w-full text-sm text-slate-600 dark:text-slate-300"
                onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
                disabled={!activeTemplate}
              />
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  onClick={handleUpload}
                  disabled={loading || !activeTemplate}
                >
                  رفع ملف Excel
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 disabled:opacity-60 dark:border-slate-600 dark:text-slate-200"
                  onClick={handleValidate}
                  disabled={loading || !importJob?.id}
                >
                  معاينة
                </button>
                <button
                  type="button"
                  className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  onClick={handleApply}
                  disabled={
                    loading ||
                    !importJob?.id ||
                    !['approved_for_apply', 'preview_ready'].includes(importJob.status)
                  }
                >
                  تطبيق
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-amber-300 px-3 py-2 text-sm font-semibold text-amber-700 disabled:opacity-60"
                  onClick={handleDownloadErrors}
                  disabled={loading || !importJob?.error_workbook_url}
                >
                  تنزيل ملف الأخطاء
                </button>
              </div>
            </div>

            {scopedJobs.length > 0 && (
              <div className="space-y-2" data-testid="planning-import-history">
                <h5 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                  سجل الاستيراد
                </h5>
                {scopedJobs.map((job) => (
                  <div
                    key={job.id}
                    className="rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700"
                  >
                    <div className="font-medium text-slate-700 dark:text-slate-200">
                      {job.template_code}
                    </div>
                    <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {JOB_STATUS_LABELS[job.status] || job.status} • صفوف: {job.row_count || 0} •
                      مطبق: {job.applied_count || 0}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-4 rounded-xl border border-slate-200 p-4 dark:border-slate-700">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-slate-800 dark:text-white">المعاينة</h4>
              {importJob && (
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-200">
                  {JOB_STATUS_LABELS[importJob.status] || importJob.status}
                </span>
              )}
            </div>

            {importJob ? (
              <div className="space-y-4" data-testid="planning-import-preview">
                <div className="grid gap-3 md:grid-cols-4">
                  <div className="rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-900/40">
                    <div className="text-slate-500 dark:text-slate-400">صفوف الملف</div>
                    <div className="mt-1 text-lg font-bold text-slate-800 dark:text-white">
                      {importJob.row_count || 0}
                    </div>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-900/40">
                    <div className="text-slate-500 dark:text-slate-400">مطبق</div>
                    <div className="mt-1 text-lg font-bold text-emerald-600 dark:text-emerald-400">
                      {importJob.applied_count || 0}
                    </div>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-900/40">
                    <div className="text-slate-500 dark:text-slate-400">مرفوض</div>
                    <div className="mt-1 text-lg font-bold text-rose-600 dark:text-rose-400">
                      {importJob.rejected_count || 0}
                    </div>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-900/40">
                    <div className="text-slate-500 dark:text-slate-400">القالب</div>
                    <div className="mt-1 text-sm font-bold text-slate-800 dark:text-white">
                      {importJob.template_code}
                    </div>
                  </div>
                </div>

                {importJob.preview_rows?.length ? (
                  <div className="max-h-[420px] overflow-auto rounded-lg border border-slate-200 dark:border-slate-700">
                    <table className="min-w-full text-sm">
                      <thead className="sticky top-0 bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                        <tr>
                          <th className="px-3 py-2 text-right">صف Excel</th>
                          <th className="px-3 py-2 text-right">الحالة</th>
                          <th className="px-3 py-2 text-right">التفاصيل</th>
                        </tr>
                      </thead>
                      <tbody>
                        {importJob.preview_rows.slice(0, 30).map((row) => (
                          <tr
                            key={`${row.excel_row}-${row.severity}`}
                            className="border-t border-slate-200 dark:border-slate-700"
                          >
                            <td className="px-3 py-2">{row.excel_row}</td>
                            <td className="px-3 py-2">
                              {JOB_STATUS_LABELS[row.severity] || row.severity}
                            </td>
                            <td className="px-3 py-2 text-slate-600 dark:text-slate-300">
                              {(row.messages || []).join(' | ') || row.task_name || row.plan_name || '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="rounded-lg border border-dashed border-slate-300 px-4 py-10 text-center text-sm text-slate-500 dark:border-slate-600 dark:text-slate-400">
                    ارفع الملف ثم نفذ المعاينة لعرض نتائج التحقق قبل التطبيق.
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-slate-300 px-4 py-10 text-center text-sm text-slate-500 dark:border-slate-600 dark:text-slate-400">
                لا توجد مهمة استيراد حالية. ابدأ بتنزيل القالب ثم رفع ملف Excel.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
