import { useState, useEffect } from 'react'
import { Customers, Sales, Items, Locations } from '../api/client'
import { useToast } from './ToastProvider'
import { toDecimal, lineTotal } from '../utils/decimal'

export default function SaleModal({ planId, onClose, onSuccess }) {
  const toast = useToast()
  const [loading, setLoading] = useState(false)

  const [customers, setCustomers] = useState([])
  const [allItems, setAllItems] = useState([])
  const [locations, setLocations] = useState([])

  const [formData, setFormData] = useState({
    customer: '',
    location: '',
    sale_date: new Date().toISOString().split('T')[0],
    status: 'draft',
    notes: '',
    items: [],
  })

  // Load dependencies
  useEffect(() => {
    const fetchDeps = async () => {
      try {
        const [custRes, itemRes, locRes] = await Promise.all([
          Customers.list({ page_size: 100 }),
          Items.list({ page_size: 1000 }), // Simplified for now
          Locations.list({ page_size: 100 }),
        ])
        setCustomers(custRes.data?.results || custRes.data || [])
        setAllItems(itemRes.data?.results || itemRes.data || [])
        setLocations(locRes.data?.results || locRes.data || [])
      } catch (e) {
        console.error(e)
        // toast.error('Failed to load form data')
      }
    }
    fetchDeps()
  }, [])

  const addItemRow = () => {
    setFormData((prev) => ({
      ...prev,
      items: [...prev.items, { item: '', quantity: 0, unit_price: 0 }],
    }))
  }

  const updateItemRow = (idx, field, val) => {
    const newItems = [...formData.items]
    newItems[idx][field] = val
    setFormData((prev) => ({ ...prev, items: newItems }))
  }

  const removeItemRow = (idx) => {
    setFormData((prev) => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== idx),
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (!planId) throw new Error('No crop plan selected')

      const payload = {
        ...formData,
        crop_plan: planId,
        // [AGRI-GUARDIAN §1.II] Use decimal utilities for financial precision
        items: formData.items.map((i) => ({
          item: i.item,
          quantity: toDecimal(i.quantity, 3),
          unit_price: toDecimal(i.unit_price, 2),
        })),
      }

      await Sales.create(payload)
      toast.success('تم تسجيل المبيعات بنجاح')
      onSuccess?.()
      onClose()
    } catch (error) {
      console.error(error)
      toast.error('فشل تسجيل المبيعات')
    } finally {
      setLoading(false)
    }
  }

  // [AGRI-GUARDIAN §1.II] Use decimal utilities for safe calculation
  const totalAmount = formData.items.reduce((acc, curr) => {
    return acc + lineTotal(curr.quantity, curr.unit_price)
  }, 0)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-4xl rounded-2xl bg-white dark:bg-slate-800 p-6 shadow-2xl">
        <h2 className="mb-6 text-2xl font-bold text-gray-800 dark:text-white">
          تسجيل مبيعات جديدة
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
                العميل
              </label>
              <div className="flex gap-2">
                <select
                  className="w-full rounded border dark:border-slate-600 p-2 bg-white dark:bg-slate-700 dark:text-white"
                  value={formData.customer}
                  onChange={(e) => setFormData({ ...formData, customer: e.target.value })}
                  required
                >
                  <option value="">اختر العميل</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
                {/* Future: Add Customer Button */}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
                تاريخ البيع
              </label>
              <input
                type="date"
                className="w-full rounded border dark:border-slate-600 p-2 bg-white dark:bg-slate-700 dark:text-white"
                value={formData.sale_date}
                onChange={(e) => setFormData({ ...formData, sale_date: e.target.value })}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
                الموقع (مصدر المخزون)
              </label>
              <select
                className="w-full rounded border dark:border-slate-600 p-2 bg-white dark:bg-slate-700 dark:text-white"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                required
              >
                <option value="">اختر الموقع</option>
                {locations.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
                الحالة
              </label>
              <select
                className="w-full rounded border dark:border-slate-600 p-2 bg-white dark:bg-slate-700 dark:text-white"
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              >
                <option value="draft">مسودة</option>
                <option value="confirmed">مؤكدة (يخصم المخزون)</option>
                <option value="paid">مدفوعة (يخصم المخزون)</option>
              </select>
            </div>
          </div>

          <div className="border-t dark:border-slate-700 pt-4">
            <h3 className="font-semibold mb-2 dark:text-white">الأصناف المباعة</h3>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-slate-700 text-end">
                <tr className="dark:text-slate-200">
                  <th className="p-2">الصنف</th>
                  <th className="p-2 w-24">الكمية</th>
                  <th className="p-2 w-32">سعر الوحدة</th>
                  <th className="p-2 w-32">الإجمالي</th>
                  <th className="p-2 w-10"></th>
                </tr>
              </thead>
              <tbody className="dark:text-slate-200">
                {formData.items.map((row, idx) => (
                  <tr key={idx} className="border-b dark:border-slate-700">
                    <td className="p-2">
                      <select
                        className="w-full border dark:border-slate-600 rounded p-1 bg-white dark:bg-slate-700 dark:text-white"
                        value={row.item}
                        onChange={(e) => updateItemRow(idx, 'item', e.target.value)}
                        required
                      >
                        <option value="">اختر الصنف</option>
                        {allItems.map((i) => (
                          <option key={i.id} value={i.id}>
                            {i.name} ({i.uom})
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="p-2">
                      <input
                        type="number"
                        step="0.001"
                        className="w-full border dark:border-slate-600 rounded p-1 bg-white dark:bg-slate-700 dark:text-white"
                        value={row.quantity}
                        onChange={(e) => updateItemRow(idx, 'quantity', e.target.value)}
                        required
                      />
                    </td>
                    <td className="p-2">
                      <input
                        type="number"
                        step="0.01"
                        className="w-full border dark:border-slate-600 rounded p-1 bg-white dark:bg-slate-700 dark:text-white"
                        value={row.unit_price}
                        onChange={(e) => updateItemRow(idx, 'unit_price', e.target.value)}
                        required
                      />
                    </td>
                    <td className="p-2 font-bold">
                      {(row.quantity * row.unit_price).toLocaleString()}
                    </td>
                    <td
                      className="p-2 text-center text-red-500 cursor-pointer"
                      onClick={() => removeItemRow(idx)}
                    >
                      x
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button
              type="button"
              onClick={addItemRow}
              className="mt-2 text-sm text-green-600 dark:text-green-400 font-semibold hover:underline"
            >
              + إضافة صنف
            </button>
          </div>

          <div className="flex justify-between items-center border-t dark:border-slate-700 pt-4">
            <div className="text-xl font-bold dark:text-white">
              الإجمالي الكلي: {totalAmount.toLocaleString()}
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700"
              >
                إلغاء
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? 'جاري الحفظ...' : 'حفظ المبيعات'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
