import { useState, useEffect } from 'react'
import { CropRecipes, Crops, Items, CropRecipeMaterials, CropRecipeTasks, Tasks } from '../../api/client'
import { Plus, Edit2, Trash2, ShieldCheck, CheckCircle2, ChevronDown, ChevronRight, Save,  AlertTriangle, Briefcase, Pipette, Leaf, Clock } from 'lucide-react'
import Modal from '../../components/Modal'
import { useAuth } from '../../auth/AuthContext'

export default function CropRecipesTab({ selectedFarmId, hasFarms }) {
    const { isAdmin, isSuperuser, hasPermission } = useAuth()

    const [recipes, setRecipes] = useState([])
    const [crops, setCrops] = useState([])
    const [items, setItems] = useState([])
    const [allTasks, setAllTasks] = useState([])

    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')

    const [expandedRecipeId, setExpandedRecipeId] = useState(null)

    const [modalOpen, setModalOpen] = useState(false)
    const [editingRecipe, setEditingRecipe] = useState(null)
    const [formData, setFormData] = useState({
        crop: '',
        name: '',
        phenological_stage: '',
        expected_labor_hours_per_ha: 0,
        is_active: true,
        notes: ''
    })

    // Material Modal
    const [matModalOpen, setMatModalOpen] = useState(false)
    const [activeRecipeId, setActiveRecipeId] = useState(null)
    const [editingMaterial, setEditingMaterial] = useState(null)
    const [matFormData, setMatFormData] = useState({
        item: '',
        standard_qty_per_ha: 0
    })

    // Task Modal
    const [taskModalOpen, setTaskModalOpen] = useState(false)
    const [editingTask, setEditingTask] = useState(null)
    const [taskFormData, setTaskFormData] = useState({
        task: '',
        name: '',
        days_offset: 0,
        estimated_hours: 0,
        notes: ''
    })

    const canManageRecipes = isAdmin || isSuperuser || hasPermission('add_croprecipe') || hasPermission('change_croprecipe')

    const fetchData = async () => {
        setLoading(true)
        setError('')
        try {
            const [resRec, resCrop, resItems, resTasks] = await Promise.all([
                CropRecipes.list(),
                Crops.list(),
                Items.list(),
                Tasks.list()
            ])
            setRecipes(resRec.data?.results || resRec.data || [])
            setCrops(resCrop.data?.results || resCrop.data || [])
            setItems(resItems.data?.results || resItems.data || [])
            setAllTasks(resTasks.data?.results || resTasks.data || [])
        } catch (err) {
            console.error(err)
            setError('تعذر استرداد بيانات البصمة الزراعية')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (hasFarms) {
            fetchData()
        }
    }, [hasFarms, selectedFarmId])

    /* --- Recipe CRUD --- */
    const handleOpenModal = (recipe = null) => {
        setEditingRecipe(recipe)
        if (recipe) {
            setFormData({
                crop: recipe.crop,
                name: recipe.name,
                phenological_stage: recipe.phenological_stage || '',
                expected_labor_hours_per_ha: recipe.expected_labor_hours_per_ha || 0,
                is_active: recipe.is_active,
                notes: recipe.notes || ''
            })
        } else {
            setFormData({
                crop: crops.length > 0 ? crops[0].id : '',
                name: '',
                phenological_stage: '',
                expected_labor_hours_per_ha: 0,
                is_active: true,
                notes: ''
            })
        }
        setModalOpen(true)
    }

    const handleSaveRecipe = async (e) => {
        e.preventDefault()
        setError('')
        setSuccess('')
        try {
            const payload = { ...formData }
            if (editingRecipe) {
                await CropRecipes.update(editingRecipe.id, payload)
                setSuccess('تم تحديث الوصفة بنجاح')
            } else {
                await CropRecipes.create(payload)
                setSuccess('تم إضافة وصفة جديدة')
            }
            setModalOpen(false)
            fetchData()
        } catch (err) {
            setError(err.response?.data?.detail || 'فشل في الحفظ')
        }
    }

    const handleDeleteRecipe = async (id) => {
        if (!window.confirm('تأكيد الحذف؟ ستفقد كافة مواد هذه الوصفة.')) return
        setError('')
        setSuccess('')
        try {
            await CropRecipes.delete(id)
            setSuccess('تم الحذف بنجاح')
            fetchData()
        } catch (err) {
            setError(err.response?.data?.detail || 'فشل الحذف')
        }
    }

    /* --- Material CRUD --- */
    const handleOpenMatModal = (recipeId, material = null) => {
        setActiveRecipeId(recipeId)
        setEditingMaterial(material)
        if (material) {
            setMatFormData({
                item: material.item,
                standard_qty_per_ha: material.standard_qty_per_ha
            })
        } else {
            setMatFormData({
                item: items.length > 0 ? items[0].id : '',
                standard_qty_per_ha: 0
            })
        }
        setMatModalOpen(true)
    }

    const handleSaveMaterial = async (e) => {
        e.preventDefault()
        setError('')
        setSuccess('')
        try {
            const payload = { ...matFormData, recipe: activeRecipeId }
            if (editingMaterial) {
                await CropRecipeMaterials.update(editingMaterial.id, payload)
                setSuccess('تم تحديث المادة المعيارية')
            } else {
                await CropRecipeMaterials.create(payload)
                setSuccess('تم إضافة مادة معيارية جديدة')
            }
            setMatModalOpen(false)
            fetchData()
        } catch (err) {
            const msg = err.response?.data?.non_field_errors?.[0] || err.response?.data?.detail || 'فشل في الحفظ'
            setError(msg)
        }
    }

    const handleDeleteMaterial = async (id) => {
        if (!window.confirm('تأكيد حذف المادة؟')) return
        setError('')
        setSuccess('')
        try {
            await CropRecipeMaterials.delete(id)
            setSuccess('تم الحذف بنجاح')
            fetchData()
        } catch (err) {
            setError('فشل الحذف')
        }
    }

    /* --- Task CRUD --- */
    const handleOpenTaskModal = (recipeId, recipeTask = null) => {
        setActiveRecipeId(recipeId)
        setEditingTask(recipeTask)
        if (recipeTask) {
            setTaskFormData({
                task: recipeTask.task || '',
                name: recipeTask.name || '',
                days_offset: recipeTask.days_offset || 0,
                estimated_hours: recipeTask.estimated_hours || 0,
                notes: recipeTask.notes || ''
            })
        } else {
            setTaskFormData({
                task: allTasks.length > 0 ? allTasks[0].id : '',
                name: '',
                days_offset: 0,
                estimated_hours: 0,
                notes: ''
            })
        }
        setTaskModalOpen(true)
    }

    const handleSaveTask = async (e) => {
        e.preventDefault()
        setError('')
        setSuccess('')
        try {
            const payload = { ...taskFormData, recipe: activeRecipeId }
            if (editingTask) {
                await CropRecipeTasks.update(editingTask.id, payload)
                setSuccess('تم تحديث المهمة المعيارية')
            } else {
                await CropRecipeTasks.create(payload)
                setSuccess('تم إضافة مهمة معيارية جديدة')
            }
            setTaskModalOpen(false)
            fetchData()
        } catch (err) {
            const msg = err.response?.data?.detail || 'فشل في الحفظ'
            setError(msg)
        }
    }

    const handleDeleteTask = async (id) => {
        if (!window.confirm('تأكيد حذف المهمة؟')) return
        setError('')
        setSuccess('')
        try {
            await CropRecipeTasks.delete(id)
            setSuccess('تم الحذف بنجاح')
            fetchData()
        } catch (err) {
            setError('فشل الحذف')
        }
    }

    const toggleExpand = (id) => {
        setExpandedRecipeId(expandedRecipeId === id ? null : id)
    }

    if (!hasFarms) {
        return (
            <div className="p-8 text-center bg-white dark:bg-slate-800 rounded-xl border border-dashed border-gray-300 dark:border-slate-700">
                <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto mb-3" />
                <p className="text-gray-500 dark:text-slate-400 font-medium">الرجاء اختيار مزرعة أولاً.</p>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center bg-white dark:bg-slate-800 p-4 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
                <div>
                    <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                        <Leaf className="w-5 h-5 text-primary" />
                        البصمة الزراعية (BOM Builder)
                    </h2>
                    <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">تحديد المدخلات المعيارية المسموحة لكل محصول (أسمدة، مبيدات، عمالة) للمعايرة وضبط التكاليف</p>
                </div>
                {canManageRecipes && (
                    <button
                        onClick={() => handleOpenModal()}
                        className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-dark transition shadow-sm"
                    >
                        <Plus className="w-4 h-4" />
                        إضافة وصفة زراعية
                    </button>
                )}
            </div>

            {success && (
                <div className="p-4 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded-lg flex items-center gap-2 border border-green-200 dark:border-green-800">
                    <CheckCircle2 className="w-5 h-5" />
                    {success}
                </div>
            )}
            {error && (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg flex items-center gap-2 border border-red-200 dark:border-red-800">
                    <AlertTriangle className="w-5 h-5" />
                    {error}
                </div>
            )}

            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 overflow-hidden">
                {loading ? (
                    <div className="p-8 text-center text-gray-500">جاري التحميل...</div>
                ) : recipes.length === 0 ? (
                    <div className="p-12 text-center">
                        <ShieldCheck className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
                        <p className="text-gray-500 dark:text-slate-400">لا توجد وصفات جاهزة بعد.</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100 dark:divide-slate-700">
                        {recipes.map((recipe) => (
                            <div key={recipe.id} className="group">
                                <div
                                    className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors"
                                    onClick={() => toggleExpand(recipe.id)}
                                >
                                    <div className="flex items-center gap-4">
                                        <button className="text-gray-400 hover:text-primary transition-colors">
                                            {expandedRecipeId === recipe.id ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                                        </button>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <h3 className="text-base font-bold text-gray-900 dark:text-white">{recipe.name}</h3>
                                                {!recipe.is_active && <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 font-medium">مُعطل</span>}
                                            </div>
                                            <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-slate-400 mt-1">
                                                <span className="flex items-center gap-1"><Leaf className="w-3.5 h-3.5" /> {recipe.crop_name}</span>
                                                {recipe.phenological_stage && <span className="flex items-center gap-1"><Pipette className="w-3.5 h-3.5" /> {recipe.phenological_stage}</span>}
                                                <span className="flex items-center gap-1"><Briefcase className="w-3.5 h-3.5" /> {recipe.expected_labor_hours_per_ha} س/هـ</span>
                                            </div>
                                        </div>
                                    </div>

                                    {canManageRecipes && (
                                        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                                            <button onClick={() => handleOpenModal(recipe)} className="p-1.5 text-gray-400 hover:text-primary hover:bg-primary/10 rounded-md transition-colors" title="تعديل">
                                                <Edit2 className="w-4 h-4" />
                                            </button>
                                            <button onClick={() => handleDeleteRecipe(recipe.id)} className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors" title="حذف">
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    )}
                                </div>

                                {/* Expanded Materials Section */}
                                {expandedRecipeId === recipe.id && (
                                    <div className="px-12 py-4 bg-gray-50/50 dark:bg-slate-800/50 border-t border-gray-100 dark:border-slate-700">
                                        <div className="flex justify-between items-center mb-3">
                                            <h4 className="text-sm font-bold text-gray-700 dark:text-slate-300">المواد المعيارية للوصفة:</h4>
                                            {canManageRecipes && (
                                                <button
                                                    onClick={() => handleOpenMatModal(recipe.id)}
                                                    className="text-xs flex items-center gap-1 text-primary hover:text-primary-dark font-medium"
                                                >
                                                    <Plus className="w-3 h-3" />
                                                    إضافة مادة معيارية
                                                </button>
                                            )}
                                        </div>

                                        {recipe.materials && recipe.materials.length > 0 ? (
                                            <div className="bg-white dark:bg-slate-700/40 rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                                                <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-600">
                                                    <thead className="bg-gray-50 dark:bg-slate-700/80">
                                                        <tr>
                                                            <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 dark:text-slate-300">المادة</th>
                                                            <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 dark:text-slate-300">الكمية / هكتار</th>
                                                            <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 dark:text-slate-300">الوحدة القياسية</th>
                                                            {canManageRecipes && <th className="px-4 py-2 w-16"></th>}
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-gray-100 dark:divide-slate-600/50">
                                                        {recipe.materials.map((mat) => (
                                                            <tr key={mat.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/50">
                                                                <td className="px-4 py-2 text-sm text-gray-900 dark:text-white font-medium">
                                                                    {mat.item_detail?.name || `Item #${mat.item}`}
                                                                </td>
                                                                <td className="px-4 py-2 text-sm text-gray-600 dark:text-slate-300 ltr font-mono">
                                                                    {Number(mat.standard_qty_per_ha).toLocaleString('en-US', { minimumFractionDigits: 1 })}
                                                                </td>
                                                                <td className="px-4 py-2 text-sm text-gray-600 dark:text-slate-300">
                                                                    {mat.item_detail?.uom || '-'}
                                                                </td>
                                                                {canManageRecipes && (
                                                                    <td className="px-4 py-2 text-left">
                                                                        <div className="flex justify-end gap-1">
                                                                            <button onClick={() => handleOpenMatModal(recipe.id, mat)} className="p-1 text-gray-400 hover:text-primary transition-colors">
                                                                                <Edit2 className="w-3.5 h-3.5" />
                                                                            </button>
                                                                            <button onClick={() => handleDeleteMaterial(mat.id)} className="p-1 text-gray-400 hover:text-red-500 transition-colors">
                                                                                <Trash2 className="w-3.5 h-3.5" />
                                                                            </button>
                                                                        </div>
                                                                    </td>
                                                                )}
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        ) : (
                                            <div className="text-center py-6 bg-white dark:bg-slate-700/30 rounded-lg border border-dashed border-gray-300 dark:border-slate-600">
                                                <p className="text-sm text-gray-500 dark:text-slate-400">لا توجد مواد مدرجة في هذا النطاق.</p>
                                            </div>
                                        )}

                                        <div className="flex justify-between items-center mb-3 mt-6">
                                            <h4 className="text-sm font-bold text-gray-700 dark:text-slate-300">المهام القياسية للوصفة:</h4>
                                            {canManageRecipes && (
                                                <button
                                                    onClick={() => handleOpenTaskModal(recipe.id)}
                                                    className="text-xs flex items-center gap-1 text-primary hover:text-primary-dark font-medium"
                                                >
                                                    <Plus className="w-3 h-3" />
                                                    إضافة مهمة قياسية
                                                </button>
                                            )}
                                        </div>

                                        {recipe.tasks && recipe.tasks.length > 0 ? (
                                            <div className="bg-white dark:bg-slate-700/40 rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                                                <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-600">
                                                    <thead className="bg-gray-50 dark:bg-slate-700/80">
                                                        <tr>
                                                            <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 dark:text-slate-300">المهمة / الوصف</th>
                                                            <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 dark:text-slate-300">توقيت البدء (T+)</th>
                                                            <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 dark:text-slate-300">الجهد المقدر</th>
                                                            {canManageRecipes && <th className="px-4 py-2 w-16"></th>}
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-gray-100 dark:divide-slate-600/50">
                                                        {recipe.tasks.map((rt) => (
                                                            <tr key={rt.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/50">
                                                                <td className="px-4 py-2 text-sm">
                                                                    <div className="font-medium text-gray-900 dark:text-white">{rt.name}</div>
                                                                    <div className="text-xs text-gray-500">{rt.task_detail?.name}</div>
                                                                </td>
                                                                <td className="px-4 py-2 text-sm text-gray-600 dark:text-slate-300">
                                                                    <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> اليوم {rt.days_offset}</span>
                                                                </td>
                                                                <td className="px-4 py-2 text-sm text-gray-600 dark:text-slate-300">
                                                                    {rt.estimated_hours} ساعة
                                                                </td>
                                                                {canManageRecipes && (
                                                                    <td className="px-4 py-2 text-left">
                                                                        <div className="flex justify-end gap-1">
                                                                            <button onClick={() => handleOpenTaskModal(recipe.id, rt)} className="p-1 text-gray-400 hover:text-primary transition-colors">
                                                                                <Edit2 className="w-3.5 h-3.5" />
                                                                            </button>
                                                                            <button onClick={() => handleDeleteTask(rt.id)} className="p-1 text-gray-400 hover:text-red-500 transition-colors">
                                                                                <Trash2 className="w-3.5 h-3.5" />
                                                                            </button>
                                                                        </div>
                                                                    </td>
                                                                )}
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        ) : (
                                            <div className="text-center py-6 bg-white dark:bg-slate-700/30 rounded-lg border border-dashed border-gray-300 dark:border-slate-600">
                                                <p className="text-sm text-gray-500 dark:text-slate-400">لا توجد مهام مدرجة في هذا النطاق.</p>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Recipe Modal */}
            <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editingRecipe ? 'تعديل الوصفة' : 'إضافة وصفة جديدة'}>
                <form onSubmit={handleSaveRecipe} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">المحصول *</label>
                        <select
                            required
                            value={formData.crop}
                            onChange={(e) => setFormData({ ...formData, crop: e.target.value })}
                            className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white shadow-sm"
                            disabled={!!editingRecipe}
                        >
                            <option value="">-- اختر المحصول --</option>
                            {crops.map((c) => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">اسم الوصفة *</label>
                        <input
                            required
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white shadow-sm"
                            placeholder="مثال: تسميد الأسبوع الرابع"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">المرحلة الفينولوجية (مرحلة النمو)</label>
                        <input
                            type="text"
                            value={formData.phenological_stage}
                            onChange={(e) => setFormData({ ...formData, phenological_stage: e.target.value })}
                            className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white shadow-sm"
                            placeholder="مثال: التزهير، العقد..."
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">العمالة القياسية (ساعة / هكتار)</label>
                        <input
                            type="number"
                            step="0.01"
                            value={formData.expected_labor_hours_per_ha}
                            onChange={(e) => setFormData({ ...formData, expected_labor_hours_per_ha: e.target.value })}
                            className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white shadow-sm ltr"
                        />
                    </div>
                    <div className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="is_active_recipe"
                            checked={formData.is_active}
                            onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                            className="rounded border-gray-300 text-primary focus:ring-primary"
                        />
                        <label htmlFor="is_active_recipe" className="text-sm font-medium text-gray-700 dark:text-slate-300 cursor-pointer">
                            وصفة نشطة ومستدامة
                        </label>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">ملاحظات</label>
                        <textarea
                            rows="3"
                            value={formData.notes}
                            onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
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
                            {editingRecipe ? 'تحديث' : 'حفظ'}
                        </button>
                    </div>
                </form>
            </Modal>

            {/* Material Modal */}
            <Modal isOpen={matModalOpen} onClose={() => setMatModalOpen(false)} title={editingMaterial ? 'تعديل المادة المعيارية' : 'إضافة مادة للوصفة'}>
                <form onSubmit={handleSaveMaterial} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">تحديد المادة الصنفية *</label>
                        <select
                            required
                            value={matFormData.item}
                            onChange={(e) => setMatFormData({ ...matFormData, item: e.target.value })}
                            className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white shadow-sm"
                            disabled={!!editingMaterial}
                        >
                            <option value="">-- اختر المادة --</option>
                            {items.map((i) => (
                                <option key={i.id} value={i.id}>{i.name} ({i.uom})</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">الكمية القياسية (لكل هكتار) *</label>
                        <input
                            required
                            type="number"
                            step="0.001"
                            min="0"
                            value={matFormData.standard_qty_per_ha}
                            onChange={(e) => setMatFormData({ ...matFormData, standard_qty_per_ha: e.target.value })}
                            className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white shadow-sm ltr"
                        />
                    </div>

                    <div className="flex gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
                        <button
                            type="button"
                            onClick={() => setMatModalOpen(false)}
                            className="flex-1 px-4 py-2 border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition"
                        >
                            إلغاء
                        </button>
                        <button
                            type="submit"
                            className="flex-1 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition flex justify-center items-center gap-2"
                        >
                            <Save className="w-4 h-4" />
                            {editingMaterial ? 'تحديث' : 'إضافة'}
                        </button>
                    </div>
                </form>
            </Modal>

            {/* Task Modal */}
            <Modal isOpen={taskModalOpen} onClose={() => setTaskModalOpen(false)} title={editingTask ? 'تعديل المهمة القياسية' : 'إضافة مهمة للوصفة'}>
                <form onSubmit={handleSaveTask} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">العملية الزراعية (Task Reference) *</label>
                        <select
                            required
                            value={taskFormData.task}
                            onChange={(e) => setTaskFormData({ ...taskFormData, task: e.target.value })}
                            className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white shadow-sm"
                        >
                            <option value="">-- اختر العملية --</option>
                            {allTasks.map((t) => (
                                <option key={t.id} value={t.id}>{t.name} ({t.stage})</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">اسم المهمة التفصيلي *</label>
                        <input
                            required
                            type="text"
                            value={taskFormData.name}
                            onChange={(e) => setTaskFormData({ ...taskFormData, name: e.target.value })}
                            className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white shadow-sm"
                            placeholder="مثال: تجهيز التربة للأسبوع الرابع"
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">توقيت البدء (T+ يوم) *</label>
                            <input
                                required
                                type="number"
                                min="0"
                                value={taskFormData.days_offset}
                                onChange={(e) => setTaskFormData({ ...taskFormData, days_offset: e.target.value })}
                                className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white shadow-sm ltr"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">الجهد المقدر (ساعة) *</label>
                            <input
                                required
                                type="number"
                                step="0.1"
                                min="0"
                                value={taskFormData.estimated_hours}
                                onChange={(e) => setTaskFormData({ ...taskFormData, estimated_hours: e.target.value })}
                                className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white shadow-sm ltr"
                            />
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">ملاحظات المهمة</label>
                        <textarea
                            rows="2"
                            value={taskFormData.notes}
                            onChange={(e) => setTaskFormData({ ...taskFormData, notes: e.target.value })}
                            className="w-full bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-600 rounded-lg p-2.5 text-sm outline-none focus:ring-2 focus:ring-primary dark:text-white shadow-sm"
                        />
                    </div>

                    <div className="flex gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
                        <button
                            type="button"
                            onClick={() => setTaskModalOpen(false)}
                            className="flex-1 px-4 py-2 border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition"
                        >
                            إلغاء
                        </button>
                        <button
                            type="submit"
                            className="flex-1 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition flex justify-center items-center gap-2"
                        >
                            <Save className="w-4 h-4" />
                            {editingTask ? 'تحديث' : 'إضافة'}
                        </button>
                    </div>
                </form>
            </Modal>

        </div>
    )
}
