const renderList = (
  title,
  items,
  formatDateTime,
  queueType,
  status,
  onInspectItem,
  onRestoreItem,
  onRemoveItem,
) => {
  if (!items?.length) {
    return null
  }
  const preview = items.slice(0, 5)
  return (
    <div className="space-y-1">
      <p className="font-semibold text-xs text-gray-600 dark:text-slate-400">{title}</p>
      <ul className="space-y-2">
        {preview.map((item, index) => {
          const scheduledAt = formatDateTime(item.queuedAt)
          const meta = item.meta || {}
          const baseInfo = [meta.farmName, meta.date || item.logPayload?.log_date, scheduledAt]
            .filter(Boolean)
            .join(' • ')
          const secondary =
            meta.taskName ||
            meta.cropName ||
            item.activityPayload?.task_id ||
            item.method ||
            item.url ||
            ''
          const resolvedQueueType = status === 'failed' ? `failed-${queueType}` : queueType
          return (
            <li
              key={item.id || index}
              className="rounded border border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700 px-3 py-2"
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="space-y-0.5 text-xs text-gray-600 dark:text-slate-400">
                  <div className="font-mono text-[11px]">#{item.id}</div>
                  {baseInfo && <div className="text-gray-700 dark:text-slate-300">{baseInfo}</div>}
                  {secondary && (
                    <div className="text-[11px] text-gray-500 dark:text-slate-500">{secondary}</div>
                  )}
                </div>
                <div className="flex flex-col gap-1 sm:items-end">
                  <button
                    type="button"
                    className="px-2 py-1 text-[11px] rounded border border-gray-300 dark:border-slate-500 text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-600"
                    onClick={() => onInspectItem(resolvedQueueType, item, status)}
                  >
                    عرض التفاصيل
                  </button>
                  {queueType === 'daily-log' && (
                    <button
                      type="button"
                      className="px-2 py-1 text-[11px] rounded border border-blue-300 dark:border-blue-600 text-blue-700 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30"
                      onClick={() => onRestoreItem(item)}
                    >
                      استعادة
                    </button>
                  )}
                  <button
                    type="button"
                    className="px-2 py-1 text-[11px] rounded border border-red-300 dark:border-red-600 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30"
                    onClick={() => onRemoveItem(resolvedQueueType, item.id)}
                  >
                    حذف
                  </button>
                </div>
              </div>
            </li>
          )
        })}
        {items.length > preview.length && (
          <li className="text-xs text-gray-400 dark:text-slate-500">
            + {items.length - preview.length} عناصر إضافية
          </li>
        )}
      </ul>
    </div>
  )
}

export default function OfflineQueueRow({
  summary,
  onClearPending,
  onClearFailed,
  onRetryFailed,
  onInspectItem,
  onRestoreItem,
  onRemoveItem,
  formatDateTime,
  onLoadMore,
}) {
  const {
    title,
    description,
    pendingCount,
    failedCount,
    pendingDetails,
    failedDetails,
    type,
    meta,
  } = summary

  const pendingMeta = meta?.pending
  const failedMeta = meta?.failed
  const hasLimitedPending = pendingMeta?.truncated
  const hasLimitedFailed = failedMeta?.truncated
  const showLimitNotice = hasLimitedPending || hasLimitedFailed

  return (
    <div className="rounded border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="space-y-2">
          <h4 className="font-semibold text-gray-800 dark:text-white">{title}</h4>
          <p className="text-sm text-gray-500 dark:text-slate-400">{description}</p>
          <div className="flex flex-wrap gap-3 text-sm text-gray-700 dark:text-slate-300">
            <span>
              قيد الانتظار: <strong>{pendingCount}</strong>
            </span>
            <span
              className={
                failedCount ? 'text-red-600 dark:text-red-400' : 'text-gray-600 dark:text-slate-400'
              }
            >
              فشل: <strong>{failedCount}</strong>
            </span>
          </div>
          {showLimitNotice && (
            <div className="flex flex-wrap items-center gap-2 rounded border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/30 px-3 py-2 text-xs text-amber-800 dark:text-amber-300">
              <span>
                تم عرض {pendingMeta?.returned ?? 0}/{pendingMeta?.total ?? 0} من العناصر المعلقة
                {typeof failedMeta?.total === 'number' && failedMeta.total > 0 && (
                  <>
                    {', '}الفاشلة {failedMeta?.returned ?? 0}/{failedMeta.total}
                  </>
                )}
              </span>
              {typeof onLoadMore === 'function' && (
                <button
                  type="button"
                  className="px-2 py-1 rounded border border-amber-400 dark:border-amber-600 text-amber-800 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-800/30"
                  onClick={onLoadMore}
                >
                  تحميل المزيد
                </button>
              )}
            </div>
          )}
          {(pendingDetails?.length || failedDetails?.length) && (
            <details className="text-xs text-gray-500 dark:text-slate-400">
              <summary className="cursor-pointer text-gray-600 dark:text-slate-300">
                عرض التفاصيل
              </summary>
              <div className="mt-2 space-y-3">
                {renderList(
                  'العناصر المعلقة',
                  pendingDetails,
                  formatDateTime,
                  type,
                  'pending',
                  onInspectItem,
                  onRestoreItem,
                  onRemoveItem,
                )}
                {renderList(
                  'العناصر الفاشلة',
                  failedDetails,
                  formatDateTime,
                  type,
                  'failed',
                  onInspectItem,
                  onRestoreItem,
                  onRemoveItem,
                )}
              </div>
            </details>
          )}
        </div>
        <div className="flex flex-col items-stretch gap-2 md:items-end">
          <div className="flex flex-wrap gap-2 justify-end">
            <button
              type="button"
              onClick={onClearPending}
              className="px-3 py-1 text-sm border border-gray-300 dark:border-slate-600 rounded hover:bg-gray-50 dark:hover:bg-slate-700 dark:text-slate-200"
              disabled={!pendingCount}
            >
              مسح المعلقات
            </button>
            <button
              type="button"
              onClick={onRetryFailed}
              className="px-3 py-1 text-sm border border-blue-300 dark:border-blue-600 rounded text-blue-700 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30"
              disabled={!failedCount}
            >
              إعادة المحاولة
            </button>
            <button
              type="button"
              onClick={onClearFailed}
              className="px-3 py-1 text-sm border border-red-300 dark:border-red-600 rounded text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30"
              disabled={!failedCount}
            >
              مسح الفاشلة
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
