import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Vault,
  ListChecks,
  AlertTriangle,
  Clock3,
  Wallet,
  Boxes,
  ReceiptText,
  BadgeDollarSign,
} from 'lucide-react'
import api from '../../api/client'
import { useFarmContext } from '../../api/farmContext'

function KpiCard({ title, value, icon: Icon, tone }) {
  return (
    <div className={`rounded-lg border p-4 ${tone}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500">{title}</p>
          <p className="text-xl font-bold text-gray-900 mt-1">{value}</p>
        </div>
        <Icon className="h-5 w-5 text-gray-600" />
      </div>
    </div>
  )
}

export default function TreasuryDashboard() {
  const { selectedFarmId } = useFarmContext()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [kpis, setKpis] = useState(null)

  const loadControlTower = useCallback(async () => {
    if (!selectedFarmId) {
      setKpis(null)
      return
    }
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/finance/fiscal-periods/control-tower/', {
        params: { farm_id: selectedFarmId },
      })
      setKpis(data?.kpis || null)
    } catch (err) {
      console.error(err)
      setError('تعذر تحميل مؤشرات الرقابة اليومية.')
      setKpis(null)
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId])

  useEffect(() => {
    loadControlTower()
  }, [loadControlTower])

  return (
    <div className="app-page">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">الخزينة</h1>
            <p className="text-sm text-gray-500 mt-1">
              إدارة الصناديق والحركات مع مؤشرات رقابة يومية
            </p>
          </div>
          <button
            type="button"
            onClick={loadControlTower}
            className="px-3 py-2 rounded-lg border bg-white hover:bg-gray-50 text-sm"
          >
            تحديث المؤشرات
          </button>
        </div>

        {loading ? <div className="text-sm text-gray-500">جاري تحميل مؤشرات الرقابة...</div> : null}
        {error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        {kpis && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            <KpiCard
              title="انحرافات حرجة اليوم"
              value={kpis.critical_variances_today}
              icon={AlertTriangle}
              tone="bg-rose-50 border-rose-200"
            />
            <KpiCard
              title="مصروفات غير مخصصة"
              value={kpis.pending_expenses}
              icon={Clock3}
              tone="bg-amber-50 border-amber-200"
            />
            <KpiCard
              title="إجمالي حركات الخزينة اليوم"
              value={kpis.treasury_amount_today}
              icon={Wallet}
              tone="bg-emerald-50 border-emerald-200"
            />
            <KpiCard
              title="مواقع مخزون فعالة"
              value={kpis.inventory_positions}
              icon={Boxes}
              tone="bg-blue-50 border-blue-200"
            />
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link
            to="/finance/supplier-settlements"
            className="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6"
          >
            <div className="flex items-center">
              <div className="p-2 bg-sky-100 rounded-lg">
                <BadgeDollarSign className="h-6 w-6 text-sky-600" />
              </div>
              <div className="mr-4">
                <h2 className="text-lg font-semibold text-gray-900">تسوية الموردين</h2>
                <p className="text-sm text-gray-500">
                  لوحة موحدة لمراجعة المستحقات والموافقة والسداد والمطابقة مع الخزينة
                </p>
              </div>
            </div>
          </Link>

          <Link
            to="/finance/receipts-deposits"
            className="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6"
          >
            <div className="flex items-center">
              <div className="p-2 bg-amber-100 rounded-lg">
                <ReceiptText className="h-6 w-6 text-amber-600" />
              </div>
              <div className="mr-4">
                <h2 className="text-lg font-semibold text-gray-900">التحصيل والتوريد</h2>
                <p className="text-sm text-gray-500">
                  لوحة رقابية موحدة لربط الفواتير المعتمدة مع حركات التحصيل بالخزينة
                </p>
              </div>
            </div>
          </Link>

          <Link
            to="/finance/treasury/cashboxes"
            className="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6"
          >
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <Vault className="h-6 w-6 text-green-600" />
              </div>
              <div className="mr-4">
                <h2 className="text-lg font-semibold text-gray-900">الصناديق</h2>
                <p className="text-sm text-gray-500">عرض الصناديق والأرصدة حسب المزرعة</p>
              </div>
            </div>
          </Link>

          <Link
            to="/finance/treasury/transactions"
            className="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6"
          >
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <ListChecks className="h-6 w-6 text-blue-600" />
              </div>
              <div className="mr-4">
                <h2 className="text-lg font-semibold text-gray-900">حركات الخزينة</h2>
                <p className="text-sm text-gray-500">تسجيل حركة جديدة واستعراض السجل</p>
              </div>
            </div>
          </Link>
        </div>
      </div>
    </div>
  )
}
