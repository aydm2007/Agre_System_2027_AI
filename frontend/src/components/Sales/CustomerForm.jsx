import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { ArrowLeft, Save, Trash2 } from 'lucide-react'

import api from '../../api/client'
import { useToast } from '../../components/ToastProvider'
import { extractApiError } from '../../utils/errorUtils'

const emptyForm = {
  name: '',
  phone: '',
  location: '',
  is_active: true,
}

export default function CustomerForm() {
  const toast = useToast()
  const { id } = useParams()
  const isEdit = useMemo(() => !!id, [id])
  const navigate = useNavigate()

  const [form, setForm] = useState(emptyForm)
  const [loading, setLoading] = useState(!!id)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!id) return
    const load = async () => {
      try {
        setLoading(true)
        const res = await api.get(`/sales/customers/${id}/`)
        setForm({
          name: res.data?.name || '',
          phone: res.data?.phone || '',
          location: res.data?.location || '',
          is_active: typeof res.data?.is_active === 'boolean' ? res.data.is_active : true,
        })
      } catch (err) {
        console.error('Error loading customer:', err)
        toast.error('فشل تحميل بيانات العميل')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id, toast])

  const onChange = (field, value) => setForm((p) => ({ ...p, [field]: value }))

  const save = async (e) => {
    e.preventDefault()
    if (!form.name?.trim()) {
      toast.error('اسم العميل مطلوب')
      return
    }

    try {
      setSaving(true)
      const payload = {
        name: form.name.trim(),
        phone: form.phone?.trim() || null,
        location: form.location?.trim() || null,
        is_active: !!form.is_active,
      }

      if (isEdit) {
        await api.patch(`/sales/customers/${id}/`, payload)
        toast.success('تم تحديث العميل بنجاح')
      } else {
        await api.post('/sales/customers/', payload)
        toast.success('تم إنشاء العميل بنجاح')
      }

      navigate('/sales/customers')
    } catch (err) {
      console.error('Error saving customer:', err)
      const msg = extractApiError(err, 'فشل حفظ العميل')
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  const remove = async () => {
    if (!id) return
    if (!confirm('هل أنت متأكد من حذف العميل؟')) return

    try {
      await api.delete(`/sales/customers/${id}/`)
      toast.success('تم حذف العميل')
      navigate('/sales/customers')
    } catch (err) {
      console.error('Error deleting customer:', err)
      toast.error(extractApiError(err, 'فشل حذف العميل'))
    }
  }

  if (loading) {
    return (
      <div className="app-page">
        <div className="bg-white rounded-lg shadow p-6">جاري التحميل...</div>
      </div>
    )
  }

  return (
    <div className="app-page">
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="p-6 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              to="/sales/customers"
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
              title="رجوع"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">
                {isEdit ? 'تعديل عميل' : 'إضافة عميل'}
              </h1>
              <p className="text-sm text-gray-500">
                إدارة بيانات العملاء (الاسم / الهاتف / الموقع)
              </p>
            </div>
          </div>

          {isEdit && (
            <button
              onClick={remove}
              className="inline-flex items-center px-3 py-2 border border-red-200 text-red-700 rounded-md hover:bg-red-50"
              title="حذف"
            >
              <Trash2 className="h-4 w-4 ml-2" />
              حذف
            </button>
          )}
        </div>

        <form onSubmit={save} className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700">اسم العميل *</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => onChange('name', e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
                placeholder="مثال: أحمد صالح"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">رقم الهاتف</label>
              <input
                type="text"
                value={form.phone}
                onChange={(e) => onChange('phone', e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
                placeholder="مثال: 77xxxxxxx"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700">الموقع</label>
              <input
                type="text"
                value={form.location}
                onChange={(e) => onChange('location', e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
                placeholder="مثال: صنعاء - التحرير"
              />
            </div>

            <div className="md:col-span-2">
              <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={!!form.is_active}
                  onChange={(e) => onChange('is_active', e.target.checked)}
                  className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                />
                نشط
              </label>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
            >
              <Save className="h-4 w-4 ml-2" />
              {saving ? 'جارٍ الحفظ...' : 'حفظ'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
