import { memo, useEffect, useMemo, useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import { EmployeeSelect } from '../ui/EmployeeSelect'
import api, { LaborEstimates } from '../../api/client'
import { extractApiError } from '../../utils/errorUtils.js'

const DailyLogResourcesInner = ({ form, updateField, lookups: _lookups, errors, taskContext }) => {
  const [estimate, setEstimate] = useState(null)
  const [estimateError, setEstimateError] = useState('')
  const [loadingEstimate, setLoadingEstimate] = useState(false)
  const [qrScanActive, setQrScanActive] = useState(false)
  const [qrStatus, setQrStatus] = useState('')

  const handleQrScan = useCallback(async () => {
    if (qrScanActive) {
      setQrScanActive(false)
      setQrStatus('')
      return
    }
    setQrScanActive(true)
    setQrStatus('جاري تشغيل الكاميرا...')
    try {
      const { Html5Qrcode } = await import('html5-qrcode')
      const scanner = new Html5Qrcode('qr-employee-reader')
      await scanner.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 200, height: 200 } },
        async (decodedText) => {
          scanner.pause(true)
          setQrStatus('جاري البحث عن العامل...')
          try {
            const res = await api.post('/qr-operations/resolve/', { qr_string: decodedText })
            if (res.data?.employee_id) {
              const currentTeam = Array.isArray(form.team) ? [...form.team] : []
              const empId = Number(res.data.employee_id)
              if (!currentTeam.includes(empId)) {
                currentTeam.push(empId)
                updateField('team', currentTeam)
              }
              setQrStatus(`✅ تم إضافة: ${res.data.employee_name || decodedText}`)
            } else {
              setQrStatus('⚠️ QR غير مرتبط بعامل')
            }
          } catch {
            setQrStatus('⚠️ تعذر التعرف على الكود')
          }
          setTimeout(() => {
            try {
              scanner.resume()
            } catch {
              /* scanner may be stopped */
            }
          }, 1500)
        },
      )
    } catch {
      setQrStatus('⚠️ تعذر تشغيل الكاميرا أو html5-qrcode غير متوفر')
      setQrScanActive(false)
    }
  }, [qrScanActive, form.team, updateField])

  const normalizedTeam = useMemo(
    () => (Array.isArray(form.team) ? form.team.map((id) => Number(id)).filter(Boolean) : []),
    [form.team],
  )

  useEffect(() => {
    const farmId = Number(form.farm)
    const surrah = Number(form.surrah_count)
    const mode = form.labor_entry_mode || 'REGISTERED'
    const workers = Number(form.casual_workers_count || 0)

    const hasRegisteredInput = mode === 'REGISTERED' && normalizedTeam.length > 0
    const hasCasualInput = mode === 'CASUAL_BATCH' && workers > 0

    const shouldFetch =
      Boolean(farmId) &&
      Number.isFinite(surrah) &&
      surrah > 0 &&
      (hasRegisteredInput || hasCasualInput)

    if (!shouldFetch) {
      setEstimate(null)
      setEstimateError('')
      return
    }

    const payload = {
      farm_id: farmId,
      labor_entry_mode: mode,
      surrah_count: String(form.surrah_count),
      period_hours: '8.0000',
    }

    if (mode === 'CASUAL_BATCH') {
      payload.workers_count = workers
    } else {
      payload.employee_ids = normalizedTeam
    }

    const timeout = setTimeout(async () => {
      try {
        setLoadingEstimate(true)
        setEstimateError('')
        const response = await LaborEstimates.preview(payload)
        setEstimate(response?.data || null)
      } catch (error) {
        setEstimate(null)
        const errMsg = extractApiError(error, 'تعذر حساب التقدير الآن.')
        setEstimateError(errMsg)
      } finally {
        setLoadingEstimate(false)
      }
    }, 350)

    return () => clearTimeout(timeout)
  }, [
    form.farm,
    form.surrah_count,
    form.casual_workers_count,
    form.labor_entry_mode,
    normalizedTeam,
  ])

  const formatDecimal = (value) => {
    const numeric = Number(value)
    if (!Number.isFinite(numeric)) return '0.00'
    return numeric.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
  }

  const laborEnabled = taskContext?.enabledCards?.labor !== false
  const laborPolicy = taskContext?.laborPolicy || {
    registeredAllowed: true,
    casualBatchAllowed: true,
    surrahRequired: laborEnabled,
  }

  useEffect(() => {
    if (!laborEnabled) return
    if (form.labor_entry_mode === 'CASUAL_BATCH' && !laborPolicy.casualBatchAllowed) {
      updateField('labor_entry_mode', laborPolicy.registeredAllowed ? 'REGISTERED' : '')
      return
    }
    if (form.labor_entry_mode !== 'CASUAL_BATCH' && !laborPolicy.registeredAllowed) {
      updateField('labor_entry_mode', laborPolicy.casualBatchAllowed ? 'CASUAL_BATCH' : '')
    }
  }, [
    form.labor_entry_mode,
    laborEnabled,
    laborPolicy.casualBatchAllowed,
    laborPolicy.registeredAllowed,
    updateField,
  ])

  if (!laborEnabled) {
    return (
      <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
          <div className="flex items-center gap-3">
            <span className="text-xl">🧾</span>
            <div>
              <h3 className="font-bold">هذه المهمة لا تتطلب بطاقة عمالة مستقلة</h3>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                سيبقى التنفيذ اليومي يعمل بالحقول الفنية المطلوبة فقط وفق عقد المهمة الذكي.
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-lg border border-gray-100 dark:border-slate-700 relative overflow-hidden group transition-all hover:shadow-xl">
        <div className="absolute top-0 right-0 w-1 h-full bg-gradient-to-b from-emerald-500 to-teal-400 opacity-70" />

        <h3 className="text-xl font-bold text-gray-800 dark:text-white mb-6 flex items-center gap-3">
          <span className="bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 w-10 h-10 rounded-xl flex items-center justify-center text-lg shadow-sm">
            👥
          </span>
          <span className="flex flex-col">
            <span>الموارد البشرية</span>
            <span className="text-xs font-normal text-gray-400">تخصيص العمالة والفترات</span>
          </span>
        </h3>

        <div className="space-y-8">
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300">
              نمط إدخال العمالة
            </label>
            <select
              data-testid="labor-entry-mode-select"
              value={form.labor_entry_mode || 'REGISTERED'}
              onChange={(e) => updateField('labor_entry_mode', e.target.value)}
              className="w-full md:w-80 p-2.5 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
            >
              {laborPolicy.registeredAllowed && (
                <option value="REGISTERED">عمالة مسجلة (موظفون)</option>
              )}
              {laborPolicy.casualBatchAllowed && (
                <option value="CASUAL_BATCH">عمالة يومية غير مسجلة (دفعة)</option>
              )}
            </select>
            <p className="text-xs text-gray-500 dark:text-slate-400">
              {laborPolicy.registeredAllowed && laborPolicy.casualBatchAllowed
                ? 'يمكن استخدام العمالة المسجلة أو الدفعات اليومية حسب واقع التنفيذ.'
                : laborPolicy.registeredAllowed
                  ? 'هذه المهمة تعتمد عمالة مسجلة فقط.'
                  : 'هذه المهمة تعتمد دفعة عمالة يومية فقط.'}
            </p>
          </div>

          <div
            className={`space-y-3 ${form.labor_entry_mode === 'CASUAL_BATCH' ? 'opacity-50' : ''}`}
          >
            <label className="block text-sm font-semibold text-gray-700 dark:text-slate-300">
              فريق العمل
            </label>
            <EmployeeSelect
              dataTestId="team-input"
              selectedIds={form.team || []}
              onChange={(ids) => updateField('team', ids)}
              farmId={form.farm}
              error={errors.team}
              disabled={form.labor_entry_mode === 'CASUAL_BATCH'}
            />

            {/* [AGRI-GUARDIAN] Optional QR Scan — مسح اختياري لإضافة عمال */}
            {form.labor_entry_mode !== 'CASUAL_BATCH' && (
              <div className="mt-3 space-y-2">
                <button
                  type="button"
                  data-testid="qr-scan-employee-btn"
                  onClick={handleQrScan}
                  className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    qrScanActive
                      ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 hover:bg-red-200'
                      : 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100'
                  }`}
                >
                  <span>{qrScanActive ? '⏹️' : '📷'}</span>
                  {qrScanActive ? 'إيقاف المسح' : 'مسح QR عامل (اختياري)'}
                </button>
                {qrStatus && (
                  <p className="text-xs text-gray-600 dark:text-slate-400">{qrStatus}</p>
                )}
                {qrScanActive && (
                  <div
                    id="qr-employee-reader"
                    className="w-full max-w-xs rounded-lg overflow-hidden border border-indigo-200 dark:border-indigo-800"
                  />
                )}
              </div>
            )}
          </div>

          {form.labor_entry_mode === 'CASUAL_BATCH' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
                  عدد العمالة اليومية
                </label>
                <input
                  data-testid="casual-workers-count-input"
                  type="number"
                  min="0"
                  step="1"
                  value={form.casual_workers_count || ''}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value)
                    if (val < 0) return
                    updateField('casual_workers_count', e.target.value)
                  }}
                  className={`w-full p-3 rounded-xl border ${errors.casual_workers_count ? 'border-red-500 bg-red-50 dark:bg-red-900/10' : 'border-gray-200 dark:border-slate-600'} bg-gray-50 dark:bg-slate-700/50 text-gray-900 dark:text-white`}
                  placeholder="مثال: 25"
                />
                {errors.casual_workers_count && (
                  <p className="text-xs text-red-500 dark:text-red-400">
                    {errors.casual_workers_count}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
                  وصف الدفعة (اختياري)
                </label>
                <input
                  data-testid="casual-batch-label-input"
                  type="text"
                  value={form.casual_batch_label || ''}
                  onChange={(e) => updateField('casual_batch_label', e.target.value)}
                  className="w-full p-3 rounded-xl border border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700/50 text-gray-900 dark:text-white"
                  placeholder="مثال: عمال مقاولة جني"
                />
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-8">
            {/* [Omega-2028] Costing Mode Toggle */}
            <div className="flex items-center gap-4 bg-slate-50 dark:bg-slate-900/40 p-4 rounded-xl border border-slate-100 dark:border-slate-700">
               <div className="flex-1">
                 <h4 className="text-sm font-bold text-gray-800 dark:text-white">نمط احتساب التكلفة</h4>
                 <p className="text-xs text-gray-500">اختر بين نظام الصرة التقليدي أو الحساب الدقيق بالساعة</p>
               </div>
               <div className="flex bg-white dark:bg-slate-800 p-1 rounded-lg border border-gray-200 dark:border-slate-700">
                 <button
                   type="button"
                   onClick={() => updateField('is_hourly', false)}
                   className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${!form.is_hourly ? 'bg-emerald-500 text-white shadow-md' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}`}
                 >
                   نظام الصرة
                 </button>
                 <button
                   type="button"
                   onClick={() => updateField('is_hourly', true)}
                   className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${form.is_hourly ? 'bg-indigo-500 text-white shadow-md' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}`}
                 >
                   نظام الساعة
                 </button>
               </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {!form.is_hourly ? (
                <div className="space-y-2 group/field">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 group-hover/field:text-emerald-600 transition-colors">
                    عدد فترات العمل (وردية)
                  </label>
                  <div className="relative">
                    <input
                      data-testid="labor-surra-input"
                      type="number"
                      min="0"
                      step="0.25"
                      value={form.surrah_count}
                      onChange={(e) => updateField('surrah_count', e.target.value)}
                      placeholder="1.0"
                      className={`w-full p-3 pl-12 rounded-xl border ${errors.surrah_count ? 'border-red-500 bg-red-50 dark:bg-red-900/10' : 'border-gray-200 dark:border-slate-600'} bg-gray-50 dark:bg-slate-700/50 text-gray-900 dark:text-white focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none transition-all`}
                    />
                    <span className="absolute left-4 top-3.5 text-gray-400 text-sm font-medium">
                      صرة
                    </span>
                  </div>
                </div>
              ) : (
                <>
                  <div className="space-y-2 group/field">
                    <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 group-hover/field:text-indigo-600 transition-colors">
                      عدد الساعات المنجزة (للفرد)
                    </label>
                    <div className="relative">
                      <input
                        data-testid="labor-hours-input"
                        type="number"
                        min="0"
                        step="0.5"
                        value={form.hours_worked}
                        onChange={(e) => updateField('hours_worked', e.target.value)}
                        placeholder="8"
                        className="w-full p-3 pl-12 rounded-xl border border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700/50 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
                      />
                      <span className="absolute left-4 top-3.5 text-gray-400 text-sm font-medium">
                        ساعة
                      </span>
                    </div>
                  </div>
                  <div className="space-y-2 group/field">
                    <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 group-hover/field:text-indigo-600 transition-colors">
                      سعر الساعة (ريال)
                    </label>
                    <div className="relative">
                      <input
                        data-testid="labor-rate-input"
                        type="number"
                        min="0"
                        value={form.hourly_rate}
                        onChange={(e) => updateField('hourly_rate', e.target.value)}
                        placeholder="500"
                        className="w-full p-3 pl-12 rounded-xl border border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700/50 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
                      />
                      <span className="absolute left-4 top-3.5 text-gray-400 text-sm font-medium">
                        ر.ي
                      </span>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* [Agri-Guardian] Direct Cost Entry Override */}
            <div className="space-y-2 pt-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
                المبلغ الميداني المباشر (اختياري)
              </label>
              <div className="relative">
                <input
                  data-testid="labor-fixed-cost-input"
                  type="number"
                  min="0"
                  value={form.fixed_wage_cost || ''}
                  onChange={(e) => updateField('fixed_wage_cost', e.target.value)}
                  placeholder="مثال: 5000"
                  className="w-full md:w-1/2 p-3 pl-12 rounded-xl border border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700/50 text-gray-900 dark:text-white focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 outline-none transition-all"
                />
                <span className="absolute left-4 top-3.5 text-gray-400 text-sm font-medium">
                  ر.ي
                </span>
              </div>
              <p className="text-[10px] text-amber-600 dark:text-amber-400 font-medium font-bold">
                * عند إدخال مبلغ هنا، سيتم اعتماده كتكلفة نهائية للعمالة وتجاهل حسابات الصرة/الساعة.
              </p>

              {/* [AGRI-GUARDIAN] Intelligent Variance Feedback */}
              {form.fixed_wage_cost && estimate?.estimated_labor_cost > 0 && (
                <div className="mt-2 p-3 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-800 animate-in fade-in duration-300">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">التكلفة المعيارية المقدرة:</span>
                    <span className="font-mono font-bold text-gray-700 dark:text-gray-300">
                      {formatDecimal(estimate.estimated_labor_cost)} ر.ي
                    </span>
                  </div>
                  {Math.abs(Number(form.fixed_wage_cost) - estimate.estimated_labor_cost) / estimate.estimated_labor_cost > 0.1 && (
                    <div className="mt-2 flex items-center gap-2 text-[11px] text-amber-600 dark:text-amber-400 font-bold bg-amber-500/5 p-2 rounded-md">
                      <span>⚠️</span>
                      <span>تنبيه: المبلغ المدخل يختلف بنسبة كبيرة عن التكلفة المعيارية المتوقعة.</span>
                    </div>
                  )}
                  {Number(form.fixed_wage_cost) > estimate.estimated_labor_cost * 5 && (
                    <div className="mt-1 flex items-center gap-2 text-[11px] text-red-600 dark:text-red-400 font-bold bg-red-500/5 p-2 rounded-md transition-all">
                      <span>🛑</span>
                      <span>تحذير حرج: المبلغ مرتفع بشكل غير منطقي (أكثر من 5 أضعاف). قد يتم رفض الحفظ.</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* [Omega-2028] Daily Achievement (Ingaz) Section */}
            <div className="pt-4 border-t border-dashed border-gray-200 dark:border-slate-700">
              <h4 className="text-sm font-bold text-gray-700 dark:text-slate-300 mb-4 flex items-center gap-2">
                <span>🏆</span> الإنجاز اليومي والقدرة الإنتاجية
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
                    كمية الإنجاز
                  </label>
                  <input
                    data-testid="achievement-qty-input"
                    type="number"
                    min="0"
                    value={form.achievement_qty}
                    onChange={(e) => updateField('achievement_qty', e.target.value)}
                    placeholder="مثال: 100"
                    className="w-full p-3 rounded-xl border border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700/50 text-gray-900 dark:text-white"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">
                    وحدة الإنجاز
                  </label>
                  <input
                    data-testid="achievement-uom-input"
                    type="text"
                    value={form.achievement_uom}
                    onChange={(e) => updateField('achievement_uom', e.target.value)}
                    placeholder="شجرة، كرتون، كيلومتر..."
                    className="w-full p-3 rounded-xl border border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700/50 text-gray-900 dark:text-white"
                  />
                </div>
              </div>
            </div>
          </div>


          {(loadingEstimate || estimate || estimateError) && (
            <div
              data-testid="labor-estimate-panel"
              className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/70 dark:bg-emerald-900/20 p-4 space-y-2"
            >
              <div className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">
                ملخص تقدير العمالة (مرجعي قبل الحفظ)
              </div>
              {loadingEstimate && (
                <div className="text-xs text-gray-600 dark:text-slate-300">
                  جاري حساب التقدير...
                </div>
              )}
              {!loadingEstimate && estimate && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                  <div>
                    <div className="text-xs text-gray-500 dark:text-slate-400">ساعات/عامل</div>
                    <div
                      data-testid="equivalent-hours-per-worker"
                      className="font-semibold text-gray-900 dark:text-white"
                    >
                      {formatDecimal(estimate.equivalent_hours_per_worker)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 dark:text-slate-400">
                      إجمالي الساعات المكافئة
                    </div>
                    <div
                      data-testid="equivalent-hours-total"
                      className="font-semibold text-gray-900 dark:text-white"
                    >
                      {formatDecimal(estimate.equivalent_hours_total)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 dark:text-slate-400">
                      تكلفة عمالة تقديرية
                    </div>
                    <div
                      data-testid="estimated-labor-cost"
                      className="font-semibold text-gray-900 dark:text-white"
                    >
                      {formatDecimal(estimate.estimated_labor_cost)} {estimate.currency || 'YER'}
                    </div>
                  </div>
                </div>
              )}
              {!loadingEstimate && estimateError && (
                <div className="text-xs text-red-600 dark:text-red-400">{estimateError}</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

DailyLogResourcesInner.propTypes = {
  form: PropTypes.object.isRequired,
  updateField: PropTypes.func.isRequired,
  lookups: PropTypes.shape({
    assets: PropTypes.array,
    materials: PropTypes.array,
    wells: PropTypes.array,
  }),
  errors: PropTypes.object,
  taskContext: PropTypes.object,
}

export const DailyLogResources = memo(DailyLogResourcesInner)
