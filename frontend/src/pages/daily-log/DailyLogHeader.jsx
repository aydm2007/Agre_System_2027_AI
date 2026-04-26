import { TEXT } from './constants'

export default function DailyLogHeader({
  isOnline,
  pendingQueueCount,
  queueSyncing,
  isEditingActivity,
  onSync,
  onManageQueue,
  onInspectQueue,
  onCancelEdit,
}) {
  return (
    <section className="space-y-4">
      {/* Main Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-black tracking-tight bg-gradient-to-r from-emerald-400 to-amber-200 bg-clip-text text-transparent">
            {TEXT.title}
          </h1>
          <p className="text-zinc-500 font-medium text-sm mt-1">تسجيل الأنشطة الزراعية اليومية</p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Online/Offline Status */}
          <span
            className={`inline-flex items-center gap-2 rounded-xl border px-4 py-2 backdrop-blur-xl ${
              isOnline
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                : 'border-amber-500/30 bg-amber-500/10 text-amber-400'
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full animate-pulse ${isOnline ? 'bg-emerald-400' : 'bg-amber-400'}`}
              aria-hidden="true"
            />
            {isOnline ? TEXT.status.online : TEXT.status.offline}
          </span>

          {/* Queue Status */}
          <span className="inline-flex items-center gap-2 rounded-xl border border-blue-500/30 bg-blue-500/10 px-4 py-2 text-blue-400">
            {pendingQueueCount > 0
              ? TEXT.status.queuePending(pendingQueueCount)
              : TEXT.status.queueEmpty}
          </span>
        </div>
      </div>

      {/* Offline Notice */}
      {!isOnline && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 backdrop-blur-xl p-4 text-sm text-amber-300">
          ⚠️ {TEXT.offlineNotice}
        </div>
      )}

      {/* Queue Notice */}
      {pendingQueueCount > 0 && (
        <div className="flex flex-col gap-3 rounded-2xl border border-blue-500/30 bg-blue-500/10 backdrop-blur-xl p-4 text-sm text-blue-300 md:flex-row md:items-center md:justify-between">
          <div className="font-medium">{TEXT.queueNotice(pendingQueueCount)}</div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onSync}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-white font-bold hover:bg-emerald-500 disabled:opacity-40 transition-colors shadow-lg shadow-emerald-500/20"
              disabled={!isOnline || queueSyncing}
            >
              {queueSyncing ? TEXT.queueSyncing : TEXT.queueSync}
            </button>
            <button
              type="button"
              className="rounded-xl border border-blue-500/30 px-4 py-2 text-blue-400 hover:bg-blue-500/10 transition-colors"
              onClick={onManageQueue}
            >
              {TEXT.queue.manage}
            </button>
            <button
              type="button"
              className="rounded-xl border border-white/10 px-4 py-2 text-white/60 hover:bg-white/5 transition-colors"
              onClick={onInspectQueue}
            >
              {TEXT.queue.inspect}
            </button>
          </div>
        </div>
      )}

      {/* Editing Mode Notice */}
      {isEditingActivity && (
        <div className="flex flex-col gap-3 rounded-2xl border border-purple-500/30 bg-purple-500/10 backdrop-blur-xl p-4 text-sm text-purple-300 md:flex-row md:items-center md:justify-between">
          <div className="font-medium">✏️ {TEXT.activitySummary.editMode}</div>
          <button
            type="button"
            onClick={onCancelEdit}
            className="rounded-xl border border-purple-500/30 px-4 py-2 text-purple-400 hover:bg-purple-500/10 transition-colors"
          >
            {TEXT.activitySummary.cancelEdit}
          </button>
        </div>
      )}
    </section>
  )
}
