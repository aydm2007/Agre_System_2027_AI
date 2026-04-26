import React, { useState, useEffect } from 'react';
import { ShoppingCart, Package, CreditCard, Tablet, Search, ShieldCheck, Wifi, WifiOff, Lock } from 'lucide-react';
import { useSettings } from '../../contexts/SettingsContext';

const POSTerminal = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const { isStrictMode, settings } = useSettings();
  const showBarcode = settings?.enable_pos_barcode || false;

  useEffect(() => {
    setIsOnline(navigator.onLine);
    window.addEventListener('online', () => setIsOnline(true));
    window.addEventListener('offline', () => setIsOnline(false));
  }, []);

  const formatPrice = (price) => {
    if (!isStrictMode) return 'متوفر';
    return price.toLocaleString() + ' ر.ي';
  };

  return (
    <div className="app-page bg-slate-900 text-slate-50 flex flex-col h-screen overflow-hidden rtl" dir="rtl">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-slate-800 border-b border-slate-700 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-600 rounded-lg">
            <Tablet size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold">نقطة البيع - AgriAsset POS</h1>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              {isOnline ? (
                <span className="flex items-center gap-1 text-emerald-400"><Wifi size={14} /> متصل بالسحابة</span>
              ) : (
                <span className="flex items-center gap-1 text-amber-400"><WifiOff size={14} /> وضع عدم الاتصال (Sovereign Mode)</span>
              )}
              <span className="text-slate-600">|</span>
              <span className={`px-2 py-0.5 rounded ${isStrictMode ? 'bg-red-900/30 text-red-400' : 'bg-blue-900/30 text-blue-400'}`}>
                {isStrictMode ? 'STRICT' : 'SIMPLE'}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="px-3 py-1 bg-slate-700 rounded-full text-sm font-medium border border-slate-600">
             وردية #7742
          </div>
          <button className="p-2 hover:bg-slate-700 rounded-full transition-colors text-slate-400">
            <Search size={22} />
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Product Grid */}
        <div className="flex-1 p-6 overflow-y-auto grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 bg-slate-900/50">
          {[1,2,3,4,5,6,7,8,9,10].map(i => (
            <div key={i} className="app-card p-4 hover:border-emerald-500/50 cursor-pointer group transition-all transform hover:-translate-y-1">
              <div className="h-32 bg-slate-800 rounded-xl mb-3 flex items-center justify-center text-slate-600">
                <Package size={40} />
              </div>
              <h3 className="font-bold text-sm mb-1 truncate">محصول {i === 1 ? 'تمر صقعي' : 'بصل بافطيم'}</h3>
              <p className="text-emerald-400 font-bold mb-2">{formatPrice(1200)}</p>
              <button className="w-full py-2 bg-slate-800 group-hover:bg-emerald-600 rounded-lg text-xs font-bold transition-colors">
                إضافة للسلة
              </button>
            </div>
          ))}
        </div>

        {/* Sidebar / Cart */}
        <div className="w-96 bg-slate-800 border-r border-slate-700 flex flex-col shadow-2xl">
          <div className="p-4 border-b border-slate-700 bg-slate-800/50">
            <div className="flex items-center gap-2 mb-4">
              <ShoppingCart size={20} className="text-emerald-500" />
              <h2 className="font-bold">سلة المشتريات</h2>
            </div>
            {/* [AGRI-GUARDIAN] Barcode Toggle Logic */}
            <div className="flex items-center justify-between p-3 bg-slate-900 rounded-xl border border-slate-700">
              <div className="flex items-center gap-2">
                <span className="text-sm">مسح الباركود</span>
                {!showBarcode && <Lock size={12} className="text-slate-500" />}
              </div>
              <div className={`w-12 h-6 rounded-full relative ${showBarcode ? 'bg-emerald-600 cursor-pointer' : 'bg-slate-700 opacity-50 cursor-not-allowed'}`}>
                <div className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow-md transition-all ${showBarcode ? 'left-1' : 'right-1'}`}></div>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            <div className="flex justify-between items-center bg-slate-900/50 p-3 rounded-xl border border-slate-700/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center text-xs">x2</div>
                <div>
                  <div className="text-sm font-bold">سماد نيتروجين</div>
                  {isStrictMode && <div className="text-xs text-slate-500">450 ر.ي</div>}
                </div>
              </div>
              <div className="font-bold">{formatPrice(900)}</div>
            </div>
          </div>

          {/* Payment Section */}
          <div className="p-6 bg-slate-800 border-t border-slate-700 space-y-4">
            {isStrictMode ? (
              <>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-slate-400">الإجمالي الفرعي</span>
                  <span>850.00 ر.ي</span>
                </div>
                <div className="flex justify-between items-center mb-4">
                  <span className="text-slate-400 font-bold text-lg">الإجمالي</span>
                  <span className="text-2xl font-black text-emerald-400">900.00 ر.ي</span>
                </div>
              </>
            ) : (
              <div className="p-4 bg-blue-900/20 rounded-2xl text-blue-400 text-xs font-bold leading-relaxed">
                ملاحظة: في المود البسيط، يتم تسجيل الكميات المباعة فقط للمتابعة المخزنية. التسوية المالية تتم في المود الصارم.
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-3">
              <button className="flex items-center justify-center gap-2 py-4 bg-slate-700 rounded-2xl hover:bg-slate-600 transition-colors font-bold">
                <CreditCard size={18} /> {isStrictMode ? 'آجل' : 'نقل للمخزن'}
              </button>
              <button className="flex items-center justify-center gap-2 py-4 bg-emerald-600 rounded-2xl hover:bg-emerald-500 transition-colors font-bold shadow-lg shadow-emerald-900/20">
                <ShieldCheck size={18} /> {isStrictMode ? 'دفع نقدي' : 'تأكيد الصرف'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default POSTerminal;
