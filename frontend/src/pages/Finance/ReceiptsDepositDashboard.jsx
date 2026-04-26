import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRightLeft, CircleDollarSign, FileCheck2, Landmark, ReceiptText } from 'lucide-react'

import api, { Sales } from '../../api/client'
import { useFarmContext } from '../../api/farmContext'
import { useSettings } from '../../contexts/SettingsContext'
import { extractApiError } from '../../utils/errorUtils'

const safeArray = (payload) =>
  Array.isArray(payload) ? payload : Array.isArray(payload?.results) ? payload.results : []

const formatMoney = (value) => {
  const numeric = Number(value || 0)
  if (Number.isNaN(numeric)) {
    return String(value || '0.00')
  }
  return numeric.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function StatCard({ title, value, helper, icon: Icon, tone = 'slate' }) {
  const toneMap = {
    slate: 'border-slate-200 bg-slate-50 text-slate-800',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    amber: 'border-amber-200 bg-amber-50 text-amber-800',
    sky: 'border-sky-200 bg-sky-50 text-sky-800',
  }

  return (
    <div className={`rounded-xl border p-4 ${toneMap[tone] || toneMap.slate}`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-medium">{title}</div>
          <div className="mt-2 text-2xl font-bold" dir="ltr">
            {value}
          </div>
          {helper ? <div className="mt-1 text-xs opacity-80">{helper}</div> : null}
        </div>
        <Icon className="h-6 w-6" />
      </div>
    </div>
  )
}

export default function ReceiptsDepositDashboard() {
  const { selectedFarmId } = useFarmContext()
  const { isStrictMode, costVisibility, visibilityLevel } = useSettings()

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [invoices, setInvoices] = useState([])
  const [transactions, setTransactions] = useState([])

  useEffect(() => {
    const load = async () => {
      if (!selectedFarmId) {
        setInvoices([])
        setTransactions([])
        return
      }

      setLoading(true)
      setError('')
      try {
        const [invoiceResponse, transactionResponse] = await Promise.all([
          Sales.list({ farm: selectedFarmId }),
          api.get('/finance/treasury-transactions/', { params: { farm_id: selectedFarmId } }),
        ])

        setInvoices(safeArray(invoiceResponse.data))
        setTransactions(safeArray(transactionResponse.data))
      } catch (err) {
        console.error(err)
        setError(extractApiError(err, 'Failed to load receipts and deposit control data.'))
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [selectedFarmId])

  const summary = useMemo(() => {
    const approvedInvoices = invoices.filter(
      (invoice) => invoice.status === 'approved' || invoice.status === 'paid',
    )
    const draftInvoices = invoices.filter(
      (invoice) => invoice.status === 'draft' || invoice.status === 'pending',
    )
    const receiptTransactions = transactions.filter((entry) => entry.transaction_type === 'RECEIPT')
    const paymentTransactions = transactions.filter((entry) => entry.transaction_type === 'PAYMENT')

    const approvedAmount = approvedInvoices.reduce(
      (sum, invoice) => sum + Number(invoice.total_amount || 0),
      0,
    )
    const receiptAmount = receiptTransactions.reduce(
      (sum, entry) => sum + Number(entry.amount || 0),
      0,
    )

    return {
      approvedInvoices,
      draftInvoices,
      receiptTransactions,
      paymentTransactions,
      approvedAmount,
      receiptAmount,
      pendingDepositCount: Math.max(approvedInvoices.length - receiptTransactions.length, 0),
    }
  }, [invoices, transactions])

  const showAmounts = costVisibility !== 'ratios_only'

  if (!selectedFarmId) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-amber-900">
        قم باختيار المزرعة أولاً للوصول إلى لوحة المقبوضات والودائع.
      </div>
    )
  }

  return (
    <div className="app-page max-w-7xl mx-auto space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">سجل المقبوضات والودائع المركزي</h1>
          <p className="mt-1 text-sm text-slate-500">
            نموذج موحد للمبيعات المعتمدة، المتحصلات النقدية، والأرصدة البنكية المُودعة.
          </p>
        </div>
        <div
          className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600"
          data-testid="receipts-deposit-policy-banner"
        >
          <span className="font-semibold text-slate-900">الوضع:</span>{' '}
          {isStrictMode ? 'صارم (STRICT)' : 'مبسط (SIMPLE)'} |{' '}
          <span className="font-semibold text-slate-900">الرؤية:</span> {visibilityLevel} |{' '}
          <span className="font-semibold text-slate-900">التكاليف:</span> {costVisibility}
        </div>
      </div>

      {loading ? <div className="text-sm text-slate-500">جاري تحميل لوحة التحكم...</div> : null}
      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="المبيعات المعتمدة"
          value={String(summary.approvedInvoices.length)}
          helper={
            showAmounts
              ? `${formatMoney(summary.approvedAmount)} القيمة المعتمدة الإجمالية`
              : 'حجم العمليات الإدارية'
          }
          icon={FileCheck2}
          tone="emerald"
        />
        <StatCard
          title="مقبوضات الخزينة"
          value={String(summary.receiptTransactions.length)}
          helper={
            showAmounts
              ? `${formatMoney(summary.receiptAmount)} المحصلة بالخزينة`
              : 'عدد حركات الخزينة'
          }
          icon={ReceiptText}
          tone="sky"
        />
        <StatCard
          title="في انتظار الإيداع"
          value={String(summary.pendingDepositCount)}
          helper="المبيعات المعتمدة التي لم يتم التوريد لقيمتها بعد."
          icon={Landmark}
          tone="amber"
        />
        <StatCard
          title="طلبات معلقة"
          value={String(summary.draftInvoices.length)}
          helper="وثائق تجارية أو مسودات تنتظر المراجعة."
          icon={CircleDollarSign}
          tone="slate"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <div>
              <div className="font-semibold text-slate-900">
                مبيعات معتمدة تنتظر التوريد (الاهتمام المالي)
              </div>
              <div className="text-xs text-slate-500">
                في الوضع المبسط (SIMPLE) ستقتصر الرؤية على الحجم التشغيلي فقط.
              </div>
            </div>
            <Link
              to="/sales"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700"
            >
              فتح المبيعات
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table
              className="min-w-full divide-y divide-slate-200"
              data-testid="receipts-deposit-invoices-table"
            >
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                    الفاتورة
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                    العميل
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                    الحالة
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                    الموقف المالي
                  </th>
                  {isStrictMode && (
                    <th
                      className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500"
                      data-testid="receipts-deposit-amount-column"
                    >
                      المبلغ
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {summary.approvedInvoices.length === 0 ? (
                  <tr>
                    <td
                      colSpan={isStrictMode ? 5 : 4}
                      className="px-4 py-10 text-center text-sm text-slate-500"
                    >
                      لا توجد فواتير معتمدة بانتظار التعامل في هذا المزرعة.
                    </td>
                  </tr>
                ) : (
                  summary.approvedInvoices.slice(0, 8).map((invoice) => (
                    <tr key={invoice.id}>
                      <td className="px-4 py-4 text-sm font-semibold text-slate-900">
                        #{invoice.invoice_number || invoice.id}
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-700">
                        {invoice.customer_name || '-'}
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-600">{invoice.status === 'approved' ? 'معتمد' : invoice.status === 'paid' ? 'مدفوع' : invoice.status}</td>
                      <td className="px-4 py-4 text-sm text-slate-600">
                        {invoice.status === 'paid'
                          ? 'الدورة التجارية مغلقة.'
                          : 'الفاتورة معتمدة؛ يرجى تتبع التحصيل أو الإيداع.'}
                      </td>
                      {isStrictMode && (
                        <td className="px-4 py-4 text-sm font-semibold text-emerald-700" dir="ltr">
                          {showAmounts ? formatMoney(invoice.total_amount) : 'رؤية محجوبة (صلاحية)'}
                        </td>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <div>
              <div className="font-semibold text-slate-900">سلسلة المقبوضات النقدية والبنكية</div>
              <div className="text-xs text-slate-500">
                حركات الاستلام والدفعات الملموسة المتعلقة بالمزرعة المحددة.
              </div>
            </div>
            <Link
              to="/finance/treasury/transactions"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700"
            >
              فتح الخزينة
            </Link>
          </div>
          <div className="divide-y divide-slate-100">
            {transactions.length === 0 ? (
              <div className="px-4 py-10 text-center text-sm text-slate-500">
                لا توجد حركات خزانة مسجلة بعد.
              </div>
            ) : (
              transactions.slice(0, 8).map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-start justify-between gap-4 px-4 py-4 text-sm"
                >
                  <div>
                    <div className="font-medium text-slate-900">
                      {entry.transaction_type === 'RECEIPT' ? 'مقبوض' : entry.transaction_type === 'PAYMENT' ? 'دفعة' : entry.transaction_type}
                    </div>
                    <div className="mt-1 text-slate-500">
                      {entry.reference || entry.note || '-'}
                    </div>
                  </div>
                  <div className="text-left">
                    <div className="font-semibold text-slate-800" dir="ltr">
                      {showAmounts ? formatMoney(entry.amount) : 'رؤية محجوبة (صلاحية)'}
                    </div>
                    <div className="mt-1 text-xs text-slate-500">
                      {entry.transaction_type === 'RECEIPT'
                        ? 'عملية تحصيل مسجلة بالصندوق/البنك.'
                        : 'تحرك مالي آخر غير محصل.'}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
        <div className="flex items-center gap-2 font-semibold text-slate-900">
          <ArrowRightLeft className="h-4 w-4" />
          ملاحظة الحوكمة والتشغيل
        </div>
        <div className="mt-2">
          الوضع المبسط (SIMPLE) يعرض مخاطر الإيداع المالي والعمليات الضرورية فقط للمشرفين. وضع (STRICT) يعرض كامل الأرقام والمبالغ مع حجب الإجمالي لمن لا يمتلك الصلاحيات.
        </div>
      </div>
    </div>
  )
}
