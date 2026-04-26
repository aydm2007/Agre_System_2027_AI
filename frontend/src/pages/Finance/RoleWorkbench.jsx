import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Clock, AlertTriangle, CheckCircle, Target } from 'lucide-react';
import api from '@/services/api';

const RoleWorkbench = () => {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchWorkbenchSnapshot = async () => {
      try {
        const response = await api.get('/api/v1/finance/approvals/role_workbench/');
        setSnapshot(response.data);
        setError(null);
      } catch (err) {
        setError(err.message || 'Failed to load role workbench');
      } finally {
        setLoading(false);
      }
    };
    fetchWorkbenchSnapshot();
  }, []);

  if (loading) {
    return (
      <div className="space-y-4 p-4 dark:bg-slate-900" dir="rtl">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-red-600 dark:text-red-400" dir="rtl">
        <AlertTriangle className="inline mr-2" />
        <span>خطأ في تحميل بيانات مسارات الاعتماد: {error}</span>
      </div>
    );
  }

  if (!snapshot || Object.keys(snapshot).length === 0) {
    return (
      <div className="p-8 text-center text-slate-500" dir="rtl">
        <CheckCircle className="mx-auto mb-4 h-12 w-12 text-slate-300" />
        <h3 className="text-lg font-medium">لا توجد مسارات بحاجة للمراجعة</h3>
      </div>
    );
  }

  // Define intended render order ensuring sector lanes visually flow in sequence
  // + incorporating the FFM local check
  const displayOrder = [
    'farm_finance_manager',
    'sector_accountant',
    'sector_reviewer',
    'sector_chief_accountant',
    'sector_finance_director',
    'sector_director'
  ];

  return (
    <div className="p-6 space-y-6 dark:bg-slate-900 dark:text-slate-100 min-h-screen" dir="rtl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight mb-2">منصة أولوية المهام (Role Workbench)</h1>
        <p className="text-slate-500 dark:text-slate-400">ملخص مسارات الاعتماد القطاعية والحالات المتأخرة</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {displayOrder.map(lane => {
          if (!snapshot[lane]) return null;
          
          const data = snapshot[lane];
          const hasOverdue = data.overdue > 0;
          const needsAttention = data.director_attention > 0 || data.farm_finance_attention > 0;

          return (
            <Card key={lane} className={`border-l-4 ${hasOverdue ? 'border-l-red-500' : 'border-l-blue-500'} dark:bg-slate-800`}>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex justify-between items-start">
                  <span>{data.role_label || lane}</span>
                  <Badge variant="outline" className="text-lg px-3 py-1 bg-slate-100 dark:bg-slate-700">
                    {data.count}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 mt-4">
                  
                  {hasOverdue && (
                    <div className="flex items-center text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded">
                      <AlertTriangle className="h-4 w-4 ml-2" />
                      <span className="text-sm font-medium">{data.overdue} متأخر (Overdue)</span>
                    </div>
                  )}

                  {needsAttention && (
                    <div className="flex items-center text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 p-2 rounded">
                      <Target className="h-4 w-4 ml-2" />
                      <span className="text-sm font-medium">
                        عناية خاصة: {data.director_attention || data.farm_finance_attention}
                      </span>
                    </div>
                  )}

                  {!hasOverdue && !needsAttention && data.count > 0 && (
                    <div className="flex items-center text-slate-500 dark:text-slate-400 p-2">
                      <CheckCircle className="h-4 w-4 ml-2 text-green-500" />
                      <span className="text-sm">حالة المسار طبيعية</span>
                    </div>
                  )}

                  {data.count === 0 && (
                    <div className="text-sm text-slate-400 dark:text-slate-500 italic p-2">
                      لا توجد طلبات معلقة
                    </div>
                  )}
                  
                  {data.oldest_started_at && (
                    <div className="flex items-center text-xs text-slate-400 mt-4 border-t pt-2 dark:border-slate-700">
                      <Clock className="h-3 w-3 ml-1" />
                      أقدم طلب: {new Date(data.oldest_started_at).toLocaleDateString('ar-SA')}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
};

export default RoleWorkbench;
