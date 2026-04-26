import { useEffect, useMemo, useState } from 'react'

import { ItemInventories, Farms, Items, Locations, StockMovements } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import InventoryImportExportCenter from '../components/inventory/InventoryImportExportCenter'
import { useToast } from '../components/ToastProvider'
import { MATERIAL_TYPES } from './daily-log/constants.js'

const TEXT = {
  title: 'لوحة متابعة المخزون',
  farmLabel: 'المزرعة',
  itemLabel: 'المادة',
  reload: 'تحديث البيانات',
  lowStock: 'حالة المخزون',
  onHand: 'الرصيد المتوفر',
  reorderLevel: 'حد إعادة الطلب',
  unit: 'الوحدة',
  unitPrice: 'سعر الوحدة (ر.ي)',
  totalValue: 'إجمالي القيمة (ر.ي)',
  statusLow: 'منخفض',
  statusOk: 'مستقر',
  loading: 'جاري تحميل بيانات المخزون...',
  filtersError: 'تعذر تحميل خيارات التصفية.',
  loadError: 'تعذر تحميل بيانات المخزون. حاول مرة أخرى.',
  farmPlaceholder: 'اختر المزرعة',
  itemPlaceholder: 'كل المواد',
  empty: 'لا توجد بيانات مخزون مطابقة للمرشح الحالي.',
}

const formatNumber = (value) => {
  if (value === null || value === undefined) return '-'
  const number = Number(value)
  if (Number.isNaN(number)) return '-'
  return number.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function StockManagementPage() {
  const auth = useAuth()
  const addToast = useToast()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [farms, setFarms] = useState([])
  const [items, setItems] = useState([])
  const [inventories, setInventories] = useState([])
  const [locations, setLocations] = useState([])
  const [locationsLoading, setLocationsLoading] = useState(false)
  const [filters, setFilters] = useState({ farm: '', item: '', location: '' })
  const [movementForm, setMovementForm] = useState({
    farm: '',
    location: '',
    item: '',
    qty: '',
    type: 'in',
    note: '',
    batch: '',
    expiry: '',
    reference: '',
    unit_cost: '',
  })
  const [movementLoading, setMovementLoading] = useState(false)

  useEffect(() => {
    let isMounted = true
    ;(async () => {
      setLoading(true)
      setError('')
      try {
        const [farmResponse, itemResponse] = await Promise.all([
          Farms.list(),
          Items.list({ exclude_group: 'Crop' }),
        ])
        if (!isMounted) return
        const allFarms = farmResponse.data?.results ?? farmResponse.data ?? []
        const accessible = allFarms.filter(
          (farm) => auth.isSuperuser || auth.isAdmin || auth.hasFarmAccess(farm.id),
        )
        setFarms(accessible)
        setItems(itemResponse.data?.results ?? itemResponse.data ?? [])
        if (accessible.length) {
          const defaultFarm = String(accessible[0].id)
          setFilters((prev) => ({ ...prev, farm: prev.farm || defaultFarm }))
          setMovementForm((prev) => ({ ...prev, farm: prev.farm || defaultFarm }))
        }
      } catch (err) {
        console.error('Failed to load stock filters', err)
        if (isMounted) setError(TEXT.filtersError)
      } finally {
        if (isMounted) setLoading(false)
      }
    })()
    return () => {
      isMounted = false
    }
  }, [auth])

  const loadInventories = async () => {
    if (!filters.farm) return
    setLoading(true)
    setError('')
    try {
      const response = await ItemInventories.list({
        farm: filters.farm,
        item: filters.item || undefined,
        location: filters.location || undefined,
        exclude_group: 'Crop',
      })
      setInventories(response.data?.results ?? response.data ?? [])
    } catch (err) {
      console.error('Failed to load inventories', err)
      setError(TEXT.loadError)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (filters.farm) {
      loadInventories()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.farm, filters.location])

  useEffect(() => {
    const fetchLocations = async () => {
      if (!filters.farm) {
        setLocations([])
        setFilters((prev) => ({ ...prev, location: '' }))
        return
      }
      setLocationsLoading(true)
      try {
        const response = await Locations.list({ farm_id: filters.farm })
        const data = response.data?.results ?? response.data ?? []
        setLocations(data)
      } catch (err) {
        console.error('Failed to load farm locations', err)
        setLocations([])
      } finally {
        setLocationsLoading(false)
      }
    }
    fetchLocations().catch(() => setLocationsLoading(false))
  }, [filters.farm])

  useEffect(() => {
    setMovementForm((prev) => ({ ...prev, farm: filters.farm || '', location: '' }))
  }, [filters.farm])

  const farmOptions = useMemo(
    () => farms.map((farm) => ({ id: String(farm.id), name: farm.name })),
    [farms],
  )

  const itemOptions = useMemo(
    () =>
      items.map((item) => {
        const uom = item.uom || item.unit?.symbol || item.unit?.name || ''
        const typeLabel = item.material_type ? MATERIAL_TYPES[item.material_type] : null
        const groupDesc = typeLabel || item.group || ''
        let display = item.name
        if (groupDesc || uom) display += ' - '
        if (groupDesc) display += `[${groupDesc}] `
        if (uom) display += `(${uom})`
        return { id: String(item.id), name: display.trim(), original_uom: uom }
      }),
    [items],
  )

  const summary = useMemo(() => {
    const total = inventories.length
    const low = inventories.filter((record) => record.low_stock).length
    const totalValue = inventories.reduce((acc, record) => {
      const price = Number(record.unit_price ?? 0)
      const qty = Number(record.qty ?? 0)
      return acc + price * qty
    }, 0)
    return {
      total,
      low,
      ok: total - low,
      totalValue,
    }
  }, [inventories])

  const handleMovementChange = (field, value) => {
    setMovementForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleMovementSubmit = async (event) => {
    event.preventDefault()
    if (!movementForm.farm || !movementForm.item || !movementForm.qty) {
      addToast('يرجى تعبئة الحقول الإجبارية للمزرعة، الصنف، والكمية.', 'error')
      return
    }
    const qtyValue = Number(movementForm.qty)
    if (!Number.isFinite(qtyValue) || qtyValue <= 0) {
      addToast('الكمية يجب أن تكون رقمًا موجبًا.', 'error')
      return
    }
    const payload = {
      farm: Number(movementForm.farm),
      item: Number(movementForm.item),
      qty_delta: movementForm.type === 'out' ? -Math.abs(qtyValue) : Math.abs(qtyValue),
      ref_type: 'manual',
      ref_id: movementForm.reference || '',
      note: movementForm.note || '',
    }
    if (movementForm.type === 'in' && movementForm.unit_cost) {
      payload.unit_cost = Number(movementForm.unit_cost)
    }
    if (movementForm.location && movementForm.location !== 'null') {
      payload.location = Number(movementForm.location)
    }
    if (movementForm.batch) {
      payload.batch_number = movementForm.batch
    }
    if (movementForm.expiry) {
      payload.expiry_date = movementForm.expiry
    }
    setMovementLoading(true)
    try {
      await StockMovements.create(payload)
      addToast('تم تسجيل حركة المخزون بنجاح.', 'success')
      setMovementForm((prev) => ({
        ...prev,
        item: '',
        qty: '',
        note: '',
        batch: '',
        expiry: '',
        reference: '',
        unit_cost: '',
        location: prev.location,
      }))
      loadInventories().catch(() => {})
    } catch (err) {
      console.error('Failed to create stock movement', err)
      addToast('تعذر حفظ حركة المخزون.', 'error')
    } finally {
      setMovementLoading(false)
    }
  }

  const openPrintView = () => {
    if (!inventories.length) {
      addToast({ intent: 'info', message: 'لا توجد بيانات للطباعة.' })
      return
    }
    const printWindow = window.open('', '_blank', 'width=900,height=600')
    if (!printWindow) return
    const tableRows = inventories
      .map(
        (record) => {
          const lineValue = Number(record.qty ?? 0) * Number(record.unit_price ?? 0)
          return `
          <tr>
            <td>${record.item_name}</td>
            <td style="text-align:center">${formatNumber(record.qty)}</td>
            <td style="text-align:center">${formatNumber(record.unit_price)}</td>
            <td style="text-align:center;font-weight:600">${formatNumber(lineValue)}</td>
            <td style="text-align:center">${formatNumber(record.reorder_level)}</td>
            <td style="text-align:center">${record.uom || record.item_unit?.symbol || '-'}</td>
            <td style="text-align:center">${record.low_stock ? TEXT.statusLow : TEXT.statusOk}</td>
          </tr>`
        },
      )
      .join('')
    printWindow.document.write(`
      <html dir="rtl" lang="ar">
        <head>
          <title>${TEXT.title}</title>
          <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 24px; }
            h1 { text-align: center; margin-bottom: 16px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid #d1d5db; padding: 8px; text-align: right; }
            th { background: #f9fafb; }
          </style>
        </head>
        <body>
          <h1>${TEXT.title}</h1>
          <p>عدد المواد: ${summary.total} — الحرجة: ${summary.low} — المستقرة: ${summary.ok}</p>
          <table>
            <thead>
              <tr>
                <th>${TEXT.itemLabel}</th>
                <th>${TEXT.onHand}</th>
                <th>${TEXT.unitPrice}</th>
                <th>${TEXT.totalValue}</th>
                <th>${TEXT.reorderLevel}</th>
                <th>${TEXT.unit}</th>
                <th>${TEXT.lowStock}</th>
              </tr>
            </thead>
            <tbody>
              ${tableRows}
            </tbody>
          </table>
        </body>
      </html>
    `)
    printWindow.document.close()
    printWindow.focus()
    printWindow.print()
  }

  if (loading && !inventories.length) {
    return (
      <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-primary-700">
        {TEXT.loading}
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm p-6 space-y-4">
        <h1 className="text-xl font-semibold text-gray-800 dark:text-white">{TEXT.title}</h1>
        <form
          className="grid gap-3 md:grid-cols-3"
          onSubmit={(event) => {
            event.preventDefault()
            loadInventories().catch(() => addToast({ intent: 'error', message: TEXT.loadError }))
          }}
        >
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-400">
              {TEXT.farmLabel}
            </label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={filters.farm}
              onChange={(event) => setFilters((prev) => ({ ...prev, farm: event.target.value }))}
              required
            >
              <option value="">{TEXT.farmPlaceholder}</option>
              {farmOptions.map((farm) => (
                <option key={farm.id} value={farm.id}>
                  {farm.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600">{TEXT.itemLabel}</label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={filters.item}
              onChange={(event) => setFilters((prev) => ({ ...prev, item: event.target.value }))}
            >
              <option value="">{TEXT.itemPlaceholder}</option>
              {itemOptions.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600">الموقع</label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={filters.location}
              onChange={(event) =>
                setFilters((prev) => ({ ...prev, location: event.target.value }))
              }
              disabled={locationsLoading || !locations.length}
            >
              <option value="">كل المواقع</option>
              <option value="null">بدون موقع</option>
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name} {['Store', 'Warehouse'].includes(loc.type) ? '[مخزن]' : ''}
                </option>
              ))}
            </select>
          </div>
          <div className="md:flex md:items-end">
            <button
              type="submit"
              className="w-full rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90"
            >
              {TEXT.reload}
            </button>
          </div>
        </form>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 shadow-sm">
          <div className="text-sm text-gray-500 dark:text-slate-400">إجمالي المواد</div>
          <div className="text-2xl font-semibold text-gray-800 dark:text-white">
            {summary.total}
          </div>
        </div>
        <div className="rounded-2xl border border-red-100 bg-red-50 p-4 shadow-sm">
          <div className="text-sm text-red-600">مواد بحاجة لتدخل</div>
          <div className="text-2xl font-semibold text-red-700">{summary.low}</div>
        </div>
        <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4 shadow-sm">
          <div className="text-sm text-emerald-600">مواد ضمن الحدود الآمنة</div>
          <div className="text-2xl font-semibold text-emerald-700">{summary.ok}</div>
        </div>
        <div className="rounded-2xl border border-blue-100 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-800 p-4 shadow-sm">
          <div className="text-sm text-blue-600 dark:text-blue-400">إجمالي قيمة المخزون (ر.ي)</div>
          <div className="text-xl font-semibold text-blue-700 dark:text-blue-300">
            {summary.totalValue > 0 ? summary.totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white">إدخال حركة مخزون</h2>
        <form className="grid gap-3 md:grid-cols-2" onSubmit={handleMovementSubmit}>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-400">المزرعة</label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={movementForm.farm}
              onChange={(event) => handleMovementChange('farm', event.target.value)}
              required
            >
              <option value="">اختر المزرعة</option>
              {farmOptions.map((farm) => (
                <option key={farm.id} value={farm.id}>
                  {farm.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600">الموقع</label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={movementForm.location}
              onChange={(event) => handleMovementChange('location', event.target.value)}
              disabled={!locations.length}
            >
              <option value="">اختياري</option>
              <option value="null">بدون موقع</option>
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name} {['Store', 'Warehouse'].includes(loc.type) ? '[مخزن]' : ''}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600">المادة</label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={movementForm.item}
              onChange={(event) => handleMovementChange('item', event.target.value)}
              required
            >
              <option value="">اختر المادة</option>
              {itemOptions.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600">نوع الحركة</label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={movementForm.type}
              onChange={(event) => handleMovementChange('type', event.target.value)}
            >
              <option value="in">إدخال (زيادة)</option>
              <option value="out">صرف (نقص)</option>
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600">
              الكمية
              {movementForm.item && items.find((i) => String(i.id) === movementForm.item) && (
                <span className="text-primary-600 font-semibold mr-1">
                  ({items.find((i) => String(i.id) === movementForm.item).uom || items.find((i) => String(i.id) === movementForm.item).unit?.symbol || '-'})
                </span>
              )}
            </label>
            <input
              type="number"
              min="0"
              step="0.01"
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={movementForm.qty}
              onChange={(event) => handleMovementChange('qty', event.target.value)}
              required
            />
          </div>
          {movementForm.type === 'in' && (
            <div className="space-y-1">
              <label className="block text-sm text-gray-600">تكلفة الوحدة (ر.ي)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                className="w-full rounded-lg border border-gray-300 px-3 py-2"
                value={movementForm.unit_cost}
                onChange={(event) => handleMovementChange('unit_cost', event.target.value)}
                placeholder="التكلفة المباشرة (اختياري)"
              />
            </div>
          )}
          <div className="space-y-1">
            <label className="block text-sm text-gray-600">الدفعة</label>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={movementForm.batch}
              onChange={(event) => handleMovementChange('batch', event.target.value)}
              placeholder="اختياري"
            />
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600">تاريخ الصلاحية</label>
            <input
              type="date"
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={movementForm.expiry}
              onChange={(event) => handleMovementChange('expiry', event.target.value)}
            />
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600">مرجع الحركة</label>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              value={movementForm.reference}
              onChange={(event) => handleMovementChange('reference', event.target.value)}
              placeholder="مثال: فاتورة شراء"
            />
          </div>
          <div className="space-y-1 md:col-span-2">
            <label className="block text-sm text-gray-600">ملاحظات</label>
            <textarea
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              rows="2"
              value={movementForm.note}
              onChange={(event) => handleMovementChange('note', event.target.value)}
              placeholder="تفاصيل إضافية..."
            />
          </div>
          <div className="md:col-span-2 flex justify-end">
            <button
              type="submit"
              className="rounded-lg bg-primary px-6 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary/90 disabled:opacity-60"
              disabled={movementLoading}
            >
              {movementLoading ? 'جاري الحفظ...' : 'حفظ حركة المخزون'}
            </button>
          </div>
        </form>
      </section>

      <InventoryImportExportCenter
        farmId={filters.farm}
        filters={filters}
        addToast={addToast}
        onImportApplied={() => {
          loadInventories().catch(() => {})
        }}
      />

      <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm p-6 space-y-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
            جدول المخزون الحالي
          </h2>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-lg border border-gray-300 dark:border-slate-600 px-4 py-2 text-sm font-semibold text-gray-700 dark:text-slate-200 hover:bg-gray-50 dark:hover:bg-slate-700"
              onClick={openPrintView}
            >
              طباعة / PDF
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 dark:bg-slate-700 text-gray-600 dark:text-slate-300">
              <tr>
                <th className="px-3 py-2 text-end font-medium">{TEXT.farmLabel}</th>
                <th className="px-3 py-2 text-end font-medium">الموقع</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.itemLabel}</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.onHand}</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.unitPrice}</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.totalValue}</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.reorderLevel}</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.unit}</th>
                <th className="px-3 py-2 text-end font-medium">{TEXT.lowStock}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {inventories.map((record) => {
                const lineValue = Number(record.qty ?? 0) * Number(record.unit_price ?? 0)
                return (
                <tr key={record.id} className="hover:bg-gray-50 dark:hover:bg-slate-700">
                  <td className="px-3 py-2 text-gray-800 dark:text-slate-200">
                    {record.farm_name || '-'}
                  </td>
                  <td className="px-3 py-2 text-gray-800 dark:text-slate-200">
                    {record.location_name || '-'}
                  </td>
                  <td className="px-3 py-2 text-gray-800 dark:text-slate-200 font-medium">
                    {record.item_name}
                    {record.item_group && (
                      <span className="block text-xs text-gray-400 dark:text-slate-500">{record.item_group}</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300 tabular-nums">
                    {formatNumber(record.qty)}
                  </td>
                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300 tabular-nums">
                    {formatNumber(record.unit_price)}
                  </td>
                  <td className="px-3 py-2 font-semibold text-blue-700 dark:text-blue-300 tabular-nums">
                    {lineValue > 0 ? formatNumber(lineValue) : '-'}
                  </td>
                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300 tabular-nums">
                    {formatNumber(record.reorder_level)}
                  </td>
                  <td className="px-3 py-2 text-gray-500 dark:text-slate-400">
                    {record.uom || record.item_unit?.symbol || '-'}
                  </td>
                  <td className="px-3 py-2">
                    {record.low_stock ? (
                      <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">
                        {TEXT.statusLow}
                      </span>
                    ) : (
                      <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                        {TEXT.statusOk}
                      </span>
                    )}
                  </td>
                </tr>
                )
              })}
              {!inventories.length && (
                <tr>
                  <td
                    className="px-3 py-3 text-center text-gray-500 dark:text-slate-400"
                    colSpan={9}
                  >
                    {TEXT.empty}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
