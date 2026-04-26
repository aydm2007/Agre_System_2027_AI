import { useState, useEffect, useRef } from 'react'
import PropTypes from 'prop-types'
import { Employees } from '../../api/client'
import { useToast } from '../ToastProvider'

/**
 * [AGRI-GUARDIAN] Employee Multi-Select Component
 * Replaces free-text TagInput to link Operations with HR/Payroll.
 */
export const EmployeeSelect = ({
  selectedIds = [],
  onChange,
  farmId,
  error,
  dataTestId,
  disabled = false,
}) => {
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const dropdownRef = useRef(null)
  const addToast = useToast()

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Fetch employees when farmId changes
  useEffect(() => {
    const fetchEmployees = async () => {
      if (!farmId) {
        setEmployees([])
        return
      }
      setLoading(true)
      try {
        const { data } = await Employees.list({ farm: farmId, is_active: true })
        setEmployees(data.results || data || [])
      } catch (err) {
        console.error('Failed to fetch employees', err)
        addToast('فشل تحميل قائمة الموظفين', 'error')
      } finally {
        setLoading(false)
      }
    }
    fetchEmployees()
  }, [farmId, addToast])

  const toggleSelection = (empId) => {
    const numericId = Number(empId)
    const newSelection = selectedIds.includes(numericId)
      ? selectedIds.filter((id) => id !== numericId)
      : [...selectedIds, numericId]
    onChange(newSelection)
  }

  const filteredEmployees = employees.filter(
    (emp) =>
      emp.name.toLowerCase().includes(search.toLowerCase()) ||
      (emp.job_title && emp.job_title.toLowerCase().includes(search.toLowerCase())),
  )

  // Map selected IDs to names for display
  const selectedNames = selectedIds
    .map((id) => employees.find((e) => e.id === Number(id))?.name)
    .filter(Boolean)

  return (
    <div className="relative w-full" ref={dropdownRef} data-testid={dataTestId}>
      <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
        فريق التنفيذ (الموظفين)
      </label>

      {/* Display / Search Box */}
      <div
        className={`w-full p-2.5 rounded-lg border ${
          error ? 'border-red-500 bg-red-50' : 'border-gray-300 dark:border-slate-600'
        } ${disabled ? 'bg-gray-100 dark:bg-slate-800 cursor-not-allowed opacity-70' : 'bg-white dark:bg-slate-700 cursor-text'} min-h-[42px] flex flex-wrap gap-2 items-center`}
        onClick={() => {
          if (!disabled) setIsOpen(true)
        }}
      >
        {selectedNames.length > 0 ? (
          selectedNames.map((name, idx) => (
            <span
              key={idx}
              className="bg-primary/10 text-primary text-xs px-2 py-1 rounded-full flex items-center gap-1"
            >
              {name}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  // Find ID by name (reverse lookup - safe enough for UI)
                  const emp = employees.find((e) => e.name === name)
                  if (emp) toggleSelection(emp.id)
                }}
                className="hover:bg-primary/20 rounded-full p-0.5"
              >
                ×
              </button>
            </span>
          ))
        ) : (
          <span className="text-gray-400 text-sm">اختر الموظفين...</span>
        )}

        {/* Inline Search Input */}
        <input
          data-testid="employee-search-input"
          type="text"
          disabled={disabled}
          className="flex-1 bg-transparent outline-none min-w-[80px] text-sm text-gray-900 dark:text-white"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setIsOpen(true)
          }}
          placeholder={selectedIds.length === 0 ? '' : 'بحث...'}
        />
      </div>

      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}

      {/* Dropdown Menu */}
      {!disabled && isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {loading ? (
            <div className="p-3 text-center text-gray-500 text-sm">جاري التحميل...</div>
          ) : filteredEmployees.length === 0 ? (
            <div className="p-3 text-center text-gray-500 text-sm">لا يوجد موظفين مطابقين</div>
          ) : (
            filteredEmployees.map((emp) => (
              <div
                key={emp.id}
                data-testid={`employee-option-${emp.id}`}
                className={`p-2 hover:bg-gray-50 dark:hover:bg-slate-700 cursor-pointer flex items-center justify-between ${
                  selectedIds.includes(emp.id) ? 'bg-primary/5' : ''
                }`}
                onClick={() => toggleSelection(emp.id)}
              >
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {emp.name}
                  </span>
                  <span className="text-xs text-gray-500">
                    {emp.job_title} • {emp.payment_mode === 'SURRA' ? 'نظام صرة' : 'راتب'}
                  </span>
                </div>
                {selectedIds.includes(emp.id) && <span className="text-primary text-sm">✓</span>}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

EmployeeSelect.propTypes = {
  selectedIds: PropTypes.array,
  onChange: PropTypes.func.isRequired,
  farmId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  error: PropTypes.string,
  dataTestId: PropTypes.string,
  disabled: PropTypes.bool,
}
