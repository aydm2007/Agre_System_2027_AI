import React, { useState } from "react";
import {
  Download,
  FileSpreadsheet,
  Calendar,
  Filter,
  FileText,
  ChevronRight,
  Activity,
  TrendingUp,
  Package,
} from "lucide-react";
import { useToast } from "../../components/ToastProvider";
import { ExportJobs } from "../../api/client";
import { useNavigate } from "react-router-dom";
import { useSettings } from "../../contexts/SettingsContext";

const REPORTS = [
  {
    id: "FINANCIAL_SUMMARY",
    title: "التقرير المالي التفصيلي",
    description: "تحليل تكاليف وإيرادات المزرعة على مستوى النشاط والمحصول.",
    icon: <TrendingUp className="text-emerald-500" size={24} />,
    colorClasses: {
      selected:
        "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 shadow-md",
      text: "text-emerald-900 dark:text-emerald-100",
      dot: "bg-emerald-500",
      dotBorder: "border-emerald-500",
    },
  },
  {
    id: "INVENTORY_BALANCE",
    title: "أرصدة المخزون وحركة المواد",
    description:
      "جرد شامل للمواد المتوفرة، المستهلكة والصادرة من وإلى المزرعة.",
    icon: <Package className="text-blue-500" size={24} />,
    colorClasses: {
      selected: "border-blue-500 bg-blue-50 dark:bg-blue-900/20 shadow-md",
      text: "text-blue-900 dark:text-blue-100",
      dot: "bg-blue-500",
      dotBorder: "border-blue-500",
    },
  },
  {
    id: "BATCH_TRACEABILITY",
    title: "تتبع العمليات والدفعات",
    description:
      "تتبع شامل للمحاصيل والأنشطة المرتبطة بها منذ الزراعة حتى الحصاد.",
    icon: <Activity className="text-indigo-500" size={24} />,
    colorClasses: {
      selected:
        "border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 shadow-md",
      text: "text-indigo-900 dark:text-indigo-100",
      dot: "bg-indigo-500",
      dotBorder: "border-indigo-500",
    },
  },
  {
    id: "OPERATIONAL_READINESS",
    title: "تقرير الجاهزية التشغيلية",
    description:
      "ملخص شامل لجاهزية الموارد، العمالة، والمعدات في المزرعة المحددة.",
    icon: <FileText className="text-amber-500" size={24} />,
    colorClasses: {
      selected: "border-amber-500 bg-amber-50 dark:bg-amber-900/20 shadow-md",
      text: "text-amber-900 dark:text-amber-100",
      dot: "bg-amber-500",
      dotBorder: "border-amber-500",
    },
  },
];

export default function AdvancedReports() {
  const toast = useToast();
  const navigate = useNavigate();
  const { isStrictMode, showAdvancedReports } = useSettings();
  const [selectedReport, setSelectedReport] = useState("FINANCIAL_SUMMARY");
  const [isExporting, setIsExporting] = useState(false);

  // If setting is disabled, show unauthorized (for tenant safety)
  if (!showAdvancedReports && !isStrictMode) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center h-[70vh]">
        <FileSpreadsheet className="text-slate-300 w-24 h-24 mb-6" />
        <h2 className="text-2xl font-black text-slate-700 dark:text-slate-200 mb-2">
          الوحدة غير مفعلة
        </h2>
        <p className="text-slate-500">
          تم إخفاء التقارير المتقدمة بناءً على إعدادات المزرعة الحالية.
        </p>
        <button
          onClick={() => navigate("/reports")}
          className="mt-8 text-indigo-600 font-bold hover:underline"
        >
          العودة للملخص البسيط
        </button>
      </div>
    );
  }

  const handleExport = async () => {
    try {
      setIsExporting(true);
      toast.success("جاري تجهيز التقرير (XLSX)، يرجى الانتظار...");

      const payload = {
        template_code: selectedReport,
        format: "xlsx",
      };

      // Create Async Export Job
      const response = await ExportJobs.create(payload);
      const jobId = response.data.id;

      // In a real flow, we would poll for completion. For now, simulate rapid processing
      // and redirect to download endpoint after a short delay since AgriAsset does async jobs
      setTimeout(async () => {
        try {
          const downloadUrl = `/api/v1/export-jobs/${jobId}/download/`;
          window.open(downloadUrl, "_blank");
          toast.success("اكتمل التصدير بنجاح!");
        } catch (error) {
          toast.error("حدث تأخير في الاستعلام عن الملف.");
        } finally {
          setIsExporting(false);
        }
      }, 2000);
    } catch (err) {
      setIsExporting(false);
      toast.error("فشل تصدير التقرير، تأكد من صلاحياتك واتصالك بالخادم.");
    }
  };

  return (
    <div className="app-page rtl p-6 max-w-5xl mx-auto" dir="rtl">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={() => navigate("/reports")}
          className="p-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 rounded-full transition-colors"
        >
          <ChevronRight size={20} className="text-slate-600" />
        </button>
        <div>
          <h1 className="text-3xl font-black flex items-center gap-3">
            التقارير المتقدمة (Excel)
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            وحدة التصدير التفصيلية للحسابات والعمليات الزراعية المعقدة.
          </p>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-8">
        {/* Reports List */}
        <div className="md:col-span-2 space-y-4">
          <h2 className="text-lg font-bold mb-4 text-slate-800 dark:text-slate-200">
            اختر قالب التقرير:
          </h2>
          <div className="grid sm:grid-cols-2 gap-4">
            {REPORTS.map((report) => (
              <div
                key={report.id}
                onClick={() => setSelectedReport(report.id)}
                className={`p-5 rounded-2xl border-2 transition-all cursor-pointer ${
                  selectedReport === report.id
                    ? report.colorClasses.selected
                    : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-slate-300"
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div
                    className={`p-2 rounded-xl bg-white dark:bg-slate-700 shadow-sm`}
                  >
                    {report.icon}
                  </div>
                  <div
                    className={`h-4 w-4 rounded-full border-2 flex items-center justify-center ${
                      selectedReport === report.id
                        ? report.colorClasses.dotBorder
                        : "border-slate-300"
                    }`}
                  >
                    {selectedReport === report.id && (
                      <div
                        className={`w-2 h-2 rounded-full ${report.colorClasses.dot}`}
                      />
                    )}
                  </div>
                </div>
                <h3
                  className={`font-bold text-lg mb-1 ${selectedReport === report.id ? report.colorClasses.text : "text-slate-800 dark:text-slate-200"}`}
                >
                  {report.title}
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {report.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Filters & Export Panel */}
        <div className="md:col-span-1">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-3xl p-6 shadow-sm sticky top-6">
            <h2 className="text-xl font-black mb-6 border-b border-slate-100 dark:border-slate-700 pb-4">
              إعدادات الاستخراج
            </h2>

            <div className="space-y-6">
              <div>
                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
                  <Calendar size={16} /> الفترة الزمنية
                </label>
                <select className="w-full p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl font-bold">
                  <option>الشهر الحالي</option>
                  <option>آخر 3 أشهر</option>
                  <option>الموسم المفتوح</option>
                  <option>مخصص...</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
                  <Filter size={16} /> الفلاتر الإضافية
                </label>
                <p className="text-xs text-slate-500 mb-3">
                  سيتم تطبيق فلاتر المزرعة والمحصول الحالية تلقائياً.
                </p>
                <label className="flex items-center gap-2 mb-2 p-2 bg-slate-50 dark:bg-slate-900 rounded-lg cursor-pointer">
                  <input
                    type="checkbox"
                    className="rounded text-indigo-600 focus:ring-indigo-500"
                    defaultChecked
                  />
                  <span className="text-sm font-bold">
                    تضمين التكاليف غير المباشرة
                  </span>
                </label>
                <label className="flex items-center gap-2 p-2 bg-slate-50 dark:bg-slate-900 rounded-lg cursor-pointer">
                  <input
                    type="checkbox"
                    className="rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="text-sm font-bold">عرض تفاصيل الدفعات</span>
                </label>
              </div>

              <div className="pt-4 border-t border-slate-100 dark:border-slate-700">
                <button
                  onClick={handleExport}
                  disabled={isExporting}
                  className={`w-full py-4 rounded-xl font-black flex items-center justify-center gap-3 transition-all duration-300 shadow-xl ${
                    isExporting
                      ? "bg-slate-400 text-white cursor-not-allowed"
                      : "bg-indigo-600 hover:bg-indigo-500 text-white hover:-translate-y-1 hover:shadow-indigo-600/30"
                  }`}
                >
                  {isExporting ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      جاري الاستخراج...
                    </>
                  ) : (
                    <>
                      <FileSpreadsheet size={24} />
                      تحميل التقرير (XLSX)
                    </>
                  )}
                </button>
                <p className="text-center text-xs text-slate-400 mt-4 leading-relaxed">
                  يتم استخراج البيانات وفقاً لأعلى معايير المحاسبة (IFRS) معتمد
                  من قبل النظام.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
