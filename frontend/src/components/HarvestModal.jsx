import { useState, useEffect } from 'react'
import { Items, Units } from '../api/client'
import { useToast } from './ToastProvider'

export default function HarvestModal({ plan, onClose, onSuccess }) {
  const toast = useToast()
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState([])
  const [units, setUnits] = useState([])

  const [formData, setFormData] = useState({
    crop_plan: plan?.id,
    date: new Date().toISOString().split('T')[0],
    product_item: '',
    qty: '',
    unit: '',
    notes: '',
  })

  const resolveProductUnitId = (item) =>
    item?.unit?.id || item?.unit_id || item?.default_unit?.id || item?.default_unit_id || item?.unit || ''

  useEffect(() => {
    // Load Items (Products) - ideally filtered by crop, but for now all items
    // In a real app we'd filter items by 'product' type or similar
    Items.list({ page_size: 100 })
      .then((res) => {
        const results = Array.isArray(res.data?.results) ? res.data.results : res.data || []
        // Filter attempts to find items matching the crop name to be helpful
        setItems(results)

        // Try to auto-select an item if it matches the crop name
        if (plan?.crop?.name) {
          const match = results.find((i) => i.name.includes(plan.crop.name))
          if (match) {
            setFormData((prev) => ({
              ...prev,
              product_item: match.id,
              unit: String(resolveProductUnitId(match) || ''),
            }))
          }
        }
      })
      .catch(console.error)

    // Load Units
    Units.list({ page_size: 100 })
      .then((res) => {
        setUnits(Array.isArray(res.data?.results) ? res.data.results : res.data || [])
      })
      .catch(console.error)
  }, [plan])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.product_item || !formData.qty) {
      toast.error('يرجى تعبئة المنتج والكمية')
      return
    }

    setLoading(true)
    try {
      // [Protocol XII] Offline Support
      // Use Service to handle Online vs Offline fallback
      const { OfflineHarvestService } = await import('../services/OfflineHarvestService')
      const result = await OfflineHarvestService.recordHarvest(formData)

      if (result.mode === 'offline') {
        toast.warning('تم حفظ الحصاد محلياً (لا يوجد اتصال). سيتم المزامنة لاحقاً 🕒')
      } else {
        toast.success('تم تسجيل الحصاد وتحديث المخزون بنجاح ✅')
      }
      onSuccess()
    } catch (error) {
      console.error(error)
      toast.error('فشل تسجيل الحصاد')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-xl font-bold mb-4 text-gray-800 dark:text-white">تسجيل حصاد جديد</h3>
        <p className="text-sm text-gray-500 dark:text-slate-400 mb-4">
          سيتم إضافة الكمية المحصودة إلى المخزون تلقائياً.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
              محصول الخطة
            </label>
            <div className="flex justify-between items-center mb-1">
              <div className="text-gray-900 dark:text-white font-semibold">{plan?.crop?.name}</div>
              {plan?.expected_yield && (
                <div className="text-sm text-gray-600 dark:text-slate-400">
                  الهدف: {Number(plan.expected_yield).toLocaleString()} {plan.yield_unit || ''}
                </div>
              )}
            </div>

            {plan?.expected_yield && (
              <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-2.5 mb-2">
                <div
                  className="bg-green-600 h-2.5 rounded-full"
                  style={{
                    width: `${Math.min(100, ((plan.total_harvested || 0) / plan.expected_yield) * 100)}%`,
                  }}
                ></div>
              </div>
            )}
            {plan?.expected_yield && (
              <div className="text-xs text-end text-gray-500 dark:text-slate-400 mb-4">
                تم حصاد {Number(plan.total_harvested || 0).toLocaleString()} من{' '}
                {Number(plan.expected_yield).toLocaleString()}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                المنتج (المخزون) *
              </label>
              <select
                className="w-full border dark:border-slate-600 rounded px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={formData.product_item}
                onChange={(e) => {
                  const nextProductId = e.target.value
                  const selectedItem = items.find((item) => String(item.id) === String(nextProductId))
                  setFormData({
                    ...formData,
                    product_item: nextProductId,
                    unit: String(resolveProductUnitId(selectedItem) || formData.unit || ''),
                  })
                }}
              >
                <option value="">اختر المنتج</option>
                {items.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.name} ({i.code})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                التاريخ *
              </label>
              <input
                type="date"
                className="w-full border dark:border-slate-600 rounded px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                الكمية *
              </label>
              <input
                type="number"
                step="0.001"
                className="w-full border dark:border-slate-600 rounded px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={formData.qty}
                onChange={(e) => setFormData({ ...formData, qty: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                الوحدة
              </label>
              <select
                className="w-full border dark:border-slate-600 rounded px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={formData.unit}
                onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
              >
                <option value="">(الافتراضية)</option>
                {units.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name_ar || u.name || u.code} ({u.symbol || u.code || '—'})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
              ملاحظات
            </label>
            <textarea
              className="w-full border dark:border-slate-600 rounded px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              rows="2"
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
            />
          </div>

          <div className="flex justify-end gap-4 mt-8 pt-4 border-t dark:border-slate-700">
            <button
              type="button"
              onClick={onClose}
              className="px-6 h-12 text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg text-lg font-medium"
            >
              إلغاء
            </button>
            <button
              type="submit"
              className="flex-1 h-12 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 text-lg font-bold shadow-lg disabled:opacity-50"
              disabled={loading}
            >
              {loading ? 'جاري الحفظ...' : 'تسجيل الحصاد (Enter)'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
