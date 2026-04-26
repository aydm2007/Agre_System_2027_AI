import React, { memo } from 'react'
import PropTypes from 'prop-types'
import { useNavigate } from 'react-router-dom'
import { useSettings } from '../../contexts/SettingsContext'

const DailyLogSetupInner = ({ form, updateField, lookups, errors, fetchSuggestions }) => {
  const { farms, locations, tasks, crops } = lookups
  const navigate = useNavigate()
  const { allowMultiLocationActivities } = useSettings()

  // [Agri-Guardian] Smart Context State
  const [suggestions, setSuggestions] = React.useState([])
  const [loadingSuggestions, setLoading] = React.useState(false)

  const handleMagicFill = async () => {
    if (!form.date) return
    setLoading(true)
    const results = await fetchSuggestions(form.date)
    setSuggestions(results)
    setLoading(false)
  }

  const applySuggestion = (s) => {
    // Auto-fill logic
    updateField('farm', s.data.farm)
    // Legacy support: if backend sends single location, array-ify it
    const locs = Array.isArray(s.data.locations)
      ? s.data.locations
      : s.data.location
        ? [s.data.location]
        : []
    updateField('locations', locs)
    updateField('crop', s.data.crop)
    if (s.data.activity_type) {
      // Try to find task by name or mapping if needed,
      // but backend returned activity_type.
      // If activity_type maps to Task ID, use it.
      // Assuming activity_type IS the task ID for now or we need a mapping?
      // Let's assume for MVP it maps to 'task'.
      updateField('task', s.data.activity_type)
    }
    setSuggestions([]) // Clear after apply
  }

  // Locations are now filtered server-side by the parent
  const filteredLocations = locations

  // Smart Filtering: Filter Tasks by Crop (if selected)
  // We show tasks that match the crop OR are generic (null/undefined crop in definition if applicable,
  // but usually in this system tasks are linked to crops.
  // If no crop selected, show ALL? Or show only General?
  // Best Practice: If no crop, show all. If crop, show Crop Specific + General.
  const filteredTasks = form.crop
    ? tasks.filter((t) => !t.crop || String(t.crop) === String(form.crop))
    : tasks

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <h3 className="text-lg font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2">
          <span className="bg-primary/10 text-primary w-8 h-8 rounded-full flex items-center justify-center text-sm">
            1
          </span>
          الإعداد الأساسي
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Date & Magic Fill */}
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
              تاريخ الإنجاز
            </label>
            <div className="flex gap-2">
              <input
                data-testid="date-input"
                type="date"
                value={form.date}
                onChange={(e) => updateField('date', e.target.value)}
                className={`flex-1 p-2.5 rounded-lg border ${errors.date ? 'border-red-500 bg-red-50 dark:bg-red-900/20' : 'border-gray-300 dark:border-slate-600'} bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary/20 outline-none transition-all`}
              />
              <button
                type="button"
                onClick={handleMagicFill}
                disabled={!form.date || loadingSuggestions}
                className="bg-purple-100 dark:bg-purple-900/30 hover:bg-purple-200 dark:hover:bg-purple-800/40 text-purple-700 dark:text-purple-400 px-3 rounded-lg flex items-center justify-center transition-colors"
                title="اقتراحات ذكية (Oracle)"
              >
                {loadingSuggestions ? '...' : '🔮'}
              </button>
            </div>
            {errors.date && (
              <p className="text-xs text-red-500 dark:text-red-400">{errors.date || 'حقل مطلوب'}</p>
            )}

            {/* Suggestions Dropdown */}
            {suggestions.length > 0 && (
              <div className="mt-2 bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800 rounded-lg p-2 space-y-2">
                <p className="text-xs font-bold text-purple-800 dark:text-purple-400">
                  نشاط مشابه العام الماضي:
                </p>
                {suggestions.map((s, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => applySuggestion(s)}
                    className="w-full text-end text-xs p-2 bg-white dark:bg-slate-700 text-gray-800 dark:text-slate-200 rounded border border-purple-100 dark:border-purple-800 hover:border-purple-300 dark:hover:border-purple-600 hover:shadow-sm transition-all"
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Farm */}
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
              المزرعة
            </label>
            <select
              data-testid="farm-select"
              value={form.farm}
              onChange={(e) => updateField('farm', e.target.value)}
              className={`w-full p-2.5 rounded-lg border ${errors.farm ? 'border-red-500 bg-red-50 dark:bg-red-900/20' : 'border-gray-300 dark:border-slate-600'} bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary/20 outline-none transition-all`}
            >
              <option value="">اختر المزرعة...</option>
              {farms.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
            {errors.farm && (
              <p className="text-xs text-red-500 dark:text-red-400">{errors.farm || 'حقل مطلوب'}</p>
            )}
          </div>

          {/* Locations (Multiple) */}
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
              المواقع (Sites)
            </label>
            <select
              data-testid="location-select"
              multiple={allowMultiLocationActivities}
              value={
                allowMultiLocationActivities ? form.locations || [] : form.locations?.[0] || ''
              }
              onChange={(e) => {
                if (allowMultiLocationActivities) {
                  const values = Array.from(e.target.selectedOptions, (option) => option.value)
                  updateField('locations', values)
                } else {
                  updateField('locations', [e.target.value])
                }
              }}
              disabled={!form.farm}
              className={`w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white disabled:bg-gray-100 dark:disabled:bg-slate-600 disabled:text-gray-400 dark:disabled:text-slate-500 focus:ring-2 focus:ring-primary/20 outline-none transition-all ${allowMultiLocationActivities ? 'min-h-[100px]' : ''}`}
            >
              <option disabled value="">
                {form.farm
                  ? allowMultiLocationActivities
                    ? 'اضغط مع الاستمرار على (Ctrl/Cmd) لاختيار أكثر من موقع...'
                    : 'اختر موقعاً واحداً...'
                  : 'حدد المزرعة أولاً'}
              </option>
              {filteredLocations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name} ({l.code})
                </option>
              ))}
            </select>
            {allowMultiLocationActivities && (
              <p className="text-[10px] text-gray-500 mt-1">
                يمكنك اختيار أكثر من موقع لتوزيع تكلفة النشاط عليها بالتساوي.
              </p>
            )}
            {errors.locations && (
              <p className="text-xs text-red-500 dark:text-red-400">
                {errors.locations || 'حقل مطلوب'}
              </p>
            )}
          </div>

          {/* Crop (Moved Up - Context Setter) */}
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
              المحصول (اختياري)
            </label>
            <select
              data-testid="crop-select"
              value={form.crop}
              onChange={(e) => updateField('crop', e.target.value)}
              className="w-full p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary/20 outline-none transition-all"
            >
              <option value="">عام / غير محدد</option>
              {crops.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            {/* [AGRI-GUARDIAN] Quick-action link when no crops available */}
            {form.farm && crops.length === 0 && (
              <div className="mt-1.5 flex items-center gap-1">
                <span className="text-xs text-amber-600 dark:text-amber-400">
                  لا توجد محاصيل لهذه المزرعة.
                </span>
                <button
                  type="button"
                  onClick={() => navigate('/settings/crops')}
                  className="text-xs text-primary font-bold hover:underline"
                >
                  ← إضافة محصول
                </button>
              </div>
            )}
          </div>

          {/* Task (Filtered by Crop) */}
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
              المهمة
            </label>
            <select
              data-testid="task-select"
              value={form.task}
              onChange={(e) => updateField('task', e.target.value)}
              className={`w-full p-2.5 rounded-lg border ${errors.task ? 'border-red-500 bg-red-50 dark:bg-red-900/20' : 'border-gray-300 dark:border-slate-600'} bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary/20 outline-none transition-all`}
            >
              <option value="">
                {form.crop
                  ? `مهام محصول ${crops.find((c) => String(c.id) === String(form.crop))?.name || ''}`
                  : 'جميع المهام'}
              </option>
              {filteredTasks.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            {errors.task && (
              <p className="text-xs text-red-500 dark:text-red-400">{errors.task || 'حقل مطلوب'}</p>
            )}
            {/* [AGRI-GUARDIAN] Quick-action link when no tasks available */}
            {form.farm && filteredTasks.length === 0 && (
              <div className="mt-1.5 flex items-center gap-1">
                <span className="text-xs text-amber-600 dark:text-amber-400">
                  لا توجد مهام متاحة{form.crop ? ' لهذا المحصول' : ''}.
                </span>
                <button
                  type="button"
                  onClick={() => navigate('/settings/tasks')}
                  className="text-xs text-primary font-bold hover:underline"
                >
                  ← إضافة مهمة
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// [AGRI-GUARDIAN] PropTypes
DailyLogSetupInner.propTypes = {
  form: PropTypes.object.isRequired,
  updateField: PropTypes.func.isRequired,
  lookups: PropTypes.shape({
    farms: PropTypes.array,
    locations: PropTypes.array,
    crops: PropTypes.array,
    tasks: PropTypes.array,
  }),
  errors: PropTypes.object,
  fetchSuggestions: PropTypes.func, // [Agri-Guardian]
}

export const DailyLogSetup = memo(DailyLogSetupInner)
