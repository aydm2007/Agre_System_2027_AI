import React from 'react';
import { FileText, Plus, Search, CheckCircle2, Clock, AlertCircle, TrendingUp, Users, Lock } from 'lucide-react';
import { useSettings } from '../../contexts/SettingsContext';

const RFQManager = () => {
  const { isStrictMode } = useSettings();

  return (
    <div className="app-page bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-50 p-6 rtl" dir="rtl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-black mb-2 flex items-center gap-3">
            <div className="p-2 bg-amber-500 rounded-xl text-white shadow-lg shadow-amber-500/20">
              <FileText size={28} />
            </div>
            إدارة المشتريات والمناقصات
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            {isStrictMode ? 'إدارة طلبات عروض الأسعار (RFQ) ومقارنة عطاءات الموردين' : 'متابعة احتياجات التوريد والطلبات التشغيلية (المود البسيط)'}
          </p>
        </div>
        {isStrictMode && (
          <button className="flex items-center justify-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-2xl font-bold transition-all shadow-lg shadow-emerald-600/20 active:scale-95">
            <Plus size={20} /> طلب عروض أسعار جديد
          </button>
        )}
      </div>

      {!isStrictMode && (
        <div className="mb-8 p-4 bg-amber-100 dark:bg-amber-900/20 rounded-2xl text-amber-700 dark:text-amber-500 text-sm font-bold flex items-center gap-3 border border-amber-200 dark:border-amber-900/40">
          <Lock size={18} /> ملاحظة: ميزات التسعير والترسية المالية مفعلة فقط في المود الصارم (STRICT).
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {[
          { label: 'طلبات نشطة', value: '12', icon: Clock, color: 'blue' },
          { label: 'بانتظار الترسية', value: isStrictMode ? '5' : '-', icon: TrendingUp, color: 'amber' },
          { label: 'مناقصات مكتملة', value: '128', icon: CheckCircle2, color: 'emerald' },
          { label: 'الموردين المعتمدين', value: '42', icon: Users, color: 'indigo' },
        ].map((stat, i) => (
          <div key={i} className="app-card p-6 border-l-4" style={{ borderLeftColor: `var(--tw-color-${stat.color}-500)` }}>
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-slate-500 mb-1">{stat.label}</p>
                <h3 className="text-2xl font-black">{stat.value}</h3>
              </div>
              <stat.icon size={24} className={`text-${stat.color}-500 opacity-20`} />
            </div>
          </div>
        ))}
      </div>

      {/* Main Content Area */}
      <div className="app-panel overflow-hidden border-slate-200 dark:border-slate-800">
        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-800/50">
          <div className="flex gap-2">
            {['نشطة', 'تحت التقييم', 'مكتملة', 'المسودات'].map((tab, i) => (
              <button 
                key={i}
                className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${i === 0 ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600' : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500'}`}
              >
                {tab}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <div className="relative">
              <Search size={18} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input type="text" placeholder="بحث في المناقصات..." className="app-input py-2 pr-10 pl-4 w-64 text-sm" />
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-right border-collapse">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-900/50 text-slate-500 text-sm">
                <th className="p-4 font-bold border-b border-slate-200 dark:border-slate-800">كود الطلب</th>
                <th className="p-4 font-bold border-b border-slate-200 dark:border-slate-800">العنوان</th>
                <th className="p-4 font-bold border-b border-slate-200 dark:border-slate-800">تاريخ الإغلاق</th>
                <th className="p-4 font-bold border-b border-slate-200 dark:border-slate-800">العروض</th>
                <th className="p-4 font-bold border-b border-slate-200 dark:border-slate-800">النوع</th>
                <th className="p-4 font-bold border-b border-slate-200 dark:border-slate-800">الحالة</th>
                <th className="p-4 font-bold border-b border-slate-200 dark:border-slate-800">الإجراءات</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {[1, 2, 3].map(i => (
                <tr key={i} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                  <td className="p-4 font-mono text-sm">#RFQ-2026-00{i}</td>
                  <td className="p-4 font-bold">شراء أسمدة ومبيدات حشرية (الموسم القادم)</td>
                  <td className="p-4 text-sm text-slate-500">2026-05-15</td>
                  <td className="p-4 text-sm">
                    {isStrictMode ? `${i * 2 + 1} عرض مستلم` : 'يدعم المزامنة'}
                  </td>
                  <td className="p-4">
                    <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-600 rounded-full text-xs font-bold">مناقصة عامة</span>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2 text-amber-500 text-sm font-bold">
                       <Clock size={14} /> بانتظار التقييم
                    </div>
                  </td>
                  <td className="p-4 space-x-2 space-x-reverse">
                    <button className="text-emerald-500 hover:underline text-sm font-bold">عرض التفاصيل</button>
                    <span className="text-slate-300">|</span>
                    <button className="text-slate-400 hover:text-red-500 transition-colors">
                      <AlertCircle size={18} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default RFQManager;
