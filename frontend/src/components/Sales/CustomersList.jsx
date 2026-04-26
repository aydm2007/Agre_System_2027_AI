import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, Plus, Edit, Trash2, Users } from 'lucide-react'

import api from '../../api/client'
import { useToast } from '../../components/ToastProvider'
import { extractApiError } from '../../utils/errorUtils'

const safeArray = (d) => (Array.isArray(d) ? d : Array.isArray(d?.results) ? d.results : [])

export default function CustomersList() {
  const toast = useToast()
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  const load = async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await api.get('/sales/customers/')
      setCustomers(safeArray(res.data))
    } catch (err) {
      console.error('Error loading customers:', err)
      setError(extractApiError(err, 'فشل تحميل العملاء'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return customers
    return customers.filter((c) => {
      const name = (c?.name || '').toLowerCase()
      const phone = (c?.phone || '').toLowerCase()
      const location = (c?.location || '').toLowerCase()
      return name.includes(q) || phone.includes(q) || location.includes(q)
    })
  }, [customers, search])

  const stats = useMemo(() => {
    const total = customers.length
    const active = customers.filter((c) => c?.is_active !== false).length
    return { total, active, inactive: Math.max(0, total - active) }
  }, [customers])

  const onDelete = async (id) => {
    if (!id) return
    const ok = window.confirm('هل تريد حذف هذا العميل؟')
    if (!ok) return

    try {
      await api.delete(`/sales/customers/${id}/`)
      toast.success('تم حذف العميل')
      await load()
    } catch (err) {
      console.error('Error deleting customer:', err)
      toast.error(extractApiError(err, 'فشل حذف العميل'))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Users className="h-7 w-7" />
            العملاء
          </h1>
          <p className="text-gray-600">إدارة قاعدة بيانات العملاء (الاسم / الجوال / العنوان)</p>
        </div>
        <Link
          to="/sales/customers/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          إضافة عميل
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">إجمالي العملاء</div>
          <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">النشط</div>
          <div className="text-2xl font-bold text-green-600">{stats.active}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">غير نشط</div>
          <div className="text-2xl font-bold text-gray-600">{stats.inactive}</div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="بحث بالاسم أو الجوال أو العنوان..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
            <p className="mt-2 text-gray-600">جاري التحميل...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center">
            <p className="text-red-600">{error}</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-600">لا يوجد عملاء</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    الاسم
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    الجوال
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    العنوان
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    الحالة
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    الإجراءات
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filtered.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{c?.name || '-'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{c?.phone || '-'}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">{c?.location || '-'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          c?.is_active === false
                            ? 'bg-gray-100 text-gray-800'
                            : 'bg-green-100 text-green-800'
                        }`}
                      >
                        {c?.is_active === false ? 'غير نشط' : 'نشط'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/sales/customers/${c.id}`}
                          className="inline-flex items-center gap-1 px-3 py-1 text-blue-600 hover:text-blue-700"
                          title="تعديل"
                        >
                          <Edit className="h-4 w-4" />
                          تعديل
                        </Link>
                        <button
                          onClick={() => onDelete(c.id)}
                          className="inline-flex items-center gap-1 px-3 py-1 text-red-600 hover:text-red-700"
                          title="حذف"
                        >
                          <Trash2 className="h-4 w-4" />
                          حذف
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
