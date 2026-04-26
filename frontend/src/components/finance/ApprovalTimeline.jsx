import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Clock, CheckCircle2, XCircle, AlertCircle, RefreshCw, FileText } from 'lucide-react';

const ACTION_ICONS = {
  created: <FileText className="w-5 h-5 text-blue-500" />,
  stage_approved: <CheckCircle2 className="w-5 h-5 text-emerald-500" />,
  final_approved: <CheckCircle2 className="w-5 h-5 text-emerald-600" fill="currentColor" />,
  rejected: <XCircle className="w-5 h-5 text-red-500" />,
  auto_escalated: <AlertCircle className="w-5 h-5 text-amber-500" />,
  reopened: <RefreshCw className="w-5 h-5 text-indigo-500" />
};

const ACTION_LABELS = {
  created: "إنشاء الطلب",
  stage_approved: "اعتماد مرحلي",
  final_approved: "اعتماد نهائي",
  rejected: "مرفوض",
  auto_escalated: "تصعيد تلقائي",
  reopened: "إعادة فتح"
};

const ApprovalTimeline = ({ events = [], isLoading = false }) => {
  if (isLoading) {
    return (
      <Card dir="rtl" className="dark:bg-slate-900 border-none shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg">سجل المراجعة والاعتمادات</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4 animate-pulse">
            {[1, 2, 3].map(i => (
              <div key={i} className="flex gap-4">
                <div className="w-8 h-8 bg-slate-200 dark:bg-slate-700 rounded-full shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/4" />
                  <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!events?.length) {
    return (
      <Card dir="rtl" className="dark:bg-slate-900 border-none shadow-sm">
        <CardContent className="pt-6 text-center text-slate-500">
          <Clock className="w-8 h-8 mx-auto mb-2 opacity-20" />
          <p>لا يوجد سجل اعتمادات متاح</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card dir="rtl" className="dark:bg-slate-900 border-slate-200 dark:border-slate-800">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg flex items-center gap-2">
          <Clock className="w-5 h-5 text-slate-500" />
          سجل المراجعة والاعتمادات
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative border-r-2 border-slate-200 dark:border-slate-700 pr-4 ml-4 space-y-6">
          {events.map((event, index) => (
            <div key={event.id || index} className="relative">
              {/* Timeline marker */}
              <div className="absolute -right-[25px] top-1 bg-white dark:bg-slate-900 rounded-full p-0.5">
                {ACTION_ICONS[event.action] || <Clock className="w-5 h-5 text-slate-400" />}
              </div>

              <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4 mr-2">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <span className="font-semibold block dark:text-slate-200">
                      {ACTION_LABELS[event.action] || event.action}
                    </span>
                    <span className="text-sm text-slate-500 dark:text-slate-400">
                      بواسطة: {event.user_name} ({event.role_label})
                    </span>
                  </div>
                  <time className="text-xs text-slate-400 whitespace-nowrap" dir="ltr">
                    {new Date(event.created_at).toLocaleString('en-GB', {
                      year: 'numeric',
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </time>
                </div>

                {event.note && (
                  <div className="mt-2 text-sm text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 p-2 rounded border border-slate-100 dark:border-slate-700">
                    <span className="text-slate-400 ml-2">ملاحظة:</span>
                    {event.note}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default ApprovalTimeline;
