import { useState, useEffect, useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, PurchaseOrders } from '../api/client'
import { ArrowLeft, Save, Plus, Trash2, Calculator, Package } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { useFarmContext } from '../api/farmContext'
import { formatMoney, sumDecimals, lineTotal } from '../utils/decimal'

export default function PurchaseOrderForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { selectedFarmId } = useFarmContext()
  const [loading, setLoading] = useState(false)
  const [itemsCatalog, setItemsCatalog] = useState([])

  const [formData, setFormData] = useState({
    vendor_name: '',
    order_date: new Date().toISOString().split('T')[0],
    expected_delivery_date: '',
    currency: 'YER',
    notes: '',
    items: [],
  })

  useEffect(() => {
    const loadCatalog = async () => {
      if (!selectedFarmId) return
      try {
        const res = await api.get('/inventory-items/', { params: { farm_id: selectedFarmId } })
        setItemsCatalog(res.data.results || res.data || [])
      } catch (err) {
        console.error('Failed to load catalog', err)
      }
    }
    loadCatalog()
  }, [selectedFarmId])

  useEffect(() => {
    if (id) {
      const fetchOrder = async () => {
        try {
          const res = await PurchaseOrders.retrieve(id)
          const data = res.data
          setFormData({
            vendor_name: data.vendor_name || '',
            order_date: data.order_date || new Date().toISOString().split('T')[0],
            expected_delivery_date: data.expected_delivery_date || '',
            currency: data.currency || 'YER',
            notes: data.notes || '',
            items: (data.items || []).map(i => ({
              id: i.id || Date.now() + Math.random(),
              item_id: i.item,
              qty: i.qty,
              unit_price: i.unit_price,
            })),
          })
        } catch (err) {
          toast.error('فشل تحميل طلب الشراء')
          navigate('/purchases')
        }
      }
      fetchOrder()
    }
  }, [id, navigate])

  const addItem = () => {
    setFormData(prev => ({
      ...prev,
      items: [
        ...prev.items,
        {
          id: Date.now(),
          item_id: '',
          qty: 1,
          unit_price: 0,
        }
      ]
    }))
  }

  const updateItem = (index, field, value) => {
    const newItems = [...formData.items]
    newItems[index][field] = value
    setFormData({ ...formData, items: newItems })
  }

  const removeItem = (index) => {
    const newItems = [...formData.items]
    newItems.splice(index, 1)
    setFormData({ ...formData, items: newItems })
  }

  const financials = useMemo(() => {
    const itemTotals = formData.items.map(item => lineTotal(item.qty || 0, item.unit_price || 0))
    const total = sumDecimals(itemTotals, 4)
    return { total }
  }, [formData.items])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.vendor_name) return toast.error('يرجى إدخال اسم المورد')
    if (formData.items.length === 0) return toast.error('يجب إضافة صنف واحد على الأقل')
    if (formData.items.some(item => !item.item_id)) return toast.error('يرجى اختيار صنف لكل سطر في الطلب')

    setLoading(true)
    try {
      const payload = {
        farm: selectedFarmId,
        vendor_name: formData.vendor_name,
        order_date: formData.order_date,
        expected_delivery_date: formData.expected_delivery_date || null,
        currency: formData.currency,
        notes: formData.notes,
        items: formData.items.map(i => ({
          item: i.item_id,
          qty: i.qty,
          unit_price: i.unit_price,
        }))
      }

      // Important: Ensure nested items creation works in backend.
      // If backend assumes specific structure, we send it here.
      if (id) {
        await PurchaseOrders.update(id, payload)
        toast.success('تم تحديث طلب الشراء')
      } else {
        await PurchaseOrders.create(payload)
        toast.success('تم إنشاء طلب الشراء')
      }
      navigate('/purchases')
    } catch (err) {
      toast.error('فشل حفظ طلب الشراء. راجع البيانات المدخلة.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div dir="rtl" className="min-h-screen bg-gray-50 dark:bg-slate-900 p-8 pb-20">
      <form onSubmit={handleSubmit} className="max-w-5xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => navigate('/purchases')}
              className="p-3 bg-gray-100 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-xl hover:bg-gray-200 dark:hover:bg-white/10 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-white/60" />
            </button>
            <div>
              <h1 className="text-3xl font-black tracking-tight bg-gradient-to-r from-emerald-600 dark:from-emerald-400 to-amber-500 dark:to-amber-200 bg-clip-text text-transparent">
                {id ? 'تعديل طلب الشراء' : 'إنشاء طلب شراء'}
              </h1>
              <p className="text-gray-500 dark:text-zinc-500 font-medium text-sm mt-1">أدخل بيانات المورد والأصناف المراد طلبها</p>
            </div>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-8 py-3 rounded-xl bg-emerald-600 text-white font-bold shadow-lg shadow-emerald-500/20 hover:bg-emerald-500 transition-all disabled:opacity-50"
          >
            <Save className="w-5 h-5" />
            {loading ? 'جاري الحفظ...' : 'حفظ الطلب'}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="rounded-2xl border border-white/10 bg-zinc-900/80 backdrop-blur-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <span className="w-1.5 h-6 bg-blue-500 rounded-full"></span>
                بيانات المورد والطلب
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-bold text-white/50 mb-2">اسم المورد</label>
                  <input
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white focus:border-emerald-500/50 focus:outline-none placeholder:text-white/20"
                    placeholder="اسم المورد أو الشركة"
                    value={formData.vendor_name}
                    onChange={(e) => setFormData({ ...formData, vendor_name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-white/50 mb-2">تاريخ الطلب</label>
                  <input
                    type="date"
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white focus:border-emerald-500/50 focus:outline-none"
                    value={formData.order_date}
                    onChange={(e) => setFormData({ ...formData, order_date: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-white/50 mb-2">تاريخ التوصيل المتوقع</label>
                  <input
                    type="date"
                    className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white focus:border-emerald-500/50 focus:outline-none"
                    value={formData.expected_delivery_date}
                    onChange={(e) => setFormData({ ...formData, expected_delivery_date: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-white/50 mb-2">العملة</label>
                  <select
                    className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white focus:border-emerald-500/50 focus:outline-none"
                    value={formData.currency}
                    onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                  >
                    <option value="YER">ريال يمني (YER)</option>
                    <option value="SAr">ريال سعودي (SAR)</option>
                    <option value="USD">دولار أمريكي (USD)</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-zinc-900/80 backdrop-blur-xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <span className="w-1.5 h-6 bg-orange-500 rounded-full"></span>
                  الأصناف المطلوبة
                </h3>
                <button
                  type="button"
                  onClick={addItem}
                  className="text-emerald-400 text-sm font-bold hover:bg-emerald-500/10 px-4 py-2 rounded-xl transition-colors flex items-center gap-1 border border-emerald-500/30"
                >
                  <Plus className="w-4 h-4" /> إضافة صنف
                </button>
              </div>

              <div className="space-y-3">
                {formData.items.length === 0 && (
                  <div className="text-center py-12 border-2 border-dashed border-white/10 rounded-xl">
                    <Package className="w-12 h-12 text-white/20 mx-auto mb-2" />
                    <p className="text-white/30">لم يتم إضافة أصناف. انقر على الزر أعلاه للبدء.</p>
                  </div>
                )}
                {formData.items.map((item, idx) => (
                  <div key={idx} className="flex flex-wrap md:flex-nowrap gap-3 items-end bg-white/5 p-4 rounded-xl border border-white/10 group">
                    <div className="flex-grow min-w-[200px]">
                      <label className="text-xs text-white/40 block mb-1">الصنف</label>
                      <select
                        className="w-full bg-zinc-800 border border-white/10 rounded-xl p-3 text-sm text-white"
                        value={item.item_id}
                        onChange={(e) => updateItem(idx, 'item_id', e.target.value)}
                      >
                        <option value="">اختر صنف...</option>
                        {itemsCatalog.map(p => (
                          <option key={p.id} value={p.id}>{p.name} {p.unit}</option>
                        ))}
                      </select>
                    </div>
                    <div className="w-24">
                      <label className="text-xs text-white/40 block mb-1">الكمية</label>
                      <input
                        type="text"
                        className="w-full bg-zinc-800 border border-white/10 rounded-xl p-3 text-sm text-center text-white"
                        placeholder="0.00"
                        value={item.qty}
                        onChange={(e) => {
                          const val = e.target.value
                          if (val === '' || /^\d*\.?\d{0,3}$/.test(val)) updateItem(idx, 'qty', val)
                        }}
                      />
                    </div>
                    <div className="w-32">
                      <label className="text-xs text-white/40 block mb-1">السعر التقديري</label>
                      <input
                        type="text"
                        className="w-full bg-zinc-800 border border-white/10 rounded-xl p-3 text-sm text-center text-white"
                        placeholder="0.00"
                        value={item.unit_price}
                        onChange={(e) => {
                          const val = e.target.value
                          if (val === '' || /^\d*\.?\d{0,2}$/.test(val)) updateItem(idx, 'unit_price', val)
                        }}
                      />
                    </div>
                    <div className="w-32 pt-6 text-start font-bold text-emerald-400">
                      {formatMoney(lineTotal(item.qty, item.unit_price))}
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
              <label className="block text-sm font-bold text-white/50 mb-2">ملاحظات وسبب الطلب</label>
              <textarea
                className="w-full bg-white/5 border border-white/10 rounded-xl p-4 h-24 text-white focus:border-emerald-500/50 focus:outline-none placeholder:text-white/20"
                placeholder="الغرض من الشراء، ملاحظات التسليم..."
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              ></textarea>
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="rounded-3xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-zinc-900 backdrop-blur-xl p-6 sticky top-6">
              <div className="flex items-center gap-2 mb-6 border-b border-white/10 pb-4">
                <Calculator className="w-5 h-5 text-emerald-400" />
                <h3 className="text-lg font-bold text-white">ملخص الطلب التقديري</h3>
              </div>

              <div className="space-y-4 text-sm">
                <div className="flex justify-between text-white/60">
                  <span>عدد الأصناف</span>
                  <span className="text-white">{formData.items.length}</span>
                </div>
                <div className="pt-4 mt-4 border-t border-white/10 flex flex-col justify-end text-end">
                  <span className="font-bold text-sm text-white/60">الإجمالي المبدئي المرجح</span>
                  <span className="font-black text-3xl text-emerald-400 block mt-2">
                    {formatMoney(financials.total)}
                    <span className="text-xs text-white/40 mr-1">{formData.currency}</span>
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
