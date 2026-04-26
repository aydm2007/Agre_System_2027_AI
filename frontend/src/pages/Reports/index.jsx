import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts';
import { FileBarChart, Download, Calendar, Filter, ChevronDown, PieChart as PieIcon, BarChart3, LineChart as LineIcon, Printer, Lock } from 'lucide-react';
import { useSettings } from '../../contexts/SettingsContext';
import { useNavigate } from 'react-router-dom';

const ReportBuilder = () => {
  const { isStrictMode, showAdvancedReports } = useSettings();
  const navigate = useNavigate();

  // Mock Data
  const data = [
    { name: 'يناير', cost: 4000, revenue: 2400 },
    { name: 'فبراير', cost: 3000, revenue: 1398 },
    { name: 'مارس', cost: 2000, revenue: 9800 },
    { name: 'أبريل', cost: 2780, revenue: 3908 },
    { name: 'مايو', cost: 1890, revenue: 4800 },
  ];

  const pieData = [
    { name: 'أسمدة', value: 400 },
    { name: 'عمالة', value: 300 },
    { name: 'وقود', value: 300 },
    { name: 'صيانة', value: 200 },
  ];

  const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'];

  const formatCurrency = (tick) => {
    if (!isStrictMode) return '***';
    return tick.toLocaleString();
  };

  return (
    <div className="app-page bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-50 p-6 rtl" dir="rtl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-black mb-2 flex items-center gap-3">
            <div className="p-2 bg-emerald-600 rounded-xl text-white shadow-lg shadow-emerald-600/20">
              <FileBarChart size={28} />
            </div>
            مركز التقارير والذكاء الاصطناعي (BI)
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            {isStrictMode ? 'تحليل البيانات التشغيلية والمالية مع تصدير التقارير الرسمية' : 'مؤشرات الأداء الإنتاجي وتوزيع الموارد (المود البسيط)'}
          </p>
        </div>
        <div className="flex gap-2">
          {isStrictMode ? (
            <>
              <button className="flex items-center justify-center gap-2 px-6 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-2xl font-bold hover:bg-slate-50 transition-all shadow-sm">
                <Download size={18} /> تصدير PDF
              </button>
              <button className="flex items-center justify-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-2xl font-bold transition-all shadow-lg shadow-emerald-600/20">
                <Printer size={18} /> طباعة
              </button>
            </>
          ) : showAdvancedReports ? (
            <button 
              onClick={() => navigate('/reports/advanced')}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl font-bold transition-all shadow-lg shadow-indigo-600/20" title="تصدير تقارير مخصصة (XLSX)">
              <Download size={18} /> التقارير المتقدمة (XLSX)
            </button>
          ) : null}
        </div>
      </div>

      {/* Control Bar */}
      <div className="flex items-center gap-4 mb-8 bg-white dark:bg-slate-800 p-4 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-900 rounded-xl">
          <Calendar size={18} className="text-slate-400" />
          <span className="text-sm font-bold">آخر 30 يوم</span>
          <ChevronDown size={14} className="text-slate-400" />
        </div>
        <div className="h-8 w-[1px] bg-slate-200 dark:bg-slate-700"></div>
        <div className="flex items-center gap-4 flex-1">
          {['ملخص الإيرادات', 'تحليل التكاليف', 'إنتاجية المحاصيل', 'كفاءة العمالة'].map((tab, i) => (
            <button key={i} className={`text-sm font-bold transition-colors ${i === 0 ? 'text-emerald-500' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}>
              {tab}
            </button>
          ))}
        </div>
        <button className="p-2 bg-slate-100 dark:bg-slate-900 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-700 transition-all">
          <Filter size={20} className="text-slate-500" />
        </button>
      </div>

      {!isStrictMode && (
        <div className="mb-8 p-4 bg-blue-100 dark:bg-blue-900/20 rounded-2xl text-blue-700 dark:text-blue-500 text-sm font-bold flex items-center justify-between border border-blue-200 dark:border-blue-900/40">
          <div className="flex items-center gap-3">
            <Lock size={18} /> وضع الاستعراض التشغيلي نشط: القيم النقدية المطلقة مخفية لضمان الخصوصية المالية.
          </div>
          <span className="bg-blue-600 text-white px-3 py-1 rounded-full text-[10px] uppercase">Simple Mode</span>
        </div>
      )}

      {/* Grid Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Chart */}
        <div className="lg:col-span-2 app-panel p-6">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-lg font-black flex items-center gap-2">
              <BarChart3 size={20} className="text-emerald-500" /> 
              {isStrictMode ? 'تقرير الإيرادات مقابل التكاليف (ر.ي)' : 'مؤشر الإنتاجية مقابل استهلاك الموارد'}
            </h2>
          </div>
          <div className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12 }} tickFormatter={formatCurrency} />
                <Tooltip 
                  formatter={(value) => [isStrictMode ? value.toLocaleString() : '---', '']}
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                />
                <Legend iconType="circle" />
                <Bar dataKey="revenue" fill="#10b981" radius={[4, 4, 0, 0]} name={isStrictMode ? 'الإيرادات' : 'الإنتاجية'} />
                <Bar dataKey="cost" fill="#3b82f6" radius={[4, 4, 0, 0]} name={isStrictMode ? 'التكاليف' : 'الاستهلاك'} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Small Charts Side */}
        <div className="lg:col-span-1 space-y-8">
          {/* Pie Chart */}
          <div className="app-panel p-6">
             <h2 className="text-lg font-black mb-6 flex items-center gap-2">
               <PieIcon size={20} className="text-amber-500" /> نسب توزيع الموارد
             </h2>
             <div className="h-[250px] w-full">
               <ResponsiveContainer width="100%" height="100%">
                 <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => `${((value / 1200) * 100).toFixed(1)}%`} />
                 </PieChart>
               </ResponsiveContainer>
             </div>
             <div className="grid grid-cols-2 gap-2 mt-4">
               {pieData.map((entry, index) => (
                 <div key={index} className="flex items-center gap-2 text-xs">
                   <div className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[index] }}></div>
                   <span className="text-slate-500 truncate">{entry.name}</span>
                   <span className="font-bold">{((entry.value / 1200) * 100).toFixed(1)}%</span>
                 </div>
               ))}
             </div>
          </div>

          {/* Mini Stats Chart */}
          <div className="app-panel p-6 bg-emerald-600 text-white border-none shadow-emerald-600/20">
             <div className="flex justify-between items-start mb-4">
                <LineIcon size={24} className="opacity-50" />
                <span className="text-xs bg-white/20 px-2 py-1 rounded-full font-bold">توقع النمو</span>
             </div>
             <p className="text-sm opacity-80 mb-1">معدل العائد المتوقع</p>
             <h3 className="text-3xl font-black mb-4">+24.5%</h3>
             <div className="h-[60px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.map(d => ({ ...d, val: Math.random() * 100 }))}>
                    <Line type="monotone" dataKey="val" stroke="#fff" strokeWidth={3} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportBuilder;
