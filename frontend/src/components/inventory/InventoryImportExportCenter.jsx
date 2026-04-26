import { useEffect, useMemo, useState } from 'react'

import { ExportJobs, ImportJobs } from '../../api/client'

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
  pending: 'قيد المعالجة',
  processing: 'قيد المعالجة',
  completed: 'مكتمل',
  expired: 'منتهي',
}

const MODE_SCOPE_LABELS = {
  mode_aware_operational: 'تشغيلي بحسب المود',
  strict_only: 'STRICT فقط',
  all: 'SIMPLE / STRICT',
}

export default function InventoryImportExportCenter({
  farmId,
  filters,
  addToast,
  onImportApplied,
}) {
  const [loading, setLoading] = useState(false)
  const [exportJobs, setExportJobs] = useState([])
  const [exportTemplates, setExportTemplates] = useState([])
  const [importJobs, setImportJobs] = useState([])
  const [templates, setTemplates] = useState([])
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [importJob, setImportJob] = useState(null)

  useEffect(() => {
    let active = true
    ;(async () => {
      try {
        const [exportTemplatesRes, exportJobsRes, importTemplatesRes, importJobsRes] = await Promise.all([
          ExportJobs.templates({
            farm_id: farmId || '',
            ui_surface: 'inventory_center',
          }),
          ExportJobs.list({
            farm_id: farmId || '',
            limit: 6,
          }),
          ImportJobs.templates({
            farm_id: farmId || '',
          }),
          ImportJobs.list({
            farm_id: farmId || '',
            limit: 6,
          }),
        ])
        const nextState = {
          exportTemplates: exportTemplatesRes?.data?.results || [],
          exportJobs: exportJobsRes?.data?.results || [],
          importTemplates: importTemplatesRes?.data?.results || [],
          importJobs: importJobsRes?.data?.results || [],
        }
        if (!active) return
        setExportTemplates(nextState.exportTemplates)
        setExportJobs(nextState.exportJobs)
        setTemplates(nextState.importTemplates)
        setImportJobs(nextState.importJobs)
        if (nextState.importTemplates.length) {
          setSelectedTemplate((prev) => prev || nextState.importTemplates[0].code)
        }
      } catch (error) {
        if (active) {
          addToast('تعذر تحميل مركز الاستيراد والتصدير للمخزون.', 'error')
        }
      }
    })()
    return () => {
      active = false
    }
  }, [addToast, farmId])

  const activeTemplate = useMemo(
    () => templates.find((entry) => entry.code === selectedTemplate) || null,
    [selectedTemplate, templates],
  )

  const inventoryExportTemplates = useMemo(
    () => exportTemplates.filter((template) => template.ui_surface === 'inventory_center'),
    [exportTemplates],
  )

  const refreshExportJob = async (jobId) => {
    for (let attempt = 0; attempt < 16; attempt += 1) {
      const { data } = await ExportJobs.status(jobId)
      setExportJobs((prev) => [data, ...prev.filter((entry) => entry.id !== data.id)].slice(0, 6))
      if (data.status === 'completed') return data
      if (data.status === 'failed') {
        throw new Error(data.error_message || 'فشل تجهيز ملف التصدير.')
      }
      await new Promise((resolve) => setTimeout(resolve, 1200))
    }
    throw new Error('انتهى وقت انتظار ملف التصدير.')
  }

  const handleExport = async (template, format) => {
    if (!farmId) {
      addToast('اختر المزرعة أولًا قبل التصدير.', 'error')
      return
    }
    setLoading(true)
    try {
      const { data } = await ExportJobs.create({
        export_type: template.export_type,
        format,
        farm_id: farmId,
        item: filters.item || '',
        location: filters.location || '',
        locale: 'ar-YE',
        rtl: true,
      })
      setExportJobs((prev) => [data, ...prev.filter((entry) => entry.id !== data.id)].slice(0, 6))
      const ready = await refreshExportJob(data.id)
      const response = await ExportJobs.download(ready.id)
      downloadBlob(response.data, ready.output_filename || `${template.export_type}.${format}`)
      addToast(`تم تجهيز ${template.title} وتنزيله بنجاح.`, 'success')
    } catch (error) {
      addToast(error?.message || 'تعذر تنفيذ التصدير.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleTemplateDownload = async () => {
    if (!selectedTemplate || !farmId) {
      addToast('اختر المزرعة والقالب أولًا.', 'error')
      return
    }
    setLoading(true)
    try {
      const response = await ImportJobs.downloadTemplate(selectedTemplate, { farm_id: farmId })
      downloadBlob(response.data, `${selectedTemplate}-${farmId}.xlsx`)
      addToast('تم تنزيل القالب بنجاح.', 'success')
    } catch (error) {
      addToast('تعذر تنزيل القالب.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async () => {
    if (!selectedTemplate || !selectedFile || !farmId) {
      addToast('اختر المزرعة والقالب وارفع ملف Excel أولًا.', 'error')
      return
    }
    setLoading(true)
    try {
      const { data } = await ImportJobs.upload({
        template_code: selectedTemplate,
        farm_id: farmId,
        file: selectedFile,
      })
      setImportJob(data)
      setImportJobs((prev) => [data, ...prev.filter((entry) => entry.id !== data.id)].slice(0, 6))
      addToast('تم رفع الملف بنجاح. نفذ التحقق الآن.', 'success')
    } catch (error) {
      addToast(error?.response?.data?.detail || 'تعذر رفع ملف Excel.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleValidate = async () => {
    if (!importJob?.id) {
      addToast('ارفع الملف أولًا.', 'error')
      return
    }
    setLoading(true)
    try {
      const { data } = await ImportJobs.validate(importJob.id)
      setImportJob(data)
      setImportJobs((prev) => [data, ...prev.filter((entry) => entry.id !== data.id)].slice(0, 6))
      addToast('تم فحص الملف وبناء المعاينة.', 'success')
    } catch (error) {
      addToast(error?.response?.data?.detail || 'تعذر التحقق من الملف.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleApply = async () => {
    if (!importJob?.id) {
      addToast('لا توجد مهمة جاهزة للتطبيق.', 'error')
      return
    }
    setLoading(true)
    try {
      const { data } = await ImportJobs.apply(importJob.id)
      setImportJob(data)
      setImportJobs((prev) => [data, ...prev.filter((entry) => entry.id !== data.id)].slice(0, 6))
      addToast('تم تطبيق ملف Excel بنجاح.', 'success')
      onImportApplied?.()
    } catch (error) {
      addToast(error?.response?.data?.detail || 'تعذر تطبيق الملف.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadErrors = async () => {
    if (!importJob?.id) return
    try {
      const response = await ImportJobs.downloadErrors(importJob.id)
      downloadBlob(response.data, `import-errors-${importJob.id}.xlsx`)
    } catch (error) {
      addToast('لا يوجد ملف أخطاء قابل للتنزيل.', 'error')
    }
  }

  return (
    <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm p-6 space-y-5">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
            مركز الاستيراد والتصدير
          </h2>
          <p className="text-sm text-gray-500 dark:text-slate-400">
            ملفات Excel عربية RTL للمخزون، مع JSON اختياري للتكامل من نفس المنصة الحاكمة.
          </p>
        </div>
        <span className="rounded-full bg-slate-100 dark:bg-slate-700 px-3 py-1 text-xs font-semibold text-slate-600 dark:text-slate-200">
          XLSX أساسي • JSON اختياري
        </span>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-4 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-800 dark:text-white">كتالوج تقارير المخزون</h3>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {inventoryExportTemplates.length} تقرير
            </span>
          </div>
          <div className="space-y-3" data-testid="inventory-export-catalog">
            {inventoryExportTemplates.map((template) => (
              <div
                key={template.export_type}
                className="rounded-lg bg-slate-50 dark:bg-slate-900/40 p-3 space-y-3"
              >
                <div className="space-y-1">
                  <div className="text-sm font-medium text-slate-700 dark:text-slate-200">
                    {template.title}
                  </div>
                  {template.description && (
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {template.description}
                    </p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                  <span className="rounded-full bg-white/80 dark:bg-slate-800 px-2 py-1">
                    {MODE_SCOPE_LABELS[template.mode_scope] || template.mode_scope}
                  </span>
                  <span className="rounded-full bg-white/80 dark:bg-slate-800 px-2 py-1">
                    {template.sensitivity_level || 'normal'}
                  </span>
                </div>
                <div className="flex gap-2">
                  {(template.formats || []).includes('xlsx') && (
                    <button
                      type="button"
                      className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
                      onClick={() => handleExport(template, 'xlsx')}
                      disabled={loading}
                    >
                      تصدير Excel
                    </button>
                  )}
                  {(template.formats || []).includes('json') && (
                    <button
                      type="button"
                      className="rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm font-semibold text-slate-700 dark:text-slate-200 disabled:opacity-60"
                      onClick={() => handleExport(template, 'json')}
                      disabled={loading}
                    >
                      تصدير JSON
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {!!exportJobs.length && (
            <div className="space-y-2" data-testid="inventory-export-jobs">
              <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200">سجل التصدير</h4>
              {exportJobs.map((job) => (
                <div
                  key={job.id}
                  className="flex flex-col gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                >
                  <span className="text-slate-700 dark:text-slate-200">
                    {job.output_filename || job.metadata?.export_type || `job-${job.id}`}
                  </span>
                  <span className="text-slate-500 dark:text-slate-400">
                    {JOB_STATUS_LABELS[job.status] || job.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-4 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-800 dark:text-white">استيراد المخزون</h3>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {templates.length} قالب
            </span>
          </div>
          <div className="space-y-3">
            <select
              className="w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={selectedTemplate}
              onChange={(event) => setSelectedTemplate(event.target.value)}
            >
              <option value="">اختر القالب</option>
              {templates.map((template) => (
                <option key={template.code} value={template.code}>
                  {template.title}
                </option>
              ))}
            </select>
            {activeTemplate && (
              <div className="rounded-lg bg-slate-50 dark:bg-slate-900/40 p-3">
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  {activeTemplate.description}
                </p>
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  {MODE_SCOPE_LABELS[activeTemplate.mode_scope] || activeTemplate.mode_scope}
                </p>
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm font-semibold text-slate-700 dark:text-slate-200 disabled:opacity-60"
                onClick={handleTemplateDownload}
                disabled={loading}
              >
                تنزيل القالب
              </button>
              <input
                type="file"
                accept=".xlsx"
                onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
                className="block text-sm text-slate-600 dark:text-slate-300"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
                onClick={handleUpload}
                disabled={loading}
              >
                رفع ملف Excel
              </button>
              <button
                type="button"
                className="rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm font-semibold text-slate-700 dark:text-slate-200 disabled:opacity-60"
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

          {importJob && (
            <div
              className="space-y-3 rounded-lg bg-slate-50 dark:bg-slate-900/40 p-3"
              data-testid="inventory-import-preview"
            >
              <div className="flex flex-wrap gap-3 text-sm text-slate-600 dark:text-slate-300">
                <span>الحالة: {JOB_STATUS_LABELS[importJob.status] || importJob.status}</span>
                <span>عدد الصفوف: {importJob.row_count || 0}</span>
                <span>المرفوض: {importJob.rejected_count || 0}</span>
                <span>المطبق: {importJob.applied_count || 0}</span>
              </div>
              {!!importJob.preview_rows?.length && (
                <div className="max-h-64 overflow-auto rounded-lg border border-slate-200 dark:border-slate-700">
                  <table className="min-w-full text-sm">
                    <thead className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      <tr>
                        <th className="px-3 py-2 text-end">صف Excel</th>
                        <th className="px-3 py-2 text-end">الحالة</th>
                        <th className="px-3 py-2 text-end">التفاصيل</th>
                      </tr>
                    </thead>
                    <tbody>
                      {importJob.preview_rows.slice(0, 25).map((row) => (
                        <tr key={row.excel_row} className="border-t border-slate-200 dark:border-slate-700">
                          <td className="px-3 py-2">{row.excel_row}</td>
                          <td className="px-3 py-2">
                            {JOB_STATUS_LABELS[row.severity] || row.severity}
                          </td>
                          <td className="px-3 py-2 text-slate-600 dark:text-slate-300">
                            {(row.messages || []).join(' | ') || row.item_name || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {!!importJobs.length && (
            <div className="space-y-2" data-testid="inventory-import-jobs">
              <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200">سجل الاستيراد</h4>
              {importJobs.map((job) => (
                <div
                  key={job.id}
                  className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                >
                  <div className="text-slate-700 dark:text-slate-200">
                    {job.template_code} • {JOB_STATUS_LABELS[job.status] || job.status}
                  </div>
                  <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    صفوف: {job.row_count || 0} • مطبق: {job.applied_count || 0} • مرفوض:{' '}
                    {job.rejected_count || 0}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
