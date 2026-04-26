/**
 * [AGRI-GUARDIAN Phase 4] LiveNotificationToast
 *
 * Surfaces real-time SSE events (useNotifications) as animated toast banners.
 * Shows on: approval_pending, approval_runtime_attention, attachment_runtime_attention,
 *           outbox_dead_letter_attention, release_health_warning.
 *
 * Requires: useNotifications hook, useAuth, react-router navigate
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, Bell, CheckCircle, X, ShieldAlert } from 'lucide-react'
import { useSettings } from '../contexts/SettingsContext.jsx'
import { useOpsRuntime } from '../contexts/OpsRuntimeContext.jsx'

const TOAST_TTL_MS = 6000 // auto-dismiss

const TOAST_STYLES = {
  critical: {
    border: 'border-rose-500',
    bg: 'bg-rose-50 dark:bg-rose-950/80',
    text: 'text-rose-800 dark:text-rose-200',
    icon: <ShieldAlert className="h-5 w-5 text-rose-500" />,
  },
  attention: {
    border: 'border-amber-400',
    bg: 'bg-amber-50 dark:bg-amber-950/80',
    text: 'text-amber-800 dark:text-amber-200',
    icon: <AlertTriangle className="h-5 w-5 text-amber-500" />,
  },
  info: {
    border: 'border-sky-400',
    bg: 'bg-sky-50 dark:bg-sky-950/80',
    text: 'text-sky-800 dark:text-sky-200',
    icon: <Bell className="h-5 w-5 text-sky-500" />,
  },
  success: {
    border: 'border-emerald-400',
    bg: 'bg-emerald-50 dark:bg-emerald-950/80',
    text: 'text-emerald-800 dark:text-emerald-200',
    icon: <CheckCircle className="h-5 w-5 text-emerald-500" />,
  },
}

function resolveToastLevel(runtimeAlerts, approvalCount) {
  const toasts = []

  // Pending approvals counter
  if (approvalCount > 0) {
    toasts.push({
      id: 'approval_pending',
      level: 'info',
      title: 'طلبات اعتماد بانتظارك',
      body: `لديك ${approvalCount} طلب معلق في قائمة الانتظار.`,
      link: '/approvals?tab=queue',
    })
  }

  // Runtime attention events
  const levelMap = {
    approval: { level: 'attention', title: 'تنبيه اعتمادات', link: '/approvals?tab=runtime' },
    attachment: { level: 'attention', title: 'تنبيه مرفقات', link: '/approvals?tab=runtime' },
    outbox: { level: 'critical', title: 'رسائل Outbox ميتة', link: '/approvals?tab=runtime' },
    release: { level: 'critical', title: 'تحذير صحة الإصدار', link: '/approvals?tab=runtime' },
    offline: { level: 'attention', title: 'تنبيه مزامنة دون اتصال', link: '/approvals?tab=runtime' },
  }

  for (const [key, meta] of Object.entries(levelMap)) {
    const alert = runtimeAlerts[key]
    if (alert?.fingerprint) {
      toasts.push({
        id: `runtime_${key}_${alert.fingerprint}`,
        level: alert.severity === 'critical' ? 'critical' : meta.level,
        title: meta.title,
        body: alert.title || alert.canonical_reason || 'حدث يستدعي المراجعة',
        link: meta.link,
      })
    }
  }

  return toasts
}

export default function LiveNotificationToast() {
  const navigate = useNavigate()
  const { isStrictMode } = useSettings()
  const { runtimeAlerts, approvalCount, isConnected } = useOpsRuntime()

  const [toastQueue, setToastQueue] = useState([])
  const seenIds = useRef(new Set())
  const timers = useRef({})

  // Build toasts whenever SSE data changes
  useEffect(() => {
    if (!isStrictMode) return
    const candidates = resolveToastLevel(runtimeAlerts, approvalCount)
    for (const toast of candidates) {
      if (seenIds.current.has(toast.id)) continue
      seenIds.current.add(toast.id)
      setToastQueue((prev) => [...prev, toast])
      timers.current[toast.id] = setTimeout(() => dismiss(toast.id), TOAST_TTL_MS)
    }
  }, [runtimeAlerts, approvalCount, isStrictMode]) // eslint-disable-line react-hooks/exhaustive-deps

  const dismiss = (id) => {
    clearTimeout(timers.current[id])
    delete timers.current[id]
    setToastQueue((prev) => prev.filter((t) => t.id !== id))
  }

  if (!isStrictMode || toastQueue.length === 0) return null

  return (
    <div
      className="fixed bottom-4 left-4 z-50 flex flex-col gap-3 max-w-sm w-full"
      dir="rtl"
      role="region"
      aria-label="إشعارات النظام الحية"
    >
      {/* SSE connection indicator — tiny dot */}
      {!isConnected && (
        <div className="flex items-center gap-2 rounded-xl border border-slate-300 bg-white/90 px-3 py-2 text-xs text-slate-500 shadow dark:border-slate-700 dark:bg-slate-900/90">
          <span className="h-2 w-2 rounded-full bg-slate-400 animate-pulse" />
          انقطع اتصال الإشعارات الحية
        </div>
      )}

      {toastQueue.map((toast) => {
        const style = TOAST_STYLES[toast.level] || TOAST_STYLES.info
        return (
          <div
            key={toast.id}
            className={`flex items-start gap-3 rounded-2xl border-2 ${style.border} ${style.bg} px-4 py-3 shadow-lg backdrop-blur-md transition-all duration-300 animate-slide-in-up`}
            role="alert"
          >
            <div className="mt-0.5 shrink-0">{style.icon}</div>
            <div className="flex-1 min-w-0">
              <div className={`text-sm font-semibold ${style.text}`}>{toast.title}</div>
              <div className={`mt-0.5 text-xs ${style.text} opacity-80 truncate`}>{toast.body}</div>
              {toast.link && (
                <button
                  type="button"
                  onClick={() => { dismiss(toast.id); navigate(toast.link) }}
                  className={`mt-1 text-xs font-semibold underline underline-offset-2 ${style.text}`}
                >
                  عرض التفاصيل ←
                </button>
              )}
            </div>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="shrink-0 rounded-full p-1 hover:bg-black/10"
              aria-label="إغلاق الإشعار"
            >
              <X className="h-3 w-3 text-slate-500" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
