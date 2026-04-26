import ApprovalButton from '../../components/ApprovalButton'
import { TEXT } from './constants'

export default function ActivityFeed({
  daySummary,
  loading,
  error,
  pendingQueueCount,
  onGoToQueue,
  highlightedLogIds,
  isEditingActivity,
  editingActivityId,
  submitting,
  deletingActivityId,
  onApproveLog,
  onEditActivity,
  onDeleteActivity,
  helpers,
}) {
  const { toDateInputValue, formatNumber, formatDateTime, formatTeamDisplay } = helpers

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4 space-y-4">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
        <h3 className="text-lg font-semibold text-gray-800">{TEXT.activitySummary.title}</h3>
        <span className="text-sm text-gray-500">{toDateInputValue(daySummary?.date)}</span>
      </div>
      {pendingQueueCount > 0 && (
        <div className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
          <span>{TEXT.queue.pending(pendingQueueCount)}</span>
          <button
            type="button"
            className="px-2 py-1 border border-amber-300 rounded text-amber-800 hover:bg-amber-100"
            onClick={onGoToQueue}
          >
            {TEXT.queue.manage}
          </button>
        </div>
      )}
      {loading ? (
        <p className="text-sm text-gray-500">{TEXT.activitySummary.loading}</p>
      ) : error ? (
        <p className="text-sm text-red-600">{TEXT.activitySummary.error}</p>
      ) : Array.isArray(daySummary?.logs) && daySummary.logs.length ? (
        daySummary.logs.map((log, logIndex) => {
          const normalizedId = log?.id != null ? String(log.id) : String(`queued-${logIndex}`)
          const isRecentlySyncedLog = normalizedId && highlightedLogIds.has(normalizedId)
          const containerClass = [
            'rounded-lg overflow-hidden',
            isRecentlySyncedLog
              ? 'border-emerald-300 ring-1 ring-emerald-300 bg-emerald-50/70'
              : 'border border-gray-200',
          ]
            .filter(Boolean)
            .join(' ')
          return (
            <div
              key={log.id || logIndex}
              id={`daily-log-entry-${normalizedId}`}
              className={containerClass}
            >
              <div className="bg-gray-50 px-3 py-2 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                <div className="flex items-center gap-3">
                  <div className="font-semibold text-gray-700">
                    #{logIndex + 1} - {log.farm?.name || TEXT.fields.noFarms}
                  </div>
                  {/* Smart Approval Button (Four-Eyes Principle) */}
                  {log.status !== 'approved' && (
                    <ApprovalButton
                      creatorId={log.created_by}
                      logId={log.id}
                      onApprove={() => onApproveLog(log.id)}
                    />
                  )}
                  {log.status === 'approved' && (
                    <span className="rounded-full bg-green-100 px-2 py-1 text-xs text-green-800">
                      معتمد ✅
                    </span>
                  )}
                </div>
                <div className="text-sm text-gray-500">
                  {TEXT.summary.activities}:{' '}
                  {Array.isArray(log.activities) ? log.activities.length : 0}
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm text-gray-700">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="px-3 py-2 text-end font-semibold">#</th>
                      <th className="px-3 py-2 text-end font-semibold">{TEXT.fields.task}</th>
                      <th className="px-3 py-2 text-end font-semibold">{TEXT.fields.location}</th>
                      <th className="px-3 py-2 text-end font-semibold">{TEXT.fields.team}</th>
                      <th className="px-3 py-2 text-end font-semibold">{TEXT.fields.hours}</th>
                      <th className="px-3 py-2 text-end font-semibold">
                        {TEXT.activitySummary.updatedAt}
                      </th>
                      <th className="px-3 py-2 text-end font-semibold">
                        {TEXT.activitySummary.actions}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {Array.isArray(log.activities) && log.activities.length ? (
                      log.activities.map((activity, activityIndex) => {
                        const isOfflinePending = Boolean(activity.isOfflinePending)
                        const canEdit = Boolean(activity.can_edit) && !isOfflinePending
                        const isActiveRow = isEditingActivity && editingActivityId === activity.id
                        const rowClass = [
                          'border-t',
                          isActiveRow ? 'bg-indigo-100' : '',
                          canEdit ? 'hover:bg-indigo-50 cursor-pointer' : 'cursor-not-allowed',
                          isOfflinePending ? 'bg-amber-50/60' : '',
                          isRecentlySyncedLog ? 'bg-emerald-50/50' : '',
                        ]
                          .filter(Boolean)
                          .join(' ')

                        return (
                          <tr
                            key={activity.id || activityIndex}
                            onClick={() => {
                              if (canEdit) {
                                onEditActivity(log, activity)
                              }
                            }}
                            className={rowClass}
                          >
                            <td className="px-3 py-2 text-end">{activityIndex + 1}</td>
                            <td className="px-3 py-2 text-end">
                              <div className="flex items-center justify-end gap-2">
                                <span>{activity.task?.name || '-'}</span>
                                {isOfflinePending && (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
                                    {TEXT.activitySummary.offlinePending}
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="px-3 py-2 text-end">
                              {activity.locations && activity.locations.length > 0
                                ? activity.locations.map((l) => l.name).join(', ')
                                : activity.location?.name || '-'}
                            </td>
                            <td className="px-3 py-2 text-end">
                              {formatTeamDisplay(activity.team)}
                            </td>
                            <td className="px-3 py-2 text-end">
                              {activity.hours != null ? formatNumber(activity.hours) : '-'}
                            </td>
                            <td className="px-3 py-2 text-end">
                              {activity.updated_at ? formatDateTime(activity.updated_at) : '-'}
                            </td>
                            <td className="px-3 py-2">
                              {canEdit ? (
                                <div className="flex flex-col sm:flex-row gap-2 justify-end">
                                  <button
                                    type="button"
                                    className="px-2 py-1 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50 disabled:opacity-60"
                                    onClick={(event) => {
                                      event.stopPropagation()
                                      onEditActivity(log, activity)
                                    }}
                                    disabled={submitting}
                                  >
                                    {TEXT.activitySummary.edit}
                                  </button>
                                  <button
                                    type="button"
                                    className="px-2 py-1 rounded border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-60"
                                    onClick={(event) => {
                                      event.stopPropagation()
                                      onDeleteActivity(activity)
                                    }}
                                    disabled={submitting || deletingActivityId === activity.id}
                                  >
                                    {deletingActivityId === activity.id
                                      ? TEXT.submit.sending
                                      : TEXT.activitySummary.delete}
                                  </button>
                                </div>
                              ) : (
                                <span className="text-xs text-gray-400">
                                  {TEXT.activitySummary.viewOnly}
                                </span>
                              )}
                            </td>
                          </tr>
                        )
                      })
                    ) : (
                      <tr>
                        <td className="px-3 py-2 text-end text-gray-500" colSpan="7">
                          {TEXT.activitySummary.empty}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )
        })
      ) : (
        <p className="text-sm text-gray-500">{TEXT.activitySummary.empty}</p>
      )}
    </div>
  )
}
