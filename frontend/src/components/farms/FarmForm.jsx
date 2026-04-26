import { useEffect, useState } from 'react'
import ar from '../../i18n/ar'

const TEXT = ar.farms
const initialFarm = { name: '', region: '', area: '', description: '' }

export default function FarmForm({ initialValues, onSubmit, onCancel, isSubmitting }) {
  const [values, setValues] = useState(initialFarm)
  const isEdit = !!initialValues

  useEffect(() => {
    if (initialValues) {
      setValues({
        name: initialValues.name || '',
        region: initialValues.region || '',
        area: initialValues.area || '',
        description: initialValues.description || '',
      })
    } else {
      setValues(initialFarm)
    }
  }, [initialValues])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!values.name.trim()) return // Simple validation
    onSubmit(values)
  }

  const handleChange = (e) => {
    const { id, value } = e.target
    // Strip prefix 'farm-' if used in IDs
    const key = id.replace('farm-', '')
    setValues((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <section className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 space-y-6">
      <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-700 pb-4">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
          {isEdit ? TEXT.editFarm : TEXT.addFarm}
        </h2>
        <button
          onClick={onCancel}
          className="text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 transition"
        >
          ✕
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-1">
            <label
              className="block text-sm font-medium text-gray-700 dark:text-slate-300"
              htmlFor="farm-name"
            >
              {TEXT.name} <span className="text-red-500">*</span>
            </label>
            <input
              id="farm-name"
              type="text"
              required
              value={values.name}
              onChange={handleChange}
              className="w-full border border-gray-300 dark:border-slate-600 rounded-lg p-2.5 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition"
              placeholder={TEXT.name}
            />
          </div>
          <div className="space-y-1">
            <label
              className="block text-sm font-medium text-gray-700 dark:text-slate-300"
              htmlFor="farm-region"
            >
              {TEXT.region}
            </label>
            <input
              id="farm-region"
              type="text"
              value={values.region}
              onChange={handleChange}
              className="w-full border border-gray-300 dark:border-slate-600 rounded-lg p-2.5 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition"
              placeholder={TEXT.region}
            />
          </div>
          <div className="space-y-1">
            <label
              className="block text-sm font-medium text-gray-700 dark:text-slate-300"
              htmlFor="farm-area"
            >
              {TEXT.area}
            </label>
            <input
              id="farm-area"
              type="number"
              min="0"
              step="0.01"
              value={values.area}
              onChange={handleChange}
              className="w-full border border-gray-300 dark:border-slate-600 rounded-lg p-2.5 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition"
              placeholder="0.00"
            />
          </div>
          <div className="space-y-1 md:col-span-2">
            <label
              className="block text-sm font-medium text-gray-700 dark:text-slate-300"
              htmlFor="farm-description"
            >
              {TEXT.description}
            </label>
            <textarea
              id="farm-description"
              value={values.description}
              onChange={handleChange}
              className="w-full border border-gray-300 dark:border-slate-600 rounded-lg p-2.5 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition min-h-[100px]"
              rows={3}
              placeholder={TEXT.description}
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-5 py-2.5 bg-gray-50 dark:bg-slate-700 text-gray-700 dark:text-slate-200 font-medium rounded-lg hover:bg-gray-100 dark:hover:bg-slate-600 transition border border-gray-200 dark:border-slate-600"
          >
            {TEXT.cancel}
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-5 py-2.5 bg-primary text-white font-medium rounded-lg hover:bg-primary-dark transition shadow-md hover:shadow-lg disabled:opacity-70 flex items-center gap-2"
          >
            {isSubmitting && (
              <svg
                className="animate-spin h-4 w-4 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            )}
            {TEXT.save}
          </button>
        </div>
      </form>
    </section>
  )
}
