import { Inbox } from 'lucide-react'

export default function EmptyState({
  icon: Icon = Inbox,
  title = 'لا توجد بيانات',
  description = 'لم يتم العثور على أي نتائج تطابق معايير البحث الخاصة بك.',
  action,
  className,
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center min-h-[300px] border-2 border-dashed border-gray-200 rounded-xl bg-gray-50/50 ${className}`}
    >
      <div className="bg-white p-4 rounded-full shadow-sm mb-4">
        <Icon className="w-8 h-8 text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>
      <p className="text-gray-500 max-w-sm mb-6 text-sm">{description}</p>

      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
