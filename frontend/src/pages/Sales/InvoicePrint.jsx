import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Sales } from '../../api/client'
import { ArrowRight, Printer } from 'lucide-react'
import { toast } from 'react-hot-toast'

/**
 * Professional Sales Invoice Print Template
 * نموذج طباعة فاتورة المبيعات الاحترافي
 * Agri-Guardian Compliant
 */
export default function InvoicePrint() {
    const { id } = useParams()
    const navigate = useNavigate()
    const printRef = useRef()
    const [invoice, setInvoice] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const fetchInvoice = async () => {
            try {
                const res = await Sales.get(id)
                setInvoice(res.data)
            } catch (err) {
                toast.error('فشل تحميل الفاتورة')
                navigate('/sales')
            } finally {
                setLoading(false)
            }
        }
        fetchInvoice()
    }, [id, navigate])

    const handlePrint = () => {
        window.print()
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-100 flex items-center justify-center">
                <div className="animate-spin w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full" />
            </div>
        )
    }

    if (!invoice) return null

    const items = invoice.items || []
    const subtotal = items.reduce((sum, item) => sum + Number(item.total || item.qty * item.unit_price || 0), 0)
    const discount = Number(invoice.discount_amount || 0)
    const total = subtotal - discount

    return (
        <div dir="rtl" className="min-h-screen bg-gray-100">
            {/* Print Controls - Hidden when printing */}
            <div className="print:hidden bg-white border-b shadow-sm sticky top-0 z-50">
                <div className="max-w-4xl mx-auto px-6 py-4 flex justify-between items-center">
                    <button
                        onClick={() => navigate('/sales')}
                        className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
                    >
                        <ArrowRight className="w-5 h-5" />
                        <span>العودة للفواتير</span>
                    </button>
                    <div className="flex gap-3">
                        <button
                            onClick={handlePrint}
                            className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 text-white rounded-lg font-bold hover:bg-emerald-500 transition-colors shadow-lg shadow-emerald-500/20"
                        >
                            <Printer className="w-5 h-5" />
                            طباعة
                        </button>
                    </div>
                </div>
            </div>

            {/* Invoice Content */}
            <div className="max-w-4xl mx-auto p-8 print:p-0 print:max-w-none">
                <div
                    ref={printRef}
                    className="bg-white rounded-2xl shadow-xl print:shadow-none print:rounded-none overflow-hidden"
                >
                    {/* Header */}
                    <div className="bg-gradient-to-l from-emerald-600 to-emerald-700 text-white p-8">
                        <div className="flex justify-between items-start">
                            <div>
                                <h1 className="text-3xl font-black mb-2">فاتورة مبيعات</h1>
                                <p className="text-emerald-100 text-lg">فاتورة مبيعات</p>
                            </div>
                            <div className="text-start">
                                <div className="text-5xl font-black opacity-30">#{invoice.invoice_number}</div>
                                <div className="mt-2 text-emerald-100">
                                    {new Date(invoice.invoice_date || invoice.date).toLocaleDateString('ar-EG', {
                                        year: 'numeric',
                                        month: 'long',
                                        day: 'numeric'
                                    })}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Farm & Customer Info */}
                    <div className="grid grid-cols-2 gap-8 p-8 border-b">
                        <div className="space-y-4">
                            <div className="text-sm text-gray-400 font-medium uppercase tracking-wider">من / From</div>
                            <div>
                                <h3 className="text-xl font-bold text-gray-900">{invoice.farm_name || 'مزرعة المحمدية'}</h3>
                                <p className="text-gray-500 mt-1">{invoice.farm_address || 'المحمدية - صنعاء'}</p>
                                <p className="text-gray-500">هاتف: {invoice.farm_phone || '---'}</p>
                            </div>
                        </div>
                        <div className="space-y-4">
                            <div className="text-sm text-gray-400 font-medium uppercase tracking-wider">إلى / To</div>
                            <div>
                                <h3 className="text-xl font-bold text-gray-900">{invoice.customer_name}</h3>
                                <p className="text-gray-500 mt-1">{invoice.customer_address || '---'}</p>
                                <p className="text-gray-500">هاتف: {invoice.customer_phone || '---'}</p>
                            </div>
                        </div>
                    </div>

                    {/* Items Table */}
                    <div className="p-8">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b-2 border-gray-200">
                                    <th className="py-4 text-end text-sm font-bold text-gray-600 uppercase tracking-wider">#</th>
                                    <th className="py-4 text-end text-sm font-bold text-gray-600 uppercase tracking-wider">المنتج</th>
                                    <th className="py-4 text-center text-sm font-bold text-gray-600 uppercase tracking-wider">الكمية</th>
                                    <th className="py-4 text-center text-sm font-bold text-gray-600 uppercase tracking-wider">الوحدة</th>
                                    <th className="py-4 text-start text-sm font-bold text-gray-600 uppercase tracking-wider">السعر</th>
                                    <th className="py-4 text-start text-sm font-bold text-gray-600 uppercase tracking-wider">الإجمالي</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {items.map((item, idx) => (
                                    <tr key={item.id || idx} className="hover:bg-gray-50">
                                        <td className="py-4 text-gray-400 font-mono">{idx + 1}</td>
                                        <td className="py-4">
                                            <div className="font-semibold text-gray-900">{item.product_name || item.item_name || `منتج ${item.item}`}</div>
                                        </td>
                                        <td className="py-4 text-center font-bold text-gray-900">{Number(item.qty || item.quantity).toLocaleString()}</td>
                                        <td className="py-4 text-center text-gray-500">{item.unit || 'كجم'}</td>
                                        <td className="py-4 text-start text-gray-600">{Number(item.unit_price).toLocaleString()} ریال</td>
                                        <td className="py-4 text-start font-bold text-gray-900">
                                            {Number(item.total || item.qty * item.unit_price).toLocaleString()} ریال
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Totals */}
                    <div className="border-t bg-gray-50 p-8">
                        <div className="flex justify-end">
                            <div className="w-80 space-y-3">
                                <div className="flex justify-between text-gray-600">
                                    <span>المجموع الفرعي</span>
                                    <span className="font-semibold">{subtotal.toLocaleString()} ریال</span>
                                </div>
                                {discount > 0 && (
                                    <div className="flex justify-between text-red-500">
                                        <span>الخصم</span>
                                        <span className="font-semibold">-{discount.toLocaleString()} ریال</span>
                                    </div>
                                )}
                                <div className="flex justify-between text-2xl font-black text-gray-900 pt-4 border-t-2 border-gray-300">
                                    <span>الإجمالي</span>
                                    <span className="text-emerald-600">{total.toLocaleString()} ریال</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="bg-gray-100 p-8 text-center">
                        <div className="flex justify-between items-center border-t border-gray-200 pt-6">
                            <div className="text-end space-y-1">
                                <div className="text-sm text-gray-400">توقيع المستلم</div>
                                <div className="w-40 border-b-2 border-gray-300 h-8"></div>
                            </div>
                            <div className="text-center">
                                <div className="text-xs text-gray-400 mb-2">الحالة</div>
                                <span className={`px-4 py-2 rounded-full text-sm font-bold ${invoice.status === 'approved' || invoice.status === 'paid'
                                        ? 'bg-emerald-100 text-emerald-700'
                                        : invoice.status === 'pending' || invoice.status === 'draft'
                                            ? 'bg-amber-100 text-amber-700'
                                            : 'bg-gray-200 text-gray-600'
                                    }`}>
                                    {invoice.status === 'approved' ? 'مؤكدة' :
                                        invoice.status === 'paid' ? 'مدفوعة' :
                                            invoice.status === 'pending' ? 'معلقة' :
                                                invoice.status === 'draft' ? 'مسودة' :
                                                    invoice.status === 'cancelled' ? 'ملغية' : invoice.status}
                                </span>
                            </div>
                            <div className="text-start space-y-1">
                                <div className="text-sm text-gray-400">توقيع البائع</div>
                                <div className="w-40 border-b-2 border-gray-300 h-8"></div>
                            </div>
                        </div>
                        <div className="mt-8 text-xs text-gray-400">
                            <p>شكراً لتعاملكم معنا • Thank you for your business</p>
                            <p className="mt-1">AgriAsset 2025 - نظام إدارة المزارع المتكامل</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Print Styles */}
            <style>{`
        @media print {
          @page {
            size: A4;
            margin: 0;
          }
          body {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          .print\\:hidden {
            display: none !important;
          }
        }
      `}</style>
        </div>
    )
}
