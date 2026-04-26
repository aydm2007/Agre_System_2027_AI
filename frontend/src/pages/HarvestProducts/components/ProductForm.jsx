import PropTypes from 'prop-types' // [AGRI-GUARDIAN] Strict Typing
import { TEXT } from '../constants'
import UnitEditor from './UnitEditor'

const ProductForm = ({
  form,
  setForm,
  submitting,
  loadingCrops,
  crops,
  farmOptions,
  cropOptions,
  itemOptions,
  units,
  // Helper functions passed from hook
  addFormUnit,
  removeFormUnit,
  updateFormUnit,
  markFormDefaultUnit,
  resetForm,
}) => {
  const blockNegativeNumericStroke = (event) => {
    if (['-', '+', 'e', 'E'].includes(event.key)) {
      event.preventDefault()
    }
  }

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <h2 className="mb-4 text-lg font-semibold text-gray-800 dark:text-white">
        {TEXT.createItemTitle}
      </h2>
      <form onSubmit={form.handleSubmit} className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {/* Farm Selection */}
        <div className="space-y-1">
          <label className="block text-sm text-gray-600 dark:text-slate-300">
            {TEXT.farmFilterLabel}
          </label>
          <select
            className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
            value={form.farm}
            onChange={(event) => setForm((previous) => ({ ...previous, farm: event.target.value }))}
            required
          >
            <option value="">{TEXT.allOption}</option>
            {farmOptions.map((farm) => (
              <option key={farm.id} value={farm.id}>
                {farm.name}
              </option>
            ))}
          </select>
        </div>

        {/* Crop Selection */}
        <div className="space-y-1">
          <label className="block text-sm text-gray-600 dark:text-slate-300">
            {TEXT.cropLabel}
          </label>
          <select
            className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
            value={form.crop}
            onChange={(event) => setForm((previous) => ({ ...previous, crop: event.target.value }))}
            required
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

        {/* Item Selection */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <label className="block text-sm text-gray-600 dark:text-slate-300">
              {TEXT.itemLabel}
            </label>
            <a
              href="/catalog"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-semibold text-primary hover:underline dark:text-emerald-400"
            >
              + إضافة صنف محصول
            </a>
          </div>
          <select
            className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
            value={form.item}
            onChange={(event) => setForm((previous) => ({ ...previous, item: event.target.value }))}
            required
          >
            <option value="">{TEXT.allOption}</option>
            {itemOptions.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          {itemOptions.length === 0 && (
            <div className="mt-2 rounded-lg border border-amber-300/80 bg-amber-50 px-2 py-1 text-[11px] text-amber-800 dark:border-amber-500/40 dark:bg-amber-900/20 dark:text-amber-200">
              لا توجد أصناف حصاد (Yield) متاحة حالياً. أضف صنفاً ثم أعد تحميل الصفحة.
            </div>
          )}
          <p className="text-[11px] text-gray-500 dark:text-slate-400 mt-1">
            اختر منتج الحصاد المرتبط بالمحصول. إذا لم تجد الصنف المطلوب أضفه من صفحة الكتالوج.
          </p>
        </div>

        {/* Primary Checkbox */}
        <div className="flex items-center gap-2 pt-6 md:pt-8">
          <input
            id="is_primary"
            type="checkbox"
            className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary/70"
            checked={form.is_primary}
            onChange={(event) =>
              setForm((previous) => ({ ...previous, is_primary: event.target.checked }))
            }
          />
          <label htmlFor="is_primary" className="text-sm text-gray-600 dark:text-slate-300">
            {TEXT.primaryLabel}
          </label>
        </div>

        {/* Notes */}
        <div className="space-y-1">
          <label className="block text-sm text-gray-600 dark:text-slate-300">
            {TEXT.notesLabel}
          </label>
          <input
            type="text"
            className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
            value={form.notes}
            onChange={(event) =>
              setForm((previous) => ({ ...previous, notes: event.target.value }))
            }
            placeholder="ملاحظات إضافية"
          />
        </div>

        {/* Quality Grade */}
        <div className="space-y-1">
          <label className="block text-sm text-gray-600 dark:text-slate-300">
            {TEXT.qualityLabel}
          </label>
          <input
            type="text"
            className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
            value={form.quality_grade}
            onChange={(event) =>
              setForm((previous) => ({ ...previous, quality_grade: event.target.value }))
            }
          />
        </div>

        {/* Packing Type */}
        <div className="space-y-1">
          <label className="block text-sm text-gray-600 dark:text-slate-300">
            {TEXT.packingTypeLabel}
          </label>
          <input
            type="text"
            className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
            value={form.packing_type}
            onChange={(event) =>
              setForm((previous) => ({ ...previous, packing_type: event.target.value }))
            }
          />
        </div>

        {/* Reference Price */}
        <div className="space-y-1">
          <label className="block text-sm text-gray-600 dark:text-slate-300">
            {TEXT.referencePriceLabel}
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
            value={form.reference_price}
            onKeyDown={blockNegativeNumericStroke}
            onChange={(event) => {
              const val = parseFloat(event.target.value)
              if (val < 0) return
              setForm((previous) => ({ ...previous, reference_price: event.target.value }))
            }}
          />
        </div>

        {/* Pack Size */}
        <div className="space-y-1">
          <label className="block text-sm text-gray-600 dark:text-slate-300">
            {TEXT.packSizeLabel}
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
            value={form.pack_size}
            onKeyDown={blockNegativeNumericStroke}
            onChange={(event) => {
              const val = parseFloat(event.target.value)
              if (val < 0) return
              setForm((previous) => ({ ...previous, pack_size: event.target.value }))
            }}
          />
        </div>

        {/* Pack UOM */}
        <div className="space-y-1">
          <label className="block text-sm text-gray-600 dark:text-slate-300">
            {TEXT.packUomLabel}
          </label>
          <input
            type="text"
            className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
            value={form.pack_uom}
            onChange={(event) =>
              setForm((previous) => ({ ...previous, pack_uom: event.target.value }))
            }
          />
        </div>

        {/* Units Editor */}
        <UnitEditor
          rows={form.units || []}
          prefix="create"
          onAdd={addFormUnit}
          onRemove={removeFormUnit}
          onChange={updateFormUnit}
          onMarkDefault={markFormDefaultUnit}
          units={units}
        />

        {/* Buttons */}
        <div className="flex items-center gap-3 md:col-span-4">
          <button
            type="submit" // Trigger form submit handled by parent via form.handleSubmit
            disabled={submitting || loadingCrops || !crops.length || !itemOptions.length}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-70 transition-all shadow-emerald-500/20"
          >
            {TEXT.submit}
          </button>
          <button
            type="button"
            className="rounded-lg border border-gray-300 dark:border-slate-600 px-4 py-2 text-sm font-semibold text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-all"
            onClick={resetForm}
          >
            {TEXT.reset}
          </button>
        </div>
      </form>
    </section>
  )
}

ProductForm.propTypes = {
  form: PropTypes.object.isRequired,
  setForm: PropTypes.func.isRequired,
  submitting: PropTypes.bool.isRequired,
  loadingCrops: PropTypes.bool.isRequired,
  crops: PropTypes.array.isRequired,
  farmOptions: PropTypes.array.isRequired,
  cropOptions: PropTypes.array.isRequired,
  itemOptions: PropTypes.array.isRequired,
  units: PropTypes.array.isRequired,
  addFormUnit: PropTypes.func.isRequired,
  removeFormUnit: PropTypes.func.isRequired,
  updateFormUnit: PropTypes.func.isRequired,
  markFormDefaultUnit: PropTypes.func.isRequired,
  resetForm: PropTypes.func.isRequired,
}

export default ProductForm
