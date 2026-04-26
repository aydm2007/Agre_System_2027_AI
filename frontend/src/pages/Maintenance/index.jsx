import React from 'react';
import { Settings, Calendar as CalendarIcon, AlertCircle, Wrench, Fuel, Activity, Clock, ChevronLeft, ChevronRight, Lock } from 'lucide-react';
import { useSettings } from '../../contexts/SettingsContext';

const MaintenanceDashboard = () => {
  const { isStrictMode } = useSettings();

  return (
    <div className="app-page bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-50 p-6 rtl" dir="rtl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-black mb-2 flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-xl text-white shadow-lg shadow-blue-600/20">
              <Settings size={28} />
            </div>
            الصيانة الوقائية والآليات
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            {isStrictMode ? 'مراقبة صحة الأصول وتكاليف الصيانة الدورية (Axis 9 & 10)' : 'متابعة الجاهزية التشغيلية للأسطول (المود البسيط)'}
          </p>
        </div>
        <div className="flex gap-2 text-xs items-center ml-4">
           {isStrictMode ? (
             <span className="bg-red-100 dark:bg-red-900/30 text-red-600 px-3 py-1 rounded-full font-bold flex items-center gap-1">
               <Lock size={12} /> STRICT
             </span>
           ) : (
             <span className="bg-blue-100 dark:bg-blue-900/30 text-blue-600 px-3 py-1 rounded-full font-bold flex items-center gap-1">
               SIMPLE MODE
             </span>
           )}
        </div>
        <div className="flex gap-2">
          <button className="flex items-center justify-center gap-2 px-6 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-2xl font-bold transition-all shadow-sm hover:bg-slate-50 active:scale-95">
            <Activity size={18} /> سجل القياسات
          </button>
          <button className="flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-bold transition-all shadow-lg shadow-blue-600/20 active:scale-95">
            <Wrench size={18} /> فتح تذكرة صيانة
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left: Active Maintenance Schedule */}
        <div className="lg:col-span-2 space-y-8">
          <div className="app-panel p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <CalendarIcon size={22} className="text-blue-500" /> جدول الصيانة القادمة
              </h2>
              <div className="flex gap-2">
                <button className="p-2 bg-slate-100 dark:bg-slate-800 rounded-lg hover:bg-slate-200"><ChevronRight size={16} /></button>
                <button className="p-2 bg-slate-100 dark:bg-slate-800 rounded-lg hover:bg-slate-200"><ChevronLeft size={16} /></button>
              </div>
            </div>

            <div className="space-y-4">
              {[
                { asset: 'حراثة نيو هولاند #402', task: 'تغيير زيت المحرك والفلتر', date: 'غداً', status: 'pending', urgent: true },
                { asset: 'مضخة بئر المنطقة A', task: 'فحص التوصيلات الكهربائية', date: '21 إبريل', status: 'pending', urgent: false },
                { asset: 'سيارة تويوتا هايلوكس', task: 'صيانة دورية (50,000 كم)', date: '25 إبريل', status: 'scheduled', urgent: false },
              ].map((job, i) => (
                <div key={i} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900/50 rounded-2xl border border-slate-100 dark:border-slate-800 group hover:border-blue-500/50 transition-all">
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-xl ${job.urgent ? 'bg-red-100 text-red-600 dark:bg-red-900/30' : 'bg-blue-100 text-blue-600 dark:bg-blue-900/30'}`}>
                      <Wrench size={20} />
                    </div>
                    <div>
                      <h3 className="font-bold">{job.asset}</h3>
                      <p className="text-sm text-slate-500">{job.task}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <p className={`text-sm font-bold ${job.urgent ? 'text-red-500' : 'text-slate-500'}`}>{job.date}</p>
                      <p className="text-xs text-slate-400">تاريخ مجدول</p>
                    </div>
                    <button className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-bold hover:bg-blue-600 hover:text-white transition-all">
                      {isStrictMode ? 'بدء (أمر صرف مالي)' : 'بدء المهمة'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {!isStrictMode && (
            <div className="bg-blue-100 dark:bg-blue-900/20 p-4 rounded-2xl text-blue-700 dark:text-blue-500 text-sm font-bold flex items-center gap-3">
              <Lock size={18} /> الصيانة التشغيلية مفعلة. ميزات الميزانية وتكاليف قطع الغيار مخفية في هذا المود.
            </div>
          )}

          {/* Machine Condition Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div className="app-panel p-6 border-r-4 border-emerald-500">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="font-bold">كفاءة تشغيل الأسطول</h3>
                  <Activity size={20} className="text-emerald-500" />
                </div>
                <div className="text-3xl font-black mb-2">94.8%</div>
                <div className="w-full bg-slate-200 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-emerald-500 h-full w-[94.8%]"></div>
                </div>
                <p className="text-xs text-slate-500 mt-3">+2% أفضل من الشهر الماضي</p>
             </div>
             <div className="app-panel p-6 border-r-4 border-amber-500">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="font-bold">استهلاك الوقود</h3>
                  <Fuel size={20} className="text-amber-500" />
                </div>
                <div className="text-3xl font-black mb-2">1,240 <span className="text-sm font-medium opacity-50">لتر</span></div>
                <p className="text-xs text-slate-500 mt-1">متوسط الاستهلاك اليومي: 42 لتر</p>
             </div>
          </div>
        </div>

        {/* Right: Asset Health Sidebar */}
        <div className="lg:col-span-1 space-y-6">
          <div className="app-panel p-6 h-full overflow-y-auto">
            <h2 className="text-lg font-black mb-6">حالة المعدات الحيوية</h2>
            <div className="space-y-6">
              {[
                { name: 'بئر المنطقة C', health: 92, lastService: '3 أيام', type: 'pump' },
                { name: 'مولد الطاقة الرئيسي', health: 45, lastService: '15 يوم', type: 'engine' },
                { name: 'خزان تبريد المحصول', health: 88, lastService: 'يوم واحد', type: 'facility' },
                { name: 'حراثة حوض رقم 4', health: 12, lastService: '45 يوم', type: 'machinery' },
              ].map((item, i) => (
                <div key={i} className="space-y-2">
                  <div className="flex justify-between items-center text-sm">
                    <span className="font-bold">{item.name}</span>
                    <span className={`font-black ${item.health < 30 ? 'text-red-500' : item.health < 60 ? 'text-amber-500' : 'text-emerald-500'}`}>
                      {item.health}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${item.health < 30 ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]' : item.health < 60 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                      style={{ width: `${item.health}%` }}
                    ></div>
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-400">
                    <span className="flex items-center gap-1"><Clock size={10} /> صيانة منذ: {item.lastService}</span>
                    {item.health < 30 && <span className="text-red-500 flex items-center gap-1 font-bold animate-pulse"><AlertCircle size={10} /> صيانة فورية!</span>}
                  </div>
                </div>
              ))}
            </div>
            
            <div className="mt-8 p-4 bg-slate-100 dark:bg-slate-800 rounded-2xl text-center">
               <button className="text-sm font-black text-blue-500 hover:underline">عرض جميع الأصول (142 أصل)</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MaintenanceDashboard;
