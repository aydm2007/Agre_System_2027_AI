import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useFarmContext } from '../api/farmContext.jsx'
import FeedbackRegion from '../components/FeedbackRegion'
import useFeedback from '../hooks/useFeedback'

export default function SharecroppingReceipts() {
  const { hasFarmRole, is_superuser, isAdmin } = useAuth()
  const { selectedFarmId } = useFarmContext()
  const [receipts, setReceipts] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const { message, error, showError } = useFeedback()

  const loadReceipts = useCallback(async () => {
    setLoading(true)
    try {
      let url = '/sharecropping-receipts/?ordering=-receipt_date'
      if (selectedFarmId) url += `&farm_id=${selectedFarmId}`
      if (filterType) url += `&receipt_type=${filterType}`
      if (filterStatus) url += `&is_posted=${filterStatus}`
      if (searchQuery) url += `&search=${searchQuery}`

      const res = await api.get(url)
      setReceipts(res.data?.results ?? res.data ?? [])
    } catch (err) {
      console.error(err)
      showError('فشل تحميل سندات الشراكة')
    } finally {
      setLoading(false)
    }
  }, [showError, filterType, filterStatus, searchQuery, selectedFarmId])

  useEffect(() => {
    loadReceipts()
  }, [loadReceipts])

  const handlePrint = (receipt) => {
    // [AGRI-GUARDIAN] Audit-compliant printing placeholder
    const printWindow = window.open('', '_blank')
    printWindow.document.write(`
            <html dir="rtl" lang="ar">
            <head>
                <title>طباعة السند #${receipt.id}</title>
                <style>
                    body { font-family: sans-serif; padding: 40px; }
                    .header { text-align: center; border-bottom: 2px solid #000; padding-bottom: 20px; margin-bottom: 20px;}
                    .detail-row { margin-bottom: 10px; font-size: 16px; }
                    .footer { margin-top: 50px; text-align: center; font-size: 14px; color: #555; border-top: 1px solid #ccc; padding-top: 20px;}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>سند استلام شراكة ومناصبة</h2>
                    <h3>مزرعة: ${receipt.farm_name}</h3>
                </div>
                <div class="detail-row"><strong>رقم السند:</strong> #${receipt.id}</div>
                <div class="detail-row"><strong>التاريخ:</strong> ${new Date(receipt.receipt_date).toLocaleDateString()}</div>
                <div class="detail-row"><strong>اسم الشريك/المزارع:</strong> ${receipt.farmer_name}</div>
                <div class="detail-row"><strong>نوع السند:</strong> ${receipt.receipt_type === 'FINANCIAL' ? 'مالي (نقدي)' : 'عيني (كمية)'}</div>
                <div class="detail-row"><strong>الكمية/القيمة:</strong> ${receipt.receipt_type === 'FINANCIAL' ? Number(receipt.amount_received).toLocaleString() + ' ريال' : receipt.quantity_received_kg + ' KG'}</div>
                <div class="detail-row"><strong>المستودع/الخزينة:</strong> ${receipt.receipt_type === 'PHYSICAL' ? receipt.destination_inventory_name || 'المستودع العام' : 'الخزينة العامة'}</div>
                <div class="detail-row"><strong>ملاحظات النظام:</strong> ${receipt.notes || 'لا يوجد'}</div>
                
                <div class="footer">
                    تم إنشاء هذا السند آلياً عبر نظام إدارة المزارع. (موثق)
                </div>
                <script>
                    window.onload = function() { window.print(); window.close(); }
                </script>
            </body>
            </html>
        `)
    printWindow.document.close()
  }

  const canManager =
    is_superuser || isAdmin || (hasFarmRole && (hasFarmRole('المدير المالي لقطاع المزارع') || hasFarmRole('رئيس حسابات القطاع') || hasFarmRole('مدير القطاع')))

  if (!canManager) {
    return (
      <div className="p-8 text-center text-red-600 dark:text-red-400">
        <h2>عذراً، لاتمتلك صلاحية الوصول لهذه الصفحة.</h2>
      </div>
    )
  }

  return (
    <section className="space-y-4">
      <FeedbackRegion error={error} message={message} />
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            سندات متحصلات الشراكة
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            عرض متحصلات الشراكة والمناصبة بنوعيها (المالي والعيني) مع دعم الفلترة المتقدمة
          </p>
        </div>
      </div>

      <div className="shadow-lg border-0 dark:bg-slate-800/80 mt-6 rounded-xl overflow-hidden bg-white">
        <div className="border-b dark:border-slate-700 pb-3 flex flex-col md:flex-row md:items-center justify-between gap-4 p-6">
          <h3 className="text-lg font-bold">سجل السندات</h3>
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              placeholder="بحث باسم الشريك..."
              className="text-sm p-2 border rounded dark:bg-slate-900 dark:border-slate-700 dark:text-white"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <select
              className="text-sm p-2 border rounded dark:bg-slate-900 dark:border-slate-700 dark:text-white"
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
            >
              <option value="">كل الأنواع</option>
              <option value="FINANCIAL">مالي (نقدي)</option>
              <option value="PHYSICAL">عيني (كمية)</option>
            </select>
            <select
              className="text-sm p-2 border rounded dark:bg-slate-900 dark:border-slate-700 dark:text-white"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="">كل الحالات</option>
              <option value="True">مُرحل</option>
              <option value="False">مسودة</option>
            </select>
            <button
              onClick={loadReceipts}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors text-sm"
            >
              تطبيق وبحث
            </button>
          </div>
        </div>
        <div className="pt-4 p-6">
          {loading ? (
            <div className="py-8 text-center text-gray-500">جاري التحميل...</div>
          ) : receipts.length === 0 ? (
            <div className="py-8 text-center text-gray-500">
              لا توجد سندات استلام مسجلة حتى الآن.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-right rtl">
                <thead className="bg-slate-50 dark:bg-slate-900/50 text-slate-700 dark:text-slate-300">
                  <tr>
                    <th className="px-4 py-3 font-semibold rounded-tr-lg">رقم السند</th>
                    <th className="px-4 py-3 font-semibold">التاريخ</th>
                    <th className="px-4 py-3 font-semibold">المزرعة</th>
                    <th className="px-4 py-3 font-semibold">اسم الشريك</th>
                    <th className="px-4 py-3 font-semibold">النوع</th>
                    <th className="px-4 py-3 font-semibold">الكمية/القيمة</th>
                    <th className="px-4 py-3 font-semibold">المستودع/الوجهة</th>
                    <th className="px-4 py-3 font-semibold">حالة الترحيل</th>
                    <th className="px-4 py-3 font-semibold rounded-tl-lg">إجراءات</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                  {receipts.map((r) => (
                    <tr
                      key={r.id}
                      className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                    >
                      <td className="px-4 py-3 text-slate-900 dark:text-slate-200 font-medium">
                        #{r.id}
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                        {r.receipt_date}
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                        {r.farm_name}
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                        {r.farmer_name}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${r.receipt_type === 'FINANCIAL'
                              ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                              : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
                            }`}
                        >
                          {r.receipt_type === 'FINANCIAL' ? 'نقدي/مالي' : 'عيني/كمية'}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-200">
                        {r.receipt_type === 'FINANCIAL' ? (
                          <span className="text-amber-600 dark:text-amber-500">
                            {Number(r.amount_received).toLocaleString()} ريال
                          </span>
                        ) : (
                          <span className="text-emerald-600 dark:text-emerald-500">
                            {r.quantity_received_kg} KG
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                        {r.receipt_type === 'PHYSICAL'
                          ? r.destination_inventory_name || 'موجه للمخزن العام'
                          : 'الخزينة العامة (استحقاق)'}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${r.is_posted
                              ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300'
                              : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300'
                            }`}
                        >
                          {r.is_posted ? 'مُرحل' : 'مسودة'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handlePrint(r)}
                          className="text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400 p-1"
                          title="طباعة السند (PDF/ورقي)"
                        >
                          <svg
                            className="w-5 h-5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth="2"
                              d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
                            />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
