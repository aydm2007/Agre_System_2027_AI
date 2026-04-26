import { createContext, useCallback, useContext, useMemo, useState } from 'react'

const ToastContext = createContext({ addToast: () => {} })

function normalizeIntent(intentOrType) {
  const raw = String(intentOrType || 'info').toLowerCase()
  if (raw === 'danger') return 'error'
  if (raw === 'warn') return 'warning'
  if (raw === 'ok') return 'success'
  return raw
}

function normalizeToastPayload(input, legacyIntent, legacyExtras = {}) {
  if (typeof input === 'string') {
    return {
      message: input,
      intent: normalizeIntent(legacyIntent || 'info'),
      ...legacyExtras,
    }
  }

  if (input && typeof input === 'object') {
    const candidate = { ...input }
    const intent = normalizeIntent(candidate.intent || candidate.type || legacyIntent || 'info')
    const message =
      typeof candidate.message === 'string'
        ? candidate.message
        : typeof candidate.title === 'string'
          ? candidate.title
          : JSON.stringify(candidate.message || candidate)

    return {
      ...candidate,
      message,
      intent,
    }
  }

  return {
    message: 'حدث خطأ غير متوقع.',
    intent: normalizeIntent(legacyIntent || 'info'),
    ...legacyExtras,
  }
}

function ToastContainer({ toasts, removeToast }) {
  return (
    <div className="fixed top-4 left-1/2 z-50 -translate-x-1/2 space-y-3">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="alert"
          className={`min-w-[18rem] rounded-md border px-4 py-3 shadow-lg transition ${
            toast.intent === 'error'
              ? 'bg-red-50 border-red-200 text-red-900 dark:bg-red-900/30 dark:border-red-700 dark:text-red-100'
              : toast.intent === 'success'
                ? 'bg-green-50 border-green-200 text-green-900 dark:bg-green-900/30 dark:border-green-700 dark:text-green-100'
                : toast.intent === 'warning'
                  ? 'bg-amber-50 border-amber-200 text-amber-900 dark:bg-amber-900/30 dark:border-amber-700 dark:text-amber-100'
                  : 'bg-blue-50 border-blue-200 text-blue-900 dark:bg-blue-900/30 dark:border-blue-700 dark:text-blue-100'
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              {toast.title && <p className="font-semibold text-sm">{toast.title}</p>}
              <p className="text-sm leading-relaxed">{toast.message}</p>
            </div>
            <button
              type="button"
              onClick={() => removeToast(toast.id)}
              className="text-xs text-gray-500 hover:text-gray-700 dark:text-slate-300 dark:hover:text-white"
            >
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id))
  }, [])

  const generateToastId = () => {
    const cryptoObj =
      typeof globalThis !== 'undefined' && globalThis.crypto ? globalThis.crypto : undefined
    if (cryptoObj && typeof cryptoObj.randomUUID === 'function') {
      return cryptoObj.randomUUID()
    }
    if (cryptoObj && typeof cryptoObj.getRandomValues === 'function') {
      const buffer = new Uint32Array(4)
      cryptoObj.getRandomValues(buffer)
      return Array.from(buffer)
        .map((value) => value.toString(16).padStart(8, '0'))
        .join('-')
    }
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
  }

  const addToast = useCallback(
    (toastInput, legacyIntent, legacyExtras) => {
      const toast = normalizeToastPayload(toastInput, legacyIntent, legacyExtras)
      const id = generateToastId()
      const intent = toast.intent || 'info'
      const duration = toast.duration ?? 4000
      setToasts((prev) => [...prev, { id, intent, ...toast }])
      if (duration > 0) {
        setTimeout(() => removeToast(id), duration)
      }
      return id
    },
    [removeToast],
  )

  const value = useMemo(() => ({ addToast, removeToast }), [addToast, removeToast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  const { addToast, removeToast } = context

  const toast = useCallback(
    (optionsOrMessage, intent, extra) => addToast(optionsOrMessage, intent, extra),
    [addToast],
  )

  toast.success = (message) => addToast({ message, intent: 'success' })
  toast.error = (message) => addToast({ message, intent: 'error' })
  toast.warning = (message) => addToast({ message, intent: 'warning' })
  toast.info = (message) => addToast({ message, intent: 'info' })
  toast.remove = removeToast

  return toast
}
