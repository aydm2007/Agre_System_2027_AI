
import React from 'react';

/**
 * Standardized Error State Component
 * per Agri-Guardian Frontend Protocol VII.
 * 
 * Usage:
 * <ErrorState 
 *   title="فشل تحميل البيانات" 
 *   message="حدث خطأ أثناء الاتصال بالخادم" 
 *   onRetry={() => loadData()} 
 * />
 */
export default function ErrorState({
    title = 'حدث خطأ',
    message = 'تعذر تحميل البيانات المطلوبة. يرجى المحاولة مرة أخرى.',
    onRetry
}) {
    return (
        <div className="flex flex-col items-center justify-center p-8 text-center border-2 border-dashed border-red-200 dark:border-red-900/50 rounded-lg bg-red-50 dark:bg-red-900/20">
            <div className="text-red-500 dark:text-red-400 text-4xl mb-4">
                ⚠️
            </div>
            <h3 className="text-lg font-semibold text-red-800 dark:text-red-300 mb-2">
                {title}
            </h3>
            <p className="text-sm text-red-600 dark:text-red-400 max-w-md mb-6">
                {message}
            </p>
            {onRetry && (
                <button
                    onClick={onRetry}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 dark:focus:ring-offset-slate-900"
                >
                    إعادة المحاولة
                </button>
            )}
        </div>
    );
}
