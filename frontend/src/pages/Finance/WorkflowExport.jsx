import { useCallback, useEffect, useState } from 'react'
import api from '../../api/client'
import { useFarmContext } from '../../api/farmContext'
import { useAuth } from '../../auth/AuthContext'
import { extractApiError } from '../../utils/errorUtils'

export default function WorkflowExport() {
  const { selectedFarmId } = useFarmContext()
  const { hasPermission, isSuperuser, isAdmin } = useAuth()
  const [requests, setRequests] = useState([])
  const [batches, setBatches] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const canApprove = isSuperuser || isAdmin || hasPermission('can_approve_finance_request')
  const canExport = isSuperuser || isAdmin || hasPermission('can_sector_finance_approve')

  const load = useCallback(async () => {
    if (!selectedFarmId) return
    setLoading(true)
    setError('')
    try {
      const [reqRes, batchRes] = await Promise.all([
        api.get('/finance/approval-requests/', { params: { farm: selectedFarmId } }),
        api.get('/integrations/finance-batches/', { params: { farm: selectedFarmId } }),
      ])
      setRequests(reqRes.data?.results || reqRes.data || [])
      setBatches(batchRes.data?.results || batchRes.data || [])
    } catch (err) {
      console.error(err)
      setError('تعذر تحميل بيانات الموافقات والتكامل المالي.')
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId])

  useEffect(() => {
    load()
  }, [load])

  const postAction = async (url, payload = {}) => {
    setError('')
    setMessage('')
    try {
      await api.post(url, payload)
      setMessage('تمت العملية بنجاح.')
      await load()
    } catch (err) {
      console.error(err)
      setError(extractApiError(err, 'فشلت العملية.'))
    }
  }

  const createBatch = async () => {
    if (!selectedFarmId) return
    const now = new Date()
    const start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
    const end = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10)
    await postAction('/integrations/finance-batches/', {
      farm: Number(selectedFarmId),
      period_start: start,
      period_end: end,
    })
  }

  return (
    <div className="app-page space-y-6" dir="rtl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">الموافقات والتكامل المالي</h1>
        <div className="flex gap-2">
          <button onClick={load} className="px-3 py-2 rounded-lg border bg-white">
            تحديث
          </button>
          {canExport && (
            <button
              onClick={createBatch}
              className="px-3 py-2 rounded-lg border bg-emerald-600 text-white"
            >
              إنشاء دفعة ترحيل
            </button>
          )}
        </div>
      </div>

      {loading && <div className="text-sm text-gray-500">جاري التحميل...</div>}
      {message && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-emerald-700">
          {message}
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-rose-700">
          {error}
        </div>
      )}

      <section className="rounded-2xl border bg-white p-4">
        <h2 className="font-bold mb-3">طلبات الموافقة</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-right text-gray-500">
                <th className="p-2">المعرف</th>
                <th className="p-2">الوحدة</th>
                <th className="p-2">الإجراء</th>
                <th className="p-2">المبلغ</th>
                <th className="p-2">الحالة</th>
                <th className="p-2">المطلوب</th>
                <th className="p-2">إجراء</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((req) => (
                <tr key={req.id} className="border-t">
                  <td className="p-2">{req.id}</td>
                  <td className="p-2">{req.module}</td>
                  <td className="p-2">{req.action}</td>
                  <td className="p-2">{req.requested_amount}</td>
                  <td className="p-2">{req.status}</td>
                  <td className="p-2">{req.required_role}</td>
                  <td className="p-2">
                    {req.status === 'PENDING' && canApprove ? (
                      <div className="flex gap-2">
                        <button
                          onClick={() =>
                            postAction(`/finance/approval-requests/${req.id}/approve/`)
                          }
                          className="px-2 py-1 rounded border bg-emerald-100 text-emerald-700"
                        >
                          اعتماد
                        </button>
                        <button
                          onClick={() =>
                            postAction(`/finance/approval-requests/${req.id}/reject/`, {
                              reason: 'Rejected by reviewer',
                            })
                          }
                          className="px-2 py-1 rounded border bg-rose-100 text-rose-700"
                        >
                          رفض
                        </button>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-2xl border bg-white p-4">
        <h2 className="font-bold mb-3">دفعات الترحيل الخارجي</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-right text-gray-500">
                <th className="p-2">المعرف</th>
                <th className="p-2">الفترة</th>
                <th className="p-2">الحالة</th>
                <th className="p-2">إجمالي مدين</th>
                <th className="p-2">إجمالي دائن</th>
                <th className="p-2">إجراء</th>
              </tr>
            </thead>
            <tbody>
              {batches.map((batch) => (
                <tr key={batch.id} className="border-t">
                  <td className="p-2">{batch.id}</td>
                  <td className="p-2">
                    {batch.period_start} - {batch.period_end}
                  </td>
                  <td className="p-2">{batch.status}</td>
                  <td className="p-2">{batch.total_debit}</td>
                  <td className="p-2">{batch.total_credit}</td>
                  <td className="p-2">
                    {canExport ? (
                      <div className="flex gap-2">
                        <button
                          onClick={() =>
                            postAction(
                              `/integrations/finance-batches/${batch.id}/build-from-ledger/`,
                            )
                          }
                          className="px-2 py-1 rounded border bg-blue-100 text-blue-700"
                        >
                          بناء وتصدير
                        </button>
                        <button
                          onClick={() =>
                            postAction(`/integrations/finance-batches/${batch.id}/acknowledge/`, {
                              external_ref: `ACK-${batch.id}`,
                            })
                          }
                          className="px-2 py-1 rounded border bg-emerald-100 text-emerald-700"
                        >
                          تأكيد استلام
                        </button>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
