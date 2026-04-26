import React from 'react';
import { Skull, ShieldAlert, FileWarning, ThumbsUp, ThumbsDown, History, ChevronRight, Activity, Lock } from 'lucide-react';
import { useSettings } from '../../contexts/SettingsContext';

const MassWriteoffDashboard = () => {
  const { isStrictMode } = useSettings();

  return (
    <div className="app-page bg-slate-950 text-slate-50 min-h-screen p-8 rtl" dir="rtl">
      {/* Strategic Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
        <div className="flex items-center gap-6">
          <div className="p-4 bg-red-600 rounded-3xl shadow-[0_0_30px_rgba(220,38,38,0.4)] animate-pulse">
            <Skull size={40} className="text-white" />
          </div>
          <div>
            <h1 className="text-4xl font-black mb-2 tracking-tight">مركز إدارة الشطب الاستثنائي (Axis 18)</h1>
            <div className="flex items-center gap-3">
              <span className="px-3 py-1 bg-red-900/50 text-red-400 rounded-full text-xs font-black border border-red-500/30">
                {isStrictMode ? 'تصريح سيادي عالي المستوى' : 'بروتوكول شطب تشغيلي'}
              </span>
              <p className="text-slate-500 text-sm">شطب الأصول البيولوجية الناتجة عن الكوارث الطبيعية أو الأوبئة (IAS 41)</p>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
           {!isStrictMode && (
             <span className="bg-blue-900/30 text-blue-400 border border-blue-500/20 px-4 py-2 rounded-2xl text-xs font-bold flex items-center gap-2">
               <Lock size={14} /> SIMPLE MODE ACTIVATED
             </span>
           )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main: Incident Reporting & Authorizations */}
        <div className="lg:col-span-2 space-y-8">
          {/* Active Incidents */}
          <div className="app-panel border-red-500/20 bg-red-950/5 p-8 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-red-600/5 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl"></div>
            
            <h2 className="text-2xl font-black mb-8 flex items-center gap-3">
              <ShieldAlert size={28} className="text-red-500" /> البلاغات النشطة بانتظار الاعتماد
            </h2>

            <div className="space-y-6">
              {[
                { id: '1025', farm: 'مزرعة تهامة النموذجية', cause: 'صقيع حاد (Frost)', count: 450, species: 'أشجار مانجو', cost: '12,400,000' },
                { id: '1026', farm: 'مزرعة الجوف - قطاع 4', cause: 'فيضانات موسمية', count: 1200, species: 'محصول قمح', cost: '8,500,000' },
              ].map((incident, i) => (
                <div key={i} className="bg-slate-900 border border-slate-800 rounded-3xl p-6 hover:border-red-500/50 transition-all group">
                  <div className="flex justify-between items-start mb-6">
                    <div>
                      <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">تذكرة رقم #{incident.id}</span>
                      <h3 className="text-xl font-bold mt-1 text-red-100">{incident.farm}</h3>
                    </div>
                    <div className="px-4 py-2 bg-red-900/30 text-red-400 rounded-xl text-sm font-black border border-red-500/20">
                      خسارة جسيمة
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
                    <div><p className="text-xs text-slate-500 mb-1">السبب</p><p className="font-bold">{incident.cause}</p></div>
                    <div><p className="text-xs text-slate-500 mb-1">الكمية</p><p className="font-bold">{incident.count} وحدة</p></div>
                    <div><p className="text-xs text-slate-500 mb-1">الصنف</p><p className="font-bold">{incident.species}</p></div>
                    <div>
                      <p className="text-xs text-slate-500 mb-1">{isStrictMode ? 'القيمة المقدرة' : 'الحالة المالية'}</p>
                      <p className={`font-bold ${isStrictMode ? 'text-red-400' : 'text-blue-400'}`}>
                        {isStrictMode ? `${incident.cost} ر.ي` : 'بانتظار التقييم'}
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3 pt-6 border-t border-slate-800">
                    <button className="flex-1 py-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-2xl font-black transition-all flex items-center justify-center gap-2">
                      <ThumbsUp size={18} /> {isStrictMode ? 'اعتماد الشطب المالي' : 'اعتماد الكميات'}
                    </button>
                    <button className="flex-1 py-4 bg-slate-800 hover:bg-red-900/30 text-slate-400 hover:text-red-400 rounded-2xl font-black transition-all flex items-center justify-center gap-2 border border-slate-700">
                      <ThumbsDown size={18} /> رفض الطلب
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8">
             <h2 className="text-xl font-bold mb-6 flex items-center gap-3">
               <History size={24} className="text-slate-500" /> سجل الشطب الاستراتيجي (30 يوم الأخيرة)
             </h2>
             <div className="space-y-4">
                {[1, 2, 3].map(i => (
                  <div key={i} className="flex items-center justify-between p-4 bg-slate-900 border border-slate-800/50 rounded-2xl opacity-60">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center text-slate-500 font-bold">Done</div>
                      <div>
                        <p className="font-bold text-sm">شطب 150 نخلة - تذكرة #982</p>
                        <p className="text-xs text-slate-500">تم بواسطة: المدير العام | 2026-03-24</p>
                      </div>
                    </div>
                    <ChevronRight size={18} className="text-slate-600" />
                  </div>
                ))}
             </div>
          </div>
        </div>

        {/* Sidebar: Forensic Health & Quarantine */}
        <div className="lg:col-span-1 space-y-8">
          <div className="app-panel border-amber-500/20 bg-amber-950/5 p-8">
             <h2 className="text-xl font-bold mb-6 flex items-center gap-3 text-amber-500">
               <FileWarning size={24} /> المحجر الصحي (Quarantine)
             </h2>
             <div className="space-y-4">
                <p className="text-sm text-slate-400">تنبيه: تم وضع 4 مزارع تحت المراقبة بسبب ارتفاع مفاجئ في بلاغات الوفاة البيولوجية.</p>
                <div className="py-3 px-4 bg-amber-900/20 rounded-2xl border border-amber-500/20 flex items-center justify-between">
                  <span className="text-xs font-bold text-amber-500">مزرعة حجة المركزية</span>
                  <span className="text-[10px] bg-amber-500 text-amber-950 px-2 py-0.5 rounded-full font-black">تحقيق نشط</span>
                </div>
             </div>
          </div>

          <div className="app-panel p-8">
            <h2 className="text-lg font-black mb-6">مؤشرات الخسائر الوطنية</h2>
            <div className="space-y-8">
              {[
                { label: 'الصقيع', val: 75, color: 'blue' },
                { label: 'الأوبئة', val: 12, color: 'red' },
                { label: 'أخرى', val: 13, color: 'slate' },
              ].map((item, i) => (
                <div key={i} className="space-y-2">
                  <div className="flex justify-between text-xs font-bold">
                    <span>{item.label}</span>
                    <span>{item.val}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div className={`h-full bg-${item.color}-500`} style={{ width: `${item.val}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
            
            <div className="mt-12 p-6 bg-red-600 rounded-3xl text-center shadow-lg shadow-red-600/20">
               <Activity size={32} className="mx-auto mb-4 text-white animate-bounce" />
               <p className="text-xs font-bold text-red-100 mb-2 uppercase tracking-wide">بيان حالة طوارئ</p>
               <h3 className="text-xl font-black mb-1 text-white">إطلاق بروتوكول Axis 18</h3>
               <p className="text-[10px] opacity-70">يمنع التعديل اليدوي في المزارع المتضررة</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MassWriteoffDashboard;
