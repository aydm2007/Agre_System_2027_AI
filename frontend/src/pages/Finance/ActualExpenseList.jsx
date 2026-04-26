import { useState, useEffect, useMemo } from 'react'
import PropTypes from 'prop-types'
import { api } from '../../api/client'
import { toast } from 'react-hot-toast'
import { useFarmContext } from '../../api/farmContext.jsx'
import { useAuth } from '../../auth/AuthContext'
import {
  DollarSign,
  Plus,
  Search,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  Trash2,
  Edit2,
  ChevronDown,
  Calendar,
} from 'lucide-react'
import { ACCOUNT_CODES } from './constants'
import ExpenseForm from './components/ExpenseForm'
import { formatMoney } from '../../utils/decimal'
import useFinancialFilters from '../../hooks/useFinancialFilters'
import FinancialFilterBar from '../../components/filters/FinancialFilterBar'

const parseApiErrorMessage = (error, fallback = 'تعذر إتمام العملية.') => {
  const payload = error?.response?.data
  if (!payload) return error?.message || fallback
  if (typeof payload === 'string' && payload.trim()) return payload
  const detail = payload?.detail
  if (Array.isArray(detail)) return detail.join(' - ')
  if (typeof detail === 'string' && detail.trim()) return detail
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

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// ACCOUNT CODES
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// LOADING SKELETON
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const LoadingSkeleton = () => (
  <div className="app-page">
    <div className="animate-pulse space-y-6 max-w-7xl mx-auto">
      <div className="h-20 bg-gray-200 dark:bg-white/5 rounded-2xl" />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 bg-gray-200 dark:bg-white/5 rounded-2xl" />
        ))}
      </div>
      <div className="h-96 bg-gray-200 dark:bg-white/5 rounded-xl" />
    </div>
  </div>
)

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// ERROR STATE
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const ErrorState = ({ error, onRetry }) => (
  <div className="app-page flex items-center justify-center">
    <div className="text-center space-y-4">
      <div className="w-16 h-16 rounded-full bg-rose-500/20 flex items-center justify-center mx-auto">
        <AlertCircle className="w-8 h-8 text-rose-400" />
      </div>
      <h2 className="text-xl font-bold text-slate-900 dark:text-white">
        حدث خطأ أثناء تحميل البيانات
      </h2>
      <p className="text-slate-600 dark:text-white/50">{error}</p>
      <button
        onClick={onRetry}
        className="px-6 py-3 rounded-xl bg-emerald-600 text-white font-bold hover:bg-emerald-500 transition-all flex items-center gap-2 mx-auto"
        aria-label="إعادة المحاولة"
      >
        <RefreshCw className="w-4 h-4" />
        إعادة المحاولة
      </button>
    </div>
  </div>
)

ErrorState.propTypes = {
  error: PropTypes.string.isRequired,
  onRetry: PropTypes.func.isRequired,
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// STAT CARD
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const StatCard = ({ title, value, icon: Icon, color, subValue }) => (
  <div
    className={`rounded-2xl border border-${color}-500/30 bg-gradient-to-br from-${color}-500/20 to-${color}-500/5 backdrop-blur-xl p-5`}
  >
    <div className="flex items-center gap-3">
      <div className={`p-2.5 bg-${color}-500/20 rounded-xl border border-${color}-500/30`}>
        <Icon className={`w-6 h-6 text-${color}-400`} />
      </div>
      <div>
        <p className={`text-${color}-400/70 text-sm font-medium`}>{title}</p>
        <h2 className="text-xl font-black text-white mt-0.5">
          {typeof value === 'number' ? formatMoney(value) : value}
          {subValue && <span className="text-sm text-white/40 me-1">{subValue}</span>}
        </h2>
      </div>
    </div>
  </div>
)

StatCard.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  icon: PropTypes.elementType.isRequired,
  color: PropTypes.string.isRequired,
  subValue: PropTypes.string,
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// EXPENSE FORM MODAL
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// MAIN COMPONENT
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export default function ActualExpenseList() {
  const { selectedFarmId, farms } = useFarmContext()
  const { hasPermission, hasFarmRole, isAdmin, isSuperuser } = useAuth()
  const [expenses, setExpenses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchFilter, setSearchFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [modalExpense, setModalExpense] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const canManageExpenses =
    isAdmin ||
    isSuperuser ||
    hasPermission('can_manage_expenses') ||
    hasFarmRole('manager') ||
    hasFarmRole('admin')

  // [AGRI-GUARDIAN Axis 6] Multi-level cascading filters
  const {
    filters: financialFilters,
    options: filterOptions,
    loading: filterLoading,
    setFilter: setFinancialFilter,
    resetFilters,
    filterParams,
  } = useFinancialFilters({ dimensions: ['farm'] })

  // Fetch expenses
  const fetchExpenses = async () => {
    if (!filterParams.farm) {
      setLoading(false)
      return
    }
    try {
      setLoading(true)
      setError(null)
      const params = { ...filterParams }
      if (statusFilter === 'allocated') params.is_allocated = true
      if (statusFilter === 'pending') params.is_allocated = false

      const res = await api.get('/finance/expenses/', { params })
      setExpenses(res.data.results || res.data || [])
    } catch (err) {
      console.error('Expense fetch error:', err)
      const message = parseApiErrorMessage(err, 'تعذر تحميل المصروفات.')
      setError(message)
      toast.error(`فشل تحميل المصروفات: ${message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchExpenses()
  }, [filterParams, statusFilter]) // eslint-disable-line react-hooks/exhaustive-deps

  // Stats
  const stats = useMemo(() => {
    const total = expenses.reduce((sum, e) => sum + Number(e.amount || 0), 0)
    const allocated = expenses.filter((e) => e.is_allocated).length
    const pending = expenses.filter((e) => !e.is_allocated).length
    return { total, allocated, pending, count: expenses.length }
  }, [expenses])

  // Filter by search
  const filteredExpenses = useMemo(() => {
    if (!searchFilter) return expenses
    const lower = searchFilter.toLowerCase()
    return expenses.filter(
      (e) =>
        e.description?.toLowerCase().includes(lower) ||
        e.account_code?.toLowerCase().includes(lower),
    )
  }, [expenses, searchFilter])

  // Delete expense
  const handleDelete = async (id) => {
    if (!canManageExpenses) {
      toast.error('لا تملك صلاحية حذف المصروفات.')
      return
    }
    if (!window.confirm('هل أنت متأكد من حذف هذا المصروف؟')) return
    try {
      await api.delete(`/finance/expenses/${id}/`)
      toast.success('تم حذف المصروف')
      fetchExpenses()
    } catch (err) {
      toast.error('فشل حذف المصروف')
    }
  }

  // Allocate expense
  const handleAllocate = async (id) => {
    if (!canManageExpenses) {
      toast.error('لا تملك صلاحية تخصيص المصروفات.')
      return
    }
    try {
      await api.post(`/finance/expenses/${id}/allocate/`)
      toast.success('تم تخصيص المصروف')
      fetchExpenses()
    } catch (err) {
      toast.error(`تعذر تخصيص المصروف: ${parseApiErrorMessage(err, 'فشل تخصيص المصروف.')}`)
    }
  }

  // Format date
  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('ar-SA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const selectedFarm = farms?.find((f) => String(f.id) === String(selectedFarmId))

  if (!selectedFarmId) {
    return (
      <div dir="rtl" className="app-page">
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-8 text-center max-w-lg mx-auto mt-20">
          <AlertCircle className="w-16 h-16 text-amber-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-amber-900 dark:text-white mb-2">اختر مزرعة</h2>
          <p className="text-amber-900/80 dark:text-white/60">
            يرجى اختيار مزرعة من الشريط العلوي لعرض المصروفات الفعلية
          </p>
        </div>
      </div>
    )
  }

  if (loading) return <LoadingSkeleton />
  if (error) return <ErrorState error={error} onRetry={fetchExpenses} />

  return (
    <div data-testid="finance-expenses-page" dir="rtl" className="app-page space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-black tracking-tight bg-gradient-to-r from-orange-500 to-amber-400 bg-clip-text text-transparent">
            المصروفات الفعلية
          </h1>
          <p className="text-gray-500 dark:text-zinc-500 font-medium mt-1">
            إدارة المصروفات والنفقات - {selectedFarm?.name || 'المزرعة'}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={fetchExpenses}
            className="p-3 rounded-xl bg-white/80 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-white dark:hover:bg-white/10 transition-all"
            aria-label="تحديث البيانات"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          {canManageExpenses && (
            <button
              onClick={() => {
                setModalExpense(null)
                setShowModal(true)
              }}
              className="px-5 py-3 rounded-xl bg-emerald-600 text-white font-bold hover:bg-emerald-500 transition-all flex items-center gap-2"
              aria-label="إضافة مصروف جديد"
            >
              <Plus className="w-5 h-5" />
              إضافة مصروف
            </button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="إجمالي المصروفات"
          value={stats.total}
          icon={DollarSign}
          color="orange"
          subValue="ريال"
        />
        <StatCard title="عدد المصروفات" value={stats.count} icon={Calendar} color="blue" />
        <StatCard title="تم التخصيص" value={stats.allocated} icon={CheckCircle} color="emerald" />
        <StatCard title="قيد الانتظار" value={stats.pending} icon={Clock} color="amber" />
      </div>

      {/* [AGRI-GUARDIAN] Multi-level filter bar */}
      <FinancialFilterBar
        filters={financialFilters}
        options={filterOptions}
        loading={filterLoading}
        setFilter={setFinancialFilter}
        onReset={resetFilters}
        dimensions={['farm']}
      />

      {/* Filters */}
      <div className="app-panel p-4 flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="relative w-full md:w-80">
          <Search className="absolute right-4 top-3 w-5 h-5 text-slate-400 dark:text-white/30" />
          <input
            type="text"
            placeholder="بحث في الوصف..."
            className="app-input pl-4 pr-12 focus:border-orange-500/50"
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            aria-label="بحث في المصروفات"
          />
        </div>

        <div className="relative">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="appearance-none pl-10 pr-4 py-3 bg-white/90 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-800 dark:text-white focus:border-orange-500/50 focus:outline-none min-w-[180px]"
            aria-label="تصفية حسب الحالة"
          >
            <option value="">جميع المصروفات</option>
            <option value="pending">قيد الانتظار</option>
            <option value="allocated">تم التخصيص</option>
          </select>
          <ChevronDown className="absolute left-3 top-3.5 w-4 h-4 text-slate-400 dark:text-white/30 pointer-events-none" />
        </div>
      </div>

      {/* Expenses Table */}
      <div className="app-panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-end">
            <thead className="bg-slate-100/90 dark:bg-white/5 text-slate-600 dark:text-white/40 font-bold border-b border-slate-200 dark:border-white/10">
              <tr>
                <th className="px-6 py-4">التاريخ</th>
                <th className="px-6 py-4">الوصف</th>
                <th className="px-6 py-4">الحساب</th>
                <th className="px-6 py-4">المبلغ</th>
                <th className="px-6 py-4">الحالة</th>
                <th className="px-6 py-4">الإجراءات</th>
              </tr>
            </thead>
            <tbody>
              {filteredExpenses.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-16 text-center text-slate-500 dark:text-white/30">
                    <DollarSign className="w-12 h-12 mx-auto mb-4 opacity-30" />
                    لا توجد مصروفات
                  </td>
                </tr>
              ) : (
                filteredExpenses.map((expense) => (
                  <tr
                    key={expense.id}
                    className="border-t border-slate-200/70 dark:border-white/5 hover:bg-slate-100/70 dark:hover:bg-white/5 transition-colors"
                  >
                    <td className="px-6 py-4 text-slate-600 dark:text-white/50">
                      {formatDate(expense.date)}
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-900 dark:text-white max-w-xs truncate">
                      {expense.description}
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-3 py-1.5 rounded-lg text-xs font-bold bg-purple-500/20 text-purple-400 border border-purple-500/30">
                        {ACCOUNT_CODES.find((a) => a.code === expense.account_code)?.label ||
                          expense.account_code}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-bold text-orange-400" dir="ltr">
                      {formatMoney(expense.amount)}
                      <span className="text-xs text-slate-500 dark:text-white/40 ms-1">
                        {expense.currency}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {expense.is_allocated ? (
                        <span className="flex items-center gap-1 text-emerald-400 text-xs">
                          <CheckCircle className="w-3.5 h-3.5" />
                          مخصص
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-amber-400 text-xs">
                          <Clock className="w-3.5 h-3.5" />
                          قيد الانتظار
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {!expense.is_allocated && canManageExpenses && (
                          <>
                            <button
                              onClick={() => handleAllocate(expense.id)}
                              className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors"
                              title="تخصيص"
                              aria-label={`تخصيص ${expense.description}`}
                            >
                              <CheckCircle className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => {
                                setModalExpense(expense)
                                setShowModal(true)
                              }}
                              className="p-2 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors"
                              title="تعديل"
                              aria-label={`تعديل ${expense.description}`}
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                          </>
                        )}
                        {canManageExpenses && (
                          <button
                            onClick={() => handleDelete(expense.id)}
                            className="p-2 rounded-lg bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition-colors"
                            title="حذف"
                            aria-label={`حذف ${expense.description}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Info Notice */}
      <div className="rounded-2xl border border-orange-500/20 bg-orange-500/5 p-5">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-orange-400 mt-0.5" />
          <div className="text-sm text-slate-700 dark:text-white/60">
            <strong className="text-orange-400">معلومة:</strong> المصروفات الفعلية هي نفقات تشغيلية
            يتم تسجيلها قبل تخصيصها للتكاليف. بعد التخصيص، تنتقل إلى دفتر الأستاذ المالي غير القابل
            للتعديل.
          </div>
        </div>
      </div>

      {/* Modal */}
      {showModal && canManageExpenses && (
        <ExpenseForm
          expense={modalExpense}
          farmId={selectedFarmId}
          onClose={() => setShowModal(false)}
          onSave={() => {
            setShowModal(false)
            fetchExpenses()
          }}
        />
      )}
    </div>
  )
}
