import React, { useState } from 'react';
import { Box, MapPin, Move, RefreshCw, BarChart3, AlertTriangle, Layers, Lock } from 'lucide-react';
import { useSettings } from '../../contexts/SettingsContext';

const WarehouseVisualizer = () => {
  const [selectedZone, setSelectedZone] = useState('A');
  const { isStrictMode } = useSettings();

  return (
    <div className="app-page bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-50 p-6 rtl" dir="rtl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-black mb-2 flex items-center gap-3">
            <div className="p-2 bg-indigo-600 rounded-xl text-white shadow-lg shadow-indigo-600/20">
              <Layers size={28} />
            </div>
            إدارة المستودعات والمواقع (Bins)
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            {isStrictMode ? 'تتبع الأصناف والتقييم المخزني على مستوى المنطقة والموقع (Axis 23)' : 'تتبع مواقع الأصناف والكميات التشغيلية (المود البسيط)'}
          </p>
        </div>
        <div className="flex gap-2 text-xs items-center ml-4">
            <div className="flex flex-col items-end mr-4">
               <span className="text-[10px] text-slate-400 font-bold uppercase tracking-tighter">Sovereign Integrity</span>
               <div className="flex items-center gap-1 text-emerald-500 font-black text-lg leading-none">
                 100<span className="text-[10px] opacity-70">/100</span>
               </div>
            </div>
           {isStrictMode ? (
             <span className="bg-red-100 dark:bg-red-900/30 text-red-600 px-3 py-1 rounded-full font-bold flex items-center gap-1">
               <Lock size={12} /> STRICT (Valuation On)
             </span>
           ) : (
             <span className="bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 px-3 py-1 rounded-full font-bold">
               SIMPLE MODE (Quantities Only)
             </span>
           )}
        </div>
        <div className="flex gap-2">
          <button className="flex items-center justify-center gap-2 px-6 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-2xl font-bold transition-all shadow-sm hover:bg-slate-50 active:scale-95">
            <Move size={18} /> نقل بين المواقع
          </button>
          <button className="flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl font-bold transition-all shadow-lg shadow-indigo-600/20 active:scale-95">
            <RefreshCw size={18} /> جرد الموقع
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 h-[calc(100vh-250px)]">
        {/* Sidebar: Zone List */}
        <div className="lg:col-span-1 space-y-4 overflow-y-auto pr-2">
          <h2 className="text-sm font-black text-slate-400 uppercase tracking-widest px-2">مناطق المستودع</h2>
          {['المنطقة A - الأسمدة', 'المنطقة B - المعدات', 'المنطقة C - قطع الغيار', 'المنطقة D - العبوات'].map((zone, i) => (
            <div 
              key={i}
              onClick={() => setSelectedZone(zone.charAt(7))}
              className={`p-4 rounded-2xl border cursor-pointer transition-all ${i === 0 ? 'bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-600/20' : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-800 hover:border-indigo-400'}`}
            >
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-bold">{zone}</h3>
                <Box size={18} className={i === 0 ? 'text-indigo-200' : 'text-slate-400'} />
              </div>
              <div className="flex justify-between text-xs opacity-70">
                <span>42 موضع (Bin)</span>
                <span>85% ممتلئ</span>
              </div>
            </div>
          ))}
          
          <div className="bg-amber-100 dark:bg-amber-900/20 p-4 rounded-2xl border border-amber-200 dark:border-amber-900/40 text-amber-700 dark:text-amber-500">
            <div className="flex gap-3">
              <AlertTriangle className="flex-shrink-0" />
              <div>
                <p className="font-bold text-sm">تنبيه تخزين!</p>
                <p className="text-xs">المنطقة A تقترب من السعة القصوى.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Main: Visual Grid */}
        <div className="lg:col-span-3 app-panel flex flex-col p-6 bg-white/50 dark:bg-slate-900/50">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <h2 className="text-xl font-bold">خارطة المواقع - المنطقة {selectedZone}</h2>
              <div className="flex gap-1">
                {[1, 2, 3].map(level => (
                  <button key={level} className={`px-3 py-1 text-xs rounded-lg border ${level === 1 ? 'bg-indigo-50 dark:bg-indigo-900/30 border-indigo-200 text-indigo-600' : 'border-slate-200'}`}>الرف {level}</button>
                ))}
              </div>
            </div>
            <div className="flex gap-2 text-xs">
              <div className="flex items-center gap-1"><div className="w-3 h-3 bg-emerald-500 rounded-sm"></div> متوفر</div>
              <div className="flex items-center gap-1"><div className="w-3 h-3 bg-red-500 rounded-sm"></div> ممتلئ</div>
              <div className="flex items-center gap-1"><div className="w-3 h-3 bg-slate-300 rounded-sm"></div> فارغ</div>
            </div>
          </div>

          <div className="flex-1 grid grid-cols-6 grid-rows-4 gap-4 overflow-hidden">
            {Array.from({ length: 24 }).map((_, i) => (
              <div 
                key={i} 
                className={`rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-800 p-3 flex flex-col justify-between transition-all hover:scale-105 hover:bg-white dark:hover:bg-slate-800 hover:border-indigo-400 group cursor-pointer ${i % 7 === 0 ? 'bg-red-50 dark:bg-red-900/10 border-red-200/50' : i % 5 === 0 ? 'bg-slate-50/50' : 'bg-emerald-50/50 dark:bg-emerald-900/10'}`}
              >
                <div className="flex justify-between items-start">
                  <span className="font-bold text-xs text-slate-400">{selectedZone}-{i + 1}</span>
                  <MapPin size={12} className="text-slate-300 group-hover:text-indigo-500" />
                </div>
                {i % 7 === 0 ? (
                  <div className="text-[10px]">
                    <p className="font-bold truncate">سماد يوريا</p>
                    <p className="text-red-500 font-black">200 كجم</p>
                    {isStrictMode && <p className="text-[8px] opacity-40">القيمة: 140,000 ر.ي</p>}
                  </div>
                ) : i % 3 === 0 && i % 7 !== 0 ? (
                  <div className="text-[10px]">
                    <p className="font-bold truncate">مبيد حشرى X</p>
                    <p className="text-indigo-500 font-black">15 عبوة</p>
                    {isStrictMode && <p className="text-[8px] opacity-40">القيمة: 45,000 ر.ي</p>}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center flex-1">
                    <div className="w-6 h-6 border-2 border-slate-200 rounded-full flex items-center justify-center text-slate-300">+</div>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="mt-6 p-4 bg-indigo-50 dark:bg-indigo-900/10 rounded-2xl flex items-center justify-between border border-indigo-100 dark:border-indigo-900/30">
            <div className="flex items-center gap-4">
               <div className="p-2 bg-indigo-500 rounded-lg text-white">
                 <Move size={18} />
               </div>
               <div>
                 <p className="text-xs text-slate-500">آخر حركة مخزنية</p>
                 <p className="text-sm font-bold">نقل 50 كجم سماد من A-12 إلى B-05</p>
               </div>
            </div>
            <button className="text-indigo-600 dark:text-indigo-400 text-sm font-bold flex items-center gap-1 hover:underline">
               سجل الحركات <BarChart3 size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WarehouseVisualizer;
