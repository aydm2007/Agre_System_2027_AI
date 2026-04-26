import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { PurchaseOrders } from '../api/client'
import { Plus, Search, CheckCircle, Eye, AlertCircle } from 'lucide-react'
import { toast } from 'react-hot-toast'
import useFinancialFilters from '../hooks/useFinancialFilters'
import FinancialFilterBar from '../components/filters/FinancialFilterBar'

export default function PurchaseOrdersPage() {
  const navigate = useNavigate()
  const { filters, options, loading: filterLoading, setFilter, resetFilters, filterParams } = useFinancialFilters({ dimensions: ['farm'] })
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  const fetchOrders = useCallback(async () => {
    if (!filterParams.farm) return
    try {
      setLoading(true)
      const res = await PurchaseOrders.list(filterParams)
      setOrders(res.data.results || res.data || [])
    } catch (err) {
      toast.error('فشل تحميل طلبات الشراء')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [filterParams])

  useEffect(() => {
    if (filterParams.farm) {
      fetchOrders()
    } else {
      setOrders([])
    }
  }, [fetchOrders, filterParams.farm])

  const handleSubmit = async (id) => {
    if (!window.confirm('هل أنت متأكد من إرسال هذا الطلب للمراجعة الفنية؟')) return
    try {
      await PurchaseOrders.submit(id)
      toast.success('تم إرسال الطلب للاعتماد')
      fetchOrders()
    } catch (err) {
      toast.error('فشل إرسال الطلب للاعتماد')
    }
  }

  const filteredOrders = orders.filter(o => 
    o.vendor_name?.includes(searchTerm) || String(o.id).includes(searchTerm)
  )

  if (!filterParams.farm) {
    return (
      <div dir="rtl" className="app-page flex items-center justify-center">
        <div className="text-center space-y-4 max-w-md">
          <div className="p-4 bg-amber-100 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 rounded-full w-fit mx-auto">
            <AlertCircle className="w-12 h-12" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">يرجى اختيار مزرعة</h2>
          <p className="text-gray-500 dark:text-gray-400">لعرض طلبات الشراء، يجب تحديد المزرعة النشطة.</p>
          <div className="mt-4 flex justify-center">
            <FinancialFilterBar filters={filters} options={options} loading={filterLoading} setFilter={setFilter} onReset={resetFilters} dimensions={['farm']} />
          </div>
        </div>
      </div>
    )
  }

  const getStatusBadge = (status) => {
    switch(status) {
      case 'DRAFT': return <span className="px-3 py-1 rounded-lg text-xs font-bold bg-slate-100 text-slate-600">مسودة</span>
      case 'PENDING_TECHNICAL': return <span className="px-3 py-1 rounded-lg text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">مراجعة فنية</span>
      case 'PENDING_FINANCIAL': return <span className="px-3 py-1 rounded-lg text-xs font-bold bg-orange-500/20 text-orange-400 border border-orange-500/30">مراجعة مالية</span>
      case 'PENDING_DIRECTOR': return <span className="px-3 py-1 rounded-lg text-xs font-bold bg-purple-500/20 text-purple-400 border border-purple-500/30">اعتماد المدير</span>
      case 'APPROVED': return <span className="px-3 py-1 rounded-lg text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">معتمد</span>
      case 'RECEIVED': return <span className="px-3 py-1 rounded-lg text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">مستلم</span>
      case 'CANCELED': case 'REJECTED': return <span className="px-3 py-1 rounded-lg text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">مرفوض/ملغي</span>
      default: return <span className="px-3 py-1 rounded-lg text-xs font-bold bg-slate-100 text-slate-600">{status}</span>
    }
  }

  return (
    <div dir="rtl" className="app-page space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-black tracking-tight bg-gradient-to-r from-emerald-600 dark:from-emerald-400 to-amber-500 dark:to-amber-200 bg-clip-text text-transparent">
            طلبات الشراء
          </h1>
          <p className="text-gray-500 dark:text-zinc-500 font-medium mt-1">إدارة واعتماد المشتريات التشغيلية</p>
        </div>
        <button
          onClick={() => navigate('/purchases/new')}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-emerald-600 text-white font-bold shadow-lg shadow-emerald-500/20 hover:bg-emerald-500 transition-all"
        >
          <Plus className="w-5 h-5" /> طلب شراء جديد
        </button>
      </div>

      <FinancialFilterBar filters={filters} options={options} loading={filterLoading} setFilter={setFilter} onReset={resetFilters} dimensions={['farm']} />

      <div className="app-panel p-4 flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="relative w-full md:w-80">
          <Search className="absolute right-4 top-3 w-5 h-5 text-slate-400 dark:text-white/30" />
          <input
            type="text"
            placeholder="بحث برقم الطلب أو المورد..."
            className="app-input pl-4 pr-12 focus:border-emerald-500/50"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="app-panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-end">
            <thead className="bg-slate-100/90 dark:bg-white/5 text-slate-600 dark:text-white/40 font-bold border-b border-slate-200 dark:border-white/10">
              <tr>
                <th className="px-6 py-4"># الطلب</th>
                <th className="px-6 py-4">المورد</th>
                <th className="px-6 py-4">التاريخ</th>
                <th className="px-6 py-4">الاستلام المتوقع</th>
                <th className="px-6 py-4">الإجمالي</th>
                <th className="px-6 py-4">الحالة</th>
                <th className="px-6 py-4 text-start">إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="7" className="py-16 text-center text-slate-500">جاري التحميل...</td></tr>
              ) : filteredOrders.length === 0 ? (
                <tr><td colSpan="7" className="py-16 text-center text-slate-500">لا توجد طلبات شراء مطابقة</td></tr>
              ) : (
                filteredOrders.map(o => (
                  <tr key={o.id} className="border-t border-slate-200/70 dark:border-white/5 hover:bg-slate-100/70 dark:hover:bg-white/5 transition-colors group">
                    <td className="px-6 py-4 font-mono text-slate-600 dark:text-white/60">PO-{o.id}</td>
                    <td className="px-6 py-4 font-medium text-slate-800 dark:text-white">{o.vendor_name}</td>
                    <td className="px-6 py-4 text-slate-500 dark:text-white/50">{new Date(o.order_date).toLocaleDateString('ar-EG')}</td>
                    <td className="px-6 py-4 text-slate-500 dark:text-white/50">{o.expected_delivery_date ? new Date(o.expected_delivery_date).toLocaleDateString('ar-EG') : 'غير محدد'}</td>
                    <td className="px-6 py-4 font-bold text-emerald-400">{Number(o.total_amount).toLocaleString()} {o.currency}</td>
                    <td className="px-6 py-4">{getStatusBadge(o.status)}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        {o.status === 'DRAFT' && (
                          <button
                            onClick={() => handleSubmit(o.id)}
                            title="إرسال للاعتماد"
                            className="p-2 text-slate-500 hover:text-emerald-500 hover:bg-emerald-500/10 rounded-lg transition-colors"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => navigate(`/purchases/${o.id}`)}
                          className="p-2 text-slate-500 hover:text-blue-500 hover:bg-blue-500/10 rounded-lg transition-colors"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
