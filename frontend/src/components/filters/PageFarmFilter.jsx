import PropTypes from 'prop-types'

export default function PageFarmFilter({
  value,
  onChange,
  options,
  canUseAll = false,
  label = 'المزرعة',
  className = '',
  testId = 'page-farm-filter',
}) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label className="text-sm text-gray-600 dark:text-slate-400">{label}</label>
      <select
        data-testid={testId}
        className="border rounded px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white dark:border-slate-600"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {canUseAll && <option value="all">كل المزارع</option>}
        <option value="">اختر المزرعة</option>
        {options.map((farm) => (
          <option key={farm.id} value={farm.id}>
            {farm.name}
          </option>
        ))}
      </select>
    </div>
  )
}

PageFarmFilter.propTypes = {
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  options: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
      name: PropTypes.string.isRequired,
    }),
  ),
  canUseAll: PropTypes.bool,
  label: PropTypes.string,
  className: PropTypes.string,
  testId: PropTypes.string,
}
