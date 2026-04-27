import React, { useEffect, useState } from 'react';
import { Activity, BarChart3, Shield, Terminal } from 'lucide-react';
import { RukunMode } from './index';

export const RukunDashboard = () => {
  const [status, setStatus] = useState('CHECKING');
  const [report, setReport] = useState(null);

  useEffect(() => {
    let mounted = true;
    RukunMode.activate().then((res) => {
      if (!mounted) return;
      setReport(res.report);
      setStatus(res.status);
    });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <section className="p-6 bg-slate-950 border border-blue-500/20 rounded-md shadow-lg space-y-6 text-white font-cairo" dir="rtl">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-xl font-black text-blue-100 flex items-center gap-3">
          <Shield className="text-blue-500" />
          لوحة فحص الركن
        </h2>
        <span className="px-3 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-300 text-xs font-bold rounded-md">
          Evidence gated
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-md space-y-2">
          <div className="text-slate-400 text-xs font-bold uppercase flex items-center gap-2">
            <Activity size={14} /> حالة الفحص
          </div>
          <div className="text-lg font-black text-emerald-300">{status}</div>
        </div>
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-md space-y-2">
          <div className="text-slate-400 text-xs font-bold uppercase flex items-center gap-2">
            <BarChart3 size={14} /> مرجع النتيجة
          </div>
          <div className="text-sm font-bold text-blue-200">verify_axis_complete_v21</div>
        </div>
      </div>

      <div className="bg-slate-900 p-4 rounded-md border border-slate-800 space-y-3">
        <div className="flex items-center gap-2 text-slate-300 text-sm font-bold">
          <Terminal size={16} /> آخر تشخيص محلي
        </div>
        <pre className="text-[10px] text-blue-100/80 font-mono leading-relaxed bg-black/50 p-3 rounded-md overflow-x-auto">
          {JSON.stringify(report, null, 2)}
        </pre>
      </div>
    </section>
  );
};

export default RukunDashboard;
