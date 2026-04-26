import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Crops } from '../api/client'
import { useToast } from '../components/ToastProvider'
import TaskContractForm, { STAGES, ARCHETYPE_LABELS, CARD_ORDER, Badge, CardBadge, OPTIONAL_CARDS } from '../components/TaskContractForm'

const TEXT = {
  title: 'مهام المحاصيل',
  subtitle: 'إدارة مهام المحصول بعقد ذكي متعدد البطاقات ومتوافق مع التنفيذ اليومي.',
  back: 'العودة إلى المحاصيل',
  noTasks: 'لا توجد مهام لهذا المحصول بعد.',
  addButton: 'إضافة مهمة جديدة',
  addTitle: 'إضافة مهمة جديدة',
  editTitle: 'تعديل المهمة',
}

const taskSelectedCards = (task) =>
  OPTIONAL_CARDS.reduce((acc, cardKey) => {
    const smartCards = task?.effective_task_contract?.smart_cards || task?.task_contract?.smart_cards || {}
    acc[cardKey] = Boolean(smartCards?.[cardKey]?.enabled)
    return acc
  }, {})

const TaskCard = ({ task, onEdit, onDelete }) => {
  const smartCards = task?.effective_task_contract?.smart_cards || task?.task_contract?.smart_cards || {}
  const enabledCardKeys = CARD_ORDER.filter((cardKey) => Boolean(smartCards?.[cardKey]?.enabled))
  return (
    <div className="group relative rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition-all hover:border-emerald-500/20 hover:bg-gray-50 hover:shadow-lg hover:shadow-emerald-900/10 dark:border-white/5 dark:bg-[#181b1a] dark:hover:bg-[#1f2321]">
      <div className="mb-3 flex items-start justify-between">
        <div>
          <h4 className="mb-1 text-base font-bold text-gray-900 transition-colors group-hover:text-emerald-600 dark:text-white dark:group-hover:text-emerald-300">{task.name}</h4>
          <span className="inline-block rounded bg-gray-100 px-2 py-1 text-xs text-gray-500 dark:bg-black/20 dark:text-zinc-500">{task.stage || STAGES.undefined}</span>
        </div>
        <div className="flex gap-2 opacity-0 transition-opacity group-hover:opacity-100">
          <button data-testid={`crop-task-edit-${task.id}`} onClick={() => onEdit(task)} className="rounded bg-gray-100 p-1.5 text-gray-500 transition-colors hover:bg-gray-200 hover:text-gray-900 dark:bg-white/5 dark:text-zinc-400 dark:hover:bg-white/10 dark:hover:text-white">تعديل</button>
          <button onClick={() => onDelete(task.id)} className="rounded bg-rose-500/10 p-1.5 text-rose-600 transition-colors hover:bg-rose-500/20 dark:text-rose-400">حذف</button>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        <Badge label={ARCHETYPE_LABELS[task.archetype] || task.archetype || 'GENERAL'} color="emerald" />
        {task.requires_well && <Badge label="يعتمد على بئر" color="blue" />}
        {task.requires_machinery && <Badge label="معدة/رافعة" color="amber" />}
        {task.is_perennial_procedure && <Badge label="خدمة معمّرة" color="rose" />}
        {task.requires_tree_count && <Badge label="عداد أشجار" color="rose" />}
        {enabledCardKeys.length > 0 && <Badge label={`${enabledCardKeys.length} بطاقة ذكية`} color="slate" />}
      </div>
      {enabledCardKeys.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {enabledCardKeys.slice(0, 5).map((cardKey) => <CardBadge key={cardKey} cardKey={cardKey} />)}
        </div>
      )}
    </div>
  )
}

const StageGroup = ({ stage, tasks, onEdit, onDelete }) => (
  <div className="mb-8 last:mb-0">
    <h3 className="sticky top-0 z-10 mb-4 flex items-center gap-3 bg-gray-50/95 py-3 text-lg font-bold text-gray-700 backdrop-blur dark:bg-slate-900/95 dark:text-zinc-300">
      <span className="h-6 w-1.5 rounded-full bg-emerald-500/50" />
      {stage}
      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-normal text-gray-500 dark:bg-white/5 dark:text-zinc-600">{tasks.length}</span>
    </h3>
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {tasks.map((task) => <TaskCard key={task.id} task={task} onEdit={onEdit} onDelete={onDelete} />)}
    </div>
  </div>
)

export default function CropTasks() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [tasks, setTasks] = useState([])
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [initialData, setInitialData] = useState({})

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const { data } = await Crops.tasks(id)
      setTasks(data.results || data || [])
    } catch (error) {
      console.error('Failed to load tasks', error)
      toast({ title: 'خطأ', message: 'تعذر تحميل المهام.', intent: 'error' })
    } finally {
      setLoading(false)
    }
  }, [id, toast])

  useEffect(() => {
    void loadData()
  }, [loadData])

  const groupedTasks = useMemo(() => {
    const groups = {}
    tasks.forEach((task) => {
      const stage = task.stage?.trim() || STAGES.undefined
      if (!groups[stage]) groups[stage] = []
      groups[stage].push(task)
    })
    return Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0], 'ar'))
  }, [tasks])

  const openFormForNew = () => {
    setEditingTask(null)
    setInitialData({})
    setIsFormOpen(true)
  }

  const openEdit = (task) => {
    setEditingTask(task)
    setInitialData({
      stage: task.stage || '',
      name: task.name || '',
      presetKey: 'CUSTOM',
      archetype: task.archetype || 'GENERAL',
      selectedCards: taskSelectedCards(task),
      requiresArea: Boolean(task.requires_area),
      isAssetTask: Boolean(task.is_asset_task),
      assetType: task.asset_type || '',
    })
    setIsFormOpen(true)
  }

  const handleDelete = async (taskId) => {
    if (!window.confirm('هل أنت متأكد من حذف هذه المهمة؟')) return
    try {
      await Crops.deleteTask(id, taskId)
      await loadData()
      toast({ title: 'نجاح', message: 'تم حذف المهمة.', intent: 'success' })
    } catch (error) {
      console.error('Failed to delete task', error)
      toast({ title: 'خطأ', message: 'تعذر حذف المهمة.', intent: 'error' })
    }
  }

  const handleTaskSubmit = async (formData, payload) => {
    try {
      if (editingTask) {
        await Crops.updateTask(id, editingTask.id, payload)
        toast({ title: 'نجاح', message: 'تم تحديث المهمة بنجاح.', intent: 'success' })
      } else {
        await Crops.addTask(id, payload)
        toast({ title: 'نجاح', message: 'تمت إضافة المهمة بنجاح.', intent: 'success' })
      }
      setIsFormOpen(false)
      await loadData()
    } catch (error) {
      console.error('Failed to save task', error)
      toast({ title: 'خطأ', message: 'تعذر حفظ المهمة.', intent: 'error' })
    }
  }

  return (
    <div dir="rtl" className="min-h-screen bg-gray-50 p-8 text-gray-800 dark:bg-slate-900 dark:text-white">
      <header className="mx-auto mb-12 flex max-w-7xl items-end justify-between">
        <div>
          <button onClick={() => navigate('/crops')} className="mb-4 flex items-center gap-2 text-sm text-gray-500 transition-colors hover:text-emerald-600 dark:text-zinc-500 dark:hover:text-emerald-400">← {TEXT.back}</button>
          <h1 className="bg-gradient-to-r from-emerald-600 to-amber-500 bg-clip-text text-4xl font-black text-transparent dark:from-emerald-400 dark:to-amber-200">{TEXT.title}</h1>
          <p className="mt-2 text-gray-500 dark:text-zinc-500">{TEXT.subtitle}</p>
        </div>
        <button onClick={openFormForNew} className="rounded-xl bg-emerald-600 px-6 py-3 font-bold text-white shadow-lg shadow-emerald-500/20 transition-all hover:scale-105 hover:bg-emerald-500">+ {TEXT.addButton}</button>
      </header>
      <main className="mx-auto max-w-7xl">
        {loading ? <div className="space-y-4 animate-pulse"><div className="h-40 rounded-2xl bg-white/5" /><div className="h-40 rounded-2xl bg-white/5" /></div> : groupedTasks.length === 0 ? <div className="rounded-3xl border border-dashed border-white/10 bg-white/5 py-20 text-center"><span className="mb-4 block text-4xl opacity-50">🗂️</span><p className="text-zinc-500">{TEXT.noTasks}</p></div> : <div className="space-y-2">{groupedTasks.map(([stage, groupTasks]) => <StageGroup key={stage} stage={stage} tasks={groupTasks} onEdit={openEdit} onDelete={handleDelete} />)}</div>}
      </main>
      {isFormOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm dark:bg-black/80">
          <div className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-3xl border border-gray-200 bg-white p-8 shadow-2xl dark:border-white/10 dark:bg-[#131615]">
            <h2 className="mb-6 text-2xl font-bold text-emerald-700 dark:text-emerald-100">{editingTask ? TEXT.editTitle : TEXT.addTitle}</h2>
            <TaskContractForm initialData={initialData} onSubmit={handleTaskSubmit} onCancel={() => setIsFormOpen(false)} />
          </div>
        </div>
      )}
    </div>
  )
}
