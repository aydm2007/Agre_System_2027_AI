import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useOfflineData } from '../hooks/useOfflineData'
import { queueSale } from '../offline/dexie_db'
import VirtualizedSelect from './VirtualizedSelect'
import { useSmartDefaults } from '../hooks/useSmartDefaults'
import { useToast } from './ToastProvider'
import { useFarm } from '../context/FarmContext'
import { toDecimal, lineTotal } from '../utils/decimal'

export default function TurboSaleModal({ onClose, onSuccess }) {
  const { currentFarm } = useFarm()
  const farmId = currentFarm?.id

  const { data: customers } = useOfflineData(farmId, 'customers')
  const { data: items } = useOfflineData(farmId, 'items')
  const { defaults, setSmartDefault } = useSmartDefaults()

  // Memoize options for VirtualizedSelect
  const customerOptions = useMemo(
    () => customers?.map((c) => ({ value: c.id, label: c.name })) || [],
    [customers],
  )

  const itemOptions = useMemo(
    () => items?.map((i) => ({ value: i.id, label: `${i.name} (${i.qty || 0})` })) || [],
    [items],
  )

  const [form, setForm] = useState({
    customer: '',
    location: '',
    date: new Date().toISOString().split('T')[0],
    items: [{ item: '', qty: '', unit_price: '', key: Date.now() }],
  })

  const addToast = useToast()
  const [saving, setSaving] = useState(false)
  const [inlineFeedback, setInlineFeedback] = useState('')
  const itemRefs = useRef([])

  const focusFirstItem = useCallback(() => {
    setTimeout(() => {
      itemRefs.current[1]?.focus()
    }, 80)
  }, [])

  // Apply Smart Defaults on mount
  useEffect(() => {
    if (defaults.lastCustomer && !form.customer) {
      setForm((f) => ({ ...f, customer: defaults.lastCustomer }))
    }
  }, [defaults]) // eslint-disable-line react-hooks/exhaustive-deps

  // --- Advanced Keyboard Logic (Protocol XVI) ---
  const handleKeyDown = (e, rowIndex, field) => {
    // Arrow Keys for Navigation (Excel Style)
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const nextRow = rowIndex + 1
      // logic to find inputs in next row...
      if (itemRefs.current[nextRow * 3 + (field === 'qty' ? 1 : 0)]) {
        itemRefs.current[nextRow * 3 + (field === 'qty' ? 1 : 0)].focus()
      }
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      const prevRow = rowIndex - 1
      if (itemRefs.current[prevRow * 3 + (field === 'qty' ? 1 : 0)]) {
        itemRefs.current[prevRow * 3 + (field === 'qty' ? 1 : 0)].focus()
      }
    }

    if (e.key === 'Enter') {
      e.preventDefault()
      if (field === 'qty') {
        addRow()
        setTimeout(() => {
          const nextRow = rowIndex + 1
          if (itemRefs.current[nextRow * 3]) {
            itemRefs.current[nextRow * 3].focus()
          }
        }, 50)
      }
    }
  }

  const addRow = () => {
    setForm((prev) => ({
      ...prev,
      items: [...prev.items, { item: '', qty: '', unit_price: '', key: Date.now() }],
    }))
  }

  const updateRow = (index, field, value) => {
    const newItems = [...form.items]
    newItems[index][field] = value

    if (field === 'item') {
      const selectedItem = items?.find((i) => String(i.id) === String(value))
      if (selectedItem) {
        newItems[index].unit_price = selectedItem.price || 0
      }
    }
    setForm({ ...form, items: newItems })
  }

  const resetForNextInvoice = useCallback(() => {
    setForm((prev) => ({
      ...prev,
      items: [{ item: '', qty: '', unit_price: '', key: Date.now() }],
    }))
    setInlineFeedback('✅ تم الحفظ. جاهز للفاتورة التالية')
    focusFirstItem()
  }, [focusFirstItem])

  const handleSave = useCallback(
    async (mode = 'save-close') => {
      if (saving) {
        return
      }

      if (!form.customer || !form.items.some((i) => i.item && i.qty)) {
        addToast({ intent: 'error', message: 'يرجى تعبئة الحقول المطلوبة' })
        return
      }

      setSaving(true)
      try {
        const payload = {
          farm_id: farmId,
          customer: form.customer,
          sale_date: form.date,
          // [AGRI-GUARDIAN §1.II] Use decimal utilities
          items: form.items
            .filter((i) => i.item && i.qty)
            .map((i) => ({
              item: i.item,
              quantity: toDecimal(i.qty, 3),
              unit_price: toDecimal(i.unit_price, 2),
            })),
        }

        await queueSale(payload)
        setSmartDefault('customer', form.customer)

        onSuccess?.()

        if (mode === 'save-new') {
          resetForNextInvoice()
        } else {
          addToast({ intent: 'success', message: 'تم حفظ الفاتورة في قائمة الانتظار دون اتصال.' })
          onClose()
        }
      } catch (err) {
        addToast({ intent: 'error', message: 'تعذر حفظ الفاتورة.' })
      } finally {
        setSaving(false)
      }
    },
    [addToast, farmId, form, onClose, onSuccess, resetForNextInvoice, saving, setSmartDefault],
  )

  useEffect(() => {
    const handleGlobalKeys = (e) => {
      // CTRL+S to Save and close
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault()
        handleSave('save-close')
      }

      // CTRL+ENTER to Save and start a new invoice
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault()
        handleSave('save-new')
      }

      // ESC to Close
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }

    window.addEventListener('keydown', handleGlobalKeys)
    return () => window.removeEventListener('keydown', handleGlobalKeys)
  }, [handleSave, onClose])

  useEffect(() => {
    if (!inlineFeedback) {
      return
    }
    const timer = setTimeout(() => setInlineFeedback(''), 1800)
    return () => clearTimeout(timer)
  }, [inlineFeedback])

  // [AGRI-GUARDIAN §1.II] Use decimal utilities
  const total = form.items.reduce((sum, i) => sum + lineTotal(i.qty, i.unit_price), 0)

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 w-full max-w-6xl h-[90vh] flex flex-col rounded-lg shadow-xl overflow-hidden">
        <div className="bg-gray-800 dark:bg-slate-900 text-white p-4 flex justify-between items-center">
          <h2 className="text-xl font-bold font-mono">⚡ وضع الفواتير السريع</h2>
          <div className="text-sm opacity-75">
            ENTER صف جديد • CTRL+ENTER حفظ وجديد • CTRL+S حفظ وإغلاق
          </div>
        </div>

        <div className="p-4 grid grid-cols-3 gap-4 bg-gray-100 dark:bg-slate-700 border-b dark:border-slate-600">
          <div>
            <label className="block text-xs font-bold text-gray-500 dark:text-slate-400 uppercase mb-1">
              العميل
            </label>
            <VirtualizedSelect
              options={customerOptions}
              value={form.customer}
              onChange={(val) => setForm({ ...form, customer: val })}
              placeholder="اختر العميل..."
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-gray-500 dark:text-slate-400 uppercase mb-1">
              التاريخ
            </label>
            <input
              type="date"
              className="w-full p-2 border dark:border-slate-600 rounded font-mono text-lg bg-white dark:bg-slate-800 dark:text-white"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
            />
          </div>
          <div className="text-end">
            <div className="text-sm text-gray-500 dark:text-slate-400">الإجمالي</div>
            <div className="text-3xl font-bold text-green-600 dark:text-green-400 font-mono">
              {total.toLocaleString()}
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-4">
          <table className="w-full text-start border-collapse">
            <thead>
              <tr className="border-b-2 border-gray-300 dark:border-slate-600 dark:text-slate-300">
                <th className="p-2 w-16">#</th>
                <th className="p-2">الصنف</th>
                <th className="p-2 w-32">الكمية</th>
                <th className="p-2 w-32">السعر</th>
                <th className="p-2 w-32">إجمالي السطر</th>
              </tr>
            </thead>
            <tbody className="dark:text-slate-200">
              {form.items.map((row, idx) => (
                <tr
                  key={row.key}
                  className="border-b border-gray-100 dark:border-slate-700 hover:bg-blue-50 dark:hover:bg-slate-700"
                >
                  <td className="p-2 text-gray-400 dark:text-slate-500 font-mono">{idx + 1}</td>
                  <td className="p-1">
                    <VirtualizedSelect
                      options={itemOptions}
                      value={row.item}
                      onChange={(val) => updateRow(idx, 'item', val)}
                      placeholder="اختر الصنف..."
                    />
                  </td>
                  <td className="p-1">
                    <input
                      className="w-full p-2 border border-transparent focus:border-blue-500 outline-none bg-transparent dark:text-white font-mono text-end"
                      value={row.qty}
                      onChange={(e) => updateRow(idx, 'qty', e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, idx, 'qty')}
                      placeholder="0"
                      ref={(el) => (itemRefs.current[idx * 3 + 1] = el)}
                    />
                  </td>
                  <td className="p-1">
                    <input
                      className="w-full p-2 border border-transparent outline-none bg-transparent font-mono text-end text-gray-500 dark:text-slate-400"
                      value={row.unit_price}
                      readOnly
                    />
                  </td>
                  <td className="p-2 font-bold text-end font-mono">
                    {lineTotal(row.qty, row.unit_price).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="p-4 border-t dark:border-slate-700 bg-gray-50 dark:bg-slate-800 flex justify-end gap-4">
          {inlineFeedback ? (
            <div className="me-auto flex items-center text-sm font-semibold text-emerald-600 dark:text-emerald-400">
              {inlineFeedback}
            </div>
          ) : null}
          <button
            onClick={onClose}
            className="px-6 py-3 font-bold text-gray-500 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-700 rounded"
          >
            CANCEL (ESC)
          </button>
          <button
            onClick={() => handleSave('save-new')}
            disabled={saving}
            className="px-8 py-3 bg-blue-600 text-white font-bold rounded shadow-lg hover:bg-blue-700 active:transform active:scale-95 transition-all disabled:opacity-70"
          >
            {saving ? 'SAVING...' : 'SAVE & NEW (CTRL+ENTER)'}
          </button>
          <button
            onClick={() => handleSave('save-close')}
            disabled={saving}
            className="px-8 py-3 bg-green-600 text-white font-bold rounded shadow-lg hover:bg-green-700 active:transform active:scale-95 transition-all disabled:opacity-70"
          >
            {saving ? 'SAVING...' : 'SAVE & CLOSE (CTRL+S)'}
          </button>
        </div>
      </div>
    </div>
  )
}
