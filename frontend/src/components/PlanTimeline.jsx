import { useMemo } from 'react'
import { format, differenceInDays, addMonths, startOfMonth, endOfMonth } from 'date-fns'
import { ar } from 'date-fns/locale'

const COLOR_MAP = {
  active: 'bg-green-500',
  completed: 'bg-gray-400',
  draft: 'bg-yellow-400',
  archived: 'bg-red-300',
}

export default function PlanTimeline({ plans = [] }) {
  const { months, minDate, totalDays } = useMemo(() => {
    if (!plans.length) return { months: [], minDate: new Date(), totalDays: 0 }

    const dates = plans.flatMap((p) => [new Date(p.start_date), new Date(p.end_date)])
    const min = new Date(Math.min(...dates))
    const max = new Date(Math.max(...dates))

    // Pad 1 month before and after
    const start = startOfMonth(addMonths(min, -1))
    const end = endOfMonth(addMonths(max, 1))
    const total = differenceInDays(end, start)

    const monthList = []
    let current = start
    while (current <= end) {
      monthList.push(current)
      current = addMonths(current, 1)
    }

    return { months: monthList, minDate: start, totalDays: total }
  }, [plans])

  if (!plans.length)
    return (
      <div className="text-center text-gray-500 dark:text-slate-400 py-8">
        لا توجد خطط لعرضها في الجدول الزمني.
      </div>
    )

  const getPosition = (dateStr) => {
    const date = new Date(dateStr)
    const days = differenceInDays(date, minDate)
    return (days / totalDays) * 100
  }

  const getWidth = (startStr, endStr) => {
    const start = new Date(startStr)
    const end = new Date(endStr)
    const days = differenceInDays(end, start)
    return (days / totalDays) * 100
  }

  return (
    <div
      className="w-full overflow-x-auto border dark:border-slate-700 rounded-xl bg-white dark:bg-slate-800 shadow-sm font-secondary"
      dir="ltr"
    >
      {' '}
      {/* LTR for timeline logic, internal RTL text */}
      <div className="min-w-[800px] p-4">
        {/* Header - Months */}
        <div className="flex border-b dark:border-slate-700 pb-2 mb-2">
          <div className="w-48 shrink-0 font-bold text-gray-700 dark:text-slate-200 text-end px-4">
            الخطط / المزارع
          </div>
          <div className="flex-1 relative h-6">
            {months.map((month, idx) => {
              const left = (differenceInDays(month, minDate) / totalDays) * 100
              return (
                <div
                  key={idx}
                  className="absolute top-0 text-xs text-gray-500 dark:text-slate-400 border-l dark:border-slate-600 pl-1"
                  style={{ left: `${left}%` }}
                >
                  {format(month, 'MMM yyyy', { locale: ar })}
                </div>
              )
            })}
          </div>
        </div>

        {/* Rows */}
        <div className="space-y-3">
          {plans.map((plan) => {
            const left = getPosition(plan.start_date)
            const width = getWidth(plan.start_date, plan.end_date)
            const color = COLOR_MAP[plan.status] || 'bg-blue-500'
            const progress = Math.min(plan.budget_consumption_pct || 0, 100)

            return (
              <div
                key={plan.id}
                className="flex items-center group hover:bg-gray-50 dark:hover:bg-slate-700 rounded py-1 transition-colors"
              >
                <div
                  className="w-48 shrink-0 text-end px-4 truncate border-r border-gray-100 dark:border-slate-700 z-10 bg-white dark:bg-slate-800 group-hover:bg-gray-50 dark:group-hover:bg-slate-700"
                  dir="rtl"
                >
                  <div
                    className="font-bold text-sm text-gray-800 dark:text-white truncate"
                    title={plan.name}
                  >
                    {plan.name}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-slate-400 truncate">
                    {plan.farm?.name || '-'}
                  </div>
                </div>

                <div className="flex-1 relative h-8">
                  {/* Grid Lines */}
                  {months.map((month, idx) => {
                    const lineLeft = (differenceInDays(month, minDate) / totalDays) * 100
                    return (
                      <div
                        key={idx}
                        className="absolute top-0 bottom-0 w-px bg-gray-100 dark:bg-slate-700"
                        style={{ left: `${lineLeft}%` }}
                      />
                    )
                  })}

                  {/* Bar */}
                  <div
                    className={`absolute top-1 bottom-1 rounded-md shadow-sm ${color} opacity-90 hover:opacity-100 cursor-pointer flex items-center justify-center text-white text-[10px] whitespace-nowrap overflow-hidden px-1 transition-all`}
                    style={{ left: `${left}%`, width: `${width}%` }}
                    title={`${plan.name}: ${plan.start_date} -> ${plan.end_date} (${Math.round(plan.budget_consumption_pct || 0)}% budget)`}
                  >
                    {/* Progress Overlay */}
                    <div
                      className="absolute top-0 bottom-0 right-0 bg-black bg-opacity-20 z-0 transition-all rounded-r-md"
                      style={{ width: `${progress}%` }}
                    />

                    <span className="z-10 relative drop-shadow-md px-1 truncate">
                      {width > 5 && plan.season}{' '}
                      {progress > 0 && width > 10 ? `(${Math.round(progress)}%)` : ''}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
