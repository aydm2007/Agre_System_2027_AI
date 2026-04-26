import PropTypes from 'prop-types'
import { TEXT } from '../pages/daily-log/constants'

export default function CollapsibleCard({
  title,
  hint,
  collapsed,
  onToggle,
  children,
  disableToggle = false,
  className = '',
}) {
  const toggleLabel = collapsed ? TEXT.sections.toggleShow : TEXT.sections.toggleHide

  return (
    <div
      className={`rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm ${className}`}
    >
      <button
        type="button"
        className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-end ${disableToggle ? 'cursor-default opacity-80' : ''}`}
        onClick={disableToggle ? undefined : onToggle}
        disabled={disableToggle}
      >
        <div className="space-y-1">
          <p className="text-sm font-semibold text-gray-800 dark:text-white">{title}</p>
          {hint && <p className="text-xs text-gray-500 dark:text-slate-400">{hint}</p>}
        </div>
        {!disableToggle && <span className="text-xs font-medium text-primary">{toggleLabel}</span>}
      </button>
      {!collapsed && (
        <div className="space-y-4 border-t border-gray-100 dark:border-slate-700 px-4 py-4">
          {children}
        </div>
      )}
    </div>
  )
}

CollapsibleCard.propTypes = {
  title: PropTypes.string.isRequired,
  hint: PropTypes.string,
  collapsed: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
  children: PropTypes.node,
  disableToggle: PropTypes.bool,
  className: PropTypes.string,
}
