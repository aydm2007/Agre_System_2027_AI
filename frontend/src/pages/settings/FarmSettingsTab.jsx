import { useCallback, useEffect, useState } from 'react'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'

function SectionCard({ title, description, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-700">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">{title}</h3>
        {description && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>}
      </div>
      <div className="p-5">{children}</div>
    </section>
  )
}

function ToggleField({ label, description, checked, onChange, disabled }) {
  return (
    <label className={`flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 p-4 transition hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-700/50 ${disabled ? 'opacity-60 cursor-not-allowed' : ''}`}>
      <div className="flex h-5 items-center">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary dark:border-slate-600 dark:bg-slate-700"
        />
      </div>
      <div className="flex-1">
        <div className="text-sm font-medium text-slate-900 dark:text-white">{label}</div>
        <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{description}</div>
      </div>
    </label>
  )
}

function SelectField({ label, description, value, options, onChange, disabled }) {
  return (
    <div className={`rounded-lg border border-slate-200 p-4 dark:border-slate-700 ${disabled ? 'opacity-60' : ''}`}>
      <label className="mb-2 block text-sm font-medium text-slate-900 dark:text-white">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary dark:border-slate-600 dark:bg-slate-900 dark:text-white"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">{description}</div>
    </div>
  )
}

function NumberField({ label, description, value, onChange, disabled, min = 0 }) {
  return (
    <div className={`rounded-lg border border-slate-200 p-4 dark:border-slate-700 ${disabled ? 'opacity-60' : ''}`}>
      <label className="mb-2 block text-sm font-medium text-slate-900 dark:text-white">{label}</label>
      <input
        type="number"
        min={min}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        disabled={disabled}
        className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary dark:border-slate-600 dark:bg-slate-900 dark:text-white"
      />
      <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">{description}</div>
    </div>
  )
}

export default function FarmSettingsTab({ selectedFarmId, hasFarms }) {
  const { isSuperuser, isAdmin, hasPermission } = useAuth()
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [record, setRecord] = useState(null)
  const [formData, setFormData] = useState({})
  const [originalData, setOriginalData] = useState({})
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const canEdit = isSuperuser || isAdmin || hasPermission('change_farmsettings')

  const loadSettings = useCallback(async () => {
    if (!selectedFarmId) return
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get(`/farm-settings/?farm=${selectedFarmId}`)
      const settingsRow = data.results[0]
      if (settingsRow) {
        setRecord(settingsRow)
        const initialForm = {
          mode: settingsRow.mode,
          approval_profile: settingsRow.approval_profile,
          cost_visibility: settingsRow.cost_visibility,
          treasury_visibility: settingsRow.treasury_visibility,
          fixed_asset_mode: settingsRow.fixed_asset_mode,
          contract_mode: settingsRow.contract_mode,
          variance_behavior: settingsRow.variance_behavior,
          enable_zakat: settingsRow.enable_zakat,
          enable_depreciation: settingsRow.enable_depreciation,
          enable_sharecropping: settingsRow.enable_sharecropping,
          enable_petty_cash: settingsRow.enable_petty_cash,
          remote_site: settingsRow.remote_site,
          single_finance_officer_allowed: settingsRow.single_finance_officer_allowed,
          mandatory_attachment_for_cash: settingsRow.mandatory_attachment_for_cash,
          weekly_remote_review_required: settingsRow.weekly_remote_review_required,
          attachment_require_clean_scan_for_strict: settingsRow.attachment_require_clean_scan_for_strict,
          allow_overlapping_crop_plans: settingsRow.allow_overlapping_crop_plans,
          allow_multi_location_activities: settingsRow.allow_multi_location_activities,
          allow_cross_plan_activities: settingsRow.allow_cross_plan_activities,
          allow_creator_self_variance_approval: settingsRow.allow_creator_self_variance_approval,
          show_daily_log_smart_card: settingsRow.show_daily_log_smart_card,
          show_finance_in_simple: settingsRow.show_finance_in_simple || false,
          show_stock_in_simple: settingsRow.show_stock_in_simple || false,
          show_employees_in_simple: settingsRow.show_employees_in_simple || false,
          show_advanced_reports: settingsRow.show_advanced_reports || false,
          enable_tree_gis_zoning: settingsRow.enable_tree_gis_zoning || false,
          enable_bulk_cohort_transition: settingsRow.enable_bulk_cohort_transition || false,
          enable_biocost_depreciation_predictor: settingsRow.enable_biocost_depreciation_predictor || false,
          enable_timed_plan_compliance: settingsRow.enable_timed_plan_compliance || false,
          offline_cache_retention_days: settingsRow.offline_cache_retention_days || 7,
          synced_draft_retention_days: settingsRow.synced_draft_retention_days || 3,
          dead_letter_retention_days: settingsRow.dead_letter_retention_days || 14,
        }
        setFormData(initialForm)
        setOriginalData(initialForm)
      } else {
        setRecord(null)
      }
    } catch (err) {
      console.error('Failed to load settings', err)
      setError('تعذر تحميل إعدادات المزرعة.')
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId])

  useEffect(() => {
    loadSettings()
  }, [loadSettings])

  const hasChanges = JSON.stringify(formData) !== JSON.stringify(originalData)

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!record?.id) {
      setError('خطأ داخلي: لا يوجد ID لسجل الإعدادات في الذاكرة.')
      return
    }

    // Show warnings for critical changes
    if (formData.mode === 'STRICT' && originalData.mode !== 'STRICT') {
      const confirmMsg =
        'تحذير: سيؤدي تحويل المزرعة للمود الصارم (STRICT) إلى حجر القيود قيد الانتظار وتطبيق حوكمة مالية (ERP) صارمة. هل أنت متأكد من جاهزية الطاقم المالي للمزرعة؟'
      if (!window.confirm(confirmMsg)) return
    }
    if (formData.cost_visibility === 'full_amounts' && originalData.cost_visibility !== 'full_amounts') {
      const confirmMsg = 'تنبيه: سيؤدي هذا الخيار إلى كشف المبالغ الكلية للتكاليف على مستوى المهام الميدانية. استمر؟'
      if (!window.confirm(confirmMsg)) return
    }

    setSubmitting(true)
    setError('')
    setMessage('')
    try {
      const { data } = await api.patch(`/farm-settings/${record.id}/`, formData)
      setMessage('تم حفظ إعدادات المزرعة بنجاح واستيعابها في نظام الحوكمة.')
      setRecord(data)
      setOriginalData(formData)
    } catch (err) {
      console.error('Failed to save settings', err)
      const data = err?.response?.data
      let errValue = data?.detail || data?.non_field_errors?.[0] || data?.message
      
      if (!errValue && data && typeof data === 'object') {
        const messages = Object.values(data).flat().filter(item => typeof item === 'string')
        if (messages.length > 0) {
          errValue = messages.join(' | ')
        }
      }
      
      errValue = errValue || 'تعذر حفظ إعدادات المزرعة. راجع رسائل التحقق.'
      if (typeof errValue === 'object') {
        errValue = errValue.message || errValue.detail || JSON.stringify(errValue)
      }
      setError(String(errValue))
    } finally {
      setSubmitting(false)
    }
  }

  if (!hasFarms) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-500 dark:border-slate-600 dark:bg-slate-900/30 dark:text-slate-400">
        حدد مزرعة أولاً حتى تظهر واجهة العرض.
      </div>
    )
  }

  if (loading) {
    return <div className="text-sm text-slate-700 dark:text-slate-300">جارٍ تحميل الإعدادات...</div>
  }

  if (!record) {
    return <div className="text-sm text-slate-700 dark:text-slate-300">لم يتم تكوين إعدادات لهذه المزرعة بعد. تواصل مع الدعم الفني أو ارجع لمنصة الحوكمة.</div>
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">إعدادات المزرعة</h2>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            أدوات ضبط وموازنة القيود التشغيلية والمالية. احرص على القراءة الجيدة لما يترتب عند إجراء تحديثات مركزية.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={loadSettings}
            disabled={submitting}
            className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700/50"
          >
            إلغاء التغييرات
          </button>
          <button
            type="submit"
            disabled={!canEdit || submitting || !hasChanges}
            className={`rounded-xl px-5 py-2 text-sm font-medium text-white shadow transition-all ${!canEdit ? 'bg-slate-400 cursor-not-allowed' : 'bg-primary hover:bg-primary/90 disabled:opacity-60'}`}
          >
            {!canEdit ? 'لا تملك صلاحية التعديل' : submitting ? 'جارٍ الحفظ...' : 'حفظ التعديلات'}
          </button>
        </div>
      </div>

      {message && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-900/20 dark:text-emerald-300">
          {message}
        </div>
      )}
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-900/20 dark:text-rose-300">
          {error}
        </div>
      )}
      <div
        data-testid="simple-compatibility-note"
        className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-200"
      >
        حقول الإظهار التوافقية في SIMPLE هي <strong>compatibility-only</strong> و<strong>display-only</strong> ومعناها
        <strong> not authoring authority</strong>. هذه الحقول لا تفتح mutation routes ولا STRICT workflows.
      </div>

      {/* 1. التوجيه الاستراتيجي */}
      <SectionCard title="التوجيه الاستراتيجي وملف الحوكمة" description="وضع النظام وطبيعة القيود المطبقة.">
        <div className="grid gap-4 md:grid-cols-2">
          <SelectField
            label="وضع النظام (Mode)"
            description="التحكم بإجبارية القيود المحاسبية وتتبع الانحراف."
            value={formData.mode}
            onChange={(val) => handleChange('mode', val)}
            disabled={!canEdit}
            options={[
              { value: 'SIMPLE', label: 'SIMPLE - مبسط (فني/رقابي فقط)' },
              { value: 'STRICT', label: 'STRICT - صارم (ERP متكامل)' },
            ]}
          />
          <SelectField
            label="سلوك الانحراف (Variance Behavior)"
            description="الإجراء المتخذ عند تجاوز الميزانية المسموحة للمهمة."
            value={formData.variance_behavior}
            onChange={(val) => handleChange('variance_behavior', val)}
            disabled={!canEdit}
            options={[
              { value: 'warn', label: 'تنبيه (يسمح بالحفظ ويسجل إنذاراً)' },
              { value: 'block', label: 'منع (يقوم برفض العملية)' },
              { value: 'quarantine', label: 'حجر (العملية تنتظر مراجعة القطاع)' },
            ]}
          />
          <SelectField
            label="ملف الاعتماد (Approval Profile)"
            description="درجة وتعدد طبقات الاعتماد داخل دورات العمل."
            value={formData.approval_profile}
            onChange={(val) => handleChange('approval_profile', val)}
            disabled={!canEdit}
            options={[
              { value: 'basic', label: 'أساسي (موافقات مبسطة)' },
              { value: 'tiered', label: 'متدرج (حسب شريحة المزرعة ومركزها)' },
              { value: 'strict_finance', label: 'مالي صارم (مراجعات متعددة)' },
            ]}
          />
        </div>
      </SectionCard>

      {/* 2. الرؤية والشفافية */}
      <SectionCard title="رؤية التكاليف والخزينة" description="حدد من يستطيع الاطلاع على المبالغ والتكاليف الجارية.">
        <div className="grid gap-4 md:grid-cols-2">
          <ToggleField
            label="رؤية مالية توافقية في SIMPLE"
            description="خيار compatibility-only وdisplay-only، وليس not authoring authority. لا يفتح mutation routes ولا STRICT workflows."
            checked={formData.show_finance_in_simple}
            onChange={(val) => handleChange('show_finance_in_simple', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="رؤية مخزون توافقية في SIMPLE"
            description="خيار compatibility-only وdisplay-only، وليس not authoring authority. لا يفتح governed stock writes ولا STRICT workflows."
            checked={formData.show_stock_in_simple}
            onChange={(val) => handleChange('show_stock_in_simple', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="رؤية الموظفين والرواتب التوافقية في SIMPLE"
            description="خيار compatibility-only وdisplay-only، وليس not authoring authority. لا يفتح payroll authoring ولا routes حاكمة."
            checked={formData.show_employees_in_simple}
            onChange={(val) => handleChange('show_employees_in_simple', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="التقارير المتقدمة في الواجهة المبسطة"
            description="إتاحة تصدير التقارير التفصيلية بصيغة XLSX بالإضافة للملخصات، حتى في واجهة SIMPLE."
            checked={formData.show_advanced_reports}
            onChange={(val) => handleChange('show_advanced_reports', val)}
            disabled={!canEdit}
          />
          <SelectField
            label="رؤية التكلفة (Cost Visibility)"
            description="العرض في شاشات الحقل والزراعة البسيطة"
            value={formData.cost_visibility}
            onChange={(val) => handleChange('cost_visibility', val)}
            disabled={!canEdit}
            options={[
              { value: 'ratios_only', label: 'نسب مئوية فقط (معدل استهلاك)' },
              { value: 'summarized_amounts', label: 'مبالغ ملخصة مبسطة' },
              { value: 'full_amounts', label: 'مبالغ كاملة ومكشوفة' },
            ]}
          />
          <SelectField
            label="رؤية الخزينة (Treasury Visibility)"
            description="توفر سجلات الخزينة والمقبوضات للمستخدمين."
            value={formData.treasury_visibility}
            onChange={(val) => handleChange('treasury_visibility', val)}
            disabled={!canEdit}
            options={[
              { value: 'hidden', label: 'مخفي' },
              { value: 'finance_only', label: 'للفرق المالية فقط' },
              { value: 'visible', label: 'ظاهر لمديري النظام والأرصدة' },
            ]}
          />
        </div>
      </SectionCard>

      {/* 3. الدورة المحاسبية والأصول */}
      <SectionCard title="الأصول والوحدات المحاسبية الإضافية" description="تفعيل أو تعطيل حسابات الإهلاك والزكاة والأصول الرأسمالية.">
        <div className="mb-5 grid gap-4 md:grid-cols-2">
          <SelectField
            label="دورة الأصول الثابتة (Fixed Asset Mode)"
            description="كيفية معاملة الأصول كالمنظومات الشمسية والآبار."
            value={formData.fixed_asset_mode}
            onChange={(val) => handleChange('fixed_asset_mode', val)}
            disabled={!canEdit}
            options={[
              { value: 'tracking_only', label: 'تتبع وصيانة فقط' },
              { value: 'full_capitalization', label: 'رسملة وتقييد محاسبي كامل' },
            ]}
          />
          <SelectField
            label="وضع العقود والشراكات (Contract Mode)"
            description="التعامل مع المقاولات، الشراكات العينية، والمستأجرين."
            value={formData.contract_mode}
            onChange={(val) => handleChange('contract_mode', val)}
            disabled={!canEdit}
            options={[
              { value: 'disabled', label: 'معطل' },
              { value: 'operational_only', label: 'تشغيلي فقط' },
              { value: 'full_erp', label: 'ERP كامل شامل التسويات' },
            ]}
          />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <ToggleField
            label="تفعيل الاستقطاع الآلي للزكاة"
            description="خصم حصيلة الزكاة آلياً عند انتهاء موسم الحصاد وفق الإرشادات."
            checked={formData.enable_zakat}
            onChange={(val) => handleChange('enable_zakat', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="تفعيل حسابات الإهلاك"
            description="رسملة المشاريع وحساب متبقي العمر الافتراضي آلياً بنهاية الفترة."
            checked={formData.enable_depreciation}
            onChange={(val) => handleChange('enable_depreciation', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="تفعيل دورة العهد النقدية (Petty Cash)"
            description="صرف المبالغ تحت التسوية لمسؤولي الصرف واستعاضتها وتصفيتها."
            checked={formData.enable_petty_cash}
            onChange={(val) => handleChange('enable_petty_cash', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="إلزام الإرفاق لصرفيات النقد (Cash)"
            description="شرط أمني: منع تسوية العهد النقدية دون إرفاق فاتورة مصدقة."
            checked={formData.mandatory_attachment_for_cash}
            onChange={(val) => handleChange('mandatory_attachment_for_cash', val)}
            disabled={!canEdit}
          />
        </div>
      </SectionCard>

      {/* 4. التحكم والمرونة في التنفيذ الزراعي */}
      <SectionCard title="التنفيذ الميداني وسجلات الأمان" description="تخفيف صرامة إدخال النشاطات المزرعية وفق ظروف كل بيئة.">
        <div className="grid gap-4 md:grid-cols-2">
          <ToggleField
            label="إظهار الكرت الذكي لليوميات"
            description="إدراج سياق واجهة العرض التفاعلية الذكية لكل مهمة."
            checked={formData.show_daily_log_smart_card}
            onChange={(val) => handleChange('show_daily_log_smart_card', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="موقع جغرافي بعيد (Remote Site)"
            description="تفهم ضوابط الاتصال وبطء المزامنة والتكفل بمراجعات أسبوعية بديلة للمعاينات."
            checked={formData.remote_site}
            onChange={(val) => handleChange('remote_site', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="موظف مالي وحيد مسموح به"
            description="استثناء للمزارع الناشئة يسمح لشخص واحد بإدارة حساباتها تحت مراجعة قطاعية دورية."
            checked={formData.single_finance_officer_allowed}
            onChange={(val) => handleChange('single_finance_officer_allowed', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="اختيار مواقع أشجار متعددة (Multi-Location)"
            description="تحديد عدة مربعات/أحواض في السجل اليومي بدل إنشاء سجل منفرد لكل مربع."
            checked={formData.allow_multi_location_activities}
            onChange={(val) => handleChange('allow_multi_location_activities', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="سماحيات الخطة المتقاطعة (Cross-Plan)"
            description="تفعيل تغطية التكاليف والموارد على أكثر من خطة زراعية مسجلة في نفس الوقت."
            checked={formData.allow_cross_plan_activities}
            onChange={(val) => handleChange('allow_cross_plan_activities', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="سماح لمنشئ السجل باعتماد التباين المحدود"
            description="منح الثقة استثنائياً لمقاول/منشئ التقرير لاعتماد زيادة طفيفة للمبالغ وفقا للسقف المتاح."
            checked={formData.allow_creator_self_variance_approval}
            onChange={(val) => handleChange('allow_creator_self_variance_approval', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="تفعيل التحقق الزمني (Cronological Compliance)"
            description="إلزام الأنشطة بتسلسل زمني محكم وتنبيه الإدارة عند التأخير أو الزحف الزمني."
            checked={formData.enable_timed_plan_compliance}
            onChange={(val) => handleChange('enable_timed_plan_compliance', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="إظهار التقارير المتقدمة (لوحة البيانات تفصيلية)"
            description="تفعيل التصدير بصيغة XLSX وعرض التقارير التحليلية المتقدمة في شاشة التقارير."
            checked={formData.show_advanced_reports}
            onChange={(val) => handleChange('show_advanced_reports', val)}
            disabled={!canEdit}
          />
        </div>
      </SectionCard>

      {/* 5. الأعمال المعمرة والتحليل الحيوي */}
      <SectionCard title="الأعمال المعمرة والتحليل الحيوي (Phase 10)" description="تفعيل أدوات المراقبة المكانية، التحكم الجماعي، وتحليل التكلفة الحيوية للأشجار المعمرة.">
        <div className="grid gap-4 md:grid-cols-2">
          <ToggleField
            label="تفعيل نظام المراقبة المكانية (Tree GIS Zoning)"
            description="عرض خريطة توزع حرارية (Heatmap) بدلاً من الجداول التقليدية في شاشة الجرد الشجري، مع إبراز مناطق التركيز والإصابات."
            checked={formData.enable_tree_gis_zoning}
            onChange={(val) => handleChange('enable_tree_gis_zoning', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="النقل المجمع للقطعان الجينية (Bulk Cohort Transition)"
            description="إتاحة تحديد ونقل حالات مئات الأشجار المعمرة معاً (مثال: من النمو إلى الإنتاج) بضغطة واحدة بحوكمة متكاملة."
            checked={formData.enable_bulk_cohort_transition}
            onChange={(val) => handleChange('enable_bulk_cohort_transition', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="مؤشر توقع الإهلاك والتكلفة الحيوية (Biocost Predictor)"
            description="تفعيل المولد الآلي لحساب توقع الإهلاك المالي وصافي القيمة الحيوية بناءً على معيار الزراعة (IAS 41)."
            checked={formData.enable_biocost_depreciation_predictor}
            onChange={(val) => handleChange('enable_biocost_depreciation_predictor', val)}
            disabled={!canEdit}
          />
        </div>
      </SectionCard>

      {/* 6. سياسة المزامنة والتنظيف */}
      <SectionCard title="سياسة المزامنة والتنظيف (Offline Policy)" description="إعدادات الحذف التلقائي للبيانات المحلية للحفاظ على أداء الجهاز.">
        <div className="grid gap-4 md:grid-cols-3">
          <NumberField
            label="احتفاظ بكاش البحث (أيام)"
            description="مدة بقاء سجلات الـ Lookup قبل التحديث أو المسح."
            value={formData.offline_cache_retention_days}
            onChange={(val) => handleChange('offline_cache_retention_days', val)}
            disabled={!canEdit}
          />
          <NumberField
            label="احتفاظ باليوميات المرفوعة (أيام)"
            description="مدة بقاء المسودات المكتملة والمرفوعة في ذاكرة الجهاز."
            value={formData.synced_draft_retention_days}
            onChange={(val) => handleChange('synced_draft_retention_days', val)}
            disabled={!canEdit}
          />
          <NumberField
            label="احتفاظ بالطلبات المتعثرة (أيام)"
            description="مدة بقاء الطلبات الفاشلة (Dead Letter) قبل الحذف النهائي."
            value={formData.dead_letter_retention_days}
            onChange={(val) => handleChange('dead_letter_retention_days', val)}
            disabled={!canEdit}
          />
        </div>

        {/* [AGRI-GUARDIAN Axis 20] Advanced Offline Governance */}
        <div className="mt-8 pt-6 border-t border-gray-100 dark:border-slate-800 grid gap-6 md:grid-cols-2">
          <ToggleField
            label="تنظيف ملفات المرفقات (Media Purge)"
            description="مسح الصور والوثائق المحلية فور نجاح مزامنتها لتحرير مساحة تخزين الجهاز."
            checked={formData.enable_offline_media_purge}
            onChange={(val) => handleChange('enable_offline_media_purge', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="سجل التنظيف المحلي (Audit Log)"
            description="تفعيل التوثيق المحلي لعمليات الحذف التلقائي للشفافية والمطابقة."
            checked={formData.enable_local_purge_audit}
            onChange={(val) => handleChange('enable_local_purge_audit', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="واجهة حل النزاعات اللحظية (Conflict UI)"
            description="إظهار أدوات الدمج والمفاضلة عند اكتشاف اختلاف بين النسخة المحلية والسيرفر."
            checked={formData.enable_offline_conflict_resolution}
            onChange={(val) => handleChange('enable_offline_conflict_resolution', val)}
            disabled={!canEdit}
          />
          <ToggleField
            label="التنبيهات الاستباقية للانحرافات (Predictive Alerts)"
            description="تحليل الجدول الزمني القادم وتنبيه الإدارة والمنفذ قبل وقوع التأخير."
            checked={formData.enable_predictive_alerts}
            onChange={(val) => handleChange('enable_predictive_alerts', val)}
            disabled={!canEdit}
          />
        </div>
      </SectionCard>
    </form>
  )
}
