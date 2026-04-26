import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../../api/client'
import { formatMoney } from '../../utils/decimal'
import { extractApiError } from '../../utils/errorUtils'

export default function SalesInvoicePreview() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [invoice, setInvoice] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true
    const load = async () => {
      try {
        setLoading(true)
        const res = await api.get(`/sales-invoices/${id}/`)
        if (!mounted) return
        setInvoice(res?.data || null)
        setError('')
      } catch (err) {
        if (!mounted) return
        const msg = extractApiError(err, 'تعذر تحميل الفاتورة.')
        setError(String(msg))
      } finally {
        if (mounted) setLoading(false)
      }
    }
    load()
    return () => {
      mounted = false
    }
  }, [id])

  const lines = useMemo(() => invoice?.items || [], [invoice])
  const subtotal = useMemo(
    () =>
      lines.reduce(
        (sum, line) =>
          sum + Number(line.total_price ?? Number(line.qty || 0) * Number(line.unit_price || 0)),
        0,
      ),
    [lines],
  )
  const total = Number(invoice?.total_amount ?? subtotal)

  if (loading) {
    return (
      <div dir="rtl" className="app-page">
        <div className="max-w-4xl mx-auto app-panel p-8">جاري تحميل الفاتورة...</div>
      </div>
    )
  }

  if (error || !invoice) {
    return (
      <div dir="rtl" className="app-page">
        <div className="max-w-4xl mx-auto app-panel p-8 text-rose-500">
          {error || 'الفاتورة غير موجودة.'}
        </div>
      </div>
    )
  }

  return (
    <div dir="rtl" className="app-page space-y-6">
      <div className="max-w-5xl mx-auto flex items-center justify-between">
        <h1 className="text-3xl font-black text-slate-900 dark:text-white">
          معاينة فاتورة #{invoice.invoice_number || invoice.id}
        </h1>
        <div className="flex gap-2">
          <button
            onClick={() => navigate(`/sales/${invoice.id}/print`)}
            className="px-4 py-2 rounded-lg bg-emerald-600 text-white font-bold"
          >
            طباعة
          </button>
          <button
            onClick={() => navigate('/sales')}
            className="px-4 py-2 rounded-lg border border-slate-300 dark:border-white/20"
          >
            رجوع
          </button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto app-panel overflow-hidden">
        <div className="p-6 grid md:grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-slate-500">العميل</div>
            <div className="font-bold">{invoice.customer_name || '-'}</div>
          </div>
          <div>
            <div className="text-slate-500">التاريخ</div>
            <div className="font-bold">
              {new Date(invoice.invoice_date || invoice.date).toLocaleDateString('ar-EG')}
            </div>
          </div>
          <div>
            <div className="text-slate-500">الحالة</div>
            <div className="font-bold">{invoice.status || '-'}</div>
          </div>
        </div>

        <div className="overflow-x-auto border-t border-slate-200 dark:border-white/10">
          <table className="w-full text-sm">
            <thead className="bg-slate-100/80 dark:bg-white/5">
              <tr>
                <th className="p-3 text-right">الصنف</th>
                <th className="p-3 text-right">الكمية</th>
                <th className="p-3 text-right">سعر الوحدة</th>
                <th className="p-3 text-right">الإجمالي</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line) => (
                <tr key={line.id} className="border-t border-slate-200 dark:border-white/10">
                  <td className="p-3">
                    {line.product_name || line.item_name || line.description || '-'}
                  </td>
                  <td className="p-3">{line.qty ?? line.quantity ?? '-'}</td>
                  <td className="p-3">{formatMoney(line.unit_price || 0)}</td>
                  <td className="p-3">
                    {formatMoney(
                      line.total_price ?? Number(line.qty || 0) * Number(line.unit_price || 0),
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="p-6 border-t border-slate-200 dark:border-white/10 text-left">
          <div className="text-slate-500">الإجمالي</div>
          <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
            {formatMoney(total)} ريال
          </div>
        </div>
      </div>
    </div>
  )
}
