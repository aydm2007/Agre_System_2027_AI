import React from 'react'
import { TEXT } from '../constants'

const ReportFilters = ({
  filters,
  handleFilterChange,
  fetchReport,
  seasons,
  farms,
  canUseAll,
  locations,
  crops,
  tasks,
  varieties,
  treeStatuses,
}) => {
  return (
    <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow">
      <h1 className="text-2xl font-bold text-gray-800 dark:text-white mb-4">{TEXT.pageTitle}</h1>
      <div className="grid md:grid-cols-6 gap-3">
        {/* Start Date */}
        <div className="flex flex-col">
          <label className="text-sm text-gray-600 dark:text-slate-400 mb-1">
            {TEXT.filters.start}
          </label>
          <input
            type="date"
            name="start"
            value={filters.start}
            onChange={handleFilterChange}
            className="border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
          />
        </div>
        {/* End Date */}
        <div className="flex flex-col">
          <label className="text-sm text-gray-600 dark:text-slate-400 mb-1">
            {TEXT.filters.end}
          </label>
          <input
            type="date"
            name="end"
            value={filters.end}
            onChange={handleFilterChange}
            className="border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
          />
        </div>
        {/* Season */}
        <div className="flex flex-col">
          <label className="text-sm text-gray-600 dark:text-slate-400 mb-1">
            {TEXT.filters.season}
          </label>
          <select
            name="season"
            value={filters.season}
            onChange={handleFilterChange}
            className="border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
          >
            <option value="">كل المواسم</option>
            {seasons.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        {/* Farm */}
        <div className="flex flex-col">
          <label className="text-sm text-gray-600 dark:text-slate-400 mb-1">
            {TEXT.filters.farm}
          </label>
          <select
            data-testid="reports-farm-filter"
            name="farm"
            value={filters.farm}
            onChange={handleFilterChange}
            className="border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
          >
            {canUseAll && <option value="all">كل المزارع</option>}
            <option value="">{TEXT.filters.placeholderFarm}</option>
            {farms.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </div>
        {/* Location */}
        <div className="flex flex-col">
          <label className="text-sm text-gray-600 dark:text-slate-400 mb-1">
            {TEXT.filters.location}
          </label>
          <select
            name="location_id"
            value={filters.location_id}
            onChange={handleFilterChange}
            disabled={!locations.length}
            className="border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
          >
            <option value="">{TEXT.filters.placeholderLocation}</option>
            {locations.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
        </div>
        {/* Crop */}
        <div className="flex flex-col">
          <label className="text-sm text-gray-600 dark:text-slate-400 mb-1">
            {TEXT.filters.crop}
          </label>
          <select
            name="crop_id"
            value={filters.crop_id}
            onChange={handleFilterChange}
            disabled={!crops.length}
            className="border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
          >
            <option value="">{TEXT.filters.placeholderCrop}</option>
            {crops.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        {/* Task */}
        <div className="flex flex-col">
          <label className="text-sm text-gray-600 dark:text-slate-400 mb-1">
            {TEXT.filters.task}
          </label>
          <select
            name="task_id"
            value={filters.task_id}
            onChange={handleFilterChange}
            disabled={!tasks.length}
            className="border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
          >
            <option value="">{TEXT.filters.placeholderTask}</option>
            {tasks.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
        {/* Variety */}
        <div className="flex flex-col">
          <label className="text-sm text-gray-600 dark:text-slate-400 mb-1">
            {TEXT.filters.variety}
          </label>
          <select
            name="variety_id"
            value={filters.variety_id}
            onChange={handleFilterChange}
            disabled={!varieties.length}
            className="border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
          >
            <option value="">{TEXT.filters.placeholderVariety}</option>
            {varieties.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </div>
        {/* Status */}
        <div className="flex flex-col">
          <label className="text-sm text-gray-600 dark:text-slate-400 mb-1">
            {TEXT.filters.status}
          </label>
          <select
            name="status_code"
            value={filters.status_code}
            onChange={handleFilterChange}
            disabled={!treeStatuses.length}
            className="border dark:border-slate-600 rounded p-2 bg-white dark:bg-slate-700 dark:text-white"
          >
            <option value="">{TEXT.filters.placeholderStatus}</option>
            {treeStatuses.map((s) => (
              <option key={s.code} value={s.code}>
                {s.name_ar || s.name_en || s.code}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="flex justify-end mt-3">
        <button
          type="button"
          onClick={fetchReport}
          className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark"
        >
          {TEXT.filters.apply}
        </button>
      </div>
    </div>
  )
}

export default ReportFilters
