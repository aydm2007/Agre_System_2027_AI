import { useEffect, useState } from 'react'
import { getFinancialRiskZone } from '../api/client'

// ─── API helper for variance radar ────────────────────────────────
const API_BASE = '/api/v1'

async function fetchVarianceAlerts(farmId) {
  const res = await fetch(`${API_BASE}/variance-radar/?farm=${farmId}&status=UNINVESTIGATED`)
  if (!res.ok) throw new Error('فشل في جلب بيانات رادار الانحرافات')
  return res.json()
}

async function resolveAlert(alertId, status, note) {
  const res = await fetch(`${API_BASE}/variance-radar/${alertId}/resolve/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, resolution_note: note }),
  })
  if (!res.ok) throw new Error('فشل في إقفال الإنذار')
  return res.json()
}

// ─── Shadow Variance Radar Component ──────────────────────────────
function ShadowVarianceRadar({ farmId }) {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!farmId) return
    setLoading(true)
    fetchVarianceAlerts(farmId)
      .then((data) => setAlerts(data.results || data))
      .catch(() => setAlerts([]))
      .finally(() => setLoading(false))
  }, [farmId])

  const handleResolve = async (id, status) => {
    const note = window.prompt('ملاحظات القرار (اختياري):') || ''
    try {
      await resolveAlert(id, status, note)
      setAlerts((prev) => prev.filter((a) => a.id !== id))
    } catch {
      alert('فشل في حفظ القرار')
    }
  }

  if (loading || !alerts.length) return null

  const categoryColors = {
    BUDGET_OVERRUN: 'border-r-red-500',
    DIESEL_ANOMALY: 'border-r-orange-500',
    LABOR_EXCESS: 'border-r-yellow-500',
    MATERIAL_WASTE: 'border-r-purple-500',
    OTHER: 'border-r-gray-500',
  }

  const categoryEmoji = {
    BUDGET_OVERRUN: '📊',
    DIESEL_ANOMALY: '⛽',
    LABOR_EXCESS: '👷',
    MATERIAL_WASTE: '📦',
    OTHER: '⚠️',
  }

  return (
    <div className="bg-white dark:bg-slate-800 shadow rounded-lg p-6 mb-6">
      <h2 className="text-xl font-bold mb-4 text-gray-800 dark:text-white flex items-center">
        <span className="text-2xl ml-2">🔍</span>
        رادار الانحرافات (Shadow ERP)
        <span className="mr-auto text-sm font-normal bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 px-3 py-1 rounded-full">
          {alerts.length} تنبيه جديد
        </span>
      </h2>

      <div className="grid gap-4 md:grid-cols-2">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className={`bg-gray-50 dark:bg-slate-700 rounded-lg p-4 border-r-4 ${
              categoryColors[alert.category] || 'border-r-gray-500'
            }`}
          >
            <div className="flex justify-between items-start mb-2">
              <span className="text-lg">{categoryEmoji[alert.category] || '⚠️'}</span>
              <span className="text-xs text-gray-500 dark:text-slate-400">
                {new Date(alert.created_at).toLocaleDateString('ar-YE')}
              </span>
            </div>

            <h3 className="font-semibold text-gray-800 dark:text-white mb-1">
              {alert.activity_name}
            </h3>

            <p className="text-sm text-gray-600 dark:text-slate-300 mb-2">{alert.alert_message}</p>

            <div className="flex justify-between text-xs text-gray-500 dark:text-slate-400 mb-3">
              <span>المخطط: {Number(alert.planned_cost).toLocaleString()}</span>
              <span className="text-red-600 dark:text-red-400 font-bold">
                الفعلي: {Number(alert.actual_cost).toLocaleString()}
              </span>
              <span>الانحراف: {alert.variance_percentage}%</span>
            </div>

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => handleResolve(alert.id, 'RESOLVED_JUSTIFIED')}
                className="px-3 py-1 text-xs bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded hover:bg-green-200 dark:hover:bg-green-800 transition-colors"
              >
                ✅ مبرر
              </button>
              <button
                onClick={() => handleResolve(alert.id, 'RESOLVED_PENALIZED')}
                className="px-3 py-1 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-800 transition-colors"
              >
                ❌ تغريم
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Original Financial Risk Zone ─────────────────────────────────
function RiskDashboard({ farmId, cropId }) {
  const [anomalies, setAnomalies] = useState([])
  const [loading, setLoading] = useState(true)
  const [_error, setError] = useState(null)

  useEffect(() => {
    async function fetchRiskData() {
      if (!farmId || !cropId) return
      setLoading(true)
      try {
        const data = await getFinancialRiskZone(farmId, cropId)
        setAnomalies(data)
      } catch (err) {
        setError('فشل في تحميل بيانات المخاطر')
      } finally {
        setLoading(false)
      }
    }
    fetchRiskData()
  }, [farmId, cropId])

  return (
    <>
      {/* Shadow Variance Radar (Phase 4 — YECO Hybrid) */}
      <ShadowVarianceRadar farmId={farmId} />

      {/* Existing financial risk zone */}
      {loading && (
        <div className="p-4 text-center dark:text-slate-400">جاري تحميل تحليل المخاطر...</div>
      )}

      {!loading && anomalies && anomalies.length > 0 && (
        <div className="bg-white dark:bg-slate-800 shadow rounded-lg p-6 mb-6 border-r-4 border-red-500">
          <h2 className="text-xl font-bold mb-4 text-gray-800 dark:text-white flex items-center">
            <span className="text-2xl ml-2">⚠️</span>
            منطقة الخطر المالي
          </h2>

          <div className="overflow-x-auto">
            <table className="min-w-full leading-normal">
              <thead>
                <tr>
                  <th className="px-5 py-3 border-b-2 border-gray-200 dark:border-slate-700 bg-gray-100 dark:bg-slate-700 text-end text-xs font-semibold text-gray-600 dark:text-slate-300 uppercase tracking-wider">
                    المهمة
                  </th>
                  <th className="px-5 py-3 border-b-2 border-gray-200 dark:border-slate-700 bg-gray-100 dark:bg-slate-700 text-end text-xs font-semibold text-gray-600 dark:text-slate-300 uppercase tracking-wider">
                    التاريخ
                  </th>
                  <th className="px-5 py-3 border-b-2 border-gray-200 dark:border-slate-700 bg-gray-100 dark:bg-slate-700 text-end text-xs font-semibold text-gray-600 dark:text-slate-300 uppercase tracking-wider">
                    التكلفة
                  </th>
                  <th className="px-5 py-3 border-b-2 border-gray-200 dark:border-slate-700 bg-gray-100 dark:bg-slate-700 text-end text-xs font-semibold text-gray-600 dark:text-slate-300 uppercase tracking-wider">
                    المتوسط
                  </th>
                  <th className="px-5 py-3 border-b-2 border-gray-200 dark:border-slate-700 bg-gray-100 dark:bg-slate-700 text-end text-xs font-semibold text-gray-600 dark:text-slate-300 uppercase tracking-wider">
                    الانحراف
                  </th>
                  <th className="px-5 py-3 border-b-2 border-gray-200 dark:border-slate-700 bg-gray-100 dark:bg-slate-700 text-center text-xs font-semibold text-gray-600 dark:text-slate-300 uppercase tracking-wider">
                    مستوى الخطر
                  </th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((item) => (
                  <tr key={item.activity_id}>
                    <td className="px-5 py-5 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm">
                      <p className="text-gray-900 dark:text-white whitespace-no-wrap">
                        {item.task_name}
                      </p>
                    </td>
                    <td className="px-5 py-5 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm">
                      <p className="text-gray-900 dark:text-slate-200 whitespace-no-wrap">
                        {item.date}
                      </p>
                    </td>
                    <td className="px-5 py-5 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm font-bold text-red-600 dark:text-red-400">
                      {Number(item.cost_total).toLocaleString()}
                    </td>
                    <td className="px-5 py-5 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm dark:text-slate-300">
                      {Number(item.mean).toLocaleString()}
                    </td>
                    <td className="px-5 py-5 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-red-500 dark:text-red-400">
                      +{Number(item.deviation).toLocaleString()}
                    </td>
                    <td className="px-5 py-5 border-b border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-center">
                      <span
                        className={`relative inline-block px-3 py-1 font-semibold leading-tight ${item.risk_score > 3 ? 'text-red-900 dark:text-red-300' : 'text-orange-900 dark:text-orange-300'}`}
                      >
                        <span
                          aria-hidden
                          className={`absolute inset-0 opacity-50 rounded-full ${item.risk_score > 3 ? 'bg-red-200 dark:bg-red-800' : 'bg-orange-200 dark:bg-orange-800'}`}
                        ></span>
                        <span className="relative">{item.risk_score}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  )
}

export default RiskDashboard
