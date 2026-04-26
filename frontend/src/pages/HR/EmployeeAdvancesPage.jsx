import { useState, useEffect, useCallback } from 'react'
import { Plus, Check, DollarSign, Clock } from 'lucide-react'
import { toDecimal } from '../../utils/decimal'

const API = '/api/v1'

export default function EmployeeAdvancesPage() {
  const [advances, setAdvances] = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ employee_id: '', amount: '', date: '', reason: '' })
  const farmId = localStorage.getItem('farm_id') || '1'

  const fetchAdvances = useCallback(async () => {
    try {
      const res = await fetch(`${API}/advances/?farm=${farmId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('access')}` },
      })
      if (!res.ok) throw new Error('فشل تحميل السلفيات')
      setAdvances(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [farmId])

  const fetchEmployees = useCallback(async () => {
    try {
      const res = await fetch(`${API}/employees/?farm=${farmId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('access')}` },
      })
      if (res.ok) {
        const data = await res.json()
        setEmployees(data.results || data || [])
      }
    } catch (e) {
      console.warn('Could not load employees:', e)
    }
  }, [farmId])

  useEffect(() => {
    fetchAdvances()
    fetchEmployees()
  }, [fetchAdvances, fetchEmployees])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      const res = await fetch(`${API}/advances/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access')}`,
        },
        body: JSON.stringify({ ...form, farm_id: farmId }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'فشل الإنشاء')
      }
      setForm({ employee_id: '', amount: '', date: '', reason: '' })
      setShowForm(false)
      fetchAdvances()
    } catch (e) {
      setError(e.message)
    }
  }

  const handleApprove = async (id) => {
    try {
      const res = await fetch(`${API}/advances/${id}/approve/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('access')}` },
      })
      if (!res.ok) throw new Error('فشل الاعتماد')
      fetchAdvances()
    } catch (e) {
      setError(e.message)
    }
  }

  const statusColors = {
    PENDING: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    APPROVED: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    DEDUCTED: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    CANCELLED: 'bg-red-500/20 text-red-400 border-red-500/30',
  }
  const statusLabels = {
    PENDING: 'معلقة',
    APPROVED: 'معتمدة',
    DEDUCTED: 'مخصومة',
    CANCELLED: 'ملغاة',
  }

  const totalPending = advances
    .filter((a) => a.status === 'PENDING')
    .reduce((s, a) => s + toDecimal(a.amount, 2), 0)
  const totalApproved = advances
    .filter((a) => a.status === 'APPROVED')
    .reduce((s, a) => s + toDecimal(a.amount, 2), 0)
  const totalDeducted = advances
    .filter((a) => a.status === 'DEDUCTED')
    .reduce((s, a) => s + toDecimal(a.amount, 2), 0)

  if (loading)
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">جاري التحميل...</div>
    )

  return (
    <div data-testid="advances-page" className="space-y-6 p-4 md:p-6" dir="rtl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">سلفيات العمال</h1>
          <p className="text-sm text-gray-400 mt-1">إدارة السلف والخصومات التلقائية من المسير</p>
        </div>
        <button
          data-testid="add-advance-btn"
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" /> سلفية جديدة
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Form */}
      {showForm && (
        <form
          data-testid="advance-form"
          onSubmit={handleCreate}
          className="bg-gray-800/60 border border-gray-700/40 rounded-xl p-5 space-y-4"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* [Gap #8] Employee Dropdown instead of raw ID input */}
            <div>
              <label className="block text-sm text-gray-400 mb-1">الموظف</label>
              <select
                data-testid="employee-select"
                value={form.employee_id}
                onChange={(e) => setForm((f) => ({ ...f, employee_id: e.target.value }))}
                required
                className="w-full px-3 py-2 bg-gray-900/60 border border-gray-700 rounded-lg text-white appearance-none"
              >
                <option value="">اختر الموظف...</option>
                {employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.first_name} {emp.last_name} — {emp.employee_id}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">المبلغ (ر.ي)</label>
              <input
                data-testid="amount-input"
                type="number"
                step="0.01"
                min="1"
                value={form.amount}
                onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                required
                className="w-full px-3 py-2 bg-gray-900/60 border border-gray-700 rounded-lg text-white"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">التاريخ</label>
              <input
                data-testid="date-input"
                type="date"
                value={form.date}
                onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                required
                className="w-full px-3 py-2 bg-gray-900/60 border border-gray-700 rounded-lg text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">السبب</label>
              <input
                data-testid="reason-input"
                type="text"
                value={form.reason}
                onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
                className="w-full px-3 py-2 bg-gray-900/60 border border-gray-700 rounded-lg text-white"
                placeholder="سلفة شخصية..."
              />
            </div>
          </div>
          <div className="flex gap-3">
            <button
              type="submit"
              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors"
            >
              حفظ
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-5 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              إلغاء
            </button>
          </div>
        </form>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
          <div className="flex items-center gap-2 text-amber-400 mb-2">
            <Clock className="w-4 h-4" />
            <span className="text-sm">معلقة</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {totalPending.toLocaleString('ar-YE')}{' '}
            <span className="text-sm text-gray-400">ر.ي</span>
          </p>
        </div>
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4">
          <div className="flex items-center gap-2 text-emerald-400 mb-2">
            <Check className="w-4 h-4" />
            <span className="text-sm">معتمدة</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {totalApproved.toLocaleString('ar-YE')}{' '}
            <span className="text-sm text-gray-400">ر.ي</span>
          </p>
        </div>
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
          <div className="flex items-center gap-2 text-blue-400 mb-2">
            <DollarSign className="w-4 h-4" />
            <span className="text-sm">مخصومة</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {totalDeducted.toLocaleString('ar-YE')}{' '}
            <span className="text-sm text-gray-400">ر.ي</span>
          </p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-gray-800/40 border border-gray-700/30 rounded-xl overflow-hidden">
        <table data-testid="advances-table" className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700/40 text-gray-400 text-xs">
              <th className="px-4 py-3 text-right">الموظف</th>
              <th className="px-4 py-3 text-right">المبلغ</th>
              <th className="px-4 py-3 text-right">التاريخ</th>
              <th className="px-4 py-3 text-right">السبب</th>
              <th className="px-4 py-3 text-center">الحالة</th>
              <th className="px-4 py-3 text-center">إجراء</th>
            </tr>
          </thead>
          <tbody>
            {advances.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-8 text-gray-500">
                  لا توجد سلفيات
                </td>
              </tr>
            ) : (
              advances.map((a) => (
                <tr
                  key={a.id}
                  className="border-b border-gray-700/30 hover:bg-gray-700/20 transition-colors"
                >
                  <td className="px-4 py-3 text-white font-medium">{a.employee_name}</td>
                  <td className="px-4 py-3 text-white font-mono">
                    {toDecimal(a.amount, 2).toLocaleString('ar-YE')}
                  </td>
                  <td className="px-4 py-3 text-gray-400">{a.date}</td>
                  <td className="px-4 py-3 text-gray-400">{a.reason || '—'}</td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-1 rounded-full text-xs border ${statusColors[a.status] || ''}`}
                    >
                      {statusLabels[a.status] || a.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {a.status === 'PENDING' && (
                      <button
                        data-testid={`approve-btn-${a.id}`}
                        onClick={() => handleApprove(a.id)}
                        className="flex items-center gap-1 mx-auto px-3 py-1 bg-emerald-600/80 hover:bg-emerald-600 text-white rounded-md text-xs transition-colors"
                      >
                        <Check className="w-3 h-3" /> اعتماد
                      </button>
                    )}
                    {a.status === 'DEDUCTED' && a.deducted_in_slip && (
                      <span className="text-xs text-blue-400">قسيمة #{a.deducted_in_slip}</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
