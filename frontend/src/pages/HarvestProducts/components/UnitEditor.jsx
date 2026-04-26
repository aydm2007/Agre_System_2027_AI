import React from 'react'
import PropTypes from 'prop-types'
import { TEXT } from '../constants'
import { Plus, Trash2 } from 'lucide-react'

const UnitEditor = ({ rows, prefix, onAdd, onRemove, onChange, onMarkDefault, units }) => {
    return (
        <div className="space-y-3 md:col-span-4">
            <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-700 dark:text-slate-200">
                    {TEXT.unitsSectionTitle}
                </span>
                <button
                    type="button"
                    className="flex items-center gap-1 rounded-lg border border-dashed border-gray-300 dark:border-slate-600 px-3 py-1 text-xs font-semibold text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700"
                    onClick={onAdd}
                >
                    <Plus className="w-3.5 h-3.5" />
                    {TEXT.addUnitButton}
                </button>
            </div>
            {rows?.length ? (
                <div className="space-y-3">
                    {rows.map((unitRow, index) => (
                        <div
                            key={unitRow.id ?? `${prefix}-${index}`}
                            className="grid gap-2 rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-3 md:grid-cols-5"
                        >
                            <div className="space-y-1">
                                <label className="block text-xs text-gray-500 dark:text-slate-400">
                                    {TEXT.unitSelectLabel}
                                </label>
                                <select
                                    className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white"
                                    value={unitRow.unit}
                                    onChange={(event) => onChange(index, 'unit', event.target.value)}
                                >
                                    <option value="">{TEXT.allOption}</option>
                                    {units.map((unit) => (
                                        <option key={unit.id} value={unit.id}>
                                            {unit.name} ({unit.symbol || unit.code})
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label className="block text-xs text-gray-500 dark:text-slate-400">
                                    {TEXT.unitMultiplierLabel}
                                </label>
                                <input
                                    type="number"
                                    step="0.0001"
                                    min="0"
                                    className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                                    value={unitRow.multiplier}
                                    onChange={(event) => onChange(index, 'multiplier', event.target.value)}
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="block text-xs text-gray-500 dark:text-slate-400">
                                    {TEXT.unitUomLabel}
                                </label>
                                <input
                                    type="text"
                                    className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                                    value={unitRow.uom}
                                    onChange={(event) => onChange(index, 'uom', event.target.value)}
                                />
                            </div>
                            <div className="flex items-center justify-center gap-2">
                                <input
                                    id={`${prefix}-default-${index}`}
                                    type="radio"
                                    name={`${prefix}-default`}
                                    className="h-4 w-4 border-gray-300 text-primary focus:ring-primary/70"
                                    checked={Boolean(unitRow.is_default)}
                                    onChange={() => onMarkDefault(index)}
                                />
                                <label
                                    htmlFor={`${prefix}-default-${index}`}
                                    className="text-xs text-gray-600 dark:text-slate-300"
                                >
                                    {TEXT.unitDefaultLabel}
                                </label>
                            </div>
                            <div className="flex items-center justify-end">
                                <button
                                    type="button"
                                    className="flex items-center gap-1 rounded-lg border border-red-200 px-3 py-1 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                                    onClick={() => onRemove(index)}
                                    disabled={(rows || []).length <= 1}
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                    {TEXT.removeUnitButton}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="rounded-lg border border-dashed border-gray-200 dark:border-slate-600 px-3 py-2 text-xs text-gray-500 dark:text-slate-400">
                    {TEXT.unitsEmpty}
                </div>
            )}
        </div>
    )
}

UnitEditor.propTypes = {
    rows: PropTypes.array.isRequired,
    prefix: PropTypes.string.isRequired,
    onAdd: PropTypes.func.isRequired,
    onRemove: PropTypes.func.isRequired,
    onChange: PropTypes.func.isRequired,
    onMarkDefault: PropTypes.func.isRequired,
    units: PropTypes.array.isRequired,
}

export default UnitEditor
