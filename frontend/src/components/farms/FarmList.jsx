import { Link } from 'react-router-dom'
import ar from '../../i18n/ar'
import { useAuth } from '../../auth/AuthContext'

const TEXT = ar.farms

export default function FarmList({ farms, onEdit, onDelete }) {
  const auth = useAuth()
  const canEdit = auth.canChangeModel('farm') || auth.isAdmin || auth.isSuperuser
  const canDelete = auth.canDeleteModel('farm') || auth.isAdmin || auth.isSuperuser

  if (!farms || farms.length === 0) {
    return (
      <div className="p-12 text-center">
        <div className="text-gray-400 dark:text-slate-500 text-lg mb-2">🌾</div>
        <p className="text-gray-500 dark:text-slate-400">{TEXT.noData}</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-100 dark:border-slate-700">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-700 text-sm">
        <thead className="bg-gray-50/50 dark:bg-slate-800/50">
          <tr>
            <th className="px-6 py-3 text-end text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {TEXT.name}
            </th>
            <th className="px-6 py-3 text-end text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {TEXT.region}
            </th>
            <th className="px-6 py-3 text-end text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {TEXT.area}
            </th>
            <th className="px-6 py-3 text-end text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {TEXT.actions}
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-slate-800 divide-y divide-gray-100 dark:divide-slate-700">
          {farms.map((farm) => (
            <tr
              key={farm.id}
              className="hover:bg-gray-50/50 dark:hover:bg-slate-700/50 transition-colors"
            >
              <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900 dark:text-white">
                {farm.name}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-gray-600 dark:text-slate-300">
                {farm.region || TEXT.fallback}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-gray-600 dark:text-slate-300 font-mono text-xs">
                {farm.area || '-'}
              </td>
              <td className="px-6 py-4 whitespace-nowrap flex flex-wrap gap-2 justify-end">
                <Link
                  to={`/farms/${farm.id}`}
                  className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-primary/10 text-primary rounded-md hover:bg-primary/20 transition-colors"
                >
                  {TEXT.viewDetails}
                </Link>
                {canEdit && (
                  <button
                    type="button"
                    onClick={() => onEdit(farm)}
                    className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 rounded-md hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
                  >
                    {TEXT.edit}
                  </button>
                )}
                {canDelete && (
                  <button
                    type="button"
                    onClick={() => onDelete(farm.id)}
                    className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-md hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors"
                  >
                    {TEXT.delete}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
