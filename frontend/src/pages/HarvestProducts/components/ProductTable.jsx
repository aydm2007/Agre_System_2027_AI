import React, { Fragment } from 'react'
import PropTypes from 'prop-types'
import { TEXT, formatNumber } from '../constants'
import UnitEditor from './UnitEditor'

const ProductTable = ({
  catalog,
  loadingCatalog,
  loadingCrops,
  farmOptions,
  cropOptions,
  selectedFarm,
  selectedCrop,
  handleFarmChange,
  setSelectedCrop,
  clearFilters,
  // Edit logic
  editingProduct,
  startEditingProduct,
  cancelEditingProduct,
  handleEditingProductChange,
  saveEditingProduct,
  editingProductSaving,
  handleDelete,
  // Edit Units logic
  addEditingUnit,
  removeEditingUnit,
  updateEditingUnit,
  markEditingDefaultUnit,
  units, // Static units list
}) => {
  return (
    <section className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      {/* Header & Filters */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
            {TEXT.catalogTableTitle}
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">{TEXT.filterHint}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {TEXT.farmFilterLabel}
            </label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={selectedFarm}
              onChange={(event) => handleFarmChange(event.target.value)}
            >
              <option value="">{TEXT.allOption}</option>
              {farmOptions.map((farm) => (
                <option key={farm.id} value={farm.id}>
                  {farm.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {TEXT.cropFilterLabel}
            </label>
            <select
              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
              value={selectedCrop}
              onChange={(event) => setSelectedCrop(event.target.value)}
              disabled={loadingCrops}
            >
              <option value="">{TEXT.allOption}</option>
              {cropOptions.map((crop) => (
                <option key={crop.id} value={crop.id}>
                  {crop.name}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            className="rounded-lg border border-gray-300 dark:border-slate-600 px-4 py-2 text-sm font-semibold text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700"
            onClick={clearFilters}
          >
            {TEXT.reset}
          </button>
        </div>
      </div>

      {/* Loading States */}
      {loadingCrops && (
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 px-3 py-2 text-sm text-blue-700 dark:text-blue-400">
          جاري تحميل قائمة المحاصيل...
        </div>
      )}

      {loadingCatalog && (
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 px-3 py-2 text-sm text-blue-700 dark:text-blue-400">
          {TEXT.loading}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-slate-700">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-700 text-end">
          <thead className="bg-gray-50 dark:bg-slate-800 text-sm text-gray-600 dark:text-slate-300">
            <tr>
              <th className="px-3 py-2 font-medium">{TEXT.cropLabel}</th>
              <th className="px-3 py-2 font-medium">{TEXT.itemLabel}</th>
              <th className="px-3 py-2 font-medium">{TEXT.packagingColumn}</th>
              <th className="px-3 py-2 font-medium">{TEXT.totalHarvest}</th>
              <th className="px-3 py-2 font-medium">{TEXT.lastHarvest}</th>
              <th className="px-3 py-2 font-medium">{TEXT.farmDetails}</th>
              <th className="px-3 py-2 font-medium">{TEXT.primaryColumn}</th>
              <th className="px-3 py-2 font-medium">{TEXT.notesColumn}</th>
              <th className="px-3 py-2 font-medium">{TEXT.actions}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-slate-700 text-sm">
            {catalog.map((record) => (
              <Fragment key={record.product_id}>
                <tr
                  className={`${editingProduct?.id === record.product_id ? 'bg-amber-50 dark:bg-amber-900/10' : 'hover:bg-gray-50 dark:hover:bg-slate-700/50'} bg-white dark:bg-slate-900`}
                >
                  <td className="px-3 py-2 text-gray-800 dark:text-slate-200">
                    {record.crop_name}
                  </td>
                  <td className="px-3 py-2 text-gray-800 dark:text-slate-200">
                    {record.item_name}
                  </td>

                  {/* Packaging Details Column */}
                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                    <div className="space-y-1 text-xs text-gray-600 dark:text-slate-400">
                      {record.quality_grade && (
                        <div>
                          <span className="font-semibold text-gray-700 dark:text-slate-300">
                            {TEXT.qualityLabel}:
                          </span>{' '}
                          {record.quality_grade}
                        </div>
                      )}
                      {record.packing_type && (
                        <div>
                          <span className="font-semibold text-gray-700 dark:text-slate-300">
                            {TEXT.packingTypeLabel}:
                          </span>{' '}
                          {record.packing_type}
                        </div>
                      )}
                      {record.reference_price != null && (
                        <div>
                          <span className="font-semibold text-gray-700 dark:text-slate-300">
                            {TEXT.referencePriceLabel}:
                          </span>{' '}
                          {formatNumber(record.reference_price)}
                        </div>
                      )}
                      {(record.pack_size != null || record.pack_uom) && (
                        <div>
                          <span className="font-semibold text-gray-700 dark:text-slate-300">
                            {TEXT.packSizeLabel}:
                          </span>{' '}
                          {record.pack_size ? formatNumber(record.pack_size) : '-'}{' '}
                          {record.pack_uom || ''}
                        </div>
                      )}

                      {/* Read-Only Units Display */}
                      <div>
                        <div className="font-semibold text-gray-700 dark:text-slate-300">
                          {TEXT.unitsSectionTitle}
                        </div>
                        {record.units?.length ? (
                          <ul className="space-y-1 mt-1">
                            {record.units.map((unit) => (
                              <li
                                key={unit.id || `${record.product_id}-${unit.unit}`}
                                className="flex items-center justify-between rounded border border-gray-100 dark:border-slate-700 px-2 py-1"
                              >
                                <span className="text-gray-700 dark:text-slate-300">
                                  {unit.unit_detail?.name ||
                                    unit.uom ||
                                    record.default_unit?.name ||
                                    record.default_uom ||
                                    '-'}
                                </span>
                                <span className="text-gray-500 dark:text-slate-400">
                                  {formatNumber(unit.multiplier)} ×{' '}
                                  {unit.uom || unit.unit_detail?.symbol || ''}
                                </span>
                                {unit.is_default && (
                                  <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
                                    {TEXT.unitDefaultTag}
                                  </span>
                                )}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <span className="text-xs text-gray-400">{TEXT.unitsEmpty}</span>
                        )}
                      </div>
                    </div>
                  </td>

                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                    {formatNumber(record.total_harvest_qty)}{' '}
                    {record.default_unit?.symbol || record.default_uom || ''}
                  </td>
                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                    {record.last_harvest_date || '-'}
                  </td>

                  {/* Farm Details */}
                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                    <div className="font-medium text-gray-700 dark:text-slate-300">
                      {record.farm_name || TEXT.farmSummaryNone}
                    </div>
                  </td>

                  {/* Primary Switch (Edit Mode or Read Only) */}
                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                    {editingProduct?.id === record.product_id ? (
                      <input
                        id={`primary-${record.product_id}`}
                        type="checkbox"
                        className="h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-600/70"
                        checked={editingProduct.is_primary}
                        onChange={(event) =>
                          handleEditingProductChange('is_primary', event.target.checked)
                        }
                      />
                    ) : record.is_primary ? (
                      <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/30 px-3 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                        {TEXT.yes}
                      </span>
                    ) : (
                      <span className="rounded-full bg-gray-100 dark:bg-slate-700 px-3 py-1 text-xs font-semibold text-gray-600 dark:text-slate-300">
                        {TEXT.no}
                      </span>
                    )}
                  </td>

                  <td className="px-3 py-2 text-gray-600 dark:text-slate-300">
                    {editingProduct?.id === record.product_id ? (
                      <input
                        type="text"
                        className="w-full rounded border border-gray-300 dark:border-slate-600 px-2 py-1 text-sm bg-white dark:bg-slate-700 dark:text-white"
                        value={editingProduct.notes}
                        onChange={(event) =>
                          handleEditingProductChange('notes', event.target.value)
                        }
                        placeholder="إضافة ملاحظات"
                      />
                    ) : (
                      record.notes || '-'
                    )}
                  </td>

                  <td className="px-3 py-2 text-end">
                    {editingProduct?.id === record.product_id ? (
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          className="rounded-lg bg-emerald-600 px-3 py-1 text-xs font-semibold text-white shadow-sm hover:bg-emerald-500 disabled:opacity-70 transition-all"
                          onClick={saveEditingProduct}
                          disabled={editingProductSaving}
                        >
                          {TEXT.save}
                        </button>
                        <button
                          type="button"
                          className="rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-1 text-xs font-semibold text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-all"
                          onClick={cancelEditingProduct}
                          disabled={editingProductSaving}
                        >
                          {TEXT.cancel}
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          className="rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-1 text-xs font-semibold text-gray-700 dark:text-slate-200 hover:bg-gray-50 dark:hover:bg-slate-700 transition-all"
                          onClick={() => startEditingProduct(record)}
                        >
                          {TEXT.edit}
                        </button>
                        <button
                          type="button"
                          className="rounded-lg border border-rose-300/30 bg-rose-500/10 px-3 py-1 text-xs font-semibold text-rose-600 dark:text-rose-400 hover:bg-rose-500/20 transition-all"
                          onClick={() => handleDelete(record)}
                        >
                          {TEXT.deleteConfirm}
                        </button>
                      </div>
                    )}
                  </td>
                </tr>

                {/* INLINE EDIT MODE EXPANSION */}
                {editingProduct?.id === record.product_id && (
                  <tr className="bg-amber-50/50 dark:bg-amber-900/10">
                    <td colSpan={9} className="px-4 py-4">
                      <div className="space-y-3">
                        <div className="grid gap-3 md:grid-cols-4">
                          <div className="space-y-1">
                            <label className="block text-sm text-gray-600 dark:text-slate-300">
                              {TEXT.qualityLabel}
                            </label>
                            <input
                              type="text"
                              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                              value={editingProduct.quality_grade}
                              onChange={(event) =>
                                handleEditingProductChange('quality_grade', event.target.value)
                              }
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="block text-sm text-gray-600 dark:text-slate-300">
                              {TEXT.packingTypeLabel}
                            </label>
                            <input
                              type="text"
                              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                              value={editingProduct.packing_type}
                              onChange={(event) =>
                                handleEditingProductChange('packing_type', event.target.value)
                              }
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="block text-sm text-gray-600 dark:text-slate-300">
                              {TEXT.referencePriceLabel}
                            </label>
                            <input
                              type="number"
                              min="0"
                              step="0.01"
                              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                              value={editingProduct.reference_price}
                              onChange={(event) => {
                                const val = parseFloat(event.target.value)
                                if (val < 0) return
                                handleEditingProductChange('reference_price', event.target.value)
                              }}
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="block text-sm text-gray-600 dark:text-slate-300">
                              {TEXT.packSizeLabel}
                            </label>
                            <input
                              type="number"
                              min="0"
                              step="0.01"
                              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                              value={editingProduct.pack_size}
                              onChange={(event) => {
                                const val = parseFloat(event.target.value)
                                if (val < 0) return
                                handleEditingProductChange('pack_size', event.target.value)
                              }}
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="block text-sm text-gray-600 dark:text-slate-300">
                              {TEXT.packUomLabel}
                            </label>
                            <input
                              type="text"
                              className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                              value={editingProduct.pack_uom}
                              onChange={(event) =>
                                handleEditingProductChange('pack_uom', event.target.value)
                              }
                            />
                          </div>
                        </div>
                        {/* Inline Unit Editor */}
                        <UnitEditor
                          rows={editingProduct.units || []}
                          prefix={`edit-${record.product_id}`}
                          onAdd={addEditingUnit}
                          onRemove={removeEditingUnit}
                          onChange={updateEditingUnit}
                          onMarkDefault={markEditingDefaultUnit}
                          units={units}
                        />
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {!catalog.length && !loadingCatalog && (
              <tr>
                <td className="px-3 py-3 text-center text-gray-500 dark:text-slate-400" colSpan={9}>
                  {TEXT.noResults}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

ProductTable.propTypes = {
  catalog: PropTypes.array.isRequired,
  loadingCatalog: PropTypes.bool.isRequired,
  loadingCrops: PropTypes.bool.isRequired,
  farmOptions: PropTypes.array.isRequired,
  cropOptions: PropTypes.array.isRequired,
  selectedFarm: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  selectedCrop: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  handleFarmChange: PropTypes.func.isRequired,
  setSelectedCrop: PropTypes.func.isRequired,
  clearFilters: PropTypes.func.isRequired,
  editingProduct: PropTypes.object,
  startEditingProduct: PropTypes.func.isRequired,
  cancelEditingProduct: PropTypes.func.isRequired,
  handleEditingProductChange: PropTypes.func.isRequired,
  saveEditingProduct: PropTypes.func.isRequired,
  editingProductSaving: PropTypes.bool.isRequired,
  handleDelete: PropTypes.func.isRequired,
  addEditingUnit: PropTypes.func.isRequired,
  removeEditingUnit: PropTypes.func.isRequired,
  updateEditingUnit: PropTypes.func.isRequired,
  markEditingDefaultUnit: PropTypes.func.isRequired,
  units: PropTypes.array.isRequired,
}

export default ProductTable
