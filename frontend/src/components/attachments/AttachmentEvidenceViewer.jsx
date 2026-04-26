import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  FileText, ShieldCheck, ShieldAlert, Archive, 
  Lock, AlertTriangle, Info, Clock, Hash
} from 'lucide-react';

// AGENTS.md § Attachment Lifecycle Doctrine mappings
const CLASS_COLORS = {
  transient: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  operational: "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300",
  financial_record: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300",
  legal_hold: "bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300"
};

const CLASS_LABELS = {
  transient: "مؤقت (Transient)",
  operational: "تشغيلي (Operational)",
  financial_record: "سجل مالي (Financial Record)",
  legal_hold: "حجز قانوني (Legal Hold)"
};

const ARCHIVE_STATES = {
  active: { icon: FileText, color: "text-blue-500", label: "نشط" },
  archived: { icon: Archive, color: "text-slate-500", label: "مؤرشف" },
  quarantined: { icon: ShieldAlert, color: "text-red-500", label: "محجوز أمنياً" },
  legal_hold: { icon: Lock, color: "text-purple-500", label: "مُجمّد بقوة القانون" }
};

const SCAN_STATES = {
  clean: { icon: ShieldCheck, color: "text-emerald-500 bg-emerald-50 dark:bg-emerald-900/20", label: "سليم (Clean)" },
  quarantined: { icon: ShieldAlert, color: "text-red-500 bg-red-50 dark:bg-red-900/20", label: "معزول (Quarantined)" },
  pending: { icon: Clock, color: "text-amber-500 bg-amber-50 dark:bg-amber-900/20", label: "قيد الفحص (Pending)" }
};

const AttachmentEvidenceViewer = ({ attachmentId, initialMetadata = null }) => {
  const [metadata, setMetadata] = useState(initialMetadata);
  const [loading, setLoading] = useState(!initialMetadata);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (initialMetadata || !attachmentId) return;

    fetch(`/api/v1/core/attachments/${attachmentId}/evidence-metadata/`)
      .then(res => {
        if (!res.ok) throw new Error("فشل استرداد بيانات المرفق");
        return res.json();
      })
      .then(data => {
        setMetadata(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [attachmentId, initialMetadata]);

  if (loading) {
    return (
      <Card dir="rtl" className="animate-pulse dark:bg-slate-900">
        <CardContent className="p-6">
          <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-1/3 mb-4" />
          <div className="space-y-2">
            <div className="h-3 bg-slate-100 dark:bg-slate-800/50 rounded w-1/2" />
            <div className="h-3 bg-slate-100 dark:bg-slate-800/50 rounded w-2/3" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !metadata) {
    return (
      <div dir="rtl" className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg flex items-center gap-2">
        <AlertTriangle className="w-5 h-5" />
        <span>تعذر تحميل السجل التوثيقي: {error}</span>
      </div>
    );
  }

  const archiveState = ARCHIVE_STATES[metadata.archive_state] || ARCHIVE_STATES.active;
  const scanState = SCAN_STATES[metadata.scan_status] || SCAN_STATES.pending;
  const StateIcon = archiveState.icon;
  const ScanIcon = scanState.icon;

  return (
    <Card dir="rtl" className="border-slate-200 dark:border-slate-800 dark:bg-slate-900 shadow-sm">
      <CardHeader className="pb-3 border-b dark:border-slate-800">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <StateIcon className={`w-5 h-5 ${archiveState.color}`} />
            البيانات التوثيقية للمرفق
            <span className="text-slate-400 text-xs font-normal">#{attachmentId}</span>
          </CardTitle>
          <span className={`px-2 py-1 rounded text-xs font-medium ${CLASS_COLORS[metadata.evidence_class] || CLASS_COLORS.transient}`}>
            {CLASS_LABELS[metadata.evidence_class] || metadata.evidence_class}
          </span>
        </div>
      </CardHeader>
      
      <CardContent className="pt-4 space-y-4">
        {/* Scan Status Badge */}
        <div className={`flex items-center gap-2 p-2 rounded-md ${scanState.color}`}>
          <ScanIcon className="w-4 h-4" />
          <span className="text-sm font-medium">حالة الفحص الأمني: {scanState.label}</span>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
              <Archive className="w-3 h-3" />
              الحالة الأرشيفية
            </div>
            <div className="text-sm font-medium dark:text-slate-200">
              {archiveState.label}
            </div>
          </div>
          
          <div className="space-y-1">
            <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              تاريخ الاستحقاق للحذف (TTL)
            </div>
            <div className="text-sm font-medium dark:text-slate-200" dir="ltr">
              {metadata.expires_at 
                ? new Date(metadata.expires_at).toLocaleString() 
                : <span className="text-xs text-indigo-500">حفظ دائم (Authoritative Record)</span>}
            </div>
          </div>

          <div className="space-y-1 md:col-span-2">
            <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
              <Hash className="w-3 h-3" />
              بصمة الملف (SHA-256)
            </div>
            <div className="text-xs font-mono bg-slate-50 dark:bg-slate-800 p-2 rounded border border-slate-100 dark:border-slate-700 text-slate-600 dark:text-slate-300 break-all select-all">
              {metadata.file_hash || "بانتظار اكمال الحساب والتخزين..."}
            </div>
          </div>
        </div>

        {metadata.legal_hold_reason && (
          <div className="mt-4 p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800 rounded-lg">
            <div className="flex gap-2 items-start text-purple-700 dark:text-purple-300">
              <Lock className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="text-sm">
                <span className="font-semibold block mb-1">سبب الحجز القانوني:</span>
                {metadata.legal_hold_reason}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default AttachmentEvidenceViewer;
