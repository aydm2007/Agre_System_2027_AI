import { DailyLogSetup } from './DailyLogSetup'
import { DailyLogResources } from './DailyLogResources'
import { DailyLogDetails } from './DailyLogDetails'

export const DailyLogWizard = ({
  form,
  updateField,
  errors,
  step,
  nextStep,
  prevStep,
  isSubmitting,
  lookups,
  onSubmit,
  perennialLogic,
  fetchSuggestions,
  taskContext,
}) => {
  const steps = [
    { num: 1, title: 'الإعداد' },
    { num: 2, title: 'الموارد' },
    { num: 3, title: 'التفاصيل' },
  ]

  const progress = (step / steps.length) * 100

  return (
    <div className="max-w-4xl mx-auto pb-20">
      {/* Stepper Header */}
      <div className="mb-8">
        <div className="relative h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
          <div
            className="absolute top-0 right-0 h-full bg-primary transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between mt-2 px-1">
          {steps.map((s) => (
            <div
              key={s.num}
              data-testid={
                s.num === 1
                  ? 'wizard-step-setup'
                  : s.num === 2
                    ? 'wizard-step-resources'
                    : 'wizard-step-details'
              }
              className={`text-sm font-medium transition-colors ${step >= s.num ? 'text-primary' : 'text-gray-400 dark:text-slate-500'}`}
            >
              {s.num}. {s.title}
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div className="min-h-[400px]">
        {step === 1 && (
          <DailyLogSetup
            form={form}
            updateField={updateField}
            lookups={lookups}
            errors={errors}
            fetchSuggestions={fetchSuggestions} // [Agri-Guardian]
          />
        )}
        {step === 2 && (
          <DailyLogResources
            form={form}
            updateField={updateField}
            lookups={lookups}
            errors={errors}
            taskContext={taskContext}
          />
        )}
        {step === 3 && (
          <DailyLogDetails
            form={form}
            updateField={updateField}
            lookups={lookups}
            errors={errors}
            perennialLogic={perennialLogic}
            taskContext={taskContext}
          />
        )}
      </div>

      {/* Navigation Footer */}
      <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 border-t border-gray-200 dark:border-slate-700 p-4 shadow-lg z-50">
        <div className="max-w-4xl mx-auto flex justify-between items-center">
          <button
            data-testid="wizard-prev-button"
            onClick={prevStep}
            disabled={step === 1 || isSubmitting}
            className={`px-6 py-2.5 rounded-lg font-medium transition-all ${step === 1 ? 'text-gray-300 dark:text-slate-600 cursor-not-allowed' : 'text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700'}`}
          >
            السابق
          </button>

          <div className="flex items-center gap-4">
            {step < 3 ? (
              <button
                data-testid="wizard-next-button"
                onClick={nextStep}
                className="bg-primary hover:bg-primary/90 text-white px-8 py-2.5 rounded-lg font-bold shadow-md shadow-primary/20 transition-all hover:scale-105 active:scale-95"
              >
                التالي
              </button>
            ) : (
              <button
                data-testid="daily-log-save"
                onClick={onSubmit}
                disabled={isSubmitting}
                className="bg-green-600 hover:bg-green-700 text-white px-8 py-2.5 rounded-lg font-bold shadow-md shadow-green-600/20 transition-all hover:scale-105 active:scale-95 disabled:opacity-70 disabled:cursor-wait"
              >
                {isSubmitting ? 'جاري الحفظ...' : 'حفظ السجل'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
