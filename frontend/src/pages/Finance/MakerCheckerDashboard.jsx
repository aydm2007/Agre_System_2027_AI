import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'
import { toast } from 'react-hot-toast'
import { useFarmContext } from '../../api/farmContext.jsx'
import { formatMoney } from '../../utils/decimal'
import { CheckCircle, AlertCircle, RefreshCw, BookOpen } from 'lucide-react'
import { ACCOUNT_LABELS } from './constants'
import { v4 as uuidv4 } from 'uuid'

const LoadingSkeleton = () => (
  <div className="app-page">
    <div className="animate-pulse space-y-6 max-w-7xl mx-auto">
      <div className="h-20 bg-gray-200 dark:bg-white/5 rounded-2xl" />
      <div className="h-96 bg-gray-200 dark:bg-white/5 rounded-xl" />
    </div>
  </div>
)

export default function MakerCheckerDashboard() {
  const { selectedFarmId } = useFarmContext()
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [approving, setApproving] = useState(false)
  const [selectedIds, setSelectedIds] = useState(new Set())

  const fetchPendingEntries = useCallback(async () => {
    if (!selectedFarmId) return
    try {
      setLoading(true)
      const res = await api.get('/finance/ledger/', {
        params: { farm_id: selectedFarmId, is_posted: false },
      })
      // Ensure we only get unposted entries
      const pending = (res.data.results || res.data || []).filter((e) => !e.is_posted)
      setEntries(pending)
      setSelectedIds(new Set())
    } catch (err) {
      console.error('Fetch error:', err)
      toast.error('تعذر تحميل القيود المعلقة')
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId])

  useEffect(() => {
    fetchPendingEntries()
  }, [fetchPendingEntries])

  const toggleSelection = (id) => {
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelectedIds(next)
  }

  const toggleAll = () => {
    if (selectedIds.size === entries.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(entries.map((e) => e.id)))
    }
  }

  const handleApprove = async () => {
    if (!selectedFarmId || selectedIds.size === 0) return
    const entry_ids = Array.from(selectedIds)

    if (!window.confirm(`هل أنت متأكد من اعتماد ${entry_ids.length} قيود وجعلها نهائية؟`)) {
      return
    }

    try {
      setApproving(true)
      const idempotencyKey = uuidv4()
      const res = await api.post(
        '/finance/ledger/approve-manual-entries/',
        { farm_id: selectedFarmId, entry_ids },
        { headers: { 'X-Idempotency-Key': idempotencyKey } },
      )
      toast.success(res.data.message || 'تم اعتماد القيود بنجاح')
      fetchPendingEntries()
    } catch (err) {
      console.error('Approval error:', err)
      toast.error(err.response?.data?.error || 'فشل في اعتماد القيود')
    } finally {
      setApproving(false)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('ar-SA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getAccountLabel = (code) => ACCOUNT_LABELS[code]?.name || code

  if (!selectedFarmId) {
    return (
      <div dir="rtl" className="app-page">
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-8 text-center max-w-lg mx-auto mt-20">
          <AlertCircle className="w-16 h-16 text-amber-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-amber-900 dark:text-white mb-2">اختر مزرعة</h2>
          <p className="text-slate-700 dark:text-white/60">
            يرجى اختيار مزرعة من الشريط العلوي لعرض القيود المعلقة
          </p>
        </div>
      </div>
    )
  }

  if (loading) return <LoadingSkeleton />

  return (
    <div data-testid="maker-checker-dashboard" dir="rtl" className="app-page space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 dark:text-white flex items-center gap-3">
            <CheckCircle className="w-8 h-8 text-emerald-500" />
            شاشة الاعتماد المالي
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            مراجعة واعتماد القيود اليدوية والتوزيعات المعلقة (Maker-Checker)
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchPendingEntries}
            className="p-2.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            title="تحديث"
          >
            <RefreshCw className="w-5 h-5 text-slate-600 dark:text-slate-300" />
          </button>
          <button
            onClick={handleApprove}
            disabled={selectedIds.size === 0 || approving}
            className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 text-white font-bold rounded-xl hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
          >
            {approving ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <CheckCircle className="w-5 h-5" />
            )}
            اعتماد المحدد ({selectedIds.size})
          </button>
        </div>
      </div>

      <div className="app-panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-end">
            <thead className="bg-slate-100/90 dark:bg-white/5 text-slate-600 dark:text-white/40 font-bold border-b border-slate-200 dark:border-white/10">
              <tr>
                <th className="px-6 py-4 w-12 text-center">
                  <input
                    type="checkbox"
                    checked={selectedIds.size === entries.length && entries.length > 0}
                    onChange={toggleAll}
                    disabled={entries.length === 0}
                    className="w-4 h-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                  />
                </th>
                <th className="px-6 py-4">التاريخ</th>
                <th className="px-6 py-4">الحساب</th>
                <th className="px-6 py-4">الوصف</th>
                <th className="px-6 py-4 text-emerald-600">مدين</th>
                <th className="px-6 py-4 text-blue-600">دائن</th>
                <th className="px-6 py-4">المنشئ</th>
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-16 text-center text-slate-500 dark:text-white/40">
                    <BookOpen className="w-12 h-12 mx-auto mb-4 opacity-30" />
                    لا توجد قيود معلقة بانتظار الاعتماد.
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr
                    key={entry.id}
                    className={`border-t border-slate-200/70 dark:border-white/5 transition-colors ${
                      selectedIds.has(entry.id)
                        ? 'bg-emerald-50/50 dark:bg-emerald-900/20'
                        : 'hover:bg-slate-50 dark:hover:bg-white/5'
                    }`}
                  >
                    <td className="px-6 py-4 text-center">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(entry.id)}
                        onChange={() => toggleSelection(entry.id)}
                        className="w-4 h-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                      />
                    </td>
                    <td className="px-6 py-4 text-slate-600 dark:text-slate-400">
                      {formatDate(entry.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2.5 py-1 text-xs font-bold rounded-lg border bg-slate-100 border-slate-200 text-slate-700 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300">
                        {entry.account_code_name || getAccountLabel(entry.account_code)}
                      </span>
                    </td>
                    <td
                      className="px-6 py-4 font-medium max-w-xs truncate"
                      title={entry.localized_description || entry.description}
                    >
                      {entry.localized_description || entry.description}
                    </td>
                    <td
                      className="px-6 py-4 font-bold text-emerald-600 dark:text-emerald-400"
                      dir="ltr"
                    >
                      {Number(entry.debit) > 0 ? formatMoney(entry.debit) : '-'}
                    </td>
                    <td className="px-6 py-4 font-bold text-blue-600 dark:text-blue-400" dir="ltr">
                      {Number(entry.credit) > 0 ? formatMoney(entry.credit) : '-'}
                    </td>
                    <td className="px-6 py-4 text-slate-600 dark:text-slate-400">
                      {entry.user_name || 'النظام'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
