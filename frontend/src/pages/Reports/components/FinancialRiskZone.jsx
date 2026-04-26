import React from 'react'
import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'

import { formatDate, formatNumber } from '../constants'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

export default function FinancialRiskZone({ filters, riskData, status = 'idle' }) {
  return (
    <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow mt-6 border-l-4 border-red-500 dark:border-red-600">
      <h2 className="text-xl font-semibold text-red-700 dark:text-red-400 mb-4">
        منطقة المخاطر المالية
      </h2>
      {status === 'loading' ? (
        <p className="text-gray-500 dark:text-slate-400">جارٍ تحميل بيانات المخاطر...</p>
      ) : !filters.farm || !filters.crop_id ? (
        <p className="text-gray-500 dark:text-slate-400">يرجى تحديد المزرعة والمحصول لعرض تحليل المخاطر.</p>
      ) : riskData.length === 0 ? (
        <p className="text-green-600 dark:text-green-400">لا توجد انحرافات تكلفة مسجلة ضمن المرشحات الحالية.</p>
      ) : (
        <>
          <div className="mb-6 h-64">
            <Bar
              data={{
                labels: riskData.map(
                  (entry) => entry.task_name || entry.item_name || entry.crop_plan_name || 'غير محدد',
                ),
                datasets: [
                  {
                    label: 'قيمة الانحراف',
                    data: riskData.map((entry) => entry.deviation || entry.risk_score || 0),
                    backgroundColor: 'rgba(239, 68, 68, 0.6)',
                    borderColor: 'rgba(239, 68, 68, 1)',
                    borderWidth: 1,
                  },
                ],
              }}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  title: { display: true, text: 'انحراف التكلفة عن المعدل الطبيعي' },
                  legend: { labels: { color: '#9ca3af' } },
                },
                scales: {
                  x: { ticks: { color: '#9ca3af' }, grid: { color: '#374151' } },
                  y: { ticks: { color: '#9ca3af' }, grid: { color: '#374151' } },
                },
              }}
            />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-end">
              <thead className="bg-red-50 dark:bg-red-900/20 text-xs text-red-800 dark:text-red-300">
                <tr>
                  <th className="px-3 py-2">المهمة</th>
                  <th className="px-3 py-2">التاريخ</th>
                  <th className="px-3 py-2">التكلفة الفعلية</th>
                  <th className="px-3 py-2">المتوسط</th>
                  <th className="px-3 py-2">الحد المرجعي</th>
                  <th className="px-3 py-2">الانحراف</th>
                </tr>
              </thead>
              <tbody className="text-gray-700 dark:text-slate-300">
                {riskData.map((item, idx) => (
                  <tr
                    key={`${item.crop_plan_id || 'risk'}-${idx}`}
                    className="border-t dark:border-slate-700 hover:bg-red-50 dark:hover:bg-red-900/10"
                  >
                    <td className="px-3 py-2 font-medium">
                      {item.task_name || item.item_name || item.crop_plan_name || '-'}
                    </td>
                    <td className="px-3 py-2">{item.date ? formatDate(item.date) : '-'}</td>
                    <td className="px-3 py-2 font-bold text-red-600 dark:text-red-400">
                      {formatNumber(item.cost_total)}
                    </td>
                    <td className="px-3 py-2">{formatNumber(item.mean)}</td>
                    <td className="px-3 py-2">{formatNumber(item.threshold)}</td>
                    <td className="px-3 py-2 text-red-600 dark:text-red-400">
                      {formatNumber(item.risk_score || item.deviation)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
