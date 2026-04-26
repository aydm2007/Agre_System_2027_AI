import { useMemo, useState } from 'react'
import { toast } from 'react-hot-toast'
import { Plus, Trash2, ReceiptText } from 'lucide-react'

const blankLine = () => ({ item: '', qty: '', price: '' })

const toNumber = (value) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

export default function SmartInvoiceForm() {
  const [transactionType, setTransactionType] = useState('INVOICE')
  const [lines, setLines] = useState([blankLine()])

  const totals = useMemo(() => {
    const base = lines.reduce((acc, line) => acc + toNumber(line.qty) * toNumber(line.price), 0)
    const normalized = Number(base.toFixed(4))
    return transactionType === 'RETURN' ? -normalized : normalized
  }, [lines, transactionType])

  const updateLine = (index, field, value) => {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, [field]: value } : line)))
  }

  const addLine = () => setLines((prev) => [...prev, blankLine()])
  const removeLine = (index) => {
    setLines((prev) => (prev.length === 1 ? prev : prev.filter((_, i) => i !== index)))
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    const invalid = lines.some((line) => !line.item || toNumber(line.qty) <= 0 || toNumber(line.price) < 0)
    if (invalid) {
      toast.error('يرجى إدخال مادة، كمية موجبة، وسعر وحدة صالح لكل سطر.')
      return
    }
    toast.success(
      transactionType === 'RETURN'
        ? 'تم تجهيز مردود الشراء. اربطه بنقطة API المخصصة قبل الإنتاج.'
        : 'تم تجهيز فاتورة الشراء. اربط النموذج بنقطة API المخصصة قبل الإنتاج.',
    )
  }

  return (
    <div dir="rtl" className="min-h-screen bg-gray-50 dark:bg-slate-900 p-8">
      <div className="max-w-6xl mx-auto rounded-3xl bg-white dark:bg-zinc-900 border border-gray-200 dark:border-white/10 shadow-xl p-6 space-y-6">
        <div className="flex items-center gap-3">
          <ReceiptText className="w-6 h-6 text-blue-600" />
          <h1 className="text-2xl font-black text-gray-900 dark:text-white">فاتورة شراء ذكية / مردود</h1>
        </div>

        <div className="inline-flex rounded-xl bg-gray-100 dark:bg-white/5 p-1">
          <button
            type="button"
            onClick={() => setTransactionType('INVOICE')}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition ${
              transactionType === 'INVOICE' ? 'bg-blue-600 text-white' : 'text-gray-600 dark:text-white/70'
            }`}
          >
            فاتورة شراء
          </button>
          <button
            type="button"
            onClick={() => setTransactionType('RETURN')}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition ${
              transactionType === 'RETURN' ? 'bg-red-600 text-white' : 'text-gray-600 dark:text-white/70'
            }`}
          >
            مردود مشتريات
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="overflow-x-auto rounded-2xl border border-gray-200 dark:border-white/10">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-white/5">
                <tr>
                  <th className="p-3 text-right">الصنف</th>
                  <th className="p-3 text-right">الكمية</th>
                  <th className="p-3 text-right">سعر الوحدة</th>
                  <th className="p-3 text-right">الإجمالي</th>
                  <th className="p-3" />
                </tr>
              </thead>
              <tbody>
                {lines.map((line, index) => {
                  const lineTotal = (toNumber(line.qty) * toNumber(line.price)).toFixed(4)
                  return (
                    <tr key={`line-${index}`} className="border-t border-gray-100 dark:border-white/10">
                      <td className="p-2">
                        <input
                          type="text"
                          value={line.item}
                          onChange={(e) => updateLine(index, 'item', e.target.value)}
                          className="w-full border border-gray-200 dark:border-white/10 rounded-lg p-2 bg-white dark:bg-white/5"
                          placeholder="مثال: سماد يوريا"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="number"
                          step="0.0001"
                          min="0"
                          value={line.qty}
                          onChange={(e) => updateLine(index, 'qty', e.target.value)}
                          className="w-full border border-gray-200 dark:border-white/10 rounded-lg p-2 bg-white dark:bg-white/5"
                        />
                      </td>
                      <td className="p-2">
                        <input
                          type="number"
                          step="0.0001"
                          min="0"
                          value={line.price}
                          onChange={(e) => updateLine(index, 'price', e.target.value)}
                          className="w-full border border-gray-200 dark:border-white/10 rounded-lg p-2 bg-white dark:bg-white/5"
                        />
                      </td>
                      <td className="p-2 font-mono font-bold">{lineTotal}</td>
                      <td className="p-2">
                        <button
                          type="button"
                          onClick={() => removeLine(index)}
                          className="p-2 text-red-500 hover:bg-red-50 rounded"
                          aria-label="حذف سطر"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <button
            type="button"
            onClick={addLine}
            className="inline-flex items-center gap-2 text-blue-700 dark:text-blue-300 font-bold"
          >
            <Plus className="w-4 h-4" /> إضافة سطر
          </button>

          <div className="rounded-2xl border border-gray-200 dark:border-white/10 p-4 flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-white/60">
              الأثر المحاسبي المتوقع: {transactionType === 'RETURN' ? 'عكس قيد المخزون والمصروف' : 'تحميل مخزون/مصروف'}
            </p>
            <p className={`text-2xl font-black font-mono ${transactionType === 'RETURN' ? 'text-red-600' : 'text-blue-700'}`}>
              {totals.toFixed(4)} ر.ي
            </p>
          </div>

          <button
            type="submit"
            className={`w-full py-3 rounded-xl text-white font-bold ${
              transactionType === 'RETURN' ? 'bg-red-700 hover:bg-red-800' : 'bg-blue-700 hover:bg-blue-800'
            }`}
          >
            {transactionType === 'RETURN' ? 'تأكيد مردود المشتريات' : 'حفظ فاتورة الشراء'}
          </button>
        </form>
      </div>
    </div>
  )
}
