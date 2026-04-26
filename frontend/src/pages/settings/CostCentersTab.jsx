import { useCallback, useEffect, useState } from 'react'
import { CostCenters } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { Plus, Edit2, CheckCircle2, XCircle } from 'lucide-react'

export default function CostCentersTab({ selectedFarmId, hasFarms }) {
    const { hasPermission, isAdmin, isSuperuser } = useAuth()
    const [costCenters, setCostCenters] = useState([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [message, setMessage] = useState('')

    const [showForm, setShowForm] = useState(false)
    const [editingId, setEditingId] = useState(null)

    const [formData, setFormData] = useState({
        code: '',
        name: '',
        description: '',
        is_active: true
    })

    // Basic check for permissions. Adjust based on custom strings if needed.
    const canManageCostCenters = isAdmin || isSuperuser || hasPermission('add_costcenter') || hasPermission('change_costcenter')

    const loadCostCenters = useCallback(async () => {
        if (!selectedFarmId) return
        setLoading(true)
        setError('')
        try {
            const response = await CostCenters.list({ farm_id: selectedFarmId })
            setCostCenters(response.data?.results || response.data || [])
        } catch (err) {
            console.error(err)
            setError('تعذر تحميل مراكز التكلفة.')
        } finally {
            setLoading(false)
        }
    }, [selectedFarmId])

    useEffect(() => {
        loadCostCenters()
    }, [loadCostCenters])

    const handleInputChange = (e) => {
        const { name, value, type, checked } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }))
    }

    const resetForm = () => {
        setFormData({ code: '', name: '', description: '', is_active: true })
        setEditingId(null)
        setShowForm(false)
    }

    const handleEdit = (cc) => {
        setEditingId(cc.id)
        setFormData({
            code: cc.code,
            name: cc.name,
            description: cc.description || '',
            is_active: cc.is_active
        })
        setShowForm(true)
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!canManageCostCenters) return

        setError('')
        setMessage('')
        try {
            const payload = { ...formData, farm: selectedFarmId }

            if (editingId) {
                await CostCenters.update(editingId, payload)
                setMessage('تم تحديث مركز التكلفة بنجاح.')
            } else {
                await CostCenters.create(payload)
                setMessage('تم إنشاء مركز التكلفة بنجاح.')
            }
            resetForm()
            loadCostCenters()
        } catch (err) {
            console.error(err)
            // Display specific API validation error if available
            const apiError = err.response?.data?.code || err.response?.data?.name || 'تعذر حفظ مركز التكلفة. تأكد من صحة البيانات وعدم تكرار الرمز.'
            setError(typeof apiError === 'string' ? apiError : JSON.stringify(apiError))
        }
    }

    if (!hasFarms) {
        return (
            <div className="bg-white dark:bg-slate-800 p-6 rounded shadow text-center text-gray-500 dark:text-slate-400">
                الرجاء تحديد مزرعة لعرض مراكز التكلفة.
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Header and Add Button */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white dark:bg-slate-800 p-4 rounded shadow">
                <div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white">مراكز التكلفة (Cost Centers)</h2>
                    <p className="text-sm text-gray-500 dark:text-slate-400">إدارة الأبعاد التحليلية للعمليات ومسارات الاعتماد الديناميكي.</p>
                </div>
                {canManageCostCenters && !showForm && (
                    <button
                        onClick={() => setShowForm(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded hover:bg-primary/90 transition"
                    >
                        <Plus className="w-4 h-4" />
                        إضافة مركز تكلفة
                    </button>
                )}
            </div>

            {/* Alerts */}
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

            {/* Form Area */}
            {showForm && (
                <form onSubmit={handleSubmit} className="bg-gray-50 dark:bg-slate-700/50 p-6 rounded border border-gray-200 dark:border-slate-600 space-y-4">
                    <h3 className="font-semibold text-gray-800 dark:text-white mb-4">
                        {editingId ? 'تعديل مركز تكلفة' : 'إنشاء مركز تكلفة جديد'}
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">رمز المركز (Code) *</label>
                            <input
                                type="text"
                                name="code"
                                required
                                value={formData.code}
                                onChange={handleInputChange}
                                className="w-full border dark:border-slate-600 rounded p-2 text-sm bg-white dark:bg-slate-800 dark:text-white"
                                placeholder="مثال: CC-EXP-01"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">الاسم (Name) *</label>
                            <input
                                type="text"
                                name="name"
                                required
                                value={formData.name}
                                onChange={handleInputChange}
                                className="w-full border dark:border-slate-600 rounded p-2 text-sm bg-white dark:bg-slate-800 dark:text-white"
                                placeholder="مثال: قطاع التصدير الطماطم"
                            />
                        </div>
                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">الوصف (Description)</label>
                            <textarea
                                name="description"
                                rows="2"
                                value={formData.description}
                                onChange={handleInputChange}
                                className="w-full border dark:border-slate-600 rounded p-2 text-sm bg-white dark:bg-slate-800 dark:text-white"
                            />
                        </div>
                        <div className="md:col-span-2 flex items-center gap-2 mt-2">
                            <input
                                type="checkbox"
                                id="is_active"
                                name="is_active"
                                checked={formData.is_active}
                                onChange={handleInputChange}
                                className="rounded border-gray-300 dark:border-slate-600"
                            />
                            <label htmlFor="is_active" className="text-sm text-gray-700 dark:text-slate-300">
                                المركز نشط ومتاح للاستخدام
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
                            فظ التغييرات
                        </button>
                    </div>
                </form>
            )}

            {/* Data Table */}
            <div className="bg-white dark:bg-slate-800 rounded shadow overflow-hidden border border-gray-100 dark:border-slate-700">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-right">
                        <thead className="bg-gray-50 dark:bg-slate-700/50 text-gray-600 dark:text-slate-300 border-b dark:border-slate-700">
                            <tr>
                                <th className="p-4 font-medium">الرمز (Code)</th>
                                <th className="p-4 font-medium">الاسم</th>
                                <th className="p-4 font-medium">الوصف</th>
                                <th className="p-4 font-medium text-center">الحالة</th>
                                <th className="p-4 font-medium w-32 text-center">الإجراءات</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-slate-700/50">
                            {loading && costCenters.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="p-8 text-center text-gray-500 dark:text-slate-400">
                                        جاري التحميل...
                                    </td>
                                </tr>
                            ) : costCenters.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="p-8 text-center text-gray-500 dark:text-slate-400">
                                        لا توجد مراكز تكلفة مسجلة في هذه المزرعة.
                                    </td>
                                </tr>
                            ) : (
                                costCenters.map((cc) => (
                                    <tr key={cc.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/30 transition">
                                        <td className="p-4">
                                            <span className="bg-gray-100 dark:bg-slate-700 text-gray-800 dark:text-slate-200 px-2 py-1 rounded font-mono text-xs">
                                                {cc.code}
                                            </span>
                                        </td>
                                        <td className="p-4 font-medium text-gray-900 dark:text-white">{cc.name}</td>
                                        <td className="p-4 text-gray-500 dark:text-slate-400 truncate max-w-[200px]" title={cc.description}>
                                            {cc.description || '-'}
                                        </td>
                                        <td className="p-4 text-center">
                                            {cc.is_active ? (
                                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                                                    نشط
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
                                                    غير نشط
                                                </span>
                                            )}
                                        </td>
                                        <td className="p-4 text-center">
                                            {canManageCostCenters && (
                                                <button
                                                    onClick={() => handleEdit(cc)}
                                                    className="p-1.5 text-gray-500 hover:text-primary dark:text-slate-400 dark:hover:text-primary rounded transition hover:bg-gray-100 dark:hover:bg-slate-700"
                                                    title="تعديل"
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
