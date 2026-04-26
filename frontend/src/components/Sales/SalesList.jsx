import { useState, useEffect, useCallback } from 'react'
import { api, Sales } from '../../api/client'
import {
  Plus,
  Search,
  FileText,
  Trash2,
  Edit2,
  TrendingUp,
  CheckCircle,
  XCircle,
  AlertCircle,
  Printer,
} from 'lucide-react'
import { toast } from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import useFinancialFilters from '../../hooks/useFinancialFilters'
import FinancialFilterBar from '../../components/filters/FinancialFilterBar'

const parseApiErrorMessage = (error, fallback = 'تعذر إتمام العملية.') => {
  const payload = error?.response?.data
  if (!payload) return error?.message || fallback

  const detail = payload.detail
  if (Array.isArray(detail)) return detail.join(' - ')
  if (typeof detail === 'string' && detail.trim()) return detail
  if (typeof payload === 'string' && payload.trim()) return payload

  if (typeof payload === 'object') {
    const messages = []
    Object.entries(payload).forEach(([field, value]) => {
      if (field === 'detail') return
      if (Array.isArray(value)) messages.push(`${field}: ${value.join(', ')}`)
      else if (typeof value === 'string') messages.push(`${field}: ${value}`)
    })
    if (messages.length) return messages.join(' - ')
  }

  return fallback
}

// Loading Skeleton
const LoadingSkeleton = () => (
  <div className="app-page">
    <div className="animate-pulse space-y-6 max-w-7xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 bg-gray-200 dark:bg-white/5 rounded-2xl" />
        ))}
      </div>
      <div className="h-16 bg-gray-200 dark:bg-white/5 rounded-xl" />
      <div className="h-96 bg-gray-200 dark:bg-white/5 rounded-xl" />
    </div>
  </div>
)

export default function SalesList() {
  const navigate = useNavigate()

  // [AGRI-GUARDIAN Axis 6] Unified financial filters
  const {
    filters: financialFilters,
    options: filterOptions,
    loading: filterLoading,
    setFilter: setFinancialFilter,
    resetFilters,
    filterParams,
  } = useFinancialFilters({ dimensions: ['farm', 'crop'] })

  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(false)
  const [confirmingInvoiceId, setConfirmingInvoiceId] = useState(null)
  const [confirmability, setConfirmability] = useState({})
  const [filter, setFilter] = useState('')
  // [AGRI-GUARDIAN] Stat State
  const [summary, setSummary] = useState({ total_revenue: 0, invoice_count: 0, average_invoice: 0 })

  const refreshConfirmability = useCallback(async (rows) => {
    const targets = (rows || []).filter((inv) => inv.status === 'draft' || inv.status === 'pending')
    if (!targets.length) {
      setConfirmability({})
      return
    }

    const checks = await Promise.allSettled(
      targets.map(async (inv) => {
        const res = await api.get(`/sales-invoices/${inv.id}/confirm-check/`)
        const payload = res?.data || {}
        return {
          id: inv.id,
          ok: payload.ok !== false,
          message: payload.message || '',
        }
      }),
    )

    const next = {}
    checks.forEach((result, idx) => {
      const id = targets[idx].id
      if (result.status === 'fulfilled') {
        next[id] = result.value
        return
      }
      const message = parseApiErrorMessage(result.reason, 'الفاتورة غير جاهزة للاعتماد.')
      next[id] = { id, ok: false, message }
    })
    setConfirmability(next)
  }, [])

  const fetchSummary = useCallback(async () => {
    if (!filterParams.farm) return
    try {
      const res = await api.get('/sales-invoices/summary/', { params: filterParams })
      setSummary(res.data)
    } catch (err) {
      console.error('Summary fetch error:', err)
    }
  }, [filterParams])

  const fetchInvoices = useCallback(async () => {
    if (!filterParams.farm) return
    try {
      setLoading(true)
      const res = await Sales.list(filterParams)
      const rows = res.data.results || res.data || []
      setInvoices(rows)
      await refreshConfirmability(rows)
    } catch (err) {
      toast.error('فشل تحميل الفواتير')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [refreshConfirmability, filterParams])

  useEffect(() => {
    if (filterParams.farm) {
      fetchInvoices()
      fetchSummary()
    } else {
      setInvoices([])
      setConfirmability({})
      setSummary({ total_revenue: 0, invoice_count: 0, average_invoice: 0 })
    }
  }, [fetchInvoices, fetchSummary, filterParams.farm])

  const handleDelete = async (id) => {
    if (!window.confirm('هل أنت متأكد من حذف هذه الفاتورة؟')) return
    try {
      await Sales.delete(id)
      toast.success('تم الحذف بنجاح')
      fetchInvoices()
    } catch (err) {
      toast.error('فشل الحذف')
    }
  }

  // [AGRI-GUARDIAN] Confirm invoice (Four-Eyes Principle)
  const handleConfirm = async (invoice) => {
    if (!window.confirm('هل تريد تأكيد هذه الفاتورة؟ سيتم خصم المخزون.')) return
    setConfirmingInvoiceId(invoice.id)
    try {
      const checkRes = await api.get(`/sales-invoices/${invoice.id}/confirm-check/`)
      if (checkRes?.data?.ok === false) {
        const reason = checkRes?.data?.message || 'الفاتورة غير جاهزة للاعتماد.'
        toast.error(`تعذر اعتماد الفاتورة: ${reason}`)
        return
      }
      await api.post(`/sales-invoices/${invoice.id}/confirm/`)
      toast.success('تم تأكيد الفاتورة بنجاح')
      setInvoices((prev) =>
        prev.map((row) => (row.id === invoice.id ? { ...row, status: 'approved' } : row)),
      )
      fetchInvoices()
    } catch (err) {
      const msg = parseApiErrorMessage(
        err,
        'فشل اعتماد الفاتورة. راجع المخزون المتاح وصلاحيات الاعتماد.',
      )
      toast.error(`تعذر اعتماد الفاتورة: ${msg}`)
    } finally {
      setConfirmingInvoiceId(null)
    }
  }

  // [AGRI-GUARDIAN] Cancel invoice
  const handleCancel = async (id) => {
    if (!window.confirm('هل تريد إلغاء هذه الفاتورة؟')) return
    try {
      await api.post(`/sales-invoices/${id}/cancel/`)
      toast.success('تم إلغاء الفاتورة')
      fetchInvoices()
    } catch (err) {
      const msg = parseApiErrorMessage(err, 'فشل إلغاء الفاتورة.')
      toast.error(`تعذر إلغاء الفاتورة: ${msg}`)
    }
  }

  const filteredInvoices = invoices.filter(
    (inv) =>
      inv.customer_name?.includes(filter) || String(inv.invoice_number || inv.id).includes(filter),
  )

  if (loading && !invoices.length) return <LoadingSkeleton />

  if (!filterParams.farm) {
    return (
      <div dir="rtl" className="app-page flex items-center justify-center">
        <div className="text-center space-y-4 max-w-md">
          <div className="p-4 bg-amber-100 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 rounded-full w-fit mx-auto">
            <AlertCircle className="w-12 h-12" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">يرجى اختيار مزرعة</h2>
          <p className="text-gray-500 dark:text-gray-400">
            لعرض سجل المبيعات، يجب تحديد المزرعة النشطة.
          </p>
          <div className="mt-4 flex justify-center">
            <FinancialFilterBar
              filters={financialFilters}
              options={filterOptions}
              loading={filterLoading}
              setFilter={setFinancialFilter}
              onReset={resetFilters}
              dimensions={['farm', 'crop']}
            />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div data-testid="sales-page" dir="rtl" className="app-page space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-black tracking-tight bg-gradient-to-r from-emerald-600 dark:from-emerald-400 to-amber-500 dark:to-amber-200 bg-clip-text text-transparent">
            فواتير المبيعات
          </h1>
          <p className="text-gray-500 dark:text-zinc-500 font-medium mt-1">
            إدارة الفواتير والإيرادات
          </p>
        </div>
        <button
          onClick={() => navigate('/sales/new')}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-emerald-600 text-white font-bold shadow-lg shadow-emerald-500/20 hover:bg-emerald-500 transition-all"
        >
          <Plus className="w-5 h-5" />
          فاتورة جديدة
        </button>
      </div>

      {/* [AGRI-GUARDIAN] Unified filter bar */}
      <FinancialFilterBar
        filters={financialFilters}
        options={filterOptions}
        loading={filterLoading}
        setFilter={setFinancialFilter}
        onReset={resetFilters}
        dimensions={['farm', 'crop']}
      />

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-3xl border border-emerald-300/60 dark:border-emerald-500/30 bg-gradient-to-br from-emerald-100/90 to-emerald-50/70 dark:from-emerald-500/20 dark:to-emerald-500/5 backdrop-blur-xl p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-emerald-500/20 rounded-2xl border border-emerald-500/30">
              <TrendingUp className="w-8 h-8 text-emerald-400" />
            </div>
            <div>
              <p className="text-emerald-700 dark:text-emerald-300 text-sm font-medium">
                إجمالي المبيعات
              </p>
              <h2 className="text-3xl font-black text-emerald-900 dark:text-white mt-1">
                {Number(summary.total_revenue).toLocaleString()}{' '}
                <span className="text-lg text-emerald-700/80 dark:text-white/40">ريال</span>
              </h2>
            </div>
          </div>
        </div>

        <div className="app-card rounded-3xl bg-gradient-to-br from-sky-50/90 to-white/70 dark:from-white/5 dark:to-white/[0.02] p-6 flex items-center justify-between">
          <div>
            <p className="text-slate-600 dark:text-white/50 text-sm">عدد الفواتير</p>
            <h2 className="text-3xl font-black text-slate-900 dark:text-white mt-1">
              {summary.invoice_count}
            </h2>
          </div>
          <div className="p-3 bg-blue-500/10 text-blue-600 dark:text-blue-400 rounded-2xl border border-blue-500/20">
            <FileText className="w-8 h-8" />
          </div>
        </div>

        <div className="app-card rounded-3xl bg-gradient-to-br from-indigo-50/90 to-white/70 dark:from-white/5 dark:to-white/[0.02] p-6 flex items-center justify-between">
          <div>
            <p className="text-slate-600 dark:text-white/50 text-sm">معدل الفاتورة</p>
            <h2 className="text-3xl font-black text-slate-900 dark:text-white mt-1">
              {Number(summary.average_invoice).toLocaleString()}{' '}
              <span className="text-lg text-slate-500 dark:text-white/40">ريال</span>
            </h2>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="app-panel p-4 flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="relative w-full md:w-80">
          <Search className="absolute right-4 top-3 w-5 h-5 text-slate-400 dark:text-white/30" />
          <input
            type="text"
            placeholder="بحث برقم الفاتورة أو العميل..."
            className="app-input pl-4 pr-12 focus:border-emerald-500/50"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
      </div>

      {/* Invoices Table */}
      <div data-testid="sales-main-grid" className="app-panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-end">
            <thead className="bg-slate-100/90 dark:bg-white/5 text-slate-600 dark:text-white/40 font-bold border-b border-slate-200 dark:border-white/10">
              <tr>
                <th className="px-6 py-4"># الفاتورة</th>
                <th className="px-6 py-4">العميل</th>
                <th className="px-6 py-4">التاريخ</th>
                <th className="px-6 py-4">إجمالي المبلغ</th>
                <th className="px-6 py-4">الحالة</th>
                <th className="px-6 py-4 text-start">إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {filteredInvoices.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-16 text-center text-slate-500 dark:text-white/30">
                    لا توجد فواتير مطابقة
                  </td>
                </tr>
              ) : (
                filteredInvoices.map((inv) => (
                  <tr
                    key={inv.id}
                    className="border-t border-slate-200/70 dark:border-white/5 hover:bg-slate-100/70 dark:hover:bg-white/5 transition-colors group"
                  >
                    <td className="px-6 py-4 font-mono text-slate-600 dark:text-white/60">
                      #{inv.invoice_number || inv.id}
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-800 dark:text-white">
                      {inv.customer_name}
                    </td>
                    <td className="px-6 py-4 text-slate-500 dark:text-white/50">
                      {new Date(inv.invoice_date || inv.date).toLocaleDateString('ar-EG')}
                    </td>
                    <td className="px-6 py-4 font-bold text-emerald-400">
                      {Number(inv.total_amount).toLocaleString()} ريال
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold ${
                          inv.status === 'paid'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : inv.status === 'approved'
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : inv.status === 'cancelled' || inv.status === 'canceled'
                                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                : inv.status === 'draft'
                                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                  : inv.status === 'pending'
                                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                    : 'bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-white/60'
                        }`}
                      >
                        {inv.status === 'paid'
                          ? 'مدفوعة'
                          : inv.status === 'cancelled' || inv.status === 'canceled'
                            ? 'مطوية إداريًا'
                            : inv.status === 'draft'
                              ? 'مسودة'
                              : inv.status === 'approved'
                                ? 'معتمدة'
                                : inv.status === 'pending'
                                  ? 'معلقة'
                                  : inv.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                        {/* Print Button - Always visible */}
                        <button
                          onClick={() => navigate(`/sales/${inv.id}/print`)}
                          title="طباعة الفاتورة"
                          className="p-2 text-slate-500 dark:text-white/40 hover:text-cyan-500 dark:hover:text-cyan-400 hover:bg-cyan-500/10 rounded-lg transition-colors"
                        >
                          <Printer className="w-4 h-4" />
                        </button>
                        {/* Confirm Button - For draft or pending */}
                        {(inv.status === 'draft' || inv.status === 'pending') && (
                          <button
                            onClick={() => handleConfirm(inv)}
                            disabled={
                              confirmingInvoiceId === inv.id || confirmability[inv.id]?.ok === false
                            }
                            title={
                              confirmability[inv.id]?.ok === false
                                ? `لا يمكن الاعتماد: ${confirmability[inv.id]?.message || 'الفاتورة غير جاهزة.'}`
                                : 'تأكيد الفاتورة (ترحيل للمخزون والمالية)'
                            }
                            className={`p-2 rounded-lg transition-colors ${
                              confirmingInvoiceId === inv.id || confirmability[inv.id]?.ok === false
                                ? 'text-slate-300 dark:text-white/20 cursor-not-allowed'
                                : 'text-slate-500 dark:text-white/40 hover:text-emerald-500 dark:hover:text-emerald-400 hover:bg-emerald-500/10'
                            }`}
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                        )}
                        {/* Cancel Button - Only for approved */}
                        {inv.status === 'approved' && (
                          <button
                            onClick={() => handleCancel(inv.id)}
                            title="إلغاء الفاتورة"
                            className="p-2 text-slate-500 dark:text-white/40 hover:text-amber-500 dark:hover:text-amber-400 hover:bg-amber-500/10 rounded-lg transition-colors"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => navigate(`/sales/${inv.id}`)}
                          className="p-2 text-slate-500 dark:text-white/40 hover:text-blue-500 dark:hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition-colors"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(inv.id)}
                          className="p-2 text-slate-500 dark:text-white/40 hover:text-rose-500 dark:hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
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
