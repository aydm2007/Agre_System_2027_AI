import React from 'react'

import { TEXT, TREE_EVENT_LABELS, formatDateTimeValue, formatNumber } from '../constants'

export default function TreeInsights({
  treeLoading,
  treeSummary,
  treeTotals,
  treeEvents,
  treeError,
  productiveTreeCount,
  showSummary = true,
  showEvents = true,
  summaryStatus = 'idle',
  eventsStatus = 'idle',
}) {
  return (
    <>
      {showSummary ? (
        <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">{TEXT.treeSummary.title}</h2>
          {treeLoading || summaryStatus === 'loading' ? (
            <p className="text-gray-500 dark:text-slate-400 text-sm">جارٍ تحميل ملخص الأشجار...</p>
          ) : treeSummary.length ? (
            <>
              <div className="grid md:grid-cols-3 gap-3 text-center mb-4">
                <div>
                  <div className="text-sm text-gray-500 dark:text-slate-400">{TEXT.treeSummary.totalTrees}</div>
                  <div className="text-2xl font-semibold text-gray-900 dark:text-white">
                    {formatNumber(treeTotals.total, 0)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-slate-400">{TEXT.treeSummary.productive}</div>
                  <div className="text-2xl font-semibold text-green-600 dark:text-green-400">
                    {formatNumber(productiveTreeCount, 0)}
                  </div>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-end">
                  <thead className="bg-gray-50 dark:bg-slate-700 text-xs text-gray-600 dark:text-slate-300">
                    <tr>
                      <th className="px-3 py-2">{TEXT.filters.location}</th>
                      <th className="px-3 py-2">{TEXT.filters.variety}</th>
                      <th className="px-3 py-2 text-center">{TEXT.treeSummary.totalTrees}</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-700 dark:text-slate-300">
                    {treeSummary.map((item) => (
                      <tr
                        key={item.id}
                        className="border-t dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700/50"
                      >
                        <td className="px-3 py-2">{item.location?.name || item.location_name || '-'}</td>
                        <td className="px-3 py-2">{item.crop_variety?.name || item.variety_name || '-'}</td>
                        <td className="px-3 py-2 text-center">{formatNumber(item.current_tree_count, 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="text-gray-500 dark:text-slate-400 text-sm">{treeError || TEXT.treeSummary.noData}</p>
          )}
        </div>
      ) : null}

      {showEvents ? (
        <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">{TEXT.treeEvents.title}</h2>
          {treeLoading || eventsStatus === 'loading' ? (
            <p className="text-gray-500 dark:text-slate-400 text-sm">جارٍ تحميل أحداث الأشجار...</p>
          ) : treeEvents.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-end">
                <thead className="bg-gray-50 dark:bg-slate-700 text-xs text-gray-600 dark:text-slate-300">
                  <tr>
                    <th className="px-3 py-2">{TEXT.treeEvents.date}</th>
                    <th className="px-3 py-2">{TEXT.treeEvents.type}</th>
                    <th className="px-3 py-2">{TEXT.treeEvents.location}</th>
                    <th className="px-3 py-2 text-center">{TEXT.treeEvents.delta}</th>
                  </tr>
                </thead>
                <tbody className="text-gray-700 dark:text-slate-300">
                  {treeEvents.map((event) => (
                    <tr
                      key={event.id}
                      className="border-t dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700/50"
                    >
                      <td className="px-3 py-2">{formatDateTimeValue(event.event_timestamp)}</td>
                      <td className="px-3 py-2">{TREE_EVENT_LABELS[event.event_type] || event.event_type}</td>
                      <td className="px-3 py-2">{event.location_tree_stock?.location?.name || '-'}</td>
                      <td className="px-3 py-2 text-center">{formatNumber(event.tree_count_delta, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 dark:text-slate-400 text-sm">{treeError || TEXT.treeEvents.noData}</p>
          )}
        </div>
      ) : null}
    </>
  )
}
