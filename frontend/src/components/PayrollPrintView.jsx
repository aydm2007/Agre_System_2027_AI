import { useRef } from 'react'
import { Printer, X } from 'lucide-react'
import { toDecimal } from '../../utils/decimal'

export default function PayrollPrintView({ slip, farm, onClose }) {
  const printRef = useRef(null)

  if (!slip) return null

  const handlePrint = () => {
    const content = printRef.current
    const win = window.open('', '', 'width=800,height=600')
    win.document.write(`
      <html dir="rtl"><head><title>كشف راتب</title>
      <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; margin: 20px; direction: rtl; }
        .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 12px; margin-bottom: 16px; }
        .header h1 { font-size: 20px; margin: 0; }
        .header p { color: #666; margin: 4px 0; }
        table { width: 100%; border-collapse: collapse; margin: 12px 0; }
        th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: right; }
        th { background: #f5f5f5; font-weight: 600; }
        .total-row td { font-weight: 700; background: #fafafa; }
        .net-row td { font-weight: 700; background: #e6f7e6; font-size: 16px; }
        .footer { margin-top: 24px; font-size: 12px; color: #999; text-align: center; }
        .signatures { display: flex; justify-content: space-between; margin-top: 40px; }
        .sig-box { text-align: center; width: 30%; }
        .sig-line { border-top: 1px solid #333; margin-top: 40px; padding-top: 4px; }
        @media print { body { margin: 0; } }
      </style></head><body>
      ${content.innerHTML}
      </body></html>
    `)
    win.document.close()
    win.print()
  }

  const basic = toDecimal(slip.basic_amount, 2)
  const overtime = toDecimal(slip.overtime_amount, 2)
  const allowances = toDecimal(slip.allowances_amount, 2)
  const deductions = toDecimal(slip.deductions_amount, 2)
  const gross = basic + overtime + allowances
  const net = toDecimal(slip.net_pay, 2)

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Toolbar */}
        <div className="flex items-center justify-between bg-gray-100 px-4 py-2 rounded-t-xl">
          <span className="text-sm font-medium text-gray-700">معاينة كشف الراتب</span>
          <div className="flex gap-2">
            <button
              onClick={handlePrint}
              className="flex items-center gap-1 px-3 py-1 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700"
            >
              <Printer className="w-3 h-3" /> طباعة
            </button>
            <button onClick={onClose} className="p-1 text-gray-500 hover:text-gray-800">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Printable content */}
        <div ref={printRef} className="p-6 text-gray-900" dir="rtl">
          <div className="header">
            <h1>كشف راتب زراعي</h1>
            <p>
              {farm?.name || 'المزرعة'} — الفترة: {slip.run?.period_start} إلى{' '}
              {slip.run?.period_end}
            </p>
          </div>

          <table>
            <tbody>
              <tr>
                <th style={{ width: '40%' }}>الموظف</th>
                <td>{slip.employee_name}</td>
              </tr>
              <tr>
                <th>رقم الموظف</th>
                <td>{slip.employee_id}</td>
              </tr>
              <tr>
                <th>أيام العمل</th>
                <td>{slip.days_worked}</td>
              </tr>
            </tbody>
          </table>

          <table>
            <thead>
              <tr>
                <th>البند</th>
                <th>المبلغ (ر.ي)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>الراتب الأساسي (الصُرات)</td>
                <td>{basic.toLocaleString('ar-YE')}</td>
              </tr>
              <tr>
                <td>العمل الإضافي</td>
                <td>{overtime.toLocaleString('ar-YE')}</td>
              </tr>
              <tr>
                <td>البدلات</td>
                <td>{allowances.toLocaleString('ar-YE')}</td>
              </tr>
              <tr className="total-row">
                <td>إجمالي المستحقات</td>
                <td>{gross.toLocaleString('ar-YE')}</td>
              </tr>
              <tr>
                <td>الخصومات (سلفيات + غياب)</td>
                <td style={{ color: '#c00' }}>({deductions.toLocaleString('ar-YE')})</td>
              </tr>
              <tr className="net-row">
                <td>صافي الراتب</td>
                <td>{net.toLocaleString('ar-YE')}</td>
              </tr>
            </tbody>
          </table>

          <div className="signatures">
            <div className="sig-box">
              <div className="sig-line">المشرف الميداني</div>
            </div>
            <div className="sig-box">
              <div className="sig-line">المدير المالي</div>
            </div>
            <div className="sig-box">
              <div className="sig-line">المستلم</div>
            </div>
          </div>

          <div className="footer">
            تم إنشاؤه بواسطة AgriAsset ERP — {new Date().toLocaleDateString('ar-YE')}
          </div>
        </div>
      </div>
    </div>
  )
}
