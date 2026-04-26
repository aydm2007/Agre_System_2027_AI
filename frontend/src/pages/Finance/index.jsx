/* eslint-disable react/no-unescaped-entities */
import React, { useState } from 'react';
import { Landmark, TrendingUp, PieChart, FileText, Download, ArrowRightLeft, Lock } from 'lucide-react';
import { useSettings } from '../../contexts/SettingsContext';
import { useFarmContext } from '../../api/farmContext';

const FinancialExplorer = () => {
  const [activeReport, setActiveReport] = useState('pl');
  const { isStrictMode } = useSettings();
  const { farms, selectedFarmId, selectFarm } = useFarmContext();

  const formatValue = (val, isMoney = true) => {
    if (!isStrictMode && isMoney) return '--- % ---';
    return isMoney ? val.toLocaleString() + ' ر.ي' : val;
  };

  return (
    <div className="app-page bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-50 p-6 rtl" dir="rtl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-black mb-2 flex items-center gap-3">
            <div className="p-2 bg-emerald-700 rounded-xl text-white shadow-lg shadow-emerald-700/20">
              <Landmark size={28} />
            </div>
            استكشاف القوائم المالية والتقارير
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            {isStrictMode ? 'تحليل الأرباح والخسائر والميزانية العمومية على أساس الاستحقاق (Axis 5)' : 'مؤشرات الأداء الإنتاجي والهيكل العام (المود البسيط)'}
          </p>
        </div>
        <div className="flex gap-2">
          {isStrictMode && (
            <>
              <button className="flex items-center justify-center gap-2 px-6 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-2xl font-bold hover:bg-slate-50 transition-all shadow-sm">
                <Download size={18} /> تصدير Excel
              </button>
              <button className="flex items-center justify-center gap-2 px-6 py-3 bg-emerald-700 hover:bg-emerald-600 text-white rounded-2xl font-bold transition-all shadow-lg shadow-emerald-700/20">
                <FileText size={18} /> معاينة التقرير الرسمي
              </button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Sidebar: Navigation & Filters */}
        <div className="lg:col-span-1 space-y-6">
          <div className="app-panel p-4 space-y-2">
            {[
              { id: 'pl', label: 'الأرباح والخسائر (P&L)', icon: TrendingUp },
              { id: 'bs', label: 'الميزانية العمومية (BS)', icon: Landmark },
              { id: 'cf', label: 'التدفقات النقدية', icon: ArrowRightLeft, disabled: !isStrictMode },
              { id: 'tb', label: 'ميزان المراجعة', icon: PieChart, disabled: !isStrictMode },
            ].map(report => (
              <button 
                key={report.id}
                disabled={report.disabled}
                onClick={() => setActiveReport(report.id)}
                className={`w-full flex items-center justify-between p-4 rounded-xl font-bold transition-all ${activeReport === report.id ? 'bg-emerald-700 text-white shadow-lg' : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500'} ${report.disabled ? 'opacity-30 cursor-not-allowed' : ''}`}
              >
                <div className="flex items-center gap-3">
                  <report.icon size={20} />
                  {report.label}
                </div>
                {report.disabled && <Lock size={14} />}
              </button>
            ))}
          </div>

          <div className="app-panel p-6">
             <h2 className="font-black text-sm uppercase tracking-wider text-slate-400 mb-4">خيارات العرض</h2>
             <div className="space-y-4">
               <div>
                  <label className="text-xs text-slate-500 block mb-2">المزرعة (فلترة)</label>
                  <select 
                    className="app-input w-full p-2 text-sm"
                    value={selectedFarmId || ''}
                    onChange={(e) => selectFarm(e.target.value)}
                  >
                    <option value="">جميع المزارع للصلاحية</option>
                    {farms.map((f) => (
                      <option key={f.id} value={f.id}>{f.name}</option>
                    ))}
                  </select>
               </div>
               <div>
                  <label className="text-xs text-slate-500 block mb-2">السنة المالية</label>
                  <select className="app-input w-full p-2 text-sm">
                    <option>2026 (الحالية)</option>
                    <option>2025</option>
                  </select>
               </div>
               <button className="w-full py-3 bg-slate-900 dark:bg-slate-700 text-white rounded-xl text-sm font-bold mt-4">تحديث البيانات</button>
             </div>
          </div>
        </div>

        {/* Main: Report Table */}
        <div className="lg:col-span-3 space-y-8">
          {/* Quick Snapshot */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
             <div className="app-panel p-6 bg-emerald-50 dark:bg-emerald-900/10 border-emerald-100 dark:border-emerald-900/40">
                <p className="text-xs text-emerald-600 dark:text-emerald-400 font-bold mb-1 uppercase tracking-widest">إجمالي الإيرادات</p>
                <h3 className="text-2xl font-black text-emerald-700 dark:text-emerald-400">
                  {isStrictMode ? '12,450,200 ر.ي' : '100% (تشغيل كامل)'}
                </h3>
             </div>
             <div className="app-panel p-6 bg-red-50 dark:bg-red-900/10 border-red-100 dark:border-red-900/40">
                <p className="text-xs text-red-600 dark:text-red-400 font-bold mb-1 uppercase tracking-widest">إجمالي التكاليف</p>
                <h3 className="text-2xl font-black text-red-700 dark:text-red-400">
                  {isStrictMode ? '8,120,450 ر.ي' : '65.2% (تحت السيطرة)'}
                </h3>
             </div>
             <div className="app-panel p-6 bg-blue-50 dark:bg-blue-900/10 border-blue-100 dark:border-blue-900/40">
                <p className="text-xs text-blue-600 dark:text-blue-400 font-bold mb-1 uppercase tracking-widest">صافي الربح</p>
                <h3 className="text-2xl font-black text-blue-700 dark:text-blue-400">
                   {isStrictMode ? '4,329,750 ر.ي' : '+34.8% (نمو إيجابي)'}
                </h3>
             </div>
          </div>

          {!isStrictMode && (
            <div className="bg-amber-100 dark:bg-amber-900/20 p-4 rounded-2xl text-amber-700 dark:text-amber-500 text-sm font-bold flex items-center gap-3">
              <Lock size={18} /> ملاحظة: أنت تشاهد "المود البسيط". الأرقام المالية الدقيقة متاحة فقط لمسؤولي المحاسبة في المود الصارم (STRICT).
            </div>
          )}

          {/* Table Container */}
          <div className="app-panel overflow-hidden border-slate-200 dark:border-slate-800">
             <div className="p-4 bg-white/50 dark:bg-slate-800/50 border-b dark:border-slate-800 flex justify-between items-center text-sm font-bold">
                <span>بيان كشف الأرباح والخسائر</span>
                <span className="text-slate-400">التاريخ: {new Date().toLocaleDateString('ar-YE')}</span>
             </div>
             <div className="overflow-x-auto">
               <table className="w-full text-right border-collapse">
                 <thead>
                   <tr className="bg-slate-100 dark:bg-slate-900 text-slate-500 text-xs">
                     <th className="p-4">اسم الحساب (Account Name)</th>
                     <th className="p-4">رقم الحساب</th>
                     <th className="p-4 text-left">الرصيد الافتتاحي</th>
                     <th className="p-4 text-left">إجمالي الحركة</th>
                     <th className="p-4 text-left">الرصيد الختامي</th>
                   </tr>
                 </thead>
                 <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                   {/* Summary Categories */}
                   <tr className="bg-emerald-50/20 dark:bg-emerald-900/5">
                     <td className="p-4 font-black" colSpan={2}>1. الإيرادات التشغيلية</td>
                     <td className="p-4 text-left font-black" colSpan={3}>{isStrictMode ? '12,450,200.00 ر.ي' : 'مفعل'}</td>
                   </tr>
                   {[
                     { name: 'مبيعات المحاصيل النقدية', code: '4101', val: 8200000 },
                     { name: 'مبيعات الفواكه والتمور', code: '4102', val: 4000000 },
                     { name: 'إيرادات أخرى', code: '4103', val: 250200 },
                   ].map((row, i) => (
                     <tr key={i} className="text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/20 transition-colors">
                       <td className="p-4 pr-10">{row.name}</td>
                       <td className="p-4 font-mono">{row.code}</td>
                       <td className="p-4 text-left">0.00</td>
                       <td className="p-4 text-left">{formatValue(row.val)}</td>
                       <td className="p-4 text-left font-bold text-emerald-600">{formatValue(row.val)}</td>
                     </tr>
                   ))}
                   
                   <tr className="bg-red-50/20 dark:bg-red-900/5">
                     <td className="p-4 font-black" colSpan={2}>2. التكاليف المباشرة (COGS)</td>
                     <td className="p-4 text-left font-black" colSpan={3}>{isStrictMode ? '(8,120,450.00) ر.ي' : 'نشط'}</td>
                   </tr>
                   {[
                     { name: 'تكلفة الأسمدة والمبيدات', code: '5101', val: 3500000 },
                     { name: 'أجور العمالة المباشرة', code: '5102', val: 2800000 },
                     { name: 'وقود وزيوت آليات', code: '5103', val: 1820450 },
                   ].map((row, i) => (
                     <tr key={i} className="text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/20 transition-colors">
                       <td className="p-4 pr-10">{row.name}</td>
                       <td className="p-4 font-mono">{row.code}</td>
                       <td className="p-4 text-left">0.00</td>
                       <td className="p-4 text-left">{formatValue(row.val)}</td>
                       <td className="p-4 text-left font-bold text-red-600">({formatValue(row.val)})</td>
                     </tr>
                   ))}
                 </tbody>
                 {isStrictMode && (
                   <tfoot>
                     <tr className="bg-slate-900 text-white font-black">
                       <td className="p-6 text-xl" colSpan={2}>إجمالي الدخل التشغيلي</td>
                       <td className="p-6 text-2xl text-left" colSpan={3}>4,329,750.00 ر.ي</td>
                     </tr>
                   </tfoot>
                 )}
               </table>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FinancialExplorer;
