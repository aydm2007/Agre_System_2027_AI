import { useState, useEffect, useMemo } from 'react'
import { api, Sales, HarvestProductCatalog, Farms, HarvestLots } from '../../api/client'
import { useNavigate, useParams } from 'react-router-dom'
import { useFarmContext } from '../../api/farmContext' // [AGRI-GUARDIAN] Strict Isolation
import { toast } from 'react-hot-toast'
import { ArrowLeft, Save, Plus, Trash2, Calculator, Package } from 'lucide-react'
import {
  formatMoney,
  toDecimal,
  multiplyDecimal,
  sumDecimals,
  lineTotal,
} from '../../utils/decimal'

const parseApiErrorMessage = (
  error,
  fallback = 'تعذر إتمام العملية. يرجى التحقق من البيانات والمحاولة مرة أخرى.',
) => {
  const payload = error?.response?.data
  if (!payload) return error?.message || fallback

  const detail = payload.detail
  if (Array.isArray(detail)) return detail.join(' - ')
  if (typeof detail === 'string' && detail.trim()) return detail
  if (typeof payload === 'string' && payload.trim()) return payload

  if (typeof payload === 'object') {
    const messages = []
    Object.entries(payload).forEach(([field, value]) => {
      if (field === 'detail') return
      if (Array.isArray(value)) messages.push(`${field}: ${value.join(', ')}`)
      else if (typeof value === 'string') messages.push(`${field}: ${value}`)
    })
    if (messages.length) return messages.join(' - ')
  }

  return fallback
}

export default function SalesForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [products, setProducts] = useState([])

  const { selectedFarmId } = useFarmContext()
  const [locations, setLocations] = useState([])
  const [customers, setCustomers] = useState([])
  const [lots, setLots] = useState([])
  const [taxRate, setTaxRate] = useState(0.15)

  const [formData, setFormData] = useState({
    customer_name: '',
    customer_id: '',
    date: new Date().toISOString().split('T')[0],
    status: 'pending',
    items: [],
    discount_amount: 0,
    notes: '',
    location_id: '', // Required by Backend
  })

  const normalizeInvoiceToForm = (data) => ({
    customer_name: data?.customer_name || '',
    customer_id: data?.customer || '',
    date: data?.invoice_date || new Date().toISOString().split('T')[0],
    status: data?.status || 'pending',
    discount_amount: data?.discount_amount ?? 0,
    notes: data?.notes ?? '',
    location_id: data?.location ?? '',
    items: (data?.items || []).map((i) => ({
      id: i?.id ?? Date.now(),
      product_id: i?.item ?? '',
      product_name: i?.product_name || '',
      quantity: i?.qty ?? '',
      unit_price: i?.unit_price ?? '',
      harvest_lot_id: i?.harvest_lot ?? '',
    })),
  })
  const isLockedInvoice = Boolean(
    id && ['approved', 'paid', 'cancelled'].includes(String(formData.status || '').toLowerCase()),
  )

  // Load Initial Data (Products, Locations, Customers, Dots, Tax Rate)
  useEffect(() => {
    const loadData = async () => {
      if (!selectedFarmId) return
      setLoading(true)
      try {
        const [prodRes, custRes, farmRes, lotRes] = await Promise.all([
          HarvestProductCatalog.list({ farm_id: selectedFarmId }),
          api.get('/customers/'),
          Farms.retrieve(selectedFarmId),
          HarvestLots.list({ farm_id: selectedFarmId }),
        ])

        const catalog = prodRes.data.results || prodRes.data || []
        // [Agri-Guardian] Filter out zero-balance items
        const availableProducts = catalog.filter((p) => (p.total_harvest_qty || 0) > 0)
        setProducts(availableProducts)
        setCustomers(custRes.data.results || custRes.data || [])

        // [Phase 10] Dynamic Tax Rate
        const farmData = farmRes.data
        if (farmData && farmData.sales_tax_percentage !== undefined) {
          setTaxRate(Number(farmData.sales_tax_percentage) / 100)
        }

        // [Phase 10] Lots
        setLots(lotRes.data.results || lotRes.data || [])
      } catch (err) {
        console.error('Failed to load initial data', err)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [selectedFarmId])

  // Load Locations when Farm changes
  useEffect(() => {
    if (selectedFarmId) {
      const fetchLocations = async () => {
        try {
          // Fetch storage locations or all locations
          const res = await api.get('/locations/', { params: { farm_id: selectedFarmId } })
          const locs = res.data.results || res.data || []
          setLocations(locs)
          // Default to first location if available and not set
          if (locs.length > 0) {
            setFormData((prev) => (prev.location_id ? prev : { ...prev, location_id: locs[0].id }))
          } else {
            toast.error('تنبيه: لا توجد مواقع/مخازن لهذه المزرعة. لا يمكن إنشاء فاتورة.')
          }
        } catch (e) {
          console.error('Failed to load locations', e)
        }
      }
      fetchLocations()
    }
  }, [selectedFarmId])

  useEffect(() => {
    if (id) {
      const fetchInvoice = async () => {
        try {
          const res = await Sales.get(id)
          setFormData(normalizeInvoiceToForm(res.data))
        } catch (err) {
          toast.error('فشل تحميل الفاتورة')
          navigate('/sales')
        }
      }
      fetchInvoice()
    }
  }, [id, navigate])

  const addItem = () => {
    setFormData((prev) => ({
      ...prev,
      items: [
        ...prev.items,
        {
          id: Date.now(),
          product_id: '',
          product_name: '',
          quantity: 1,
          unit_price: 0,
          harvest_lot_id: '',
        },
      ],
    }))
  }

  const updateItem = (index, field, value) => {
    const newItems = [...formData.items]
    newItems[index][field] = value
    if (field === 'product_id') {
      const prod = products.find((p) => String(p.item_id) === String(value))
      if (prod) {
        newItems[index].product_name = prod.name
        newItems[index].unit_price = prod.reference_price || 0
      }
    }
    setFormData({ ...formData, items: newItems })
  }

  const removeItem = (index) => {
    const newItems = [...formData.items]
    newItems.splice(index, 1)
    setFormData({ ...formData, items: newItems })
  }

  const financials = useMemo(() => {
    // [AGRI-GUARDIAN] Axis 5: Strict Decimal Arithmetic
    const itemTotals = formData.items.map((item) =>
      lineTotal(item.quantity || 0, item.unit_price || 0),
    )
    const subtotal = sumDecimals(itemTotals, 2)
    const discount = toDecimal(formData.discount_amount || 0, 2)
    const taxableBase = Math.max(0, subtotal - discount)
    const taxAmount = multiplyDecimal(taxableBase, taxRate, 2)
    const total = sumDecimals([taxableBase, taxAmount], 2)

    return { subtotal, taxAmount, total, discount }
  }, [formData.items, formData.discount_amount, taxRate])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (isLockedInvoice) {
      return toast.error('لا يمكن تعديل فاتورة بعد اعتمادها أو دفعها أو إلغائها.')
    }
    if (!formData.customer_name) return toast.error('يرجى إدخال اسم العميل')
    if (formData.items.length === 0) return toast.error('يجب إضافة منتج واحد على الأقل')
    if (!formData.location_id) return toast.error('يرجى تحديد موقع/مخزن للاستلام منه')
    if (formData.items.some((item) => !item.product_id)) {
      return toast.error('يرجى اختيار صنف لكل سطر في الفاتورة')
    }

    setLoading(true)

    try {
      // 1. Resolve Customer ID
      let finalCustomerId = formData.customer_id

      // If no ID but we have a name, check if existing or create new
      if (!finalCustomerId && formData.customer_name) {
        const existing = customers.find((c) => c.name === formData.customer_name)
        if (existing) {
          finalCustomerId = existing.id
        } else {
          // Create new customer on the fly
          const newCust = await api.post('/customers/', {
            name: formData.customer_name,
            customer_type: 'individual', // Default
          })
          finalCustomerId = newCust.data.id
        }
      }

      if (!finalCustomerId) throw new Error('فشل تحديد حساب العميل')

      // 2. Prepare Payload for Backend
      const payload = {
        customer: finalCustomerId,
        location: formData.location_id,
        invoice_date: new Date(formData.date).toISOString().split('T')[0], // YYYY-MM-DD
        notes: formData.notes,
        // Map items to backend expected format
        items: formData.items.map((item) => ({
          item: item.product_id, // 'item' FK to Inventory Item
          qty: item.quantity,
          unit_price: item.unit_price,
          description: item.product_name,
          harvest_lot: item.harvest_lot_id || null, // [Phase 10] Traceability
        })),
      }

      if (id) {
        await Sales.update(id, payload)
        toast.success('تم تحديث الفاتورة')
      } else {
        await Sales.create(payload)
        toast.success('تم إنشاء الفاتورة')
      }
      navigate('/sales')
    } catch (err) {
      const message = parseApiErrorMessage(
        err,
        'فشل حفظ الفاتورة. تأكد من اختيار الموقع والأصناف والكميات بشكل صحيح.',
      )
      const normalized =
        message === 'Only draft invoices can be updated.'
          ? 'لا يمكن تعديل الفاتورة بعد اعتمادها. التعديل متاح فقط في حالة مسودة.'
          : message
      toast.error(`فشل حفظ الفاتورة: ${normalized}`)
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div dir="rtl" className="min-h-screen bg-gray-50 dark:bg-slate-900 p-8 pb-20">
      <form onSubmit={handleSubmit} className="max-w-5xl mx-auto space-y-8">
        {/* Top Actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => navigate('/sales')}
              className="p-3 bg-gray-100 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl hover:bg-gray-200 dark:hover:bg-white/10 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-white/60" />
            </button>
            <div>
              <h1 className="text-3xl font-black tracking-tight bg-gradient-to-r from-emerald-600 dark:from-emerald-400 to-amber-500 dark:to-amber-200 bg-clip-text text-transparent">
                {id ? 'تعديل فاتورة' : 'إنشاء فاتورة مبيعات'}
              </h1>
              <p className="text-gray-500 dark:text-zinc-500 font-medium text-sm mt-1">
                أدخل بيانات الفاتورة والمنتجات
              </p>
            </div>
          </div>
          <button
            type="submit"
            disabled={loading || isLockedInvoice}
            className="flex items-center gap-2 px-8 py-3 rounded-xl bg-emerald-600 text-white font-bold shadow-lg shadow-emerald-500/20 hover:bg-emerald-500 transition-all disabled:opacity-50"
          >
            <Save className="w-5 h-5" />
            {loading
              ? 'جاري الحفظ...'
              : isLockedInvoice
                ? 'الفاتورة مقفلة للتعديل'
                : 'حفظ الفاتورة'}
          </button>
        </div>

        {isLockedInvoice && (
          <div className="max-w-5xl mx-auto rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-200 p-4">
            هذه الفاتورة حالتها <strong>غير قابلة للتعديل</strong>. أي تصحيح يتم عبر إجراءات
            عكس/إلغاء وليس التعديل المباشر.
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Form Area */}
          <div className="lg:col-span-2 space-y-6">
            {/* Customer Info Card */}
            <div className="rounded-2xl border border-white/10 bg-zinc-900/80 backdrop-blur-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <span className="w-1.5 h-6 bg-blue-500 rounded-full"></span>
                بيانات العميل
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-bold text-white/50 mb-2">اسم العميل</label>
                  <input
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white focus:border-emerald-500/50 focus:outline-none placeholder:text-white/20"
                    placeholder="مثال: شركة المراعي الخضراء"
                    value={formData.customer_name ?? ''}
                    onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-white/50 mb-2">
                    الموقع / المخزن
                  </label>
                  <select
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white focus:border-emerald-500/50 focus:outline-none"
                    value={formData.location_id ?? ''}
                    onChange={(e) => setFormData({ ...formData, location_id: e.target.value })}
                  >
                    <option value="">اختر موقع...</option>
                    {locations.map((loc) => (
                      <option key={loc.id} value={loc.id}>
                        {loc.name}
                      </option>
                    ))}
                  </select>
                  {locations.length === 0 && (
                    <p className="text-xs text-rose-400 mt-1">
                      ⚠️ لا توجد مواقع لهذه المزرعة. يرجى إضافة موقع أولاً.
                    </p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-bold text-white/50 mb-2">
                    تاريخ الفاتورة
                  </label>
                  <input
                    type="date"
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white focus:border-emerald-500/50 focus:outline-none"
                    value={formData.date ?? ''}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-bold text-white/50 mb-2">حالة الدفع</label>
                  <div className="flex gap-4">
                    <label
                      className={`flex-1 cursor-pointer border rounded-xl p-4 flex items-center justify-center gap-2 transition-all ${formData.status === 'pending' ? 'bg-amber-500/20 border-amber-500/30 text-amber-400 font-bold' : 'bg-white/5 border-white/10 text-white/40'}`}
                    >
                      <input
                        type="radio"
                        name="status"
                        value="pending"
                        className="hidden"
                        checked={formData.status === 'pending'}
                        onChange={() => setFormData({ ...formData, status: 'pending' })}
                      />
                      ⏳ معلقة (آجل)
                    </label>
                    <label
                      className={`flex-1 cursor-pointer border rounded-xl p-4 flex items-center justify-center gap-2 transition-all ${formData.status === 'paid' ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400 font-bold' : 'bg-white/5 border-white/10 text-white/40'}`}
                    >
                      <input
                        type="radio"
                        name="status"
                        value="paid"
                        className="hidden"
                        checked={formData.status === 'paid'}
                        onChange={() => setFormData({ ...formData, status: 'paid' })}
                      />
                      ✅ مدفوعة بالكامل
                    </label>
                  </div>
                </div>
              </div>
            </div>

            {/* Items Card */}
            <div className="rounded-2xl border border-white/10 bg-zinc-900/80 backdrop-blur-xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <span className="w-1.5 h-6 bg-orange-500 rounded-full"></span>
                  المنتجات والخدمات
                </h3>
                <button
                  type="button"
                  onClick={addItem}
                  className="text-emerald-400 text-sm font-bold hover:bg-emerald-500/10 px-4 py-2 rounded-xl transition-colors flex items-center gap-1 border border-emerald-500/30"
                >
                  <Plus className="w-4 h-4" />
                  إضافة بند
                </button>
              </div>

              <div className="space-y-3">
                {formData.items.length === 0 && (
                  <div className="text-center py-12 border-2 border-dashed border-white/10 rounded-xl">
                    <Package className="w-12 h-12 text-white/20 mx-auto mb-2" />
                    <p className="text-white/30">لا توجد منتجات مضافة</p>
                  </div>
                )}
                {formData.items.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex flex-wrap md:flex-nowrap gap-3 items-end bg-white/5 p-4 rounded-xl border border-white/10 group"
                  >
                    <div className="flex-grow min-w-[200px]">
                      <label className="text-xs text-white/40 block mb-1">المنتج</label>
                      <select
                        className="w-full bg-zinc-800 border border-white/10 rounded-xl p-3 text-sm text-white"
                        value={item.product_id ?? ''}
                        onChange={(e) => updateItem(idx, 'product_id', e.target.value)}
                      >
                        <option value="">اختر منتج...</option>
                        {products.map((p) => (
                          <option key={p.item_id} value={p.item_id}>
                            {p.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="flex-grow min-w-[150px]">
                      <label className="text-xs text-white/40 block mb-1">الدفعة (Lot)</label>
                      <select
                        className="w-full bg-zinc-800 border border-white/10 rounded-xl p-3 text-sm text-white"
                        value={item.harvest_lot_id ?? ''}
                        onChange={(e) => updateItem(idx, 'harvest_lot_id', e.target.value)}
                      >
                        <option value="">لا يوجد...</option>
                        {lots
                          .filter((l) => String(l.product) === String(item.product_id))
                          .map((l) => (
                            <option key={l.id} value={l.id}>
                              {l.harvest_date} - {l.grade}
                            </option>
                          ))}
                      </select>
                    </div>
                    <div className="w-24">
                      <label className="text-xs text-white/40 block mb-1">الكمية</label>
                      <input
                        type="text"
                        inputMode="decimal"
                        pattern="[0-9]*"
                        className="w-full bg-zinc-800 border border-white/10 rounded-xl p-3 text-sm text-center text-white"
                        placeholder="0.000"
                        value={item.quantity ?? ''}
                        onKeyPress={(event) => {
                          if (!/[0-9.]/.test(event.key)) {
                            event.preventDefault()
                          }
                        }}
                        onChange={(e) => {
                          const val = e.target.value
                          if (val === '' || /^\d*\.?\d{0,3}$/.test(val)) {
                            updateItem(idx, 'quantity', val)
                          }
                        }}
                      />
                    </div>
                    <div className="w-32">
                      <label className="text-xs text-white/40 block mb-1">سعر الوحدة</label>
                      <input
                        type="text"
                        inputMode="decimal"
                        pattern="[0-9]*"
                        className="w-full bg-zinc-800 border border-white/10 rounded-xl p-3 text-sm text-center text-white"
                        placeholder="0.00"
                        value={item.unit_price ?? ''}
                        onKeyPress={(event) => {
                          if (!/[0-9.]/.test(event.key)) {
                            event.preventDefault()
                          }
                        }}
                        onChange={(e) => {
                          const val = e.target.value
                          if (val === '' || /^\d*\.?\d{0,2}$/.test(val)) {
                            updateItem(idx, 'unit_price', val)
                          }
                        }}
                      />
                    </div>
                    <div className="w-32 pt-6 text-start font-bold text-emerald-400">
                      {formatMoney(lineTotal(item.quantity, item.unit_price))}
                    </div>
                    <button
                      type="button"
                      onClick={() => removeItem(idx)}
                      className="p-2 text-white/40 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors mb-0.5"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-zinc-900/80 backdrop-blur-xl p-6">
              <label className="block text-sm font-bold text-white/50 mb-2">ملاحظات إضافية</label>
              <textarea
                className="w-full bg-white/5 border border-white/10 rounded-xl p-4 h-24 text-white focus:border-emerald-500/50 focus:outline-none placeholder:text-white/20"
                placeholder="شروط الدفع، ملاحظات التسليم..."
                value={formData.notes ?? ''}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              ></textarea>
            </div>
          </div>

          {/* Sidebar Financials */}
          <div className="lg:col-span-1">
            <div className="rounded-3xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-zinc-900 backdrop-blur-xl p-6 sticky top-6">
              <div className="flex items-center gap-2 mb-6 border-b border-white/10 pb-4">
                <Calculator className="w-5 h-5 text-emerald-400" />
                <h3 className="text-lg font-bold text-white">ملخص الفاتورة</h3>
              </div>

              <div className="space-y-4 text-sm">
                <div className="flex justify-between text-white/60">
                  <span>المجموع الفرعي</span>
                  <span className="text-white">{formatMoney(financials.subtotal)}</span>
                </div>

                <div className="flex justify-between items-center text-white/60">
                  <span>الخصم</span>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    className="w-24 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-end text-white focus:border-emerald-500/50 focus:outline-none"
                    value={formData.discount_amount ?? ''}
                    onChange={(e) => {
                      const val = e.target.value
                      if (val === '' || parseFloat(val) >= 0) {
                        setFormData({ ...formData, discount_amount: val })
                      }
                    }}
                  />
                </div>

                <div className="flex justify-between text-white/60">
                  <span>الضريبة ({Math.round(taxRate * 100)}%)</span>
                  <span className="text-white">{formatMoney(financials.taxAmount)}</span>
                </div>

                <div className="pt-4 mt-4 border-t border-white/10 flex justify-between items-center">
                  <span className="font-bold text-lg text-white">الإجمالي النهائي</span>
                  <span className="font-black text-2xl text-emerald-400">
                    {formatMoney(financials.total)}{' '}
                    <span className="text-xs text-white/40">ريال</span>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </form>
    </div>
  )
}
