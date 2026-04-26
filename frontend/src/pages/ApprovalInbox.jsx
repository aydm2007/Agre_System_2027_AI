import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AlertTriangle, Clock3, Eye, Filter, RefreshCw, ShieldCheck } from 'lucide-react'
import { ApprovalRequests, api } from '../api/client'
import { useFarmContext } from '../api/farmContext.jsx'
import { useOpsRuntime } from '../contexts/OpsRuntimeContext.jsx'
import { useSettings } from '../contexts/SettingsContext.jsx'
import {
  formatBlocker,
  formatBooleanArabic,
  formatLaneHealth,
  formatOpsKind,
  formatOpsReason,
  formatOpsSeverity,
  formatPolicySource,
} from '../utils/opsArabic'

const TABS = [
  ['overview', 'نظرة عامة'],
  ['farms', 'المزارع'],
  ['policy', 'أثر السياسة'],
  ['queue', 'طابوري'],
  ['workbench', 'لوحة القطاع'],
  ['attention', 'التنبيهات'],
  ['runtime', 'التشغيل الحي'],
  ['selected', 'الطلب المحدد'],
]

const STATUS = { PENDING: 'قيد الانتظار', APPROVED: 'معتمد', REJECTED: 'مرفوض' }
const STATUS_TONE = {
  PENDING: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  APPROVED: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  REJECTED: 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300',
}
const HEALTH_TONE = {
  blocked: 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300',
  attention: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
  healthy: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
}

const fmtDate = (v) => {
  if (!v) return '—'
  try { return new Date(v).toLocaleString('ar-YE') } catch { return v }
}

const fmtMoney = (v) =>
  Number(v || 0).toLocaleString('ar-YE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function Pill({ children, cls = 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200' }) {
  return <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${cls}`}>{children}</span>
}

function Stat({ title, value, helper, icon: Icon, tone = 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700' }) {
  return (
    <div className={`rounded-2xl border p-4 shadow-sm ${tone}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm text-slate-500 dark:text-slate-400">{title}</div>
          <div className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">{value}</div>
          {helper ? <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{helper}</div> : null}
        </div>
        {Icon ? <Icon className="h-5 w-5 text-slate-500 dark:text-slate-400" /> : null}
      </div>
    </div>
  )
}

export default function ApprovalInbox() {
  const location = useLocation()
  const navigate = useNavigate()
  const { isStrictMode } = useSettings()
  const { farms } = useFarmContext()
  const { topAlerts, localOfflineSignals, offlineSnapshot, canObserveOps, loadRequestTrace } = useOpsRuntime()
  const [tab, setTab] = useState('queue')
  const [items, setItems] = useState([])
  const [summary, setSummary] = useState({ pending_count: 0, overdue_count: 0, blocked_count: 0, lanes: [] })
  const [workbench, setWorkbench] = useState({ rows: [], summary: {} })
  const [workbenchSummary, setWorkbenchSummary] = useState({ summary: {} })
  const [attention, setAttention] = useState({ count: 0, items: [] })
  const [maintenance, setMaintenance] = useState({ attachment_runtime: {} })
  const [runtimeGovernance, setRuntimeGovernance] = useState({ lane_health_totals: {}, blocked_reasons: {}, remote_review_posture: {}, attachment_runtime_posture: {}, request_headers: {} })
  const [runtimeGovernanceDetail, setRuntimeGovernanceDetail] = useState({ detail_rows: [], filtered_total: 0 })
  const [sectorDashboard, setSectorDashboard] = useState({ kpis: {}, top_farms: [], top_lanes: [], blocked_buckets: {}, attention_summary: {} })
  const [policyImpact, setPolicyImpact] = useState({ approval_profile_counts: {}, approval_profile_source_counts: {}, threshold_driven_escalations: {}, affected_farms: [] })
  const [farmGovernance, setFarmGovernance] = useState(null)
  const [farmOps, setFarmOps] = useState(null)
  const [outboxDetail, setOutboxDetail] = useState({ detail_rows: [], filtered_total: 0 })
  const [attachmentDetail, setAttachmentDetail] = useState({ detail_rows: [], filtered_total: 0 })
  const [selectedOutboxIds, setSelectedOutboxIds] = useState([])
  const [selectedAttachmentIds, setSelectedAttachmentIds] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [selected, setSelected] = useState(null)
  const [selectedTrace, setSelectedTrace] = useState(null)
  const [statusFilter, setStatusFilter] = useState('PENDING')
  const [laneFilter, setLaneFilter] = useState('ALL')
  const [farmFilter, setFarmFilter] = useState('ALL')
  const [scopeFilter, setScopeFilter] = useState('ALL')
  const [healthFilter, setHealthFilter] = useState('ALL')
  const [kindFilter, setKindFilter] = useState('ALL')
  const [overdueOnly, setOverdueOnly] = useState(false)
  const [directorOnly, setDirectorOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [modal, setModal] = useState({ show: false, reqId: null, action: null })
  const [reason, setReason] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const [opsActionLoading, setOpsActionLoading] = useState(false)

  const farmMap = useMemo(() => Object.fromEntries((farms || []).map((f) => [f.id, f.name])), [farms])
  const activeFarmId = useMemo(() => {
    if (farmFilter !== 'ALL') return farmFilter
    if (selected?.farm) return String(selected.farm)
    if (farms?.[0]?.id) return String(farms[0].id)
    return ''
  }, [farmFilter, selected?.farm, farms])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    if (!isStrictMode) {
      setItems([])
      setSummary({ pending_count: 0, overdue_count: 0, blocked_count: 0, lanes: [] })
      setWorkbench({ rows: [], summary: {} })
      setWorkbenchSummary({ summary: {} })
      setAttention({ count: 0, items: [] })
      setRuntimeGovernance({ lane_health_totals: {}, blocked_reasons: {}, remote_review_posture: {}, attachment_runtime_posture: {}, request_headers: {} })
      setRuntimeGovernanceDetail({ detail_rows: [], filtered_total: 0 })
      setSectorDashboard({ kpis: {}, top_farms: [], top_lanes: [], blocked_buckets: {}, attention_summary: {} })
      setPolicyImpact({ approval_profile_counts: {}, approval_profile_source_counts: {}, threshold_driven_escalations: {}, affected_farms: [] })
      setError('سطح الاعتمادات القطاعية متاح فقط في الوضع الصارم.')
      setLoading(false)
      return
    }
    try {
      const [listRes, summaryRes, maintenanceRes, runtimeRes, runtimeDetailRes, workbenchRes, workbenchSummaryRes, attentionRes, sectorDashboardRes, policyImpactRes] = await Promise.all([
        statusFilter === 'PENDING' ? ApprovalRequests.myQueue({ status: statusFilter }) : ApprovalRequests.list({ status: statusFilter }),
        ApprovalRequests.queueSummary(),
        ApprovalRequests.maintenanceSummary(),
        ApprovalRequests.runtimeGovernance(),
        ApprovalRequests.runtimeGovernanceDetail(),
        ApprovalRequests.roleWorkbench(),
        ApprovalRequests.roleWorkbenchSummary(),
        ApprovalRequests.attentionFeed(),
        ApprovalRequests.sectorDashboard(),
        ApprovalRequests.policyImpact(),
      ])
      const nextItems = listRes.data?.results || listRes.data || []
      setItems(nextItems)
      setSummary(summaryRes.data || {})
      setMaintenance(maintenanceRes.data || {})
      setRuntimeGovernance(runtimeRes.data || { lane_health_totals: {}, blocked_reasons: {}, remote_review_posture: {}, attachment_runtime_posture: {}, request_headers: {} })
      setRuntimeGovernanceDetail(runtimeDetailRes.data || { detail_rows: [], filtered_total: 0 })
      setWorkbench(workbenchRes.data || { rows: [], summary: {} })
      setWorkbenchSummary(workbenchSummaryRes.data || { summary: {} })
      setAttention(attentionRes.data || { count: 0, items: [] })
      setSectorDashboard(sectorDashboardRes.data || { kpis: {}, top_farms: [], top_lanes: [], blocked_buckets: {}, attention_summary: {} })
      setPolicyImpact(policyImpactRes.data || { approval_profile_counts: {}, approval_profile_source_counts: {}, threshold_driven_escalations: {}, affected_farms: [] })
      setSelectedOutboxIds([])
      setSelectedAttachmentIds([])
      if (!selectedId && nextItems[0]?.id) setSelectedId(nextItems[0].id)
    } catch (err) {
      console.error(err)
      setError('تعذر تحميل منصة الاعتمادات القطاعية.')
    } finally {
      setLoading(false)
    }
  }, [isStrictMode, selectedId, statusFilter])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const queryTab = params.get('tab')
    const queryFarm = params.get('farm')
    const queryRequest = params.get('request')
    const knownTabs = new Set(TABS.map(([key]) => key))
    if (queryTab && knownTabs.has(queryTab)) setTab(queryTab)
    if (queryFarm) setFarmFilter(String(queryFarm))
    if (queryRequest && /^\d+$/.test(queryRequest)) setSelectedId(Number(queryRequest))
  }, [location.search])
  useEffect(() => {
    let dead = false
    if (!isStrictMode) {
      setFarmGovernance(null)
      setFarmOps(null)
      setOutboxDetail({ detail_rows: [], filtered_total: 0 })
      setAttachmentDetail({ detail_rows: [], filtered_total: 0 })
      return undefined
    }
    if (!activeFarmId) {
      setFarmGovernance(null)
      setFarmOps(null)
      setOutboxDetail({ detail_rows: [], filtered_total: 0 })
      setAttachmentDetail({ detail_rows: [], filtered_total: 0 })
      return undefined
    }
    Promise.all([
      ApprovalRequests.farmGovernance({ farm: activeFarmId }),
      ApprovalRequests.farmOps({ farm: activeFarmId }).catch(() => ({ data: null })),
      api.get('/dashboard/outbox-health/detail/', { params: { farm_id: activeFarmId, limit: 25 } }).catch(() => ({ data: { detail_rows: [], filtered_total: 0 } })),
      api.get('/dashboard/attachment-runtime-health/detail/', { params: { farm_id: activeFarmId, limit: 25 } }).catch(() => ({ data: { detail_rows: [], filtered_total: 0 } })),
    ])
      .then(([farmGovernanceRes, farmOpsRes, outboxDetailRes, attachmentDetailRes]) => {
        if (dead) return
        setFarmGovernance(farmGovernanceRes.data || null)
        setFarmOps(farmOpsRes.data || null)
        setOutboxDetail(outboxDetailRes.data || { detail_rows: [], filtered_total: 0 })
        setAttachmentDetail(attachmentDetailRes.data || { detail_rows: [], filtered_total: 0 })
      })
      .catch((err) => {
        console.error(err)
        if (!dead) {
          setFarmGovernance(null)
          setFarmOps(null)
          setOutboxDetail({ detail_rows: [], filtered_total: 0 })
          setAttachmentDetail({ detail_rows: [], filtered_total: 0 })
        }
      })
    return () => { dead = true }
  }, [activeFarmId, isStrictMode, load])
  useEffect(() => {
    let dead = false
    if (!isStrictMode) {
      setSelected(null)
      setSelectedTrace(null)
      return undefined
    }
    if (!selectedId) {
      setSelected(null)
      setSelectedTrace(null)
      return undefined
    }
    setDetailLoading(true)
    Promise.all([
      ApprovalRequests.retrieve(selectedId),
      loadRequestTrace({ request_id: selectedId }).catch(() => null),
    ])
      .then(([detailRes, traceRes]) => {
        if (dead) return
        setSelected(detailRes.data || null)
        setSelectedTrace(traceRes || null)
      })
      .catch((err) => {
        console.error(err)
        if (!dead) setError('تعذر تحميل تفاصيل الطلب المحدد.')
      })
      .finally(() => { if (!dead) setDetailLoading(false) })
    return () => { dead = true }
  }, [isStrictMode, loadRequestTrace, selectedId])

  const queueRows = useMemo(() => {
    let rows = [...items]
    if (laneFilter !== 'ALL') rows = rows.filter((x) => x?.queue_snapshot?.current_role === laneFilter)
    if (farmFilter !== 'ALL') rows = rows.filter((x) => String(x.farm) === String(farmFilter))
    if (healthFilter !== 'ALL') rows = rows.filter((x) => x?.queue_snapshot?.lane_health === healthFilter)
    if (overdueOnly) rows = rows.filter((x) => Boolean(x?.queue_snapshot?.is_overdue))
    return rows
  }, [farmFilter, healthFilter, items, laneFilter, overdueOnly])

  const workbenchRows = useMemo(() => {
    let rows = [...(workbench.rows || [])]
    if (laneFilter !== 'ALL') rows = rows.filter((x) => x.role === laneFilter)
    if (farmFilter !== 'ALL') rows = rows.filter((x) => String(x.farm_id) === String(farmFilter))
    if (scopeFilter !== 'ALL') rows = rows.filter((x) => x.owner_scope === scopeFilter)
    if (healthFilter !== 'ALL') rows = rows.filter((x) => x.lane_health === healthFilter)
    if (directorOnly) rows = rows.filter((x) => x.director_attention)
    if (overdueOnly) rows = rows.filter((x) => x.overdue > 0)
    return rows
  }, [directorOnly, farmFilter, healthFilter, laneFilter, overdueOnly, scopeFilter, workbench.rows])

  const attentionRows = useMemo(() => {
    let rows = [...(attention.items || [])]
    if (farmFilter !== 'ALL') rows = rows.filter((x) => String(x.farm_id || '') === String(farmFilter))
    if (kindFilter !== 'ALL') rows = rows.filter((x) => x.kind === kindFilter)
    return rows
  }, [attention.items, farmFilter, kindFilter])

  const openModal = (reqId, action) => { setModal({ show: true, reqId, action }); setReason('') }
  const closeModal = () => { setModal({ show: false, reqId: null, action: null }); setReason('') }
  const pick = (reqId) => { setSelectedId(reqId); setTab('selected') }

  const submitAction = async (e) => {
    e.preventDefault()
    setActionLoading(true)
    setError('')
    setMessage('')
    try {
      const payload = { reason }
      if (modal.action === 'APPROVE') await ApprovalRequests.approve(modal.reqId, payload)
      else if (modal.action === 'OVERRIDE') await ApprovalRequests.overrideStage(modal.reqId, payload)
      else if (modal.action === 'REOPEN') await ApprovalRequests.reopen(modal.reqId, payload)
      else await ApprovalRequests.reject(modal.reqId, payload)
      setMessage('تم تنفيذ الإجراء بنجاح.')
      closeModal()
      await load()
      setSelectedId(modal.reqId)
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || 'تعذر تنفيذ القرار الحالي.')
      closeModal()
    } finally {
      setActionLoading(false)
    }
  }

  const toggleSelection = (value, setter) => {
    setter((prev) => (prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value]))
  }

  const runOpsAction = async ({ label, confirmText, execute, clear }) => {
    if (confirmText && typeof window !== 'undefined' && !window.confirm(confirmText)) return
    setOpsActionLoading(true)
    setError('')
    setMessage('')
    try {
      await execute()
      if (clear) clear()
      setMessage(label)
      await load()
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || err.message || 'تعذر تنفيذ الإجراء التشغيلي المطلوب.')
    } finally {
      setOpsActionLoading(false)
    }
  }

  const retrySelectedOutbox = async () => {
    await runOpsAction({
      label: 'تمت إعادة جدولة أحداث outbox المحددة.',
      confirmText: `Retry ${selectedOutboxIds.length} selected outbox event(s)?`,
      execute: async () => {
        await api.post('/dashboard/outbox-health/retry/', { event_ids: selectedOutboxIds })
      },
      clear: () => setSelectedOutboxIds([]),
    })
  }

  const rescanSelectedAttachments = async () => {
    await runOpsAction({
      label: 'تمت إعادة فحص المرفقات المحددة.',
      confirmText: `Rescan ${selectedAttachmentIds.length} selected attachment(s)?`,
      execute: async () => {
        await api.post('/dashboard/attachment-runtime-health/rescan/', { attachment_ids: selectedAttachmentIds })
      },
      clear: () => setSelectedAttachmentIds([]),
    })
  }

  const runMaintenanceDryRun = async () => {
    await runOpsAction({
      label: 'تم تشغيل dry-run لدورة governance maintenance.',
      confirmText: 'تشغيل المعاينة الجافة لصيانة الحوكمة الآن؟',
      execute: async () => {
        await ApprovalRequests.dryRunMaintenance({})
      },
    })
  }

  const selectedSnapshot = selectedTrace?.queue_snapshot || selected?.queue_snapshot || {}
  const selectedPolicy = selectedTrace?.policy_context || selectedSnapshot.policy_context || selected?.workflow_blueprint?.policy_context || {}
  const selectedBlockers = selectedTrace?.blockers || selectedSnapshot.blockers || selected?.workflow_blueprint?.blockers || []

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900 dark:text-white">
              <ShieldCheck className="h-6 w-6 text-primary" /> منصة طوابير واعتمادات القطاع
            </h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">سطح موحد للطابور ولوحة القطاع وموجز التنبيهات والحوكمة التشغيلية داخل `/approvals`.</p>
          </div>
          <button onClick={load} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700">
            <RefreshCw className="h-4 w-4" /> تحديث
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4 xl:grid-cols-8">
        <Stat title="طلباتي المعلقة" value={summary.pending_count || 0} helper="طلبات تنتظر مرحلتك" icon={Clock3} tone="bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/60" />
        <Stat title="طلباتي المتأخرة" value={summary.overdue_count || 0} helper="تجاوزت المهلة" icon={AlertTriangle} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
        <Stat title="طلباتي المعطلة" value={summary.blocked_count || 0} helper="معطلة بفعل السياسة" icon={ShieldCheck} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
        <Stat title="صفوف لوحة القطاع" value={workbenchSummary.summary?.rows || 0} helper="مسارات مجمعة" icon={Filter} tone="bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-900/60" />
        <Stat title="تدخل المدير" value={workbenchSummary.summary?.director_attention_count || 0} helper="تدخل قطاعي" icon={AlertTriangle} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
        <Stat title="موجز التنبيهات" value={attention.count || 0} helper="عناصر موحدة" icon={Eye} tone="bg-sky-50 dark:bg-sky-950/30 border-sky-200 dark:border-sky-900/60" />
        <Stat title="تعطيل المراجعة البعيدة" value={maintenance.remote_review_blocked_escalations || 0} helper="موقوفة بسياسة صارمة" icon={AlertTriangle} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
        <Stat title="تشغيل المرفقات" value={maintenance.attachment_runtime?.quarantined || 0} helper="أدلة معزولة" icon={ShieldCheck} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
      </div>

      <div className="flex flex-wrap gap-2">
        {TABS.map(([key, label]) => <button key={key} onClick={() => setTab(key)} className={`rounded-full px-4 py-2 text-sm font-semibold ${tab === key ? 'bg-primary text-white' : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200'}`}>{label}</button>)}
      </div>

      {message ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-300">{message}</div> : null}
      {error ? <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300">{error}</div> : null}
      {loading ? <div className="rounded-2xl border border-dashed border-slate-300 p-10 text-center text-slate-500 dark:border-slate-700 dark:text-slate-400">جارٍ تحميل منصة الاعتمادات...</div> : null}

      {!loading && tab === 'overview' ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4 xl:grid-cols-8">
            <Stat title="معلّق" value={sectorDashboard.kpis?.pending_requests || 0} helper="على مستوى القطاع" icon={Clock3} tone="bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/60" />
            <Stat title="متجاوز للمهلة" value={sectorDashboard.kpis?.overdue_requests || 0} helper="تجاوز مهلة المسار" icon={AlertTriangle} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
            <Stat title="معطل" value={sectorDashboard.kpis?.blocked_requests || 0} helper="العوائق الحاكمة" icon={ShieldCheck} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
            <Stat title="المالية الصارمة" value={sectorDashboard.kpis?.strict_finance_pending || 0} helper="معلّق تحت الحوكمة" icon={ShieldCheck} tone="bg-sky-50 dark:bg-sky-950/30 border-sky-200 dark:border-sky-900/60" />
            <Stat title="تدخل المدير" value={sectorDashboard.kpis?.director_attention_count || 0} helper="ضغط تنفيذي" icon={AlertTriangle} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
            <Stat title="تعطيل المراجعة البعيدة" value={sectorDashboard.kpis?.remote_review_blocked || 0} helper="نوافذ المراجعة" icon={AlertTriangle} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
            <Stat title="تعطيل المرفقات" value={sectorDashboard.kpis?.attachment_runtime_blocked || 0} helper="فحص وعزل" icon={ShieldCheck} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
            <Stat title="عناصر التنبيه" value={sectorDashboard.attention_summary?.count || 0} helper="حجم الموجز" icon={Eye} tone="bg-sky-50 dark:bg-sky-950/30 border-sky-200 dark:border-sky-900/60" />
          </div>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">أعلى المسارات</div>
              <div className="space-y-3">
                {(sectorDashboard.top_lanes || []).length === 0 ? <div className="text-sm text-slate-500 dark:text-slate-400">لا توجد مسارات حاليًا.</div> : sectorDashboard.top_lanes.map((row) => (
                  <button key={`${row.role}-${row.farm_id}`} type="button" onClick={() => { if (row.farm_id) setFarmFilter(String(row.farm_id)); setTab('workbench') }} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-right dark:border-slate-700 dark:bg-slate-900/30">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-white">{row.role_label}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">{row.farm_name || '—'}</div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Pill cls={HEALTH_TONE[row.lane_health] || HEALTH_TONE.healthy}>{formatLaneHealth(row.lane_health)}</Pill>
                        {row.attention_bucket ? <Pill cls="bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">{formatOpsReason(row.attention_bucket)}</Pill> : null}
                      </div>
                    </div>
                    <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-600 dark:text-slate-300">
                      <div>الإجمالي: {row.count}</div>
                      <div>المتأخر: {row.overdue}</div>
                      <div>المعطل: {row.blocked_count}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">أعلى المزارع</div>
              <div className="space-y-3">
                {(sectorDashboard.top_farms || []).length === 0 ? <div className="text-sm text-slate-500 dark:text-slate-400">لا توجد مزارع بحمولة عالية حاليًا.</div> : sectorDashboard.top_farms.map((farm) => (
                  <button key={farm.farm_id} type="button" onClick={() => { setFarmFilter(String(farm.farm_id)); setTab('farms') }} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-right dark:border-slate-700 dark:bg-slate-900/30">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-white">{farm.farm_name}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">مزرعة #{farm.farm_id}</div>
                      </div>
                      <Pill cls="bg-indigo-100 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300">{farm.pending_count} معلّق</Pill>
                    </div>
                    <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-600 dark:text-slate-300">
                      <div>المعطل: {farm.blocked_count}</div>
                      <div>المتأخر: {farm.overdue_count}</div>
                      <div>المعلّق: {farm.pending_count}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {!loading && tab === 'farms' ? (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
            <div className="flex flex-wrap gap-2">
              <select value={farmFilter} onChange={(e) => setFarmFilter(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"><option value="ALL">كل المزارع</option>{(farms || []).map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {(policyImpact.affected_farms || []).filter((farm) => farmFilter === 'ALL' || String(farm.farm_id) === String(farmFilter)).map((farm) => (
              <button key={farm.farm_id} type="button" onClick={() => setFarmFilter(String(farm.farm_id))} className="rounded-2xl border border-slate-200 bg-white p-4 text-right shadow-sm dark:border-slate-700 dark:bg-slate-800">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-lg font-bold text-slate-900 dark:text-white">{farm.farm_name}</div>
                    <div className="mt-1 text-sm text-slate-500 dark:text-slate-400">{farm.effective_mode} / {farm.approval_profile}</div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Pill cls="bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">{formatPolicySource(farm.approval_profile_source)}</Pill>
                    {farm.strict_finance_required ? <Pill cls="bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">مالية صارمة</Pill> : null}
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {farm.remote_review_required ? <Pill cls="bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">مراجعة بعيدة مطلوبة</Pill> : null}
                  {farm.attachment_strict ? <Pill cls="bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">مرفقات صارمة</Pill> : null}
                </div>
              </button>
            ))}
          </div>
          {farmGovernance ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-bold text-slate-900 dark:text-white">{farmGovernance.farm_name}</h2>
                  <div className="mt-1 text-sm text-slate-500 dark:text-slate-400">{farmGovernance.effective_mode} / {farmGovernance.approval_profile}</div>
                </div>
                {farmGovernance.approval_profile_source ? <Pill cls="bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">{formatPolicySource(farmGovernance.approval_profile_source)}</Pill> : null}
              </div>
              <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-4">
                <Stat title="طلبات المزرعة" value={farmGovernance.lane_summary?.pending_requests || 0} />
                <Stat title="تأخر المزرعة" value={farmGovernance.lane_summary?.overdue_requests || 0} />
                <Stat title="طلبات التفعيل" value={(farmGovernance.open_activation_requests || []).length} />
                <Stat title="طلبات الاستثناء" value={(farmGovernance.open_exception_requests || []).length} />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {Object.keys(farmGovernance.active_blockers || {}).length ? Object.entries(farmGovernance.active_blockers || {}).map(([blocker, count]) => <Pill key={blocker} cls="bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">{formatBlocker(blocker)}: {count}</Pill>) : <Pill cls="bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">لا توجد عوائق نشطة</Pill>}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {!loading && tab === 'policy' ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">ملفات الاعتماد</div>
              <div className="space-y-2">{Object.entries(policyImpact.approval_profile_counts || {}).map(([key, count]) => <div key={key} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-900/30"><span>{key}</span><Pill>{count}</Pill></div>)}</div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">مصادر السياسة</div>
              <div className="space-y-2">{Object.entries(policyImpact.approval_profile_source_counts || {}).map(([key, count]) => <div key={key} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-900/30"><span>{formatPolicySource(key)}</span><Pill cls="bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">{count}</Pill></div>)}</div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">تصعيدات العتبات</div>
              <div className="space-y-2">{Object.entries(policyImpact.threshold_driven_escalations || {}).map(([key, count]) => <div key={key} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-900/30"><span>{key}</span><Pill cls="bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">{count}</Pill></div>)}</div>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <Stat title="انحراف المصدر" value={policyImpact.policy_source_drift_count || 0} helper="مصدر خارج إعدادات المزرعة" icon={Filter} tone="bg-sky-50 dark:bg-sky-950/30 border-sky-200 dark:border-sky-900/60" />
            <Stat title="مزارع المالية الصارمة" value={policyImpact.strict_finance_farms_count || 0} helper="ملف يتطلب اعتمادًا قطاعيًا نهائيًا" icon={ShieldCheck} tone="bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/60" />
            <Stat title="مزارع المراجعة البعيدة" value={policyImpact.remote_review_farms_count || 0} helper="سياسة المراجعة مفعلة" icon={AlertTriangle} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
            <Stat title="مزارع المرفقات الصارمة" value={policyImpact.attachment_strict_farms_count || 0} helper="يتطلب فحصًا نظيفًا" icon={ShieldCheck} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
          </div>
        </div>
      ) : null}

      {!loading && tab === 'queue' ? (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              {['PENDING', 'APPROVED', 'REJECTED'].map((st) => <button key={st} onClick={() => setStatusFilter(st)} className={`rounded-lg px-4 py-2 text-sm font-medium ${statusFilter === st ? 'bg-primary text-white' : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200'}`}>{STATUS[st]}</button>)}
              <button onClick={() => setOverdueOnly((v) => !v)} className={`rounded-full px-3 py-1.5 text-xs font-semibold ${overdueOnly ? 'bg-rose-600 text-white' : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200'}`}>المتأخر فقط</button>
            </div>
            <div className="flex flex-wrap gap-2">
              <select value={laneFilter} onChange={(e) => setLaneFilter(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"><option value="ALL">كل المسارات</option>{(summary.lanes || []).map((l) => <option key={l.role} value={l.role}>{l.label}</option>)}</select>
              <select value={farmFilter} onChange={(e) => setFarmFilter(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"><option value="ALL">كل المزارع</option>{(farms || []).map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select>
              <select value={healthFilter} onChange={(e) => setHealthFilter(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"><option value="ALL">كل الصحة المرحلية</option><option value="blocked">معطل</option><option value="attention">يحتاج متابعة</option><option value="healthy">سليم</option></select>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {queueRows.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">لا توجد طلبات مطابقة للفلاتر الحالية.</div> : queueRows.map((req) => {
              const snap = req.queue_snapshot || {}
              return <button key={req.id} type="button" onClick={() => pick(req.id)} className="rounded-2xl border border-slate-200 bg-white p-4 text-right shadow-sm transition hover:border-primary hover:shadow-md dark:border-slate-700 dark:bg-slate-800">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-semibold ${STATUS_TONE[req.status] || STATUS_TONE.PENDING}`}>{STATUS[req.status] || req.status}</span>
                  <Pill cls={HEALTH_TONE[snap.lane_health] || HEALTH_TONE.healthy}>{formatLaneHealth(snap.lane_health || 'healthy')}</Pill>
                  <Pill cls="bg-indigo-100 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300">{farmMap[req.farm] || `مزرعة #${req.farm}`}</Pill>
                </div>
                <div className="mt-3 flex items-start justify-between gap-3">
                  <div><div className="text-lg font-bold text-slate-900 dark:text-white">{req.module} / {req.action}</div><div className="mt-1 text-sm text-slate-500 dark:text-slate-400">{snap.current_role_label || req.required_role} · {fmtDate(snap.due_at)}</div></div>
                  <div className="text-left"><div className="text-lg font-bold text-primary">{fmtMoney(req.amount)}</div><div className="text-xs text-slate-500 dark:text-slate-400">القيمة</div></div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">{(snap.blockers || []).map((b) => <Pill key={b} cls="bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">{formatBlocker(b)}</Pill>)}{snap.policy_context?.threshold_reason ? <Pill cls="bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">{snap.policy_context.threshold_reason}</Pill> : null}</div>
              </button>
            })}
          </div>
        </div>
      ) : null}

      {!loading && tab === 'workbench' ? (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <button onClick={() => setDirectorOnly((v) => !v)} className={`rounded-full px-3 py-1.5 text-xs font-semibold ${directorOnly ? 'bg-rose-600 text-white' : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200'}`}>تدخل المدير فقط</button>
              <button onClick={() => setOverdueOnly((v) => !v)} className={`rounded-full px-3 py-1.5 text-xs font-semibold ${overdueOnly ? 'bg-rose-600 text-white' : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200'}`}>المتأخر فقط</button>
            </div>
            <div className="flex flex-wrap gap-2">
              <select value={farmFilter} onChange={(e) => setFarmFilter(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"><option value="ALL">كل المزارع</option>{(farms || []).map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select>
              <select value={scopeFilter} onChange={(e) => setScopeFilter(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"><option value="ALL">كل النطاقات</option><option value="farm">المزرعة</option><option value="sector">القطاع</option></select>
              <select value={healthFilter} onChange={(e) => setHealthFilter(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"><option value="ALL">كل الصحة المرحلية</option><option value="blocked">معطل</option><option value="attention">يحتاج متابعة</option><option value="healthy">سليم</option></select>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
            {workbenchRows.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">لا توجد مسارات مطابقة للفلاتر الحالية.</div> : workbenchRows.map((row) => (
              <button key={`${row.role}-${row.farm_id}`} type="button" onClick={() => row.sample_request_ids?.[0] && pick(row.sample_request_ids[0])} className="rounded-2xl border border-slate-200 bg-white p-4 text-right shadow-sm transition hover:border-primary hover:shadow-md dark:border-slate-700 dark:bg-slate-800">
                <div className="flex items-start justify-between gap-3"><div><div className="text-lg font-bold text-slate-900 dark:text-white">{row.role_label}</div><div className="mt-1 text-sm text-slate-500 dark:text-slate-400">{row.farm_name || '—'}</div></div><div className="text-left"><div className="text-2xl font-bold text-primary">{row.count}</div><div className="text-xs text-slate-500 dark:text-slate-400">طلبات</div></div></div>
                <div className="mt-3 flex flex-wrap gap-2"><Pill cls={row.owner_scope === 'sector' ? 'bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300' : 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300'}>{row.owner_scope === 'sector' ? 'القطاع' : row.owner_scope === 'farm' ? 'المزرعة' : row.owner_scope}</Pill><Pill cls={HEALTH_TONE[row.lane_health] || HEALTH_TONE.healthy}>{formatLaneHealth(row.lane_health)}</Pill>{row.policy_context_summary?.approval_profile_source ? <Pill cls="bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">{formatPolicySource(row.policy_context_summary.approval_profile_source)}</Pill> : null}</div>
                <div className="mt-3 grid grid-cols-2 gap-3 text-sm text-slate-700 dark:text-slate-200"><div>المتأخر: {row.overdue}</div><div>المعطل: {row.blocked_count}</div><div>مهلة SLA: {row.lane_sla_hours} ساعة</div><div>{formatOpsReason(row.threshold_reason) || '—'}</div></div>
                <div className="mt-3 flex flex-wrap gap-2">{row.remote_review_blocked ? <Pill cls="bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">موقوفة بالمراجعة البعيدة</Pill> : null}{row.attachment_scan_blocked ? <Pill cls="bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">موقوفة بفحص المرفقات</Pill> : null}{row.strict_finance_required ? <Pill cls="bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">مالية صارمة مطلوبة</Pill> : null}</div>
              </button>
            ))}
          </div>
        </div>
      ) : null}
      {!loading && tab === 'attention' ? (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
            <div className="flex flex-wrap gap-2">
              <select value={farmFilter} onChange={(e) => setFarmFilter(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"><option value="ALL">كل المزارع</option>{(farms || []).map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select>
              <select value={kindFilter} onChange={(e) => setKindFilter(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"><option value="ALL">كل الأنواع</option><option value="approval_overdue">طلب متجاوز للمهلة</option><option value="sector_final_attention">تدخل قطاعي نهائي</option><option value="farm_finance_volume_attention">ضغط مالية المزرعة</option><option value="remote_review_blocked">تعطيل المراجعة البعيدة</option><option value="attachment_runtime_block">تعطيل تشغيل المرفقات</option></select>
            </div>
          </div>
          <div className="space-y-3">
            {attentionRows.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">لا توجد عناصر تنبيه مطابقة.</div> : attentionRows.map((item, index) => (
              <button key={`${item.kind}-${item.request_id || item.farm_id || index}`} type="button" onClick={() => (item.request_id || item.sample_request_ids?.[0]) && pick(item.request_id || item.sample_request_ids[0])} className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-right shadow-sm transition hover:border-primary hover:shadow-md dark:border-slate-700 dark:bg-slate-800">
                <div className="flex flex-wrap items-center gap-2">
                  <Pill cls={item.severity === 'critical' ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300' : item.severity === 'high' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300' : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200'}>{formatOpsSeverity(item.severity)}</Pill>
                  <Pill cls="bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">{formatOpsKind(item.kind)}</Pill>
                  {item.farm_name ? <Pill cls="bg-indigo-100 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300">{item.farm_name}</Pill> : null}
                </div>
                <div className="mt-3 text-sm font-semibold text-slate-900 dark:text-white">{formatOpsReason(item.message)}</div>
                <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">{item.role_label ? `${item.role_label} · ` : ''}{fmtDate(item.created_at)}</div>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {!loading && tab === 'runtime' ? (
        <div className="space-y-4">
          {canObserveOps ? (
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800 xl:col-span-2">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-slate-900 dark:text-white">التنبيهات النشطة</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">موجز موحد للتنبيهات مع روابط داخلية ودليل تشغيل.</div>
                  </div>
                  <Pill cls="bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">{topAlerts.length}</Pill>
                </div>
                <div className="space-y-3">
                  {topAlerts.length === 0 ? <div className="text-sm text-slate-500 dark:text-slate-400">لا توجد تنبيهات تشغيلية غير معالجة حاليًا.</div> : topAlerts.map((alert) => (
                    <button key={alert.fingerprint} type="button" onClick={() => navigate(alert.deep_link || '/approvals?tab=runtime')} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-right dark:border-slate-700 dark:bg-slate-900/30">
                      <div className="flex flex-wrap items-center gap-2">
                        <Pill cls={alert.severity === 'critical' ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'}>{formatOpsSeverity(alert.severity)}</Pill>
                        <Pill cls="bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">{formatOpsKind(alert.kind)}</Pill>
                        {alert.canonical_reason ? <Pill cls="bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200">{alert.canonical_reason}</Pill> : null}
                      </div>
                      <div className="mt-2 text-sm font-semibold text-slate-900 dark:text-white">{formatOpsReason(alert.title || alert.canonical_reason)}</div>
                      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{alert.runbook_key} · {fmtDate(alert.created_at)}</div>
                    </button>
                  ))}
                </div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
                <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">إشارات العمل دون اتصال</div>
                <div className="grid grid-cols-1 gap-3">
                  <Stat title="طلبات في الانتظار" value={localOfflineSignals.queuedRequests || 0} />
                  <Stat title="طلبات فاشلة" value={localOfflineSignals.failedRequests || 0} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
                  <Stat title="تعارضات الخلفية" value={offlineSnapshot.sync_conflict_dlq_pending || 0} tone="bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/60" />
                  <Stat title="حمولات معزولة" value={offlineSnapshot.offline_sync_quarantine_pending || 0} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
                </div>
              </div>
            </div>
          ) : null}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3 xl:grid-cols-6">
            <Stat title="طلبات معلقة" value={runtimeGovernance.pending_requests || 0} icon={Clock3} tone="bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/60" />
            <Stat title="طلبات متأخرة" value={runtimeGovernance.overdue_requests || 0} icon={AlertTriangle} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
            <Stat title="طلبات معطلة" value={runtimeGovernance.blocked_requests || 0} helper={formatLaneHealth(runtimeGovernance.severity || 'healthy')} icon={ShieldCheck} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
            <Stat title="مالية صارمة معلقة" value={runtimeGovernance.strict_finance_pending || 0} icon={ShieldCheck} tone="bg-sky-50 dark:bg-sky-950/30 border-sky-200 dark:border-sky-900/60" />
            <Stat title="تعطيل المراجعة البعيدة" value={runtimeGovernance.remote_review_posture?.blocked_requests || 0} icon={AlertTriangle} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
            <Stat title="تعطيل المرفقات" value={runtimeGovernance.attachment_runtime_posture?.quarantined || 0} helper={runtimeGovernance.request_headers?.correlation_id || 'معرّف الربط غير متاح'} icon={AlertTriangle} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Stat title="فحص معلق" value={runtimeGovernance.attachment_runtime_posture?.pending_scan || 0} helper={`نمط الفحص: ${runtimeGovernance.attachment_runtime_posture?.scan_mode === 'strict' ? 'صارم' : 'استدلالي'}`} icon={ShieldCheck} tone="bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/60" />
            <Stat title="معزول" value={runtimeGovernance.attachment_runtime_posture?.quarantined || 0} icon={AlertTriangle} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
            <Stat title="جاهز للأرشفة" value={runtimeGovernance.attachment_runtime_posture?.due_archive || 0} icon={Clock3} tone="bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-900/60" />
            <Stat title="تصعيدات المراجعة البعيدة" value={runtimeGovernance.remote_review_posture?.open_escalations || 0} icon={AlertTriangle} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
          </div>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">أسباب التعطيل</div>
              <div className="space-y-2">
                {Object.entries(runtimeGovernance.blocked_reasons || {}).length === 0 ? <div className="text-sm text-slate-500 dark:text-slate-400">لا توجد عوائق تشغيلية نشطة.</div> : Object.entries(runtimeGovernance.blocked_reasons || {}).map(([key, count]) => <div key={key} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-900/30"><span>{formatBlocker(key)}</span><Pill cls="bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">{count}</Pill></div>)}
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">تشخيص المسارات ومهلات SLA</div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                <Stat title="مسارات سليمة" value={runtimeGovernance.lane_health_totals?.healthy || 0} tone="bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-900/60" />
                <Stat title="مسارات تحتاج متابعة" value={runtimeGovernance.lane_health_totals?.attention || 0} tone="bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/60" />
                <Stat title="مسارات معطلة" value={runtimeGovernance.lane_health_totals?.blocked || 0} tone="bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60" />
              </div>
              <div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-900/30 dark:text-slate-300">
                معرّف الطلب: <span className="font-mono">{runtimeGovernance.request_headers?.request_id || 'X-Request-Id'}</span>
                <br />
                معرّف الربط: <span className="font-mono">{runtimeGovernance.request_headers?.correlation_id || 'X-Correlation-Id'}</span>
              </div>
            </div>
          </div>
          {selectedTrace ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">عارض التتبع</div>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                <div className="rounded-xl bg-slate-50 p-4 text-sm dark:bg-slate-900/30">
                  <div className="font-semibold text-slate-900 dark:text-white">معرّف الربط</div>
                  <div className="mt-2 break-all font-mono text-xs text-slate-600 dark:text-slate-300">{selectedTrace.correlation_id || '—'}</div>
                </div>
                <div className="rounded-xl bg-slate-50 p-4 text-sm dark:bg-slate-900/30">
                  <div className="font-semibold text-slate-900 dark:text-white">أحداث صندوق الإرسال المرتبطة</div>
                  <div className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">{selectedTrace.linked_outbox_events?.length || 0}</div>
                </div>
                <div className="rounded-xl bg-slate-50 p-4 text-sm dark:bg-slate-900/30">
                  <div className="font-semibold text-slate-900 dark:text-white">العوائق الحاكمة</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {selectedBlockers.length ? selectedBlockers.map((blocker) => <Pill key={`trace-${blocker}`} cls="bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">{formatBlocker(blocker)}</Pill>) : <Pill cls="bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">لا توجد عوائق</Pill>}
                  </div>
                </div>
              </div>
            </div>
          ) : null}
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-slate-900 dark:text-white">التفاصيل التشخيصية</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">تفاصيل الطلبات المعطلة مع صندوق الإرسال والمرفقات ضمن نطاق المزرعة المختارة.</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button onClick={runMaintenanceDryRun} disabled={opsActionLoading} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 dark:border-slate-700 dark:text-slate-200 disabled:opacity-60">تشغيل معاينة الصيانة</button>
                <button onClick={retrySelectedOutbox} disabled={opsActionLoading || selectedOutboxIds.length === 0} className="rounded-lg bg-sky-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-60">إعادة محاولة صندوق الإرسال ({selectedOutboxIds.length})</button>
                <button onClick={rescanSelectedAttachments} disabled={opsActionLoading || selectedAttachmentIds.length === 0} className="rounded-lg bg-amber-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-60">إعادة فحص المرفقات ({selectedAttachmentIds.length})</button>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <div className="rounded-xl border border-slate-200 dark:border-slate-700">
                <div className="border-b border-slate-200 px-4 py-3 text-sm font-semibold text-slate-900 dark:border-slate-700 dark:text-white">الاعتمادات المعطلة ({runtimeGovernanceDetail.filtered_total || 0})</div>
                <div className="max-h-80 overflow-auto">
                  {(runtimeGovernanceDetail.detail_rows || []).length === 0 ? <div className="p-4 text-sm text-slate-500 dark:text-slate-400">لا توجد صفوف تشغيلية غير سليمة حاليًا.</div> : (runtimeGovernanceDetail.detail_rows || []).map((row) => (
                    <button key={row.request_id} type="button" onClick={() => pick(row.request_id)} className="block w-full border-b border-slate-100 px-4 py-3 text-right last:border-b-0 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-900/40">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="font-semibold text-slate-900 dark:text-white">{row.farm_name} · {row.required_role_label}</div>
                        <div className="flex flex-wrap gap-2">
                          <Pill cls={HEALTH_TONE[row.lane_health] || HEALTH_TONE.healthy}>{formatLaneHealth(row.lane_health)}</Pill>
                          {row.attention_bucket ? <Pill cls="bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">{formatOpsReason(row.attention_bucket)}</Pill> : null}
                        </div>
                      </div>
                      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{row.module} / {row.action} · الاستحقاق {fmtDate(row.due_at)}</div>
                      <div className="mt-2 flex flex-wrap gap-2">{(row.blockers || []).map((blocker) => <Pill key={`${row.request_id}-${blocker}`} cls="bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">{formatBlocker(blocker)}</Pill>)}</div>
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-4">
                <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                  <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">تشخيص المزرعة</div>
                  {!farmOps ? <div className="text-sm text-slate-500 dark:text-slate-400">اختر مزرعة لعرض الأثر التشغيلي.</div> : (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <Stat title="طلبات المزرعة" value={farmOps.governance?.lane_summary?.pending_requests || 0} />
                        <Stat title="تأخر المزرعة" value={farmOps.governance?.lane_summary?.overdue_requests || 0} />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(farmOps.governance?.active_blockers || {}).length === 0 ? <Pill cls="bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">لا توجد عوائق نشطة</Pill> : Object.entries(farmOps.governance?.active_blockers || {}).map(([key, count]) => <Pill key={key} cls="bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">{formatBlocker(key)}: {count}</Pill>)}
                      </div>
                    </div>
                  )}
                </div>
                <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                  <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">تشغيل صندوق الإرسال ({outboxDetail.filtered_total || 0})</div>
                  <div className="max-h-60 overflow-auto space-y-2">
                    {(outboxDetail.detail_rows || []).length === 0 ? <div className="text-sm text-slate-500 dark:text-slate-400">لا توجد صفوف outbox مطابقة للنطاق الحالي.</div> : (outboxDetail.detail_rows || []).map((row) => (
                      <label key={row.id} className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">
                        <input type="checkbox" checked={selectedOutboxIds.includes(row.id)} onChange={() => toggleSelection(row.id, setSelectedOutboxIds)} disabled={!row.retry_eligible || opsActionLoading} className="mt-1" />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-semibold text-slate-900 dark:text-white">{row.event_type}</span>
                            <Pill cls={row.status === 'dead_letter' ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300' : 'bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300'}>{row.status}</Pill>
                          </div>
                          <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{formatBlocker(row.canonical_reason)} · ربط {row.correlation_id}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                  <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">تشغيل المرفقات ({attachmentDetail.filtered_total || 0})</div>
                  <div className="max-h-60 overflow-auto space-y-2">
                    {(attachmentDetail.detail_rows || []).length === 0 ? <div className="text-sm text-slate-500 dark:text-slate-400">لا توجد مرفقات تشغيلية تحتاج تدخلًا حاليًا.</div> : (attachmentDetail.detail_rows || []).map((row) => (
                      <label key={row.id} className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">
                        <input type="checkbox" checked={selectedAttachmentIds.includes(row.id)} onChange={() => toggleSelection(row.id, setSelectedAttachmentIds)} disabled={!row.rescan_eligible || opsActionLoading} className="mt-1" />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-semibold text-slate-900 dark:text-white">{row.name}</span>
                            <Pill cls={row.canonical_reason === 'attachment_scan_blocked' ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'}>{formatBlocker(row.canonical_reason)}</Pill>
                          </div>
                          <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{row.scan_state} · {row.archive_state} · {row.farm_name || 'غير محدد النطاق'}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {!loading && tab === 'selected' ? (
        detailLoading ? <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">جاري تحميل تفاصيل الطلب...</div> : (
          <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
            {!selected ? <div className="text-sm text-slate-500 dark:text-slate-400">اختر طلبًا من الطابور أو من لوحة القطاع.</div> : <>
              <div className="flex flex-col gap-3 border-b border-slate-100 pb-4 dark:border-slate-700 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-semibold ${STATUS_TONE[selected.status] || STATUS_TONE.PENDING}`}>{STATUS[selected.status] || selected.status}</span>
                    <Pill cls="bg-indigo-100 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300">{farmMap[selected.farm] || `مزرعة #${selected.farm}`}</Pill>
                    <Pill cls={HEALTH_TONE[selectedSnapshot.lane_health] || HEALTH_TONE.healthy}>{formatLaneHealth(selectedSnapshot.lane_health || 'healthy')}</Pill>
                    {selectedPolicy.approval_profile_source ? <Pill cls="bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">{formatPolicySource(selectedPolicy.approval_profile_source)}</Pill> : null}
                  </div>
                  <h2 className="mt-3 text-xl font-bold text-slate-900 dark:text-white">{selected.module} / {selected.action}</h2>
                  <div className="mt-1 text-sm text-slate-500 dark:text-slate-400">{selectedSnapshot.current_role_label || selected.required_role} · الاستحقاق {fmtDate(selectedSnapshot.due_at)} · المصدر {selected.object_id || '—'}</div>
                </div>
                <div className="text-left"><div className="text-2xl font-bold text-primary">{fmtMoney(selected.amount)}</div><div className="text-xs text-slate-500 dark:text-slate-400">القيمة</div></div>
              </div>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/40"><div className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">سلسلة المراحل</div><div className="space-y-2">{(selected.stage_chain || []).length ? (selected.stage_chain || []).map((s) => <div key={`${s.stage}-${s.role}`} className="flex items-center justify-between gap-3 rounded-lg bg-white px-3 py-2 text-sm dark:bg-slate-800"><span className="font-medium text-slate-900 dark:text-white">{s.label}</span><Pill>#{s.stage}</Pill></div>) : <div className="text-sm text-slate-500 dark:text-slate-400">لا توجد مراحل معروضة.</div>}</div></div>
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/40"><div className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">سياق السياسة</div><div className="grid grid-cols-1 gap-2 text-sm text-slate-700 dark:text-slate-200"><div>ملف الاعتماد: {selectedPolicy.approval_profile || '—'}</div><div>الوضع الفعّال: {selectedPolicy.effective_mode || '—'}</div><div>سبب العتبة: {selectedPolicy.threshold_reason || '—'}</div><div>المالية الصارمة مطلوبة: {formatBooleanArabic(selectedPolicy.strict_finance_required)}</div><div>عتبة المالية المحلية: {selectedPolicy.local_finance_threshold || '—'}</div><div>عتبة مراجعة القطاع: {selectedPolicy.sector_review_threshold || '—'}</div><div>معرّف الربط: {selectedTrace?.correlation_id || '—'}</div></div></div>
              </div>
              <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/40"><div className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">العوائق والخط الزمني</div><div className="mb-3 flex flex-wrap gap-2">{selectedBlockers.length ? selectedBlockers.map((b) => <Pill key={b} cls="bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">{formatBlocker(b)}</Pill>) : <Pill cls="bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">لا توجد عوائق</Pill>}</div><div className="space-y-2">{(selectedTrace?.stage_events || selected.stage_events || []).length ? (selectedTrace?.stage_events || selected.stage_events || []).map((ev) => <div key={ev.id} className="flex items-start justify-between gap-3 rounded-lg bg-white px-3 py-2 text-sm dark:bg-slate-800"><div><div className="font-semibold text-slate-900 dark:text-white">المرحلة {ev.stage_number} · {ev.role_label}</div><div className="text-slate-500 dark:text-slate-400">{ev.action_type}{ev.actor_username ? ` · ${ev.actor_username}` : ''}</div>{ev.note ? <div className="text-slate-500 dark:text-slate-400">{ev.note}</div> : null}</div><div className="text-xs text-slate-500 dark:text-slate-400">{fmtDate(ev.created_at)}</div></div>) : <div className="text-sm text-slate-500 dark:text-slate-400">لا توجد أحداث مرحلية.</div>}</div>{selectedTrace?.linked_outbox_events?.length ? <div className="mt-4 rounded-xl bg-white p-3 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">أحداث صندوق الإرسال المرتبطة: {selectedTrace.linked_outbox_events.length}</div> : null}</div>
              {(selected.status === 'PENDING' && (selected.can_current_user_approve || selected.can_current_user_override)) || (selected.status === 'REJECTED' && selected.can_current_user_reopen) ? <div className="flex flex-wrap gap-3 border-t border-slate-100 pt-4 dark:border-slate-700">{selected.status === 'PENDING' ? <button onClick={() => openModal(selected.id, 'REJECT')} className="rounded-lg border border-rose-300 bg-white px-4 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-50 dark:border-rose-900/60 dark:bg-slate-800 dark:text-rose-300">رفض</button> : null}{selected.status === 'PENDING' && selected.can_current_user_override && !selected.can_current_user_approve ? <button onClick={() => openModal(selected.id, 'OVERRIDE')} className="rounded-lg border border-amber-300 bg-white px-4 py-2 text-sm font-semibold text-amber-700 hover:bg-amber-50 dark:border-amber-900/60 dark:bg-slate-800 dark:text-amber-300">تجاوز موثق</button> : null}{selected.status === 'PENDING' && selected.can_current_user_approve ? <button onClick={() => openModal(selected.id, 'APPROVE')} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700">اعتماد/تمرير المرحلة</button> : null}{selected.status === 'REJECTED' && selected.can_current_user_reopen ? <button onClick={() => openModal(selected.id, 'REOPEN')} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">إعادة الفتح</button> : null}</div> : null}
            </>}
          </div>
        )
      ) : null}

      {modal.show ? <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4 backdrop-blur-sm"><div className="w-full max-w-md rounded-2xl bg-white shadow-xl dark:bg-slate-800"><div className={`rounded-t-2xl px-5 py-4 ${modal.action === 'APPROVE' ? 'bg-emerald-50 dark:bg-emerald-950/30' : 'bg-rose-50 dark:bg-rose-950/30'}`}><h2 className="text-lg font-bold text-slate-900 dark:text-white">{modal.action === 'APPROVE' ? 'تأكيد اعتماد/تمرير المرحلة' : modal.action === 'OVERRIDE' ? 'تأكيد تجاوز المرحلة' : modal.action === 'REOPEN' ? 'تأكيد إعادة الفتح' : 'تأكيد الرفض'}</h2></div><form onSubmit={submitAction} className="space-y-4 p-5"><div><label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200">{modal.action === 'APPROVE' ? 'ملاحظة الاعتماد (اختياري)' : modal.action === 'OVERRIDE' ? 'سبب التجاوز (مطلوب)' : modal.action === 'REOPEN' ? 'ملاحظة إعادة الفتح (اختياري)' : 'سبب الرفض (مطلوب)'}</label><textarea value={reason} onChange={(e) => setReason(e.target.value)} required={modal.action === 'OVERRIDE' || modal.action === 'REJECT'} rows={4} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none ring-0 focus:border-primary dark:border-slate-700 dark:bg-slate-900 dark:text-white" /></div><div className="flex justify-end gap-3"><button type="button" onClick={closeModal} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 dark:border-slate-700 dark:text-slate-200">إلغاء</button><button type="submit" disabled={actionLoading} className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">{actionLoading ? 'جارٍ التنفيذ...' : 'تأكيد'}</button></div></form></div></div> : null}
    </div>
  )
}



