/**
 * [AGRI-GUARDIAN] Document Cycle — سجل الإنجاز (Log History & Approval)
 *
 * Complete document lifecycle:
 *   DRAFT → SUBMITTED → APPROVED | REJECTED
 *
 * Variance workflow:
 *   OK | WARNING (needs supervisor note) | CRITICAL (needs manager approval)
 */
import { useEffect, useState, useCallback, useMemo } from 'react'
import { useAuth } from '../auth/AuthContext'
import { DailyLogs, Activities } from '../api/client'
import { useToast } from '../components/ToastProvider'
import { usePageFarmFilter } from '../hooks/usePageFarmFilter'
import PageFarmFilter from '../components/filters/PageFarmFilter'
import { useNavigate } from 'react-router-dom'
import { useSettings } from '../contexts/SettingsContext'

/* ──────────────── Constants ──────────────── */
const STATUS_LABELS = {
  DRAFT: 'مسودة',
  SUBMITTED: 'مُقدَّم',
  APPROVED: 'معتمد',
  REJECTED: 'مرفوض',
}

const STATUS_COLORS = {
  DRAFT: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  SUBMITTED: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  APPROVED: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  REJECTED: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
}

const VARIANCE_COLORS = {
  OK: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  WARNING: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  CRITICAL: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
}

const VARIANCE_ICONS = {
  OK: '✅',
  WARNING: '⚠️',
  CRITICAL: '🚨',
}

/* ──────────────── Helpers ──────────────── */
const norm = (s) => (s || '').toUpperCase()

/* ──────────────── Status Badge ──────────────── */
function StatusBadge({ status }) {
  const key = norm(status)
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_COLORS[key] || 'bg-gray-100 text-gray-600'}`}
    >
      {STATUS_LABELS[key] || status}
    </span>
  )
}

function VarianceBadge({ status }) {
  const key = norm(status)
  if (!key || key === 'OK') return null
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${VARIANCE_COLORS[key]}`}
    >
      {VARIANCE_ICONS[key]} {key}
    </span>
  )
}

/* ──────────────── Confirmation Dialog ──────────────── */
function ConfirmDialog({
  open,
  title,
  message,
  onConfirm,
  onCancel,
  children,
  confirmLabel = 'تأكيد',
  confirmColor = 'bg-primary',
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl dark:bg-slate-800">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">{title}</h3>
        {message && <p className="text-sm text-gray-600 dark:text-slate-400 mb-4">{message}</p>}
        {children}
        <div className="mt-4 flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="rounded-xl px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 transition"
          >
            إلغاء
          </button>
          <button
            onClick={onConfirm}
            className={`rounded-xl px-4 py-2 text-sm font-medium text-white ${confirmColor} hover:opacity-90 transition`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ──────────────── Activity Row ──────────────── */
function ActivityRow({ activity }) {
  const [expanded, setExpanded] = useState(false)

  const costDisplay = activity.cost_total
    ? Number(activity.cost_total).toLocaleString('en-US', { minimumFractionDigits: 2 })
    : '—'

  const hasDetails =
    activity.items?.length > 0 ||
    activity.employee_details?.length > 0 ||
    activity.asset ||
    activity.machine_details
  const workersCount = activity.worker_count || activity.employee_details?.length || 0

  return (
    <div className="flex flex-col rounded-xl border border-slate-200/70 bg-slate-50 overflow-hidden dark:border-slate-600/50 dark:bg-slate-700/40">
      <div
        className={`flex items-center justify-between px-4 py-3 ${hasDetails ? 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-600/50' : ''}`}
        onClick={() => hasDetails && setExpanded(!expanded)}
      >
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-semibold text-gray-800 dark:text-slate-200">
            {activity.task_name || activity.task?.name || `مهمة #${activity.task}`}
          </span>
          <span className="text-xs text-gray-500 dark:text-slate-400">
            {activity.location_name || activity.location?.name || (activity.location != null ? `موقع #${activity.location}` : '')}
            {activity.crop_name ? ` • ${activity.crop_name}` : ''}
          </span>
          {activity.activity_notes && (
            <span className="text-xs text-gray-400 dark:text-slate-500 mt-1 italic">
              {activity.activity_notes}
            </span>
          )}
        </div>
        <div className="flex flex-col items-end gap-0.5">
          <span className="text-sm font-bold text-emerald-700 dark:text-emerald-400 font-mono">
            {costDisplay} ر.ي
          </span>
          <div className="flex gap-2 items-center">
            {workersCount > 0 && (
              <span className="text-xs text-gray-500 dark:text-slate-400">
                👷 {workersCount} عامل
              </span>
            )}
            {hasDetails && (
              <span className="text-xs text-primary font-bold">{expanded ? '▲' : '▼'}</span>
            )}
          </div>
        </div>
      </div>

      {expanded && hasDetails && (
        <div className="bg-white px-4 py-3 border-t border-slate-100 dark:bg-slate-800 dark:border-slate-600/50 flex flex-col gap-3">
          {activity.employee_details?.length > 0 && (
            <div>
              <p className="font-semibold text-gray-700 dark:text-slate-300 text-xs mb-1 flex items-center gap-1">
                👥 تفاصيل العمالة
              </p>
              <ul className="list-disc list-inside text-gray-600 dark:text-slate-400 text-xs space-y-0.5">
                {activity.employee_details.map((emp) => (
                  <li key={emp.id}>
                    {emp.employee_name || emp.labor_batch_label || `عامل #${emp.employee}`}
                    {' - '}
                    <span className="text-gray-500">
                      {emp.labor_type === 'SURRAH' ? 'سرة' : 'يومية'}
                    </span>
                    {' ('}
                    <span className="font-mono text-emerald-600 dark:text-emerald-400">
                      {emp.wage_cost} ر.ي
                    </span>
                    {')'}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {activity.items?.length > 0 && (
            <div>
              <p className="font-semibold text-gray-700 dark:text-slate-300 text-xs mb-1 flex items-center gap-1">
                📦 المواد والمستهلكات
              </p>
              <ul className="list-disc list-inside text-gray-600 dark:text-slate-400 text-xs space-y-0.5">
                {activity.items.map((item) => (
                  <li key={item.id}>
                    {item.item_name || `مادة #${item.item}`}
                    {' - '}
                    <span className="text-gray-500">
                      {item.qty} {item.uom}
                    </span>
                    {' ('}
                    <span className="font-mono text-emerald-600 dark:text-emerald-400">
                      {item.total_cost || 0} ر.ي
                    </span>
                    {')'}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(activity.asset || activity.machine_details) && (
            <div>
              <p className="font-semibold text-gray-700 dark:text-slate-300 text-xs mb-1 flex items-center gap-1">
                🚜 المعدات والآليات
              </p>
              <ul className="list-disc list-inside text-gray-600 dark:text-slate-400 text-xs space-y-0.5">
                {activity.asset && (
                  <li>
                    الآلة: <span className="text-gray-500">{activity.asset.name}</span>
                  </li>
                )}
                {activity.machine_details && (
                  <li>
                    ساعات التشغيل:{' '}
                    <span className="font-mono">{activity.machine_details.machine_hours || 0}</span>
                    {activity.machine_details.fuel_consumed ? ` | الوقود المستهلك: ` : ''}
                    {activity.machine_details.fuel_consumed ? (
                      <span className="font-mono">{activity.machine_details.fuel_consumed}</span>
                    ) : (
                      ''
                    )}
                  </li>
                )}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ──────────────── Log Timeline (Audit Trail) ──────────────── */
function LogTimeline({ log }) {
  const events = []

  if (log.created_at) {
    events.push({
      id: 'created',
      title: 'تم الإنشاء',
      actor: log.created_by_name || log.created_by || 'النظام',
      date: log.created_at,
      color: 'bg-gray-400',
    })
  }

  if (log.status !== 'DRAFT' && log.updated_at) {
    events.push({
      id: 'submitted',
      title: log.status === 'REJECTED' && !log.approved_at ? 'تم التقديم' : 'قُدم للاعتماد',
      actor: log.updated_by_name || log.updated_by || 'النظام',
      date: log.status === 'SUBMITTED' ? log.updated_at : log.created_at,
      color: 'bg-blue-500',
    })
  }

  if (log.status === 'REJECTED') {
    events.push({
      id: 'rejected',
      title: 'تم الرفض',
      actor: log.approved_by_name || log.approved_by || 'المشرف',
      date: log.updated_at,
      color: 'bg-red-500',
      note: log.rejection_reason,
    })
  }

  // [AGRI-GUARDIAN FIX] Gap 20: Show correction history trail
  const corrections = log.metadata?.correction_history || []
  corrections.forEach((entry, idx) => {
    events.push({
      id: `correction-${idx}`,
      title: `🔄 إعادة فتح (تعديل #${idx + 1})`,
      actor: entry.reopened_by_name || `مستخدم #${entry.reopened_by}`,
      date: entry.reopened_at,
      color: 'bg-purple-500',
      note: entry.previous_rejection_reason
        ? `السبب السابق: ${entry.previous_rejection_reason}`
        : null,
    })
  })

  if (log.status === 'APPROVED' && log.approved_at) {
    events.push({
      id: 'approved',
      title: 'تم الاعتماد',
      actor: log.approved_by_name || log.approved_by || 'المدير',
      date: log.approved_at,
      color: 'bg-emerald-500',
    })
  }

  // Sort chronologically
  events.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

  if (events.length === 0) return null

  return (
    <div className="mt-2 mb-2 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200/60 dark:border-slate-700">
      <h4 className="text-xs font-bold text-gray-700 dark:text-slate-300 mb-4 px-1 flex items-center gap-1">
        ⏱️ التتبع الزمني (Timeline)
      </h4>
      <div className="relative border-r-2 border-slate-300 dark:border-slate-600 pr-4 ml-2">
        {events.map((ev, idx) => (
          <div key={`${ev.id}-${idx}`} className="mb-4 relative last:mb-0">
            <div
              className={`absolute -right-[21px] top-1 w-3 h-3 rounded-full ${ev.color} border-2 border-white dark:border-slate-800`}
            ></div>
            <div className="text-xs">
              <span className="font-semibold text-gray-800 dark:text-slate-200">{ev.title}</span>
              <span className="text-gray-500 dark:text-slate-400 mr-1">بواسطة {ev.actor}</span>
            </div>
            {ev.date && (
              <div className="text-[10px] text-gray-400 dark:text-slate-500 mt-0.5 font-mono">
                {new Date(ev.date).toLocaleString('ar-SA')}
              </div>
            )}
            {ev.note && (
              <div className="mt-1.5 text-xs bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400 p-2 rounded-lg border border-red-200 dark:border-red-500/30">
                <span className="font-semibold">السبب:</span> {ev.note}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

/* ──────────────── Log Detail Panel ──────────────── */
export function LogDetailPanel({ log, onAction, loading, getFarmName }) {
  const [activities, setActivities] = useState([])
  const [loadingAct, setLoadingAct] = useState(false)
  const [dialog, setDialog] = useState(null)
  const [dialogInput, setDialogInput] = useState('')
  const { isAdmin, is_superuser, hasFarmRole } = useAuth()
  const { isStrictMode = false } = useSettings?.() || {}
  const canApprove = useMemo(() => {
    const managerialRoles = [
      'مدير المزرعة',
      'مدير النظام',
      'رئيس الحسابات',
      'المدير المالي للمزرعة',
      'محاسب القطاع',
      'مراجع القطاع',
      'رئيس حسابات القطاع',
      'المدير المالي لقطاع المزارع',
      'مدير القطاع',
      'مشرف ميداني',
    ]
    return isAdmin || is_superuser || managerialRoles.some((role) => hasFarmRole(role))
  }, [hasFarmRole, isAdmin, is_superuser])
  const logStatus = norm(log?.status)
  const logVariance = norm(log?.variance_status)

  useEffect(() => {
    if (!log?.id) return
    setLoadingAct(true)
    Activities.list({ log: log.id })
      .then((res) => setActivities(res.data?.results || res.data || []))
      .catch(() => setActivities([]))
      .finally(() => setLoadingAct(false))
  }, [log?.id])

  const handleAction = (action) => {
    if (action === 'reject') {
      setDialog({ action: 'reject', title: 'رفض السجل', message: 'يرجى إدخال سبب الرفض:' })
      setDialogInput('')
    } else if (action === 'warningNote') {
      setDialog({
        action: 'warningNote',
        title: 'ملاحظة تحذيرية',
        message: 'يرجى إدخال ملاحظة المشرف على الانحراف:',
      })
      setDialogInput('')
    } else if (action === 'approveVariance') {
      setDialog({
        action: 'approveVariance',
        title: 'اعتماد الانحراف',
        message: 'يرجى إدخال ملاحظة المدير لاعتماد الانحراف الحرج:',
      })
      setDialogInput('')
    } else {
      onAction(action, log.id)
    }
  }

  const confirmDialog = () => {
    if (!dialog) return
    onAction(dialog.action, log.id, dialogInput)
    setDialog(null)
    setDialogInput('')
  }

  if (!log) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-400 dark:text-slate-500">
        <span className="text-sm">← اختر سجلاً لعرض التفاصيل</span>
      </div>
    )
  }

  const totalCost = activities.reduce((sum, a) => sum + (Number(a.cost_total) || 0), 0)
  const governanceBlocked =
    Boolean(log?.ghost_cost_blocked) ||
    Boolean(log?.missing_price_governance) ||
    Boolean(log?.material_governance_blocked)
  const governanceReason =
    log?.ghost_cost_blocked
      ? (log?.ghost_cost_reasons?.[0] || 'يوجد تنفيذ فعلي لكن التكلفة غير مكتملة')
      : log?.missing_price_governance
        ? (isStrictMode ? 'الاعتماد محجوب حتى اكتمال حوكمة الأسعار في الوضع الصارم' : 'الاعتماد محجوب حتى اكتمال حوكمة الأسعار')
        : log?.material_governance_blocked
          ? 'الاعتماد محجوب حتى اكتمال حوكمة المواد والتشغيلة'
          : 'اعتماد السجل'

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">📋 سجل {log.log_date}</h3>
          <p className="text-sm text-gray-500 dark:text-slate-400">
            {getFarmName ? getFarmName(log) : log.farm_name || `مزرعة #${log.farm}`}
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <StatusBadge status={log.status} />
          <VarianceBadge status={log.variance_status} />
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl bg-blue-50 p-3 text-center dark:bg-blue-900/20">
          <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
            {activities.length}
          </div>
          <div className="text-xs text-blue-600 dark:text-blue-400">أنشطة</div>
        </div>
        <div className="rounded-xl bg-emerald-50 p-3 text-center dark:bg-emerald-900/20">
          <div className="text-lg font-bold text-emerald-700 dark:text-emerald-300 font-mono">
            {totalCost.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-xs text-emerald-600 dark:text-emerald-400">إجمالي التكلفة (ر.ي)</div>
        </div>
        <div className="rounded-xl bg-purple-50 p-3 text-center dark:bg-purple-900/20">
          <div className="text-2xl font-bold text-purple-700 dark:text-purple-300">
            {activities.reduce(
              (sum, a) => sum + (Number(a.worker_count) || a.employee_details?.length || 0),
              0,
            )}
          </div>
          <div className="text-xs text-purple-600 dark:text-purple-400">عمال</div>
        </div>
      </div>

      {/* Variance Alert */}
      {logVariance === 'WARNING' && (
        <div className="rounded-xl border-l-4 border-yellow-400 bg-yellow-50 p-3 dark:border-yellow-500 dark:bg-yellow-900/20">
          <p className="text-sm font-semibold text-yellow-800 dark:text-yellow-300">
            ⚠️ انحراف تحذيري
          </p>
          {log.variance_note && (
            <p className="text-xs text-yellow-700 dark:text-yellow-400 mt-1">{log.variance_note}</p>
          )}
        </div>
      )}
      {logVariance === 'CRITICAL' && (
        <div className="rounded-xl border-l-4 border-red-400 bg-red-50 p-3 dark:border-red-500 dark:bg-red-900/20">
          <p className="text-sm font-semibold text-red-800 dark:text-red-300">
            🚨 انحراف حرج — يتطلب اعتماد مدير
          </p>
          {log.variance_note && (
            <p className="text-xs text-red-700 dark:text-red-400 mt-1">{log.variance_note}</p>
          )}
        </div>
      )}

      {/* Rejection Reason */}
      {logStatus === 'REJECTED' && log.rejection_reason && (
        <div className="rounded-xl border-l-4 border-red-400 bg-red-50 p-3 dark:border-red-500 dark:bg-red-900/20">
          <p className="text-sm font-semibold text-red-800 dark:text-red-300">سبب الرفض:</p>
          <p className="text-sm text-red-700 dark:text-red-400 mt-1">{log.rejection_reason}</p>
        </div>
      )}

      {/* Activities List */}
      <div>
        <h4 className="text-sm font-bold text-gray-700 dark:text-slate-300 mb-2">الأنشطة</h4>
        {loadingAct ? (
          <div className="text-sm text-gray-400 animate-pulse">جارٍ التحميل...</div>
        ) : activities.length === 0 ? (
          <div className="text-sm text-gray-400 dark:text-slate-500">لا توجد أنشطة مسجلة</div>
        ) : (
          <div className="flex flex-col gap-2">
            {activities.map((a) => (
              <ActivityRow key={a.id} activity={a} />
            ))}
          </div>
        )}
      </div>

      {/* Notes */}
      {log.notes && (
        <div className="rounded-xl bg-gray-50 p-3 dark:bg-slate-700/50">
          <p className="text-xs font-semibold text-gray-500 dark:text-slate-400 mb-1">ملاحظات</p>
          <p className="text-sm text-gray-700 dark:text-slate-300">{log.notes}</p>
        </div>
      )}

      {/* Log Timeline (Audit Trail) replaces basic Approval Info */}
      <LogTimeline log={log} />

      {/* [DOCUMENT CYCLE] Workflow Action Buttons */}
      <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-200 dark:border-slate-700">
        {/* DRAFT → Submit */}
        {logStatus === 'DRAFT' && (
          <button
            onClick={() => handleAction('submit')}
            disabled={loading}
            className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition disabled:opacity-50"
          >
            📤 تقديم للاعتماد
          </button>
        )}

        {/* SUBMITTED → Approve / Reject (Supervisor only) */}
        {logStatus === 'SUBMITTED' && canApprove && (
          <>
            <button
              data-testid="dailylog-approve-button"
              onClick={() => handleAction('approve')}
              disabled={
                loading ||
                governanceBlocked ||
                (logVariance === 'WARNING' && !log.variance_note) ||
                (logVariance === 'CRITICAL' && !log.variance_approved_by)
              }
              title={
                governanceBlocked
                  ? governanceReason
                  : logVariance === 'WARNING' && !log.variance_note
                    ? 'يجب إضافة ملاحظة المشرف لتبرير الانحراف التحذيري'
                    : logVariance === 'CRITICAL' && !log.variance_approved_by
                      ? 'يتطلب اعتماد الانحراف الحرج من المدير أولاً'
                      : 'اعتماد السجل'
              }
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              ✅ اعتماد
            </button>
            <button
              data-testid="dailylog-reject-button"
              onClick={() => handleAction('reject')}
              disabled={loading}
              className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 transition disabled:opacity-50"
            >
              ❌ رفض
            </button>
          </>
        )}

        {/* Variance: WARNING → Note */}
        {logVariance === 'WARNING' && !log.variance_note && canApprove && (
          <button
            data-testid="dailylog-warning-note-button"
            onClick={() => handleAction('warningNote')}
            disabled={loading}
            className="rounded-xl bg-yellow-500 px-4 py-2 text-sm font-semibold text-white hover:bg-yellow-600 transition disabled:opacity-50"
          >
            📝 إضافة ملاحظة تحذيرية
          </button>
        )}

        {/* Variance: CRITICAL → Manager Approval */}
        {logVariance === 'CRITICAL' && !log.variance_approved_by && canApprove && (
          <button
            data-testid="dailylog-approve-variance-button"
            onClick={() => handleAction('approveVariance')}
            disabled={loading}
            className="rounded-xl bg-orange-600 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-700 transition disabled:opacity-50"
          >
            🔐 اعتماد الانحراف
          </button>
        )}

        {/* REJECTED → Reopen & Edit (Creator or Supervisor) */}
        {logStatus === 'REJECTED' && (
          <div className="flex flex-col gap-2 w-full">
            {/* [AGRI-GUARDIAN FIX] Correction History Badge */}
            {log.correction_count > 0 && (
              <div className="text-xs bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 px-3 py-1.5 rounded-lg border border-purple-200 dark:border-purple-700/40">
                🔄 تم تعديل هذا السجل{' '}
                <span className="font-bold font-mono">{log.correction_count}</span> مرة سابقاً
              </div>
            )}
            <button
              data-testid="dailylog-reopen-button"
              onClick={() => handleAction('reopen')}
              disabled={loading}
              title="يمكن لمنشئ السجل أو المشرف فقط إعادة فتح السجل المرفوض"
              className="rounded-xl bg-purple-600 px-4 py-2 text-sm font-semibold text-white hover:bg-purple-700 transition disabled:opacity-50"
            >
              ✏️ إعادة فتح وتعديل السجل المرفوض
            </button>
          </div>
        )}
      </div>

      {/* Dialogs */}
      <ConfirmDialog
        open={!!dialog}
        title={dialog?.title || ''}
        message={dialog?.message || ''}
        onConfirm={confirmDialog}
        onCancel={() => {
          setDialog(null)
          setDialogInput('')
        }}
        confirmLabel={dialog?.action === 'reject' ? 'رفض' : 'تأكيد'}
        confirmColor={dialog?.action === 'reject' ? 'bg-red-600' : 'bg-primary'}
      >
        <textarea
          value={dialogInput}
          onChange={(e) => setDialogInput(e.target.value)}
          className="w-full rounded-xl border border-gray-300 p-3 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white focus:ring-2 focus:ring-primary/30"
          rows={3}
          placeholder="اكتب هنا..."
          dir="rtl"
        />
      </ConfirmDialog>
    </div>
  )
}

/* ──────────────── Main Component ──────────────── */
export default function DailyLogHistory() {
  const { user } = useAuth()
  const {
    farmId: selectedFarmId,
    setFarmId: setSelectedFarmId,
    farmOptions: farms,
    canUseAll,
    effectiveFarmScope,
  } = usePageFarmFilter({
    storageKey: 'page_farm.daily_log_history',
    allowAllForAdmin: true,
    defaultPolicy: 'first',
  })
  const addToast = useToast()
  const navigate = useNavigate()

  const getFarmName = useCallback(
    (log) => {
      if (!log) return ''
      if (log.farm_name) return log.farm_name
      const farm = farms?.find((f) => String(f.id) === String(log.farm))
      return farm ? farm.name : `مزرعة #${log.farm}`
    },
    [farms],
  )

  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [selectedLog, setSelectedLog] = useState(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [dateRange, setDateRange] = useState({ from: '', to: '' })
  const [searchText, setSearchText] = useState('')

  const fetchLogs = useCallback(async () => {
    if (!user) return
    setLoading(true)
    try {
      const params = {}
      if (effectiveFarmScope) params.farm = effectiveFarmScope
      if (statusFilter) params.status = statusFilter
      if (dateRange.from) params.log_date__gte = dateRange.from
      if (dateRange.to) params.log_date__lte = dateRange.to

      const res = await DailyLogs.list(params)
      setLogs(res.data?.results || res.data || [])
    } catch (err) {
      console.error('Failed to load logs', err)
      addToast('فشل تحميل السجلات', 'error')
    } finally {
      setLoading(false)
    }
  }, [user, effectiveFarmScope, statusFilter, dateRange, addToast])

  // Auto-fetch when date range changes
  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  useEffect(() => {
    const handleDailyLogSynced = (event) => {
      const syncedRows = Array.isArray(event?.detail?.syncedDailyLogs)
        ? event.detail.syncedDailyLogs
        : []
      if (!syncedRows.length) return

      const matchesCurrentScope = syncedRows.some((row) => {
        const farmMatches =
          !effectiveFarmScope ||
          String(row.farmId || row.farm_id || '') === String(effectiveFarmScope)
        const date = row.date || row.log_date || ''
        const fromMatches = !dateRange.from || !date || date >= dateRange.from
        const toMatches = !dateRange.to || !date || date <= dateRange.to
        return farmMatches && fromMatches && toMatches
      })

      if (matchesCurrentScope) {
        fetchLogs()
      }
    }

    window.addEventListener('offline-daily-log-synced', handleDailyLogSynced)
    return () => window.removeEventListener('offline-daily-log-synced', handleDailyLogSynced)
  }, [dateRange.from, dateRange.to, effectiveFarmScope, fetchLogs])

  // Workflow action handler
  const handleAction = useCallback(
    async (action, logId, note = '') => {
      setActionLoading(true)
      try {
        switch (action) {
          case 'submit':
            await DailyLogs.submit(logId)
            addToast('تم تقديم السجل للاعتماد', 'success')
            break
          case 'approve':
            await DailyLogs.approve(logId)
            addToast('تم اعتماد السجل بنجاح ✅', 'success')
            break
          case 'reject':
            if (!note.trim()) {
              addToast('يرجى إدخال سبب الرفض', 'error')
              setActionLoading(false)
              return
            }
            await DailyLogs.reject(logId, note)
            addToast('تم رفض السجل', 'warning')
            break
          case 'warningNote':
            if (!note.trim()) {
              addToast('يرجى إدخال الملاحظة', 'error')
              setActionLoading(false)
              return
            }
            await DailyLogs.warningNote(logId, note)
            addToast('تم حفظ ملاحظة الانحراف', 'success')
            break
          case 'approveVariance':
            if (!note.trim()) {
              addToast('يرجى إدخال ملاحظة الاعتماد', 'error')
              setActionLoading(false)
              return
            }
            await DailyLogs.approveVariance(logId, note)
            addToast('تم اعتماد الانحراف الحرج', 'success')
            break
          case 'reopen':
            await DailyLogs.reopen(logId)
            addToast('تم إعادة فتح السجل. جاري تحويلك لصفحة التعديل...', 'success')
            // Navigate to DailyLog wizard with this draft ID
            setTimeout(() => {
              navigate(`/daily-log?draftId=${logId}`)
            }, 1000)
            break
          default:
            break
        }
        // Refresh after action
        await fetchLogs()
        // Update selected log
        const updated = await DailyLogs.get(logId)
        setSelectedLog(updated.data)
      } catch (err) {
        const errData = err?.response?.data
        const httpStatus = err?.response?.status

        // [AGRI-GUARDIAN FIX] Gap 19: Specific permission denied message
        if (httpStatus === 403) {
          const permMsg =
            errData?.detail ||
            'ليس لديك صلاحية لتنفيذ هذا الإجراء. إعادة فتح السجل مسموح فقط لمنشئ السجل أو المشرفين.'
          addToast(`🔒 ${permMsg}`, 'error')
          setActionLoading(false)
          return
        }

        // Extract Arabic error detail from DRF response, handling nested objects/arrays robustly
        let msg = 'حدث خطأ أثناء تنفيذ الإجراء'
        if (errData) {
          const extractMessage = (data) => {
            if (typeof data === 'string') {
              // Clean up python stringified arrays like "['لا يمكنك اعتماد...']"
              const match = data.match(/^\[['"](.*)['"]\]$/)
              return match ? match[1] : data
            }
            if (Array.isArray(data)) {
              return data.map(extractMessage).filter(Boolean).join(' | ')
            }
            if (typeof data === 'object' && data !== null) {
              const parts = []
              for (const [key, val] of Object.entries(data)) {
                const valStr = extractMessage(val)
                if (valStr) {
                  parts.push(
                    key === 'non_field_errors' || key === 'detail' || key === 'error'
                      ? valStr
                      : `${key}: ${valStr}`,
                  )
                }
              }
              return parts.join(' | ')
            }
            return String(data)
          }

          const extracted = extractMessage(errData)
          if (extracted) {
            msg = extracted
          }
        }
        // Refetch log data so variance_status (updated by backend) reflects in UI
        try {
          const refreshed = await DailyLogs.get(logId)
          setSelectedLog(refreshed.data)
        } catch (_) {
          /* ignore refetch errors */
        }
        addToast(msg, 'error')
        console.error('خطأ في الإجراء:', msg)
      } finally {
        setActionLoading(false)
      }
    },
    [fetchLogs, addToast, navigate],
  )

  // Stats
  const stats = useMemo(() => {
    const s = { total: logs.length, DRAFT: 0, SUBMITTED: 0, APPROVED: 0, REJECTED: 0 }
    logs.forEach((l) => {
      const k = norm(l.status)
      if (s[k] !== undefined) s[k]++
    })
    return s
  }, [logs])

  // Client-side search filter (on top of server-side filters)
  const filteredLogs = useMemo(() => {
    if (!searchText.trim()) return logs
    const q = searchText.trim().toLowerCase()
    return logs.filter(
      (l) =>
        (l.log_date || '').includes(q) ||
        (l.farm_name || getFarmName(l) || '').toLowerCase().includes(q) ||
        (l.notes || '').toLowerCase().includes(q) ||
        (l.created_by_name || '').toLowerCase().includes(q),
    )
  }, [logs, searchText, getFarmName])

  return (
    <div className="space-y-4" dir="rtl">
      {/* Page Title */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          📋 سجل الإنجاز — الدورة المستندية
        </h1>
        <PageFarmFilter
          value={selectedFarmId}
          onChange={setSelectedFarmId}
          options={farms}
          canUseAll={canUseAll}
          testId="daily-log-history-farm-filter"
          className="min-w-[220px]"
        />
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="rounded-xl bg-gray-50 p-3 text-center dark:bg-slate-800">
          <div className="text-xl font-bold text-gray-700 dark:text-slate-200">{stats.total}</div>
          <div className="text-xs text-gray-500 dark:text-slate-400">الكل</div>
        </div>
        <div
          className={`rounded-xl p-3 text-center cursor-pointer transition ${statusFilter === 'DRAFT' ? 'ring-2 ring-amber-400' : ''} bg-amber-50 dark:bg-amber-900/20`}
          onClick={() => setStatusFilter(statusFilter === 'DRAFT' ? '' : 'DRAFT')}
        >
          <div className="text-xl font-bold text-amber-700 dark:text-amber-300">{stats.DRAFT}</div>
          <div className="text-xs text-amber-600 dark:text-amber-400">🟡 مسودة</div>
        </div>
        <div
          className={`rounded-xl p-3 text-center cursor-pointer transition ${statusFilter === 'SUBMITTED' ? 'ring-2 ring-blue-400' : ''} bg-blue-50 dark:bg-blue-900/20`}
          onClick={() => setStatusFilter(statusFilter === 'SUBMITTED' ? '' : 'SUBMITTED')}
        >
          <div className="text-xl font-bold text-blue-700 dark:text-blue-300">
            {stats.SUBMITTED}
          </div>
          <div className="text-xs text-blue-600 dark:text-blue-400">🔵 مُقدَّم</div>
        </div>
        <div
          className={`rounded-xl p-3 text-center cursor-pointer transition ${statusFilter === 'APPROVED' ? 'ring-2 ring-emerald-400' : ''} bg-emerald-50 dark:bg-emerald-900/20`}
          onClick={() => setStatusFilter(statusFilter === 'APPROVED' ? '' : 'APPROVED')}
        >
          <div className="text-xl font-bold text-emerald-700 dark:text-emerald-300">
            {stats.APPROVED}
          </div>
          <div className="text-xs text-emerald-600 dark:text-emerald-400">🟢 معتمد</div>
        </div>
        <div
          className={`rounded-xl p-3 text-center cursor-pointer transition ${statusFilter === 'REJECTED' ? 'ring-2 ring-red-400' : ''} bg-red-50 dark:bg-red-900/20`}
          onClick={() => setStatusFilter(statusFilter === 'REJECTED' ? '' : 'REJECTED')}
        >
          <div className="text-xl font-bold text-red-700 dark:text-red-300">{stats.REJECTED}</div>
          <div className="text-xs text-red-600 dark:text-red-400">🔴 مرفوض</div>
        </div>
      </div>

      {/* Date + Search Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-gray-600 dark:text-slate-400">من:</label>
          <input
            type="date"
            value={dateRange.from}
            onChange={(e) => setDateRange((p) => ({ ...p, from: e.target.value }))}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-gray-600 dark:text-slate-400">إلى:</label>
          <input
            type="date"
            value={dateRange.to}
            onChange={(e) => setDateRange((p) => ({ ...p, to: e.target.value }))}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
          />
        </div>
        {/* Search */}
        <div className="flex-1 min-w-[180px]">
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="🔍 بحث بالتاريخ / المزرعة / المنشئ..."
            className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
          />
        </div>
        {(statusFilter || dateRange.from || dateRange.to || searchText) && (
          <button
            onClick={() => {
              setStatusFilter('')
              setDateRange({ from: '', to: '' })
              setSearchText('')
            }}
            className="text-xs text-primary hover:underline"
          >
            مسح الفلاتر
          </button>
        )}
      </div>

      {/* Main Content: List + Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Log List */}
        <div className="lg:col-span-2 flex flex-col gap-2 max-h-[70vh] overflow-y-auto rounded-2xl border border-gray-200 bg-white p-3 shadow-sm dark:border-slate-700 dark:bg-slate-800">
          {loading ? (
            <div className="flex h-32 items-center justify-center">
              <div className="text-sm text-gray-400 animate-pulse">جارٍ تحميل السجلات...</div>
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="flex h-32 flex-col items-center justify-center gap-1 text-sm text-gray-400 dark:text-slate-500">
              <span>لا توجد سجلات{searchText ? ' تطابق البحث' : ''}</span>
              {searchText && (
                <button onClick={() => setSearchText('')} className="text-xs text-primary hover:underline">مسح البحث</button>
              )}
            </div>
          ) : (
            filteredLogs.map((log) => {
              const activityCount = log.activity_count ?? log.activities_count ?? null
              const isEmptyDraft = norm(log.status) === 'DRAFT' && activityCount === 0
              return (
              <button
                key={log.id}
                onClick={() => setSelectedLog(log)}
                className={`w-full text-start rounded-xl border p-3 transition-all ${
                  selectedLog?.id === log.id
                    ? 'border-primary bg-primary/5 shadow-md dark:bg-primary/10'
                    : 'border-gray-200 bg-gray-50 hover:border-primary/40 hover:bg-primary/5 dark:border-slate-600 dark:bg-slate-700/50 dark:hover:bg-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-bold text-gray-800 dark:text-slate-200">
                    📅 {log.log_date}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {isEmptyDraft && (
                      <span className="text-[10px] text-amber-600 bg-amber-50 dark:bg-amber-900/20 px-1.5 py-0.5 rounded-full border border-amber-200 dark:border-amber-700"
                        title="مسودة فارغة — لم يتم حفظ أي نشاط بعد">
                        فارغة
                      </span>
                    )}
                    <StatusBadge status={log.status} />
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 dark:text-slate-400">
                    {getFarmName(log)}
                  </span>
                  <div className="flex items-center gap-2">
                    {activityCount !== null && (
                      <span className="text-xs font-medium text-blue-600 dark:text-blue-400">
                        ⚡ {activityCount} نشاط
                      </span>
                    )}
                    <VarianceBadge status={log.variance_status} />
                  </div>
                </div>
                {/* Creator + time */}
                {log.created_by_name && (
                  <div className="mt-1 text-[10px] text-gray-400 dark:text-slate-500">
                    بواسطة {log.created_by_name}
                    {log.created_at && (
                      <span className="mr-1 font-mono">
                        — {new Date(log.created_at).toLocaleString('ar-SA', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })}
                      </span>
                    )}
                  </div>
                )}
              </button>
              )
            })
          )}
        </div>

        {/* Detail Panel */}
        <div className="lg:col-span-3 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
          <LogDetailPanel
            log={selectedLog}
            onAction={handleAction}
            loading={actionLoading}
            getFarmName={getFarmName}
          />
        </div>
      </div>
    </div>
  )
}
