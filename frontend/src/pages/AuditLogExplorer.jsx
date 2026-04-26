/**
 * [AGRI-GUARDIAN Phase 4] AuditLog Explorer
 *
 * Full-page forensic audit log viewer with filtering and CSV export.
 * Backed by AuditLogViewSet (read-only, requires superuser or sector finance authority).
 *
 * Route: /audit-explorer (admin/superuser only)
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Download, Filter, RefreshCw, Search, Shield } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useFarmContext } from '../api/farmContext'

const fmtDate = (v) => {
  if (!v) return '—'
  try {
    return new Date(v).toLocaleString('ar-YE')
  } catch {
    return v
  }
}

const ACTION_LABELS = {
  CREATE: 'إنشاء',
  UPDATE: 'تحديث',
  DELETE: 'حذف',
  APPROVE: 'اعتماد',
  REJECT: 'رفض',
  OVERRIDE: 'تجاوز',
  REOPEN: 'إعادة فتح',
  ROUTE_BREACH_ATTEMPT: 'محاولة اختراق مسار',
}

function exportCSV(rows) {
  const headers = ['المعرف', 'الوقت', 'المنفذ', 'الإجراء', 'النموذج', 'الكائن', 'السبب']
  const csvRows = [
    headers.join(','),
    ...rows.map((r) =>
      [r.id, r.timestamp, r.actor_name, r.action, r.model, r.object_id, `"${(r.reason || '').replace(/"/g, '""')}"`].join(','),
    ),
  ]
  const blob = new Blob(['\uFEFF' + csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', `audit-log-${new Date().toISOString().slice(0, 10)}.csv`)
  link.click()
  URL.revokeObjectURL(url)
}

export default function AuditLogExplorer() {
  const { isAdmin, is_superuser } = useAuth()
  const { farms } = useFarmContext()

  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [totalCount, setTotalCount] = useState(0)
  const [page, setPage] = useState(1)

  // Filters
  const [search, setSearch] = useState('')
  const [actionFilter, setActionFilter] = useState('')
  const [modelFilter, setModelFilter] = useState('')
  const [farmFilter, setFarmFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const PAGE_SIZE = 30

  const load = useCallback(async (currentPage = 1) => {
    setLoading(true)
    setError('')
    try {
      const params = {
        page: currentPage,
        page_size: PAGE_SIZE,
        ordering: '-timestamp',
      }
      if (actionFilter) params.action = actionFilter
      if (modelFilter) params.model = modelFilter
      if (farmFilter) params.farm_id = farmFilter
      if (dateFrom) params.timestamp__gte = dateFrom
      if (dateTo) params.timestamp__lte = dateTo + 'T23:59:59'
      const res = await api.get('/audit-logs/', { params })
      const data = res.data
      const results = Array.isArray(data) ? data : data?.results || []
      setRows(results)
      setTotalCount(typeof data?.count === 'number' ? data.count : results.length)
    } catch (err) {
      const msg = err.response?.data?.detail || 'تعذر تحميل سجل التدقيق.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [actionFilter, modelFilter, farmFilter, dateFrom, dateTo])

  useEffect(() => {
    load(1)
    setPage(1)
  }, [load])

  const handleExport = () => exportCSV(rows)

  const filteredRows = useMemo(() => {
    if (!search.trim()) return rows
    const q = search.trim().toLowerCase()
    return rows.filter(
      (r) =>
        (r.actor_name || '').toLowerCase().includes(q) ||
        (r.action || '').toLowerCase().includes(q) ||
        (r.model || '').toLowerCase().includes(q) ||
        (r.object_id || '').toLowerCase().includes(q) ||
        (r.reason || '').toLowerCase().includes(q),
    )
  }, [rows, search])

  const totalPages = Math.ceil(totalCount / PAGE_SIZE)

  if (!isAdmin && !is_superuser) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Shield className="h-12 w-12 text-slate-400 mb-4" />
        <div className="text-lg font-semibold text-slate-700 dark:text-slate-200">الوصول مقيد</div>
        <div className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          سجل التدقيق الجنائي مقيد على المشرفين والسلطة المالية القطاعية.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6" dir="rtl">
      {/* Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900 dark:text-white">
            <Shield className="h-6 w-6 text-primary" />
            مستكشف سجل التدقيق الجنائي
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            سجل قانوني للإجراءات — للقراءة فقط — مرتب زمنياً تنازلياً.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => load(page)}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <RefreshCw className="h-4 w-4" /> تحديث
          </button>
          <button
            type="button"
            onClick={handleExport}
            disabled={rows.length === 0}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60"
          >
            <Download className="h-4 w-4" /> تصدير CSV
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
          <Filter className="h-4 w-4" /> الفلاتر
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <div className="relative xl:col-span-2">
            <Search className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="بحث في السجل..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white pr-9 pl-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
            />
          </div>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
          >
            <option value="">كل الإجراءات</option>
            {Object.entries(ACTION_LABELS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="النموذج (FarmSettings...)"
            value={modelFilter}
            onChange={(e) => setModelFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
          />
          <select
            value={farmFilter}
            onChange={(e) => setFarmFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
          >
            <option value="">كل المزارع</option>
            {(farms || []).map((f) => (
              <option key={f.id} value={f.id}>{f.name}</option>
            ))}
          </select>
          <div className="flex gap-2">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="flex-1 rounded-xl border border-slate-200 bg-white px-2 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
              title="من تاريخ"
            />
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="flex-1 rounded-xl border border-slate-200 bg-white px-2 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
              title="إلى تاريخ"
            />
          </div>
        </div>
      </div>

      {/* State indicators */}
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300">
          {error}
        </div>
      )}
      {!loading && !error && (
        <div className="text-xs text-slate-500 dark:text-slate-400">
          عرض {filteredRows.length} من {totalCount} سجل
        </div>
      )}

      {/* Table */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
                <th className="px-4 py-3 text-right font-semibold text-slate-600 dark:text-slate-300">الوقت</th>
                <th className="px-4 py-3 text-right font-semibold text-slate-600 dark:text-slate-300">المنفذ</th>
                <th className="px-4 py-3 text-right font-semibold text-slate-600 dark:text-slate-300">الإجراء</th>
                <th className="px-4 py-3 text-right font-semibold text-slate-600 dark:text-slate-300">النموذج</th>
                <th className="px-4 py-3 text-right font-semibold text-slate-600 dark:text-slate-300">الكائن</th>
                <th className="px-4 py-3 text-right font-semibold text-slate-600 dark:text-slate-300">السبب</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-slate-100 dark:border-slate-700/50">
                    {Array.from({ length: 6 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-3 rounded bg-slate-200 dark:bg-slate-700 animate-pulse" style={{ width: `${60 + Math.random() * 30}%` }} />
                      </td>
                    ))}
                  </tr>
                ))
              ) : filteredRows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-slate-400 dark:text-slate-500">
                    لا توجد سجلات مطابقة للفلاتر الحالية.
                  </td>
                </tr>
              ) : (
                filteredRows.map((row) => (
                  <tr key={row.id} className="border-b border-slate-100 hover:bg-slate-50 dark:border-slate-700/50 dark:hover:bg-slate-900/40 transition-colors">
                    <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">{fmtDate(row.timestamp)}</td>
                    <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-100">{row.actor_name || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                        row.action?.includes('BREACH') || row.action === 'DELETE'
                          ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300'
                          : row.action === 'APPROVE'
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                          : row.action === 'REJECT'
                          ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'
                          : 'bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300'
                      }`}>
                        {ACTION_LABELS[row.action] || row.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600 dark:text-slate-300">{row.model || '—'}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500 dark:text-slate-400 max-w-[8rem] truncate">{row.object_id || '—'}</td>
                    <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 max-w-[14rem] truncate" title={row.reason}>{row.reason || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 dark:border-slate-700">
            <div className="text-xs text-slate-500 dark:text-slate-400">
              الصفحة {page} من {totalPages}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => { const p = Math.max(1, page - 1); setPage(p); load(p) }}
                disabled={page === 1}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-700 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200"
              >
                السابق
              </button>
              <button
                type="button"
                onClick={() => { const p = Math.min(totalPages, page + 1); setPage(p); load(p) }}
                disabled={page === totalPages}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-700 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200"
              >
                التالي
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
