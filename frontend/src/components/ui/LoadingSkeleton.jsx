
import React from 'react';

/**
 * Standardized Loading Skeleton Component
 * 
 * Usage:
 * <LoadingSkeleton className="h-4 w-full" count={3} />
 */
export default function LoadingSkeleton({ className = "h-4 w-full", count = 1 }) {
    return (
        <div className="space-y-2 w-full animate-pulse">
            {[...Array(count)].map((_, i) => (
                <div
                    key={i}
                    className={`bg-gray-200 dark:bg-slate-700 rounded ${className}`}
                ></div>
            ))}
        </div>
    );
}
