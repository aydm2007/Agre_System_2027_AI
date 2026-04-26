import { useCallback, useEffect, useState } from 'react'
import { SharecroppingContracts, Crops, Seasons } from '../../api/client'
import FeedbackRegion from '../../components/FeedbackRegion'
import useFeedback from '../../hooks/useFeedback'

const INITIAL_FORM = {
  farmer_name: '',
  farmer_id_number: '',
  crop: '',
  season: '',
  contract_type: 'SHARECROPPING',
  irrigation_type: 'WELL_PUMP',
  institution_percentage: '0.3000',
  annual_rent_amount: '',
  is_active: true,
  notes: '',
}

export default function SharecroppingContractsTab({ selectedFarmId, hasFarms }) {
  const [contracts, setContracts] = useState([])
  const [contractsLoading, setContractsLoading] = useState(false)
  const [form, setForm] = useState(INITIAL_FORM)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)

  const [cropsList, setCropsList] = useState([])
  const [seasonsList, setSeasonsList] = useState([])

  const { message, error, showMessage, showError } = useFeedback()

  const loadDependencies = useCallback(async () => {
    try {
      const [crRes, seRes] = await Promise.all([Crops.list(), Seasons.list()])
      setCropsList(crRes.data?.results ?? crRes.data ?? [])
      setSeasonsList(seRes.data?.results ?? seRes.data ?? [])
    } catch (err) {
      console.error('Failed to load dependencies', err)
    }
  }, [])

  useEffect(() => {
    loadDependencies()
  }, [loadDependencies])

  const loadContracts = useCallback(
    async (farmId) => {
      if (!farmId) {
        setContracts([])
        return
      }
      setContractsLoading(true)
      try {
        const response = await SharecroppingContracts.list({ farm: farmId })
        const data = response.data?.results ?? response.data ?? []
        setContracts(Array.isArray(data) ? data : [])
      } catch (err) {
        console.error('Failed to load contracts', err)
        showError('فشل تحميل عقود الشراكة')
        setContracts([])
      } finally {
        setContractsLoading(false)
      }
    },
    [showError],
  )

  useEffect(() => {
    setForm(INITIAL_FORM)
    setEditingId(null)
    loadContracts(selectedFarmId)
  }, [loadContracts, selectedFarmId])

  const handleSubmit = useCallback(
    async (event) => {
      event.preventDefault()
      if (
        !form.farmer_name.trim() ||
        !form.crop ||
        !form.contract_type ||
        !form.irrigation_type ||
        !form.institution_percentage
      ) {
        showError('الرجاء إكمال كافة الحقول الإلزامية')
        return
      }
      setSaving(true)
      try {
        const payload = {
          farm: selectedFarmId,
          farmer_name: form.farmer_name.trim(),
          farmer_id_number: form.farmer_id_number.trim() || undefined,
          crop: form.crop,
          season: form.season || null,
          contract_type: form.contract_type,
          irrigation_type: form.irrigation_type,
          institution_percentage: form.institution_percentage,
          annual_rent_amount:
            form.contract_type === 'RENTAL' ? form.annual_rent_amount || null : null,
          is_active: form.is_active,
          notes: form.notes.trim() || '',
        }

        if (editingId) {
          await SharecroppingContracts.update(editingId, payload)
          showMessage('تم تحديث العقد بنجاح')
        } else {
          await SharecroppingContracts.create(payload)
          showMessage('تمت إضافة العقد بنجاح')
        }
        setForm(INITIAL_FORM)
        setEditingId(null)
        loadContracts(selectedFarmId)
      } catch (err) {
        console.error('Failed to save contract', err)
        showError('خطأ أثناء حفظ العقد')
      } finally {
        setSaving(false)
      }
    },
    [editingId, form, loadContracts, selectedFarmId, showError, showMessage],
  )

  const handleEdit = useCallback((contract) => {
    setEditingId(contract.id)
    setForm({
      farmer_name: contract.farmer_name || '',
      farmer_id_number: contract.farmer_id_number || '',
      crop: contract.crop || '',
      season: contract.season || '',
      contract_type: contract.contract_type || 'SHARECROPPING',
      irrigation_type: contract.irrigation_type || 'WELL_PUMP',
      institution_percentage: contract.institution_percentage
        ? contract.institution_percentage.toString()
        : '0.3000',
      annual_rent_amount: contract.annual_rent_amount ? contract.annual_rent_amount.toString() : '',
      is_active: contract.is_active ?? true,
      notes: contract.notes || '',
    })
  }, [])

  const handleCancelEdit = useCallback(() => {
    setEditingId(null)
    setForm(INITIAL_FORM)
  }, [])

  const handleRemove = useCallback(
    async (id) => {
      if (!window.confirm('هل أنت متأكد من حذف هذا العقد؟')) return
      try {
        await SharecroppingContracts.remove(id)
        showMessage('تم إلغاء العقد بنجاح')
        setContracts((prev) => prev.filter((c) => c.id !== id))
      } catch (err) {
        console.error('Failed to remove contract', err)
        showError('واجهنا مشكلة أثناء إزالة العقد')
      }
    },
    [showError, showMessage],
  )

  if (!hasFarms) return null

  return (
    <section className="space-y-4">
      <FeedbackRegion error={error} message={message} />

      <form
        onSubmit={handleSubmit}
        className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow border dark:border-slate-700 space-y-4"
      >
        <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100">
          {editingId ? 'تعديل عقد شراكة/إيجار' : 'إضافة عقد جديد'}
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200">
              اسم الشريك / المزارع *
            </label>
            <input
              required
              type="text"
              value={form.farmer_name}
              onChange={(e) => setForm((p) => ({ ...p, farmer_name: e.target.value }))}
              className="mt-1 border dark:border-slate-600 rounded p-2 text-sm w-full bg-white dark:bg-slate-700 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200">
              رقم الهوية
            </label>
            <input
              type="text"
              value={form.farmer_id_number}
              onChange={(e) => setForm((p) => ({ ...p, farmer_id_number: e.target.value }))}
              className="mt-1 border dark:border-slate-600 rounded p-2 text-sm w-full bg-white dark:bg-slate-700 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200">
              المحصول *
            </label>
            <select
              required
              value={form.crop}
              onChange={(e) => setForm((p) => ({ ...p, crop: e.target.value }))}
              className="mt-1 border dark:border-slate-600 rounded p-2 text-sm w-full bg-white dark:bg-slate-700 dark:text-white"
            >
              <option value="">-- المحصول --</option>
              {cropsList.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200">
              الموسم
            </label>
            <select
              value={form.season}
              onChange={(e) => setForm((p) => ({ ...p, season: e.target.value }))}
              className="mt-1 border dark:border-slate-600 rounded p-2 text-sm w-full bg-white dark:bg-slate-700 dark:text-white"
            >
              <option value="">-- اختياري --</option>
              {seasonsList.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200">
              نوع العقد *
            </label>
            <select
              value={form.contract_type}
              onChange={(e) => setForm((p) => ({ ...p, contract_type: e.target.value }))}
              className="mt-1 border dark:border-slate-600 rounded p-2 text-sm w-full bg-white dark:bg-slate-700 dark:text-white"
            >
              <option value="SHARECROPPING">شراكة (مناصبة)</option>
              <option value="RENTAL">إيجار</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200">
              نوع الري (يحدد الزكاة 5% أم 10%) *
            </label>
            <select
              value={form.irrigation_type}
              onChange={(e) => setForm((p) => ({ ...p, irrigation_type: e.target.value }))}
              className="mt-1 border dark:border-slate-600 rounded p-2 text-sm w-full bg-white dark:bg-slate-700 dark:text-white"
            >
              <option value="WELL_PUMP">آبار / طاقة شمسية (5%)</option>
              <option value="RAIN">أمطار / غيول (10%)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200">
              نسبة المؤسسة * (مثال 0.3 لـ 30%) - تُطبق مالياً أو عينياً حسب سياسة الإعدادات
            </label>
            <input
              required
              type="number"
              step="0.0001"
              min="0"
              max="1"
              value={form.institution_percentage}
              onChange={(e) => setForm((p) => ({ ...p, institution_percentage: e.target.value }))}
              className="mt-1 border dark:border-slate-600 rounded p-2 text-sm w-full bg-white dark:bg-slate-700 dark:text-white"
            />
          </div>
          {form.contract_type === 'RENTAL' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200">
                مبلغ الإيجار السنوي
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.annual_rent_amount}
                onChange={(e) => setForm((p) => ({ ...p, annual_rent_amount: e.target.value }))}
                className="mt-1 border dark:border-slate-600 rounded p-2 text-sm w-full bg-white dark:bg-slate-700 dark:text-white"
              />
            </div>
          )}

          <div className="flex items-center pt-6">
            <input
              type="checkbox"
              id="is_active"
              checked={form.is_active}
              onChange={(e) => setForm((p) => ({ ...p, is_active: e.target.checked }))}
              className="h-4 w-4 text-primary rounded border-gray-300 dark:border-slate-600 focus:ring-primary"
            />
            <label htmlFor="is_active" className="mr-2 text-sm text-gray-700 dark:text-slate-200">
              نشط
            </label>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          {editingId && (
            <button
              type="button"
              onClick={handleCancelEdit}
              className="px-4 py-2 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-slate-200 rounded hover:bg-gray-300 dark:hover:bg-slate-600"
            >
              الغاء
            </button>
          )}
          <button
            type="submit"
            disabled={saving || !selectedFarmId}
            className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark disabled:opacity-60"
          >
            {saving ? 'جاري الحفظ...' : 'حفظ العقد'}
          </button>
        </div>
      </form>

      <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow border dark:border-slate-700">
        <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">العقود الحالية</h3>
        {contractsLoading ? (
          <div className="text-center text-gray-500 py-4">جاري التحميل...</div>
        ) : contracts.length === 0 ? (
          <div className="text-center text-gray-500 py-4">لا توجد عقود مسجلة</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm text-right rtl">
              <thead className="bg-gray-50 dark:bg-slate-700 text-gray-700 dark:text-slate-200">
                <tr>
                  <th className="px-4 py-2 font-medium">اسم المزارع</th>
                  <th className="px-4 py-2 font-medium">نوع العقد</th>
                  <th className="px-4 py-2 font-medium">المحصول</th>
                  <th className="px-4 py-2 font-medium">نسبة المؤسسة</th>
                  <th className="px-4 py-2 font-medium">الحالة</th>
                  <th className="px-4 py-2 font-medium">إجراءات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-slate-700">
                {contracts.map((contract) => (
                  <tr key={contract.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/50">
                    <td className="px-4 py-2 text-gray-900 dark:text-white font-medium">
                      {contract.farmer_name}
                    </td>
                    <td className="px-4 py-2 text-gray-600 dark:text-slate-400">
                      {contract.contract_type === 'SHARECROPPING' ? 'شراكة' : 'إيجار'}
                    </td>
                    <td className="px-4 py-2 text-gray-600 dark:text-slate-400">
                      {cropsList.find((c) => c.id === contract.crop)?.name ||
                        `محصول #${contract.crop}`}
                    </td>
                    <td className="px-4 py-2 text-gray-600 dark:text-slate-400">
                      {(parseFloat(contract.institution_percentage) * 100).toFixed(2)}%
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`px-2 py-1 rounded text-xs ${contract.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}
                      >
                        {contract.is_active ? 'نشط' : 'مغلق'}
                      </span>
                    </td>
                    <td className="px-4 py-2 flex gap-2 justify-end">
                      <button
                        onClick={() => handleEdit(contract)}
                        className="text-primary hover:text-primary-dark"
                      >
                        تعديل
                      </button>
                      <button
                        onClick={() => handleRemove(contract.id)}
                        className="text-red-500 hover:text-red-700 mr-2"
                      >
                        حذف
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  )
}
