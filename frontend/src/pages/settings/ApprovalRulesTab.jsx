import { useCallback, useEffect, useState } from 'react'
import { ApprovalRules, CostCenters, Memberships } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { Plus, Edit2, CheckCircle2, XCircle } from 'lucide-react'

// Common Modules and Actions based on backend constants
const MODULE_CHOICES = [
    { value: 'EXPENSE', label: 'المصروفات (Expenses)' },
    { value: 'DAILY_LOG', label: 'السجلات اليومية (Daily Logs)' },
    { value: 'TREASURY', label: 'حركات الخزينة (Treasury)' },
    { value: 'ALL', label: 'جميع الأنظمة (All Modules)' },
]

export default function ApprovalRulesTab({ selectedFarmId, hasFarms }) {
    const { hasPermission, isAdmin, isSuperuser } = useAuth()
    const [rules, setRules] = useState([])
    const [costCenters, setCostCenters] = useState([])
    const [roles, setRoles] = useState([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [message, setMessage] = useState('')

    const [showForm, setShowForm] = useState(false)
    const [editingId, setEditingId] = useState(null)

    const [formData, setFormData] = useState({
        module: 'EXPENSE',
        action: 'create',
        cost_center: '',
        min_amount: '0.00',
        max_amount: '9999999.00',
        required_role: '',
        is_active: true
    })

    const canManageRules = isAdmin || isSuperuser || hasPermission('add_approvalrule') || hasPermission('change_approvalrule')

    const loadData = useCallback(async () => {
        if (!selectedFarmId) return
        setLoading(true)
        setError('')
        try {
            const [rulesRes, ccRes, rolesRes] = await Promise.all([
                ApprovalRules.list({ farm_id: selectedFarmId }),
                CostCenters.list({ farm_id: selectedFarmId }),
                Memberships.roles()
            ])

            setRules(rulesRes.data?.results || rulesRes.data || [])
            setCostCenters(ccRes.data?.results || ccRes.data || [])

            const fetchedRoles = rolesRes.data?.results || rolesRes.data || []
            setRoles(fetchedRoles)

            setFormData(prev => (
                fetchedRoles.length > 0 && !prev.required_role
                    ? { ...prev, required_role: fetchedRoles[0].value }
                    : prev
            ))
        } catch (err) {
            console.error(err)
            setError('تعذر تحميل بيانات قواعد الاعتماد.')
        } finally {
            setLoading(false)
        }
    }, [selectedFarmId])

    useEffect(() => {
        loadData()
    }, [loadData])

    const handleInputChange = (e) => {
        const { name, value, type, checked } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }))
    }

    const resetForm = () => {
        setFormData({
            module: 'EXPENSE',
            action: 'create',
            cost_center: '',
            min_amount: '0.00',
            max_amount: '9999999.00',
            required_role: roles.length > 0 ? roles[0].value : '',
            is_active: true
        })
        setEditingId(null)
        setShowForm(false)
    }

    const handleEdit = (rule) => {
        setEditingId(rule.id)
        setFormData({
            module: rule.module,
            action: rule.action,
            cost_center: rule.cost_center || '', // ID of related cost center
            min_amount: rule.min_amount,
            max_amount: rule.max_amount || '',
            required_role: rule.required_role,
            is_active: rule.is_active
        })
        setShowForm(true)
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!canManageRules) return

        setError('')
        setMessage('')
        try {
            const payload = {
                ...formData,
                farm: selectedFarmId,
                cost_center: formData.cost_center || null // Convert empty string to null for backend
            }

            if (editingId) {
                await ApprovalRules.update(editingId, payload)
                setMessage('تم تحديث قاعدة الاعتماد بنجاح.')
            } else {
                await ApprovalRules.create(payload)
                setMessage('تم إنشاء قاعدة الاعتماد بنجاح.')
            }
            resetForm()
            loadData()
        } catch (err) {
            console.error(err)
            const apiError = err.response?.data?.detail || err.response?.data || 'تعذر حفظ القاعدة. تأكد من صحة البيانات.'
            setError(typeof apiError === 'string' ? apiError : JSON.stringify(apiError))
        }
    }

    const formatMoney = (amount) => {
        if (!amount) return '0.00'
        return Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2 })
    }

    const getRoleLabel = (val) => roles.find((r) => r.value === val)?.label || val
    const getCCName = (val) => costCenters.find((c) => c.id === val)?.name || 'الكل (غير مقيد)'

    if (!hasFarms) {
        return (
            <div className="bg-white dark:bg-slate-800 p-6 rounded shadow text-center text-gray-500 dark:text-slate-400">
                الرجاء تحديد مزرعة لعرض قواعد الاعتماد.
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white dark:bg-slate-800 p-4 rounded shadow">
                <div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white">قواعد الاعتماد (Approval Rules)</h2>
                    <p className="text-sm text-gray-500 dark:text-slate-400">إدارة مسارات المصادقة الديناميكية بحسب المبالغ والوحدات.</p>
                </div>
                {canManageRules && !showForm && (
                    <button
                        onClick={() => setShowForm(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded hover:bg-primary/90 transition"
                    >
                        <Plus className="w-4 h-4" />
                        إضافة قاعدة
                    </button>
                )}
            </div>

            {message && (
                <div className="p-4 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded flex items-center gap-2 border border-green-200 dark:border-green-800">
                    <CheckCircle2 className="w-5 h-5" />
                    {message}
                </div>
            )}
            {error && (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded flex items-center gap-2 border border-red-200 dark:border-red-800">
                    <XCircle className="w-5 h-5 shrink-0" />
                    {error}
                </div>
            )}

            {showForm && (
                <form onSubmit={handleSubmit} className="bg-gray-50 dark:bg-slate-700/50 p-6 rounded border border-gray-200 dark:border-slate-600 space-y-4">
                    <h3 className="font-semibold text-gray-800 dark:text-white mb-4">
                        {editingId ? 'تعديل قاعدة' : 'إنشاء قاعدة اعتماد'}
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">النظام (Module) *</label>
                            <select
                                name="module"
                                required
                                value={formData.module}
                                onChange={handleInputChange}
                                className="w-full border dark:border-slate-600 rounded p-2 text-sm bg-white dark:bg-slate-800 dark:text-white"
                            >
                                {MODULE_CHOICES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">الرتبة المطلوبة (Role) *</label>
                            <select
                                name="required_role"
                                required
                                value={formData.required_role}
                                onChange={handleInputChange}
                                className="w-full border dark:border-slate-600 rounded p-2 text-sm bg-white dark:bg-slate-800 dark:text-white"
                            >
                                {roles.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">مركز التكلفة (اختياري)</label>
                            <select
                                name="cost_center"
                                value={formData.cost_center}
                                onChange={handleInputChange}
                                className="w-full border dark:border-slate-600 rounded p-2 text-sm bg-white dark:bg-slate-800 dark:text-white"
                            >
                                <option value="">الكل (غير مقيد)</option>
                                {costCenters.map(cc => <option key={cc.id} value={cc.id}>{cc.name}</option>)}
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">الحد الأدنى (Min Amount) *</label>
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                name="min_amount"
                                required
                                value={formData.min_amount}
                                onChange={handleInputChange}
                                className="w-full border dark:border-slate-600 rounded p-2 text-sm bg-white dark:bg-slate-800 dark:text-white text-left ltr"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">الحد الأقصى (Max Amount)</label>
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                name="max_amount"
                                value={formData.max_amount}
                                onChange={handleInputChange}
                                className="w-full border dark:border-slate-600 rounded p-2 text-sm bg-white dark:bg-slate-800 dark:text-white text-left ltr"
                            />
                        </div>

                        <div className="flex items-center gap-2 mt-6">
                            <input
                                type="checkbox"
                                id="is_active"
                                name="is_active"
                                checked={formData.is_active}
                                onChange={handleInputChange}
                                className="rounded border-gray-300 dark:border-slate-600"
                            />
                            <label htmlFor="is_active" className="text-sm text-gray-700 dark:text-slate-300">
                                القاعدة فعّالة
                            </label>
                        </div>
                    </div>
                    <div className="flex justify-end gap-3 pt-4">
                        <button
                            type="button"
                            onClick={resetForm}
                            className="px-4 py-2 text-sm bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded hover:bg-gray-50 dark:hover:bg-slate-700 dark:text-white"
                        >
                            إلغاء
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 text-sm bg-primary text-white rounded hover:bg-primary/90 shadow-sm"
                        >
                            حفظ التغييرات
                        </button>
                    </div>
                </form>
            )}

            <div className="bg-white dark:bg-slate-800 rounded shadow overflow-hidden border border-gray-100 dark:border-slate-700">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-right">
                        <thead className="bg-gray-50 dark:bg-slate-700/50 text-gray-600 dark:text-slate-300 border-b dark:border-slate-700">
                            <tr>
                                <th className="p-4 font-medium">الوحدة</th>
                                <th className="p-4 font-medium">من - إلى (Amount)</th>
                                <th className="p-4 font-medium">الرتبة المعتمِدة</th>
                                <th className="p-4 font-medium">مركز التكلفة</th>
                                <th className="p-4 font-medium text-center">الحالة</th>
                                <th className="p-4 font-medium w-24 text-center">تعديل</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-slate-700/50">
                            {loading && rules.length === 0 ? (
                                <tr>
                                    <td colSpan="6" className="p-8 text-center text-gray-500 dark:text-slate-400">جاري التحميل...</td>
                                </tr>
                            ) : rules.length === 0 ? (
                                <tr>
                                    <td colSpan="6" className="p-8 text-center text-gray-500 dark:text-slate-400">لا توجد قواعد اعتماد مسجلة.</td>
                                </tr>
                            ) : (
                                rules.map((r) => (
                                    <tr key={r.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/30 transition">
                                        <td className="p-4 font-medium text-gray-900 dark:text-white">{r.module}</td>
                                        <td className="p-4 font-mono text-xs">
                                            {formatMoney(r.min_amount)} ↔ {r.max_amount ? formatMoney(r.max_amount) : '∞'}
                                        </td>
                                        <td className="p-4 text-primary dark:text-primary/80 font-semibold">{getRoleLabel(r.required_role)}</td>
                                        <td className="p-4 text-gray-500 dark:text-slate-400">
                                            {r.cost_center ? (
                                                <span className="bg-gray-100 dark:bg-slate-700 px-2 py-1 rounded text-xs">{getCCName(r.cost_center)}</span>
                                            ) : 'الكل'}
                                        </td>
                                        <td className="p-4 text-center">
                                            {r.is_active ? (
                                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">نشط</span>
                                            ) : (
                                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">متوقف</span>
                                            )}
                                        </td>
                                        <td className="p-4 text-center">
                                            {canManageRules && (
                                                <button
                                                    onClick={() => handleEdit(r)}
                                                    className="p-1.5 text-gray-500 hover:text-primary dark:text-slate-400 dark:hover:text-primary rounded transition hover:bg-gray-100 dark:hover:bg-slate-700"
                                                >
                                                    <Edit2 className="w-4 h-4" />
                                                </button>
                                            )}
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
