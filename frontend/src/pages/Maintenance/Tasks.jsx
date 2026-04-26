import React from 'react';
import { Wrench, Clock, Search, Filter, Plus, ChevronRight, Lock } from 'lucide-react';
import { useSettings } from '../../contexts/SettingsContext';

const MaintenanceTasks = () => {
  const { isStrictMode } = useSettings();

  return (
    <div className="app-page bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-50 p-6 rtl" dir="rtl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-black mb-2 flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-xl text-white shadow-lg shadow-blue-600/20">
              <Wrench size={28} />
            </div>
            مهام الصيانة الميدانية
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            {isStrictMode ? 'إدارة أوامر العمل وتتبع القطع المستهلكة (Axis 10)' : 'قائمة المهام الفنية والجاهزية (المود البسيط)'}
          </p>
        </div>
        <button className="flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-bold transition-all shadow-lg shadow-blue-600/20 active:scale-95">
          <Plus size={20} /> إضافة مهمة صيانة
        </button>
      </div>

      {/* Control Bar */}
      <div className="flex flex-col md:flex-row items-center gap-4 mb-8 bg-white dark:bg-slate-800 p-4 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-800">
        <div className="flex gap-2 w-full md:w-auto overflow-x-auto">
          {['الكل', 'قيد العمل', 'معلق', 'مكتمل'].map((t, i) => (
            <button key={i} className={`px-4 py-2 rounded-xl text-sm font-bold transition-all whitespace-nowrap ${i === 0 ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700'}`}>
              {t}
            </button>
          ))}
        </div>
        <div className="h-8 w-[1px] bg-slate-200 dark:bg-slate-700 hidden md:block mx-2"></div>
        <div className="relative flex-1 w-full">
          <Search size={18} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input type="text" placeholder="بحث برقم الآلية أو النوع..." className="app-input py-2 pr-10 pl-4 w-full text-sm" />
        </div>
        <button className="p-2 bg-slate-100 dark:bg-slate-900 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-700 transition-all">
          <Filter size={20} className="text-slate-500" />
        </button>
      </div>

      {/* Task List */}
      <div className="space-y-4">
        {[
          { id: 'MT-8842', asset: 'حراثة نيو هولاند', type: 'دورية', dur: '4 ساعات', status: 'In Progress', urgent: true },
          { id: 'MT-8845', asset: 'مضخة رش الأسمدة', type: 'إصلاح عطل', dur: '12 ساعة', status: 'Pending', urgent: false },
          { id: 'MT-8839', asset: 'بئر المنطقة الشمالية', type: 'وقائية', dur: '30 دقيقة', status: 'Complete', urgent: false },
        ].map((task, i) => (
          <div key={i} className="app-card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 border-r-4 transition-all hover:scale-[1.01]" style={{ borderRightColor: task.urgent ? '#ef4444' : task.status === 'Complete' ? '#10b981' : '#3b82f6' }}>
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-xl ${task.urgent ? 'bg-red-100 text-red-600' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'}`}>
                <Wrench size={22} />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono text-slate-400">{task.id}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${task.urgent ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'}`}>
                    {task.type}
                  </span>
                </div>
                <h3 className="text-xl font-black">{task.asset}</h3>
              </div>
            </div>

            <div className="flex items-center gap-8 pr-4 border-r border-slate-100 dark:border-slate-800">
              <div className="text-center md:text-right">
                <p className="text-xs text-slate-400 mb-1">المدة المقدرة</p>
                <p className="font-bold flex items-center gap-1 text-sm"><Clock size={14} /> {task.dur}</p>
              </div>
              <div className="text-center md:text-right">
                <p className="text-xs text-slate-400 mb-1">الحالة</p>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${task.status === 'Complete' ? 'bg-emerald-500' : task.status === 'Pending' ? 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]' : 'bg-blue-500 animate-pulse'}`}></div>
                  <span className="text-sm font-bold">{task.status === 'Complete' ? 'مكتمل' : task.status === 'Pending' ? 'معلق' : 'قيد العمل'}</span>
                </div>
              </div>
              <button className="p-3 bg-slate-100 dark:bg-slate-800 rounded-xl hover:bg-blue-600 hover:text-white transition-all group">
                <ChevronRight size={20} className="group-hover:translate-x-[-2px] transition-transform" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {!isStrictMode && (
        <div className="mt-8 p-6 bg-blue-900/10 border border-blue-500/20 rounded-3xl flex items-center gap-4">
          <div className="p-2 bg-blue-500 rounded-lg text-white">
            <Lock size={20} />
          </div>
          <div>
            <h4 className="font-bold text-blue-500">خاصية الربط المالي مقفلة</h4>
            <p className="text-xs text-blue-400/80">في المود البسيط، يمكنك تسجيل انتهاء المهام تقنياً فقط. التكاليف والمخصصات المالية مجهزة في المود الصارم.</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default MaintenanceTasks;
