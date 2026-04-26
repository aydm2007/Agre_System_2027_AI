import { useCallback, useEffect, useState } from 'react'
import { RoleDelegations, Memberships } from '../../api/client'
import FeedbackRegion from '../../components/FeedbackRegion'
import useFeedback from '../../hooks/useFeedback'
import { Trash2, Plus, Shield, User, Info, Save } from 'lucide-react'
import Modal from '../../components/Modal'

const TEXT = {
    title: 'منشئ الفرق وتفويض الصلاحيات',
    subtitle: 'إدارة تفويض المهام والأدوار بين أعضاء الفريق بشكل مؤقت ووفق الجدول الزمني.',
    addDelegation: 'إضافة تفويض جديد',
    delegationList: 'قائمة التفويضات النشطة',
    principal: 'المفوِّض الأصلي (الأصيل)',
    delegate: 'المفوَّض إليه (الوكيل)',
    role: 'الدور المفوَّض',
    reason: 'سبب التفويض',
    startsAt: 'تاريخ البدء',
    endsAt: 'تاريخ الانتهاء',
    status: 'الحالة',
    actions: 'الإجراءات',
    noFarms: 'يرجى اختيار مزرعة أولاً للوصول إلى إدارة الفريق.',
    noDelegations: 'لا توجد تفويضات حالياً لهذه المزرعة.',
    active: 'نشط',
    expired: 'منتهي',
    pending: 'قيد الانتظار',
    effective: 'فعّال حالياً',
    saveSuccess: 'تم حفظ التفويض بنجاح',
    deleteSuccess: 'تم حذف التفويض بنجاح',
    confirmDelete: 'هل أنت متأكد من حذف هذا التفويض؟ سيتم سحب الصلاحيات فوراً.',
    errorLoad: 'فشل تحميل بيانات الفريق',
    errorSave: 'فشل حفظ التفويض. يرجى التأكد من أن المفوِّض لديه الدور المطلوب.',
    errorDelete: 'فشل حذف التفويض',
    notePlaceholder: 'اكتب سبب التفويض هنا (مثال: إجازة سنوية، مهمة عمل خارجية...)',
}

const SOVEREIGN_ROLES = [
    "المدير المالي لقطاع المزارع", 
    "رئيس الحسابات", 
    "مدير النظام", 
    "محاسب القطاع", 
    "مراجع القطاع",
    "رئيس حسابات القطاع"
]

const isSovereign = (role) => SOVEREIGN_ROLES.includes(role)

export default function TeamBuilderTab({ selectedFarmId }) {
    const [delegations, setDelegations] = useState([])
    const [members, setMembers] = useState([])
    const [roles, setRoles] = useState([])
    const [, setLoading] = useState(false)
    const [modalOpen, setModalOpen] = useState(false)
    
    // XP-2428-PAGE Security State
    const [page, setPage] = useState(1)
    const [total, setTotal] = useState(0)
    const PAGE_SIZE = 10

    const { message, error, showMessage, showError } = useFeedback()

    const [formData, setFormData] = useState({
        principal_user: '',
        delegate_user: '',
        role: '',
        reason: '',
        starts_at: new Date().toISOString().split('T')[0],
        ends_at: '',
        is_active: true
    })

    const loadData = useCallback(async () => {
        if (!selectedFarmId) return
        setLoading(true)
        try {
            const [delRes, memRes, roleRes] = await Promise.all([
                RoleDelegations.list({ farm: selectedFarmId, page }),
                Memberships.list({ farm: selectedFarmId }),
                Memberships.roles()
            ])
            
            setDelegations(delRes.data.results || [])
            setTotal(delRes.data.count || 0)
            setMembers(memRes.data.results || [])
            setRoles(roleRes.data.results || [])
        } catch (err) {
            console.error(err)
            showError(TEXT.errorLoad)
        } finally {
            setLoading(false)
        }
    }, [selectedFarmId, showError])

    useEffect(() => {
        loadData()
    }, [loadData])

    const handleOpenAdd = () => {
        setFormData({
            principal_user: '',
            delegate_user: '',
            role: '',
            reason: '',
            starts_at: new Date().toISOString().split('T')[0],
            ends_at: '',
            is_active: true
        })
        setModalOpen(true)
    }

    const handleSave = async (e) => {
        e.preventDefault()
        try {
            await RoleDelegations.create({
                ...formData,
                farm: selectedFarmId
            })
            showMessage(TEXT.saveSuccess)
            setModalOpen(false)
            loadData()
        } catch (err) {
            console.error(err)
            showError(TEXT.errorSave)
        }
    }

    const handleDelete = async (id) => {
        if (!window.confirm(TEXT.confirmDelete)) return
        try {
            await RoleDelegations.remove(id)
            showMessage(TEXT.deleteSuccess)
            loadData()
        } catch (err) {
            console.error(err)
            showError(TEXT.errorDelete)
        }
    }

    if (!selectedFarmId) {
        return (
            <div className="p-8 text-center bg-gray-50 dark:bg-slate-800 rounded-xl border-2 border-dashed border-gray-200 dark:border-slate-700">
                <Info className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600 dark:text-slate-400 font-medium">{TEXT.noFarms}</p>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <FeedbackRegion message={message} error={error} />
            
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                        <Shield className="w-6 h-6 text-primary" />
                        {TEXT.title}
                    </h2>
                    <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{TEXT.subtitle}</p>
                </div>
                <button
                    onClick={handleOpenAdd}
                    className="inline-flex items-center gap-2 px-4 py-2.5 bg-primary text-white rounded-lg hover:bg-primary-dark transition shadow-md active:scale-95"
                >
                    <Plus className="w-5 h-5" />
                    {TEXT.addDelegation}
                </button>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-gray-100 dark:border-slate-800 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-right border-collapse">
                        <thead>
                            <tr className="bg-gray-50 dark:bg-slate-800/50 text-gray-600 dark:text-slate-400 text-xs font-bold uppercase tracking-wider">
                                <th className="px-6 py-4">{TEXT.role}</th>
                                <th className="px-6 py-4">{TEXT.principal}</th>
                                <th className="px-6 py-4">{TEXT.delegate}</th>
                                <th className="px-6 py-4">{TEXT.status}</th>
                                <th className="px-6 py-4">{TEXT.startsAt}</th>
                                <th className="px-6 py-4">{TEXT.endsAt}</th>
                                <th className="px-6 py-4 text-center">{TEXT.actions}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-slate-800">
                            {delegations.length === 0 ? (
                                <tr>
                                    <td colSpan="7" className="px-6 py-12 text-center text-gray-500 dark:text-slate-500 italic">
                                        {TEXT.noDelegations}
                                    </td>
                                </tr>
                            ) : (
                                delegations.map(del => (
                                    <tr key={del.id} className="hover:bg-gray-50 dark:hover:bg-slate-800/30 transition-colors group">
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${
                                                    isSovereign(del.role) 
                                                    ? 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-100 dark:border-amber-800 ring-2 ring-amber-400/20' 
                                                    : 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-100 dark:border-blue-800'
                                                }`}>
                                                    {del.role}
                                                </span>
                                                {isSovereign(del.role) && (
                                                    <Shield className="w-3.5 h-3.5 text-amber-500" title="دور سيادي (عالي الحساسية)" />
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                <div className="w-7 h-7 rounded-lg bg-gray-100 dark:bg-slate-800 flex items-center justify-center">
                                                    <User className="w-4 h-4 text-gray-500" />
                                                </div>
                                                <div className="text-sm font-semibold text-gray-900 dark:text-white">{del.principal_username}</div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
                                                    <User className="w-4 h-4 text-primary" />
                                                </div>
                                                <div className="text-sm font-semibold text-gray-900 dark:text-white">{del.delegate_username}</div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            {del.is_currently_effective ? (
                                                <span className="flex items-center gap-1.5 text-xs font-bold text-green-600 dark:text-green-400">
                                                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                                    {TEXT.effective}
                                                </span>
                                            ) : (
                                                <span className="text-xs font-medium text-gray-400 dark:text-slate-500">
                                                    {del.is_active ? TEXT.pending : TEXT.expired}
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-sm text-gray-500 dark:text-slate-400 font-mono italic">{del.starts_at}</td>
                                        <td className="px-6 py-4 text-sm text-gray-500 dark:text-slate-400 font-mono italic">{del.ends_at || '---'}</td>
                                        <td className="px-6 py-4 text-center">
                                            <button
                                                onClick={() => handleDelete(del.id)}
                                                className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all transform hover:scale-110 opacity-0 group-hover:opacity-100"
                                                title="سحب التفويض فوراً"
                                            >
                                                <Trash2 className="w-5 h-5" />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* XP-2428-PAGE Pagination Controls */}
                {total > PAGE_SIZE && (
                    <div className="bg-gray-50 dark:bg-slate-800/20 px-6 py-3 border-t border-gray-100 dark:border-slate-800 flex items-center justify-between">
                        <div className="text-sm text-gray-500 dark:text-slate-400">
                            عرض {delegations.length} من {total} تفويض
                        </div>
                        <div className="flex gap-2">
                            <button
                                disabled={page === 1}
                                onClick={() => setPage(p => p - 1)}
                                className="px-3 py-1 text-xs font-bold border border-gray-200 dark:border-slate-700 rounded-md hover:bg-white dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                            >
                                السابق
                            </button>
                            <span className="px-3 py-1 text-xs font-bold bg-primary/10 text-primary rounded-md">
                                {page}
                            </span>
                            <button
                                disabled={page * PAGE_SIZE >= total}
                                onClick={() => setPage(p => p + 1)}
                                className="px-3 py-1 text-xs font-bold border border-gray-200 dark:border-slate-700 rounded-md hover:bg-white dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                            >
                                التالي
                            </button>
                        </div>
                    </div>
                )}
            </div>

            <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={TEXT.addDelegation}>
                <form onSubmit={handleSave} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">{TEXT.role} *</label>
                            <select
                                required
                                value={formData.role}
                                onChange={e => setFormData({ ...formData, role: e.target.value })}
                                className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white"
                            >
                                <option value="">-- اختر الدور --</option>
                                {roles.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">{TEXT.principal} *</label>
                            <select
                                required
                                value={formData.principal_user}
                                onChange={e => setFormData({ ...formData, principal_user: e.target.value })}
                                className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white"
                            >
                                <option value="">-- من هو صاحب الصلاحية؟ --</option>
                                {members.filter(m => m.role === formData.role).map(m => (
                                    <option key={m.user_id} value={m.user_id}>{m.username} ({m.role})</option>
                                ))}
                            </select>
                            {formData.role && members.filter(m => m.role === formData.role).length === 0 && (
                                <p className="text-[10px] text-orange-500 mt-1">لا يوجد مستخدم يحمل هذا الدور حالياً.</p>
                            )}
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">{TEXT.delegate} *</label>
                        <select
                            required
                            value={formData.delegate_user}
                            onChange={e => setFormData({ ...formData, delegate_user: e.target.value })}
                            className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white"
                        >
                            <option value="">-- من سينوب عنه؟ --</option>
                            {members.map(m => (
                                <option key={m.user_id} value={m.user_id}>{m.username} - {m.role}</option>
                            ))}
                        </select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">{TEXT.startsAt} *</label>
                            <input
                                required
                                type="date"
                                value={formData.starts_at}
                                onChange={e => setFormData({ ...formData, starts_at: e.target.value })}
                                className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white font-mono"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">{TEXT.endsAt}</label>
                            <input
                                type="date"
                                value={formData.ends_at}
                                onChange={e => setFormData({ ...formData, ends_at: e.target.value })}
                                className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white font-mono"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">{TEXT.reason} *</label>
                        <textarea
                            required
                            rows="2"
                            value={formData.reason}
                            onChange={e => setFormData({ ...formData, reason: e.target.value })}
                            placeholder={TEXT.notePlaceholder}
                            className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white shadow-sm"
                        />
                    </div>

                    <div className="flex gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
                        <button
                            type="button"
                            onClick={() => setModalOpen(false)}
                            className="flex-1 px-4 py-2 border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition"
                        >
                            إلغاء
                        </button>
                        <button
                            type="submit"
                            className="flex-1 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition flex justify-center items-center gap-2"
                        >
                            <Save className="w-4 h-4" />
                            حفظ التفويض
                        </button>
                    </div>
                </form>
            </Modal>
        </div>
    )
}
