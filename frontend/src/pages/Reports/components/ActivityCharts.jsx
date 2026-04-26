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

import { TEXT } from '../constants'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

export default function ActivityCharts({ materialChart, machineryChart, status = 'idle' }) {
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { ticks: { color: '#9ca3af' }, grid: { color: '#374151' } },
      y: { ticks: { color: '#9ca3af' }, grid: { color: '#374151' } },
    },
    plugins: {
      legend: { labels: { color: '#9ca3af' } },
    },
  }

  return (
    <div className="grid md:grid-cols-2 gap-3">
      <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">{TEXT.charts.materials}</h2>
        {status === 'loading' ? (
          <p className="text-gray-500 dark:text-slate-400 text-sm">جارٍ تحميل الرسوم البيانية...</p>
        ) : materialChart ? (
          <div style={{ height: 320 }}>
            <Bar data={materialChart} options={options} />
          </div>
        ) : (
          <p className="text-gray-500 dark:text-slate-400 text-sm">{TEXT.charts.noData}</p>
        )}
      </div>
      <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">{TEXT.charts.machines}</h2>
        {status === 'loading' ? (
          <p className="text-gray-500 dark:text-slate-400 text-sm">جارٍ تحميل الرسوم البيانية...</p>
        ) : machineryChart ? (
          <div style={{ height: 320 }}>
            <Bar data={machineryChart} options={options} />
          </div>
        ) : (
          <p className="text-gray-500 dark:text-slate-400 text-sm">{TEXT.charts.noData}</p>
        )}
      </div>
    </div>
  )
}
