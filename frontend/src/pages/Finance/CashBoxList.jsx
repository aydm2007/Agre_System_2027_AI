import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Vault } from 'lucide-react';

import api from '../../api/client';
import { useFarmContext } from '../../api/farmContext';
import { useToast } from '../../components/ToastProvider';
import { formatMoney } from '../../utils/decimal';

const safeArray = (d) => (Array.isArray(d) ? d : Array.isArray(d?.results) ? d.results : []);

const BOX_TYPE_LABEL = {
  MAIN: 'رئيسي',
  PETTY: 'عهدة',
};

export default function CashBoxList() {
  const toast = useToast();
  const { selectedFarmId } = useFarmContext();
  const [loading, setLoading] = useState(true);
  const [cashBoxes, setCashBoxes] = useState([]);

  const load = async () => {
    if (!selectedFarmId) {
      setCashBoxes([]);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const { data } = await api.get('/finance/cashboxes/', {
        params: { farm_id: selectedFarmId },
      });
      setCashBoxes(safeArray(data));
    } catch (err) {
      console.error(err);
      toast.error('فشل تحميل الصناديق');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFarmId]);

  const totals = useMemo(() => {
    const count = cashBoxes.length;
    const byCurrency = {};
    cashBoxes.forEach((b) => {
      const cur = b.currency || '---';
      const bal = Number(b.balance || 0);
      byCurrency[cur] = (byCurrency[cur] || 0) + (Number.isFinite(bal) ? bal : 0);
    });
    return { count, byCurrency };
  }, [cashBoxes]);

  return (
    <div className="app-page">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Vault className="h-6 w-6 text-gray-700" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">الصناديق</h1>
              <p className="text-sm text-gray-500">عرض الصناديق والأرصدة للمزرعة المحددة</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to="/finance/treasury"
              className="inline-flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50"
            >
              <ArrowLeft className="h-4 w-4" />
              رجوع
            </Link>
            <button
              onClick={load}
              className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
            >
              <RefreshCw className="h-4 w-4" />
              تحديث
            </button>
          </div>
        </div>

        {!selectedFarmId ? (
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-700">اختر مزرعة أولاً لعرض الصناديق.</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-white rounded-lg shadow p-4">
                <div className="text-sm text-gray-500">عدد الصناديق</div>
                <div className="text-2xl font-semibold text-gray-900">{totals.count}</div>
              </div>
              <div className="bg-white rounded-lg shadow p-4 md:col-span-2">
                <div className="text-sm text-gray-500 mb-2">إجمالي الأرصدة حسب العملة</div>
                <div className="flex flex-wrap gap-3">
                  {Object.keys(totals.byCurrency).length === 0 ? (
                    <span className="text-gray-700">—</span>
                  ) : (
                    Object.entries(totals.byCurrency).map(([cur, total]) => (
                      <span
                        key={cur}
                        className="inline-flex items-center px-3 py-1 rounded-full bg-gray-100 text-gray-800 text-sm"
                        dir="ltr"
                      >
                        {formatMoney(total)} {cur}
                      </span>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الاسم</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">النوع</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">العملة</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">الرصيد</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {loading ? (
                      <tr>
                        <td colSpan="4" className="px-6 py-4 text-center text-gray-500">
                          جاري التحميل...
                        </td>
                      </tr>
                    ) : cashBoxes.length === 0 ? (
                      <tr>
                        <td colSpan="4" className="px-6 py-4 text-center text-gray-500">
                          لا توجد صناديق
                        </td>
                      </tr>
                    ) : (
                      cashBoxes.map((b) => (
                        <tr key={b.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{b.name}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                            {BOX_TYPE_LABEL[b.box_type] || b.box_type}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{b.currency}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900" dir="ltr">
                            {formatMoney(b.balance)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
