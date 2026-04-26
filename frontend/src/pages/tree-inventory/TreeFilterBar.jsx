// Tree Inventory Filter Bar Component
// Extracted from TreeInventory.jsx for atomic component architecture

export default function TreeFilterBar({
  draftFilters,
  onFilterChange,
  onApply,
  onReset,
  farms = [],
  locations = [],
  varieties = [],
  treeStatuses = [],
  treeLossReasons = [],
  columnVisibility = {},
  columnLabels = {},
  onToggleColumn,
  TEXT,
}) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 space-y-4">
      {/* Date Range Filters */}
      <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-600" htmlFor="filter-start">
            من تاريخ
          </label>
          <input
            id="filter-start"
            type="date"
            name="start"
            value={draftFilters.start}
            onChange={onFilterChange}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-600" htmlFor="filter-end">
            إلى تاريخ
          </label>
          <input
            id="filter-end"
            type="date"
            name="end"
            value={draftFilters.end}
            onChange={onFilterChange}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-600" htmlFor="filter-farm">
            {TEXT?.filters?.farm || 'المزرعة'}
          </label>
          <select
            id="filter-farm"
            name="farm"
            value={draftFilters.farm}
            onChange={onFilterChange}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">الكل</option>
            {farms.map((farm) => (
              <option key={farm.id} value={farm.id}>
                {farm.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-600" htmlFor="filter-location">
            {TEXT?.filters?.location || 'الموقع'}
          </label>
          <select
            id="filter-location"
            name="location_id"
            value={draftFilters.location_id}
            onChange={onFilterChange}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">الكل</option>
            {locations.map((loc) => (
              <option key={loc.id} value={loc.id}>
                {loc.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Second Row Filters */}
      <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-600" htmlFor="filter-variety">
            {TEXT?.filters?.variety || 'الصنف'}
          </label>
          <select
            id="filter-variety"
            name="variety_id"
            value={draftFilters.variety_id}
            onChange={onFilterChange}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">الكل</option>
            {varieties.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-600" htmlFor="filter-status">
            {TEXT?.filters?.status || 'الحالة'}
          </label>
          <select
            id="filter-status"
            name="status_code"
            value={draftFilters.status_code}
            onChange={onFilterChange}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">الكل</option>
            {treeStatuses.map((s) => (
              <option key={s.code} value={s.code}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-600" htmlFor="filter-loss">
            {TEXT?.filters?.lossReason || 'سبب الفقد'}
          </label>
          <select
            id="filter-loss"
            name="loss_reason"
            value={draftFilters.loss_reason}
            onChange={onFilterChange}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">الكل</option>
            {treeLossReasons.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Service Date Range */}
      <div className="grid gap-3 md:grid-cols-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-600" htmlFor="filter-service-start">
            خدمات من
          </label>
          <input
            id="filter-service-start"
            type="date"
            name="service_start"
            value={draftFilters.service_start}
            onChange={onFilterChange}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-600" htmlFor="filter-service-end">
            خدمات إلى
          </label>
          <input
            id="filter-service-end"
            type="date"
            name="service_end"
            value={draftFilters.service_end}
            onChange={onFilterChange}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Column Toggles */}
      {onToggleColumn && Object.keys(columnLabels).length > 0 && (
        <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-100">
          {Object.entries(columnLabels).map(([key, label]) => (
            <label
              key={key}
              className={`
                inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer
                transition-colors duration-200
                ${
                  columnVisibility[key]
                    ? 'bg-indigo-100 text-indigo-700 border border-indigo-200'
                    : 'bg-gray-100 text-gray-500 border border-gray-200 hover:bg-gray-200'
                }
              `}
            >
              <input
                type="checkbox"
                checked={columnVisibility[key] || false}
                onChange={() => onToggleColumn(key)}
                className="sr-only"
              />
              {label}
            </label>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-2">
        <button
          type="button"
          onClick={onApply}
          className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-sm font-medium rounded-lg
                     shadow-lg shadow-indigo-500/20 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300"
        >
          {TEXT?.buttons?.apply || 'تطبيق'}
        </button>
        <button
          type="button"
          onClick={onReset}
          className="px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg
                     hover:bg-gray-200 transition-colors duration-200"
        >
          {TEXT?.buttons?.reset || 'إعادة تعيين'}
        </button>
      </div>
    </div>
  )
}
