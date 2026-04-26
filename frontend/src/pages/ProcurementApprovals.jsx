import { useCallback, useEffect, useState } from 'react'
import { PurchaseOrders } from '../api/client'
import { CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react'
import { useFarmContext } from '../api/farmContext.jsx'

const STATUS_LABELS = {
  DRAFT: 'مسودة',
  PENDING_TECHNICAL: 'قيد المراجعة الفنية',
  PENDING_FINANCIAL: 'قيد المراجعة المالية',
  PENDING_DIRECTOR: 'قيد اعتماد المدير',
  APPROVED: 'معتمد',
  REJECTED: 'مرفوض',
  RECEIVED: 'مستلم',
  CANCELED: 'ملغي',
}

const STATUS_COLORS = {
  DRAFT: 'bg-gray-100 text-gray-800',
  PENDING_TECHNICAL: 'bg-yellow-100 text-yellow-800',
  PENDING_FINANCIAL: 'bg-orange-100 text-orange-800',
  PENDING_DIRECTOR: 'bg-purple-100 text-purple-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
  RECEIVED: 'bg-blue-100 text-blue-800',
  CANCELED: 'bg-slate-200 text-slate-800',
}

export default function ProcurementApprovals() {
  const { selectedFarmId } = useFarmContext()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const loadOrders = useCallback(async () => {
    if (!selectedFarmId) {
      setOrders([])
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await PurchaseOrders.list({ farm_id: selectedFarmId })
      const data = res.data?.results || res.data || []
      setOrders(data.filter((po) => !['DRAFT', 'CANCELED', 'RECEIVED'].includes(po.status)))
    } catch (err) {
      console.error(err)
      setError('تعذر تحميل طلبات الشراء.')
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId])

  useEffect(() => {
    loadOrders()
  }, [loadOrders])

  const handleApprove = async (id, role) => {
    setError('')
    setMessage('')
    try {
      await PurchaseOrders.approve(id, role)
      setMessage('تم تسجيل الاعتماد بنجاح.')
      loadOrders()
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || 'فشل الاعتماد. تحقق من صلاحياتك.')
    }
  }

  const formatMoney = (amount) => {
    if (!amount) return '0.00'
    return Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2 })
  }

  return (
    <div className="space-y-6">
      <div className="flex bg-white dark:bg-slate-800 p-4 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-primary" />
            لجنة المشتريات (Procurement Approvals)
          </h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            المراجعة والاعتماد متعدد المستويات لطلبات الشراء
          </p>
        </div>
      </div>

      {message && (
        <div className="p-4 bg-green-50 text-green-700 rounded-lg flex gap-2">
          <CheckCircle2 className="w-5 h-5" />
          {message}
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg flex gap-2">
          <AlertTriangle className="w-5 h-5" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full py-12 text-center text-gray-500">جاري تحميل الطلبات...</div>
        ) : orders.length === 0 ? (
          <div className="col-span-full py-12 text-center bg-white dark:bg-slate-800 rounded-xl border border-dashed border-gray-300">
            <ShieldCheck className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 font-medium">لا توجد طلبات شراء بانتظار الاعتماد حالياً.</p>
          </div>
        ) : (
          orders.map((order) => (
            <div
              key={order.id}
              className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border overflow-hidden flex flex-col"
            >
              <div className="p-4 border-b flex justify-between items-start">
                <div>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${STATUS_COLORS[order.status]}`}
                  >
                    {STATUS_LABELS[order.status] || order.status}
                  </span>
                  <h3 className="text-lg font-bold mt-2">المورد: {order.vendor_name}</h3>
                  <p className="text-sm text-gray-500 mt-1">PO-{order.id}</p>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold font-mono text-primary ltr inline-block">
                    {formatMoney(order.total_amount)}
                  </div>
                  <div className="text-xs text-gray-400">{order.currency}</div>
                </div>
              </div>

              <div className="p-4 flex-1 space-y-3">
                <div className="flex justify-between items-center text-sm border-b pb-2">
                  <span className="text-gray-500">تاريخ الطلب:</span>
                  <span className="font-medium">{order.order_date}</span>
                </div>
                <div className="flex justify-between items-center text-sm border-b pb-2">
                  <span className="text-gray-500">لجنة المشتريات:</span>
                  <span className="font-medium text-xs">
                    {order.is_high_value ? 'يتطلب 3 توقيعات (قيمة عالية)' : 'اعتماد تقني فقط'}
                  </span>
                </div>

                <div className="mt-4">
                  <h4 className="text-xs font-bold text-gray-500 mb-2">سجل التوقيعات:</h4>
                  <ul className="text-sm space-y-1">
                    <li className="flex justify-between">
                      <span>الفني:</span>
                      <span
                        className={order.technical_signature ? 'text-green-600' : 'text-gray-400'}
                      >
                        {order.technical_signature ? 'تم التوقيع' : 'في الانتظار'}
                      </span>
                    </li>
                    <li className="flex justify-between">
                      <span>المالي:</span>
                      <span
                        className={order.financial_signature ? 'text-green-600' : 'text-gray-400'}
                      >
                        {order.financial_signature ? 'تم التوقيع' : 'في الانتظار'}
                      </span>
                    </li>
                    <li className="flex justify-between">
                      <span>المدير:</span>
                      <span
                        className={order.director_signature ? 'text-green-600' : 'text-gray-400'}
                      >
                        {order.director_signature ? 'تم التوقيع' : 'في الانتظار'}
                      </span>
                    </li>
                  </ul>
                </div>
              </div>

              <div className="p-4 bg-gray-50 flex gap-2 border-t">
                {order.status === 'PENDING_TECHNICAL' && (
                  <button
                    onClick={() => handleApprove(order.id, 'technical')}
                    className="flex-1 py-2 text-sm text-white bg-blue-600 rounded"
                  >
                    اعتماد فني
                  </button>
                )}
                {order.status === 'PENDING_FINANCIAL' && (
                  <button
                    onClick={() => handleApprove(order.id, 'financial')}
                    className="flex-1 py-2 text-sm text-white bg-orange-600 rounded"
                  >
                    اعتماد مالي
                  </button>
                )}
                {order.status === 'PENDING_DIRECTOR' && (
                  <button
                    onClick={() => handleApprove(order.id, 'director')}
                    className="flex-1 py-2 text-sm text-white bg-purple-600 rounded"
                  >
                    اعتماد المدير
                  </button>
                )}
                {order.status === 'APPROVED' && (
                  <div className="flex-1 text-center py-2 text-sm text-green-600 font-bold">
                    اعتمد نهائياً
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
