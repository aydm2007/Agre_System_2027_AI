import { useOfflineQueue } from '../offline/OfflineQueueProvider.jsx'
import { toast } from 'react-hot-toast'
import { logRuntimeError } from '../utils/runtimeLogger'

const formatDateTime = (value) => {
  if (!value) return 'غير متوفر'
  try {
    return new Date(value).toLocaleString('ar-EG', { hour12: false })
  } catch (error) {
    return value
  }
}

export default function OfflineStatusBanner() {
  const {
    isOnline,
    queuedRequests,
    queuedHarvests,
    queuedDailyLogs,
    queuedCustody,
    failedRequests,
    failedHarvests,
    failedDailyLogs,
    failedCustody,
    syncing,
    lastSync,
    syncNow,
  } = useOfflineQueue()

  const totalPending = queuedRequests + queuedHarvests + queuedDailyLogs + queuedCustody
  const totalFailed = failedRequests + failedHarvests + failedDailyLogs + failedCustody

  if (isOnline && totalPending === 0 && totalFailed === 0) {
    return null
  }

  const stateClasses = isOnline
    ? 'bg-blue-50 border-blue-200 text-blue-800'
    : 'bg-yellow-50 border-yellow-200 text-yellow-800'

  return (
    <div
      className={`rounded-md border p-3 text-sm ${stateClasses} flex flex-col gap-2 md:flex-row md:items-center md:justify-between`}
    >
      <div className="space-y-1">
        <p className="font-semibold">
          {isOnline
            ? 'تم رصد عناصر غير متزامنة في الطابور.'
            : 'أنت غير متصل. سيتم المزامنة عند عودة الاتصال.'}
        </p>
        {(totalPending > 0 || totalFailed > 0) && (
          <p className="text-sm text-gray-700">
            المعلقة: <strong>{totalPending}</strong> | الفاشلة: <strong>{totalFailed}</strong>
          </p>
        )}
        {lastSync && (
          <p className="text-xs text-gray-600">آخر مزامنة ناجحة: {formatDateTime(lastSync)}</p>
        )}
      </div>
      <div className="flex gap-2">
        {totalPending > 0 && (
          <button
            type="button"
            onClick={() =>
              syncNow().catch((error) => {
                logRuntimeError('OFFLINE_MANUAL_SYNC_FAILED', error, { totalPending, totalFailed })
                toast.error('تعذرت المزامنة اليدوية. راجع اتصال الشبكة وحاول مجددًا.')
              })
            }
            className="px-3 py-1 rounded bg-primary text-white text-xs md:text-sm disabled:opacity-60"
            disabled={!isOnline || syncing}
          >
            {syncing ? 'جاري المزامنة...' : 'مزامنة الآن'}
          </button>
        )}
      </div>
    </div>
  )
}
