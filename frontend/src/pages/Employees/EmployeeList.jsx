import { useState, useEffect, useMemo } from 'react'
import PropTypes from 'prop-types' // [AGRI-GUARDIAN] Strict Typing
import { api } from '../../api/client'
import { toast } from 'react-hot-toast'
import { useFarmContext } from '../../api/farmContext.jsx'
import {
  Users,
  Plus,
  Search,
  Edit2,
  Trash2,
  RefreshCw,
  AlertCircle,
  UserCheck,
  UserX,
  Phone,
  Mail,
  Briefcase,
  DollarSign,
} from 'lucide-react'
import EmployeeForm from './EmployeeForm'
import useFinancialFilters from '../../hooks/useFinancialFilters'
import FinancialFilterBar from '../../components/filters/FinancialFilterBar'

// ─────────────────────────────────────────────────────────────────────────────
// LOADING SKELETON
// ─────────────────────────────────────────────────────────────────────────────
const LoadingSkeleton = () => (
  <div className="animate-pulse space-y-6">
    <div className="h-16 bg-slate-200/60 dark:bg-white/5 rounded-2xl" />
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="h-32 bg-slate-200/60 dark:bg-white/5 rounded-2xl" />
      ))}
    </div>
    <div className="h-96 bg-slate-200/60 dark:bg-white/5 rounded-xl" />
  </div>
)

// ─────────────────────────────────────────────────────────────────────────────
// STAT CARD
// ─────────────────────────────────────────────────────────────────────────────
const COLORS = {
  blue: {
    border: 'border-blue-500/30',
    bg: 'from-blue-500/10',
    iconBg: 'bg-blue-500/20',
    iconText: 'text-blue-400',
  },
  emerald: {
    border: 'border-emerald-500/30',
    bg: 'from-emerald-500/10',
    iconBg: 'bg-emerald-500/20',
    iconText: 'text-emerald-400',
  },
  rose: {
    border: 'border-rose-500/30',
    bg: 'from-rose-500/10',
    iconBg: 'bg-rose-500/20',
    iconText: 'text-rose-400',
  },
  amber: {
    border: 'border-amber-500/30',
    bg: 'from-amber-500/10',
    iconBg: 'bg-amber-500/20',
    iconText: 'text-amber-400',
  },
}

const StatCard = ({ title, value, icon: Icon, color }) => {
  const styles = COLORS[color] || COLORS.blue
  return (
    <div
      className={`rounded-2xl border ${styles.border} bg-gradient-to-br ${styles.bg} to-transparent p-5`}
    >
      <div className="flex items-center gap-3">
        <div className={`p-2.5 ${styles.iconBg} rounded-xl`}>
          <Icon className={`w-6 h-6 ${styles.iconText}`} />
        </div>
        <div>
          <p className="text-slate-600 dark:text-white/50 text-sm">{title}</p>
          <h3 className="text-2xl font-bold text-slate-900 dark:text-white">{value}</h3>
        </div>
      </div>
    </div>
  )
}

StatCard.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  icon: PropTypes.elementType.isRequired,
  color: PropTypes.string.isRequired,
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
export default function EmployeeList() {
  const { selectedFarmId, farms } = useFarmContext()
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editEmployee, setEditEmployee] = useState(null)

  // [AGRI-GUARDIAN Axis 6] Unified financial filters
  const {
    filters: financialFilters,
    options: filterOptions,
    loading: filterLoading,
    setFilter: setFinancialFilter,
    resetFilters,
    filterParams,
  } = useFinancialFilters({ dimensions: ['farm'] })

  // [AGRI-GUARDIAN] Fetch employees with farm tenant isolation
  const fetchEmployees = async () => {
    if (!filterParams.farm) return
    try {
      setLoading(true)
      const res = await api.get('/employees/', {
        params: { farm: filterParams.farm },
      })
      setEmployees(res.data.results || res.data || [])
    } catch (err) {
      toast.error('فشل تحميل بيانات الموظفين')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchEmployees()
  }, [filterParams.farm]) // eslint-disable-line react-hooks/exhaustive-deps

  // Delete handler
  const handleDelete = async (id) => {
    if (!window.confirm('هل أنت متأكد من حذف هذا الموظف؟')) return
    try {
      await api.delete(`/employees/${id}/`)
      toast.success('تم حذف الموظف')
      fetchEmployees()
    } catch (err) {
      toast.error('فشل الحذف')
    }
  }

  // Stats
  const stats = useMemo(() => {
    const safeEmployees = employees || []
    const active = safeEmployees.filter((e) => e.is_active).length
    const inactive = safeEmployees.filter((e) => !e.is_active).length
    const totalWages = safeEmployees.reduce((sum, e) => sum + Number(e.daily_rate || 0), 0)
    return { active, inactive, total: safeEmployees.length, totalWages }
  }, [employees])

  // Filter
  const filteredEmployees = useMemo(() => {
    const safeEmployees = employees || []
    if (!filter) return safeEmployees
    const lf = filter.toLowerCase()
    return safeEmployees.filter(
      (e) =>
        e.name?.toLowerCase().includes(lf) ||
        e.job_title?.toLowerCase().includes(lf) ||
        e.phone?.includes(filter),
    )
  }, [employees, filter])

  const selectedFarm = farms?.find((f) => f.id === selectedFarmId)

  return (
    <div dir="rtl" className="app-page space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-black tracking-tight bg-gradient-to-r from-blue-600 dark:from-blue-400 to-cyan-500 bg-clip-text text-transparent">
            إدارة الموظفين
          </h1>
          <p className="text-gray-500 dark:text-zinc-500 font-medium mt-1">
            {selectedFarm?.name || 'اختر مزرعة'} - العمالة والأجور
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchEmployees}
            className="p-3 rounded-xl bg-white/80 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-600 dark:text-white/60 hover:text-slate-900 dark:hover:text-white hover:bg-white dark:hover:bg-white/10 transition-all"
            aria-label="تحديث القائمة"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          {selectedFarmId && (
            <button
              onClick={() => {
                setEditEmployee(null)
                setShowModal(true)
              }}
              className="flex items-center gap-2 px-5 py-3 rounded-xl bg-emerald-600 text-white font-bold shadow-lg shadow-emerald-500/20 hover:bg-emerald-500 transition-all"
              aria-label="إضافة موظف جديد"
            >
              <Plus className="w-5 h-5" />
              إضافة موظف
            </button>
          )}
        </div>
      </div>

      {!filterParams.farm ? (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-100/70 dark:bg-amber-500/10 p-6 text-center">
          <AlertCircle className="w-12 h-12 text-amber-400 mx-auto mb-3" />
          <p className="text-amber-900 dark:text-white/70">
            يرجى اختيار مزرعة من الفلاتر أدناه لعرض الموظفين
          </p>
          <div className="mt-4 flex justify-center">
            <FinancialFilterBar
              filters={financialFilters}
              options={filterOptions}
              loading={filterLoading}
              setFilter={setFinancialFilter}
              onReset={resetFilters}
              dimensions={['farm']}
            />
          </div>
        </div>
      ) : loading ? (
        <LoadingSkeleton />
      ) : (
        <>
          {/* [AGRI-GUARDIAN] Unified filter bar */}
          <FinancialFilterBar
            filters={financialFilters}
            options={filterOptions}
            loading={filterLoading}
            setFilter={setFinancialFilter}
            onReset={resetFilters}
            dimensions={['farm']}
          />

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <StatCard title="إجمالي الموظفين" value={stats.total} icon={Users} color="blue" />
            <StatCard title="نشطون" value={stats.active} icon={UserCheck} color="emerald" />
            <StatCard title="غير نشطين" value={stats.inactive} icon={UserX} color="rose" />
            <StatCard
              title="إجمالي الأجور اليومية"
              value={`${stats.totalWages.toLocaleString()} ر`}
              icon={DollarSign}
              color="amber"
            />
          </div>

          {/* Search */}
          <div className="app-panel p-4">
            <div className="relative w-full md:w-80">
              <Search className="absolute right-4 top-3 w-5 h-5 text-slate-400 dark:text-white/30" />
              <input
                type="text"
                placeholder="بحث بالاسم أو المسمى أو الهاتف..."
                className="app-input pl-4 pr-12 focus:border-blue-500/50"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                aria-label="بحث عن موظف"
              />
            </div>
          </div>

          {/* Employees Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredEmployees.length === 0 ? (
              <div className="col-span-full app-card p-8 text-center">
                <Users className="w-12 h-12 text-slate-300 dark:text-white/20 mx-auto mb-3" />
                <p className="text-slate-500 dark:text-white/40">لا يوجد موظفون مطابقون</p>
              </div>
            ) : (
              filteredEmployees.map((emp) => (
                <div
                  key={emp.id}
                  className={`rounded-2xl border p-5 transition-all ${
                    emp.is_active
                      ? 'border-slate-200 dark:border-white/10 bg-white/85 dark:bg-zinc-900/60 hover:bg-slate-50 dark:hover:bg-white/5'
                      : 'border-slate-200/80 dark:border-white/5 bg-slate-50/80 dark:bg-white/[0.02] opacity-70'
                  }`}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                        {emp.name}
                      </h3>
                      <div className="flex items-center gap-2 text-slate-500 dark:text-white/50 text-sm mt-1">
                        <Briefcase className="w-3.5 h-3.5" />
                        {emp.job_title || 'بدون مسمى'}
                      </div>
                    </div>
                    <span
                      className={`px-2.5 py-1 rounded-lg text-xs font-bold ${
                        emp.is_active
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-rose-500/20 text-rose-400'
                      }`}
                    >
                      {emp.is_active ? 'نشط' : 'غير نشط'}
                    </span>
                  </div>

                  <div className="space-y-2 text-sm text-slate-600 dark:text-white/50 mb-4">
                    {emp.phone && (
                      <div className="flex items-center gap-2">
                        <Phone className="w-3.5 h-3.5" />
                        {emp.phone}
                      </div>
                    )}
                    {emp.email && (
                      <div className="flex items-center gap-2">
                        <Mail className="w-3.5 h-3.5" />
                        {emp.email}
                      </div>
                    )}
                    {emp.daily_rate && (
                      <div className="flex items-center gap-2">
                        <DollarSign className="w-3.5 h-3.5" />
                        {Number(emp.daily_rate).toLocaleString()} ريال/يوم
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setEditEmployee(emp)
                        setShowModal(true)
                      }}
                      className="flex-1 py-2 rounded-xl bg-slate-100 dark:bg-white/5 text-slate-700 dark:text-white/60 text-sm font-medium hover:bg-slate-200 dark:hover:bg-white/10 transition-colors flex items-center justify-center gap-1"
                      aria-label={`تعديل بيانات ${emp.name}`}
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                      تعديل
                    </button>
                    <button
                      onClick={() => handleDelete(emp.id)}
                      className="py-2 px-3 rounded-xl bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 transition-colors"
                      aria-label={`حذف الموظف ${emp.name}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}

      {/* Modal */}
      {showModal && (
        <EmployeeForm
          employee={editEmployee}
          farmId={selectedFarmId}
          onClose={() => setShowModal(false)}
          onSave={() => {
            setShowModal(false)
            fetchEmployees()
          }}
        />
      )}
    </div>
  )
}
