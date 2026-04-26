import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { useOpsRuntime } from '../../contexts/OpsRuntimeContext.jsx'
import {
  formatBlocker,
  formatOpsKind,
  formatOpsReason,
  formatOpsSeverity,
  formatPolicyFieldLabel,
  formatPolicySection,
  formatPolicySource,
  formatPolicyValidationMessage,
  formatPolicyValue,
} from '../../utils/opsArabic'

const TAB_DEFS = [
  { key: 'effective', label: 'السياسة الفعالة' },
  { key: 'usage', label: 'استخدام الحزم' },
  { key: 'timeline', label: 'الخط الزمني للتفعيل' },
  { key: 'pressure', label: 'ضغط الاستثناءات' },
  { key: 'impact', label: 'أثر المزرعة' },
  { key: 'ops', label: 'الصحة التشغيلية' },
  { key: 'packages', label: 'حزم السياسات' },
  { key: 'versions', label: 'إصدارات السياسات' },
  { key: 'activations', label: 'طلبات التفعيل' },
  { key: 'exceptions', label: 'استثناءات المزرعة' },
  { key: 'delegations', label: 'التفويضات' },
  { key: 'profile', label: 'ملف الحوكمة' },
]

const TAB_GROUPS = [
  {
    key: 'reading',
    title: 'قراءة وتشخيص',
    description: 'السياسة الفعالة، أثر المزرعة، والصحة التشغيلية كطبقة قراءة ومراقبة.',
    scope: 'مزيج محلي وقطاعي',
    tabs: ['effective', 'usage', 'timeline', 'pressure', 'impact', 'ops'],
  },
  {
    key: 'central',
    title: 'إدارة مركزية',
    description: 'الحزم والإصدارات وطلبات التفعيل كقدرات قطاعية مركزية.',
    scope: 'مركزي / قطاعي',
    tabs: ['packages', 'versions', 'activations'],
  },
  {
    key: 'farm',
    title: 'حوكمة المزرعة',
    description: 'الاستثناءات، ملف الحوكمة، والتفويضات ضمن نطاق المزرعة.',
    scope: 'مزرعة',
    tabs: ['exceptions', 'delegations', 'profile'],
  },
]

const TAB_MAP = Object.fromEntries(TAB_DEFS.map((tab) => [tab.key, tab]))

const ACTION_HEADERS = (suffix) => ({
  headers: { 'X-Idempotency-Key': `gov-${suffix}-${Date.now()}` },
})

function prettyJson(value) {
  return JSON.stringify(value ?? {}, null, 2)
}

function parseJsonText(text, fallback = {}) {
  const trimmed = String(text || '').trim()
  if (!trimmed) return fallback
  return JSON.parse(trimmed)
}

function extractList(data) {
  return Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : []
}

function parseExplicitIds(text) {
  return Array.from(new Set(
    String(text || '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
      .map((item) => Number.parseInt(item, 10))
      .filter((item) => Number.isInteger(item) && item > 0),
  ))
}

function formatTimestamp(value) {
  if (!value) return 'غير محدد'
  try {
    return new Date(value).toLocaleString('ar-YE')
  } catch {
    return value
  }
}

function buildVersionForm(policyPackages, settingsRecord, payloadText = null) {
  return {
    id: null,
    package: policyPackages[0]?.id ? String(policyPackages[0].id) : '',
    version_label: '',
    payloadText: payloadText ?? prettyJson(settingsRecord?.effective_policy_payload || {}),
  }
}

function formatSeverityLabel(value) {
  return formatOpsSeverity(value)
}

function formatAlertKindLabel(value) {
  return formatOpsKind(value)
}

function statusTone(status) {
  const key = String(status || '').toLowerCase()
  if (['approved', 'applied', 'active'].includes(key)) return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
  if (['pending', 'draft'].includes(key)) return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
  if (['rejected', 'retired', 'expired', 'inactive'].includes(key)) return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
  return 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200'
}

function sourceTone(source) {
  const key = String(source || '').toLowerCase()
  if (key.includes('exception')) return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300'
  if (key.includes('binding')) return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
  if (key.includes('farm_settings')) return 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200'
  return 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
}

function SummaryCard({ title, value, hint }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {title}
      </div>
      <div className="mt-2 text-lg font-semibold text-slate-900 dark:text-white">{value}</div>
      {hint ? <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">{hint}</div> : null}
    </div>
  )
}

function SectionCard({ title, description, actions = null, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 dark:border-slate-700 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">{title}</h3>
          {description ? <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p> : null}
        </div>
        {actions}
      </div>
      <div className="p-5">{children}</div>
    </section>
  )
}

function EmptyState({ text }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-500 dark:border-slate-600 dark:bg-slate-900/30 dark:text-slate-400">
      {text}
    </div>
  )
}

function JsonBlock({ value }) {
  return (
    <pre className="max-h-96 overflow-auto rounded-xl bg-slate-950/95 p-4 text-xs leading-6 text-slate-100">
      {prettyJson(value)}
    </pre>
  )
}

function ScopeBadge({ scope, editable = false }) {
  const label = scope === 'farm' ? 'محلي' : scope === 'sector' ? 'قطاعي' : scope || 'محلي'
  const tone =
    scope === 'farm'
      ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
      : 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300'
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className={`rounded-full px-2 py-1 text-xs font-medium ${tone}`}>{label}</span>
      <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700 dark:bg-slate-700 dark:text-slate-200">
        {editable ? 'قابل للإجراء' : 'عرض فقط'}
      </span>
    </div>
  )
}

function RestrictionNotice({ text }) {
  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-900/20 dark:text-amber-300">
      {text}
    </div>
  )
}

function ActionButton({ label, onClick, disabled = false, disabledReason = '', tone = 'primary', className = '' }) {
  const tones = {
    primary: 'bg-primary text-white',
    neutral: 'border border-slate-300 text-slate-700 dark:border-slate-600 dark:text-slate-200',
    success: 'bg-green-700 text-white',
    danger: 'bg-red-700 text-white',
    dark: 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900',
    info: 'bg-sky-600 text-white',
    warning: 'bg-amber-600 text-white',
  }
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={disabled ? disabledReason : ''}
      className={`rounded-lg px-3 py-1.5 text-xs font-medium disabled:cursor-not-allowed disabled:opacity-60 ${tones[tone] || tones.primary} ${className}`}
    >
      {label}
    </button>
  )
}

function SectionToolbar({ searchValue, onSearchChange, searchPlaceholder, filterValue, onFilterChange, filterOptions = [] }) {
  return (
    <div className="flex flex-col gap-3 md:flex-row">
      <input
        value={searchValue}
        onChange={(event) => onSearchChange(event.target.value)}
        placeholder={searchPlaceholder}
        className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
      />
      {filterOptions.length ? (
        <select
          value={filterValue}
          onChange={(event) => onFilterChange(event.target.value)}
          className="rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
        >
          {filterOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : null}
    </div>
  )
}

function normalizeRequestError(err, fallback) {
  const status = Number(err?.response?.status || 0)
  if (status === 401 || status === 403) return 'هذا القسم يحتاج صلاحية حوكمة أو لم يُتح لهذا السياق.'
  if (status === 404) return 'الخدمة الخلفية لم تُتح هذا القسم لهذا السياق.'
  return err?.response?.data?.detail || err?.message || fallback
}

function canDo(item, capability, fallback = false) {
  if (typeof item?.capabilities?.[capability] === 'boolean') return item.capabilities[capability]
  return fallback
}

export default function GovernanceTab({ selectedFarmId, hasFarms }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { isAdmin, isSuperuser, hasPermission } = useAuth()
  const { topAlerts, canObserveOps, acknowledgeAlert, snoozeAlert, loadOutboxTrace, loadAttachmentTrace } = useOpsRuntime()
  const [activeTab, setActiveTab] = useState('effective')
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [sectionErrors, setSectionErrors] = useState({})
  const [settingsRecord, setSettingsRecord] = useState(null)
  const [policyPackages, setPolicyPackages] = useState([])
  const [policyVersions, setPolicyVersions] = useState([])
  const [activationRequests, setActivationRequests] = useState([])
  const [exceptionRequests, setExceptionRequests] = useState([])
  const [delegations, setDelegations] = useState([])
  const [governanceProfiles, setGovernanceProfiles] = useState([])
  const [farmMembers, setFarmMembers] = useState([])
  const [membershipMeta, setMembershipMeta] = useState({})
  const [delegationMeta, setDelegationMeta] = useState({})
  const [delegationRoles, setDelegationRoles] = useState([])
  const [delegateSearchTerm, setDelegateSearchTerm] = useState('')
  const [delegateOptions, setDelegateOptions] = useState([])
  const [packageUsage, setPackageUsage] = useState({ packages: [], summary: {} })
  const [activationTimeline, setActivationTimeline] = useState({ counts_by_status: {}, maker_checker: {}, latest_requests: [], latest_events: [] })
  const [exceptionPressure, setExceptionPressure] = useState({ open_by_farm: [], open_by_field_family: {}, forbidden_field_rejections: 0, expiring_soon: [] })
  const [farmImpact, setFarmImpact] = useState(null)
  const [operationalHealth, setOperationalHealth] = useState({ release: {}, releaseDetail: {}, outbox: {}, outboxDetail: {}, attachment: {}, attachmentDetail: {}, runtime: {}, farmOps: {} })
  const [packageFilter, setPackageFilter] = useState('all')
  const [packageSearch, setPackageSearch] = useState('')
  const [versionFilter, setVersionFilter] = useState('all')
  const [versionSearch, setVersionSearch] = useState('')
  const [activationFilter, setActivationFilter] = useState('all')
  const [activationSearch, setActivationSearch] = useState('')
  const [exceptionFilter, setExceptionFilter] = useState('all')
  const [exceptionSearch, setExceptionSearch] = useState('')
  const [delegationFilter, setDelegationFilter] = useState('all')
  const [delegationSearch, setDelegationSearch] = useState('')
  const [packageForm, setPackageForm] = useState({ id: null, name: '', slug: '', description: '', is_active: true })
  const [versionForm, setVersionForm] = useState({ id: null, package: '', version_label: '', payloadText: '{}' })
  const [activationForm, setActivationForm] = useState({ policy_version: '', rationale: '', effective_from: '' })
  const [exceptionForm, setExceptionForm] = useState({ requested_patch_text: '{}', rationale: '', effective_from: '', effective_to: '' })
  const [governanceProfileForm, setGovernanceProfileForm] = useState({ id: null, farm: '', tier: 'MEDIUM', rationale: '' })
  const [delegationForm, setDelegationForm] = useState({
    id: null,
    farm: '',
    principal_user: '',
    delegate_user: '',
    role: '',
    reason: '',
    starts_at: '',
    ends_at: '',
    is_active: true,
  })
  const [versionDiff, setVersionDiff] = useState(null)
  const [versionSimulation, setVersionSimulation] = useState(null)
  const [diffVersionId, setDiffVersionId] = useState('')
  const [compareToVersionId, setCompareToVersionId] = useState('')
  const [outboxActionIdsText, setOutboxActionIdsText] = useState('')
  const [attachmentActionIdsText, setAttachmentActionIdsText] = useState('')
  const [selectedOpsAlert, setSelectedOpsAlert] = useState(null)
  const [tracePayload, setTracePayload] = useState(null)
  const canManageCentralPolicy =
    isSuperuser ||
    isAdmin ||
    hasPermission('add_policypackage') ||
    hasPermission('change_policypackage') ||
    hasPermission('add_policyversion') ||
    hasPermission('change_policyversion')

  const canManageGovernanceProfile =
    isSuperuser || isAdmin || hasPermission('change_farmsettings')

  const selectedGovernanceProfile = useMemo(
    () =>
      governanceProfiles.find((item) => String(item.farm) === String(selectedFarmId)) ||
      governanceProfiles[0] ||
      null,
    [governanceProfiles, selectedFarmId],
  )

  const filteredPackages = useMemo(() => {
    return policyPackages.filter((pkg) => {
      if (packageFilter === 'active' && !pkg.is_active) return false
      if (packageFilter === 'inactive' && pkg.is_active) return false
      if (!packageSearch.trim()) return true
      const haystack = `${pkg.name} ${pkg.slug} ${pkg.description || ''}`.toLowerCase()
      return haystack.includes(packageSearch.trim().toLowerCase())
    })
  }, [packageFilter, packageSearch, policyPackages])

  const filteredVersions = useMemo(() => {
    return policyVersions.filter((version) => {
      if (versionFilter !== 'all' && version.status !== versionFilter) return false
      if (!versionSearch.trim()) return true
      const haystack = `${version.package_name} ${version.version_label} ${version.status}`.toLowerCase()
      return haystack.includes(versionSearch.trim().toLowerCase())
    })
  }, [policyVersions, versionFilter, versionSearch])

  const filteredActivations = useMemo(() => {
    return activationRequests.filter((item) => {
      if (activationFilter !== 'all' && item.status !== activationFilter) return false
      if (!activationSearch.trim()) return true
      const haystack = `${item.policy_package_name} ${item.policy_version_label} ${item.status} ${item.rationale || ''}`.toLowerCase()
      return haystack.includes(activationSearch.trim().toLowerCase())
    })
  }, [activationRequests, activationFilter, activationSearch])

  const filteredExceptions = useMemo(() => {
    return exceptionRequests.filter((item) => {
      if (exceptionFilter !== 'all' && item.status !== exceptionFilter) return false
      if (!exceptionSearch.trim()) return true
      const haystack = `${item.id} ${(item.policy_fields || []).join(' ')} ${item.status} ${item.rationale || ''}`.toLowerCase()
      return haystack.includes(exceptionSearch.trim().toLowerCase())
    })
  }, [exceptionRequests, exceptionFilter, exceptionSearch])

  const filteredDelegations = useMemo(() => {
    return delegations.filter((item) => {
      const statusKey = item.is_currently_effective ? 'current' : item.is_active ? 'active' : 'inactive'
      if (delegationFilter !== 'all' && statusKey !== delegationFilter) return false
      if (!delegationSearch.trim()) return true
      const haystack = `${item.principal_username} ${item.delegate_username} ${item.role} ${item.reason || ''}`.toLowerCase()
      return haystack.includes(delegationSearch.trim().toLowerCase())
    })
  }, [delegationFilter, delegationSearch, delegations])

  const principalRoleMap = useMemo(
    () => Object.fromEntries(farmMembers.map((member) => [String(member.user_id || member.user), member.role])),
    [farmMembers],
  )

  const delegateUserOptions = useMemo(() => {
    const merged = new Map()
    farmMembers.forEach((member) => {
      const id = String(member.user_id || member.user)
      merged.set(id, {
        id,
        username: member.username,
        full_name: member.full_name || member.username,
        email: member.email,
      })
    })
    delegateOptions.forEach((option) => {
      merged.set(String(option.id), { ...option, id: String(option.id) })
    })
    return Array.from(merged.values())
  }, [delegateOptions, farmMembers])

  const groupedEffectiveFields = useMemo(() => {
    const catalog = settingsRecord?.policy_field_catalog || {}
    const groups = {}
    for (const fieldMeta of settingsRecord?.effective_policy_fields || []) {
      const section = catalog[fieldMeta.field]?.section || 'unclassified'
      if (!groups[section]) groups[section] = []
      groups[section].push(fieldMeta)
    }
    return groups
  }, [settingsRecord])

  const governanceSummary = useMemo(() => ({
    reading: {
      title: 'السياسة والصحة',
      count: Object.keys(groupedEffectiveFields || {}).length,
      hint: 'الأقسام المقروءة المتاحة للسياسة الفعالة والتشخيص',
    },
    central: {
      title: 'عناصر الإدارة المركزية',
      count: policyPackages.length + policyVersions.length + activationRequests.length,
      hint: 'حزم + إصدارات + طلبات تفعيل',
    },
    farm: {
      title: 'عناصر حوكمة المزرعة',
      count: exceptionRequests.length + delegations.length + (selectedGovernanceProfile ? 1 : 0),
      hint: 'استثناءات + تفويضات + ملف الحوكمة',
    },
  }), [groupedEffectiveFields, policyPackages.length, policyVersions.length, activationRequests.length, exceptionRequests.length, delegations.length, selectedGovernanceProfile])

  const selectedOutboxActionIds = useMemo(() => parseExplicitIds(outboxActionIdsText), [outboxActionIdsText])
  const selectedAttachmentActionIds = useMemo(() => parseExplicitIds(attachmentActionIdsText), [attachmentActionIdsText])
  const selectedOutboxPreview = useMemo(
    () => (operationalHealth.outboxDetail?.detail_rows || []).filter((row) => selectedOutboxActionIds.includes(row.id)),
    [operationalHealth.outboxDetail, selectedOutboxActionIds],
  )
  const selectedAttachmentPreview = useMemo(
    () => (operationalHealth.attachmentDetail?.detail_rows || []).filter((row) => selectedAttachmentActionIds.includes(row.id)),
    [operationalHealth.attachmentDetail, selectedAttachmentActionIds],
  )
  const hasOpsHealthAccess = canObserveOps || canManageCentralPolicy || canManageGovernanceProfile
  const currentTabGroup = useMemo(
    () => TAB_GROUPS.find((group) => group.tabs.includes(activeTab)) || TAB_GROUPS[0],
    [activeTab],
  )

  const getSectionError = useCallback((tabKey) => sectionErrors?.[tabKey] || '', [sectionErrors])

  const permissionReason = useCallback((scopeLabel) => `يتطلب هذا الإجراء صلاحية ${scopeLabel}.`, [])

  const changeTab = useCallback((tabKey) => {
    setActiveTab(tabKey)
    const params = new URLSearchParams(location.search)
    params.set('governanceTab', tabKey)
    navigate({ search: `?${params.toString()}` }, { replace: true })
  }, [location.search, navigate])

  const confirmThen = useCallback((promptText, callback) => {
    if (!window.confirm(promptText)) return
    callback()
  }, [])

  const resetPackageForm = useCallback(() => {
    setPackageForm({ id: null, name: '', slug: '', description: '', is_active: true })
  }, [])

  const resetVersionForm = useCallback(
    (payloadText = null, packages = policyPackages, settings = settingsRecord) => {
      setVersionForm(buildVersionForm(packages, settings, payloadText))
    },
    [policyPackages, settingsRecord],
  )

  const resetActivationForm = useCallback(() => {
    const approvedVersion = policyVersions.find((item) => item.status === 'approved')
    setActivationForm({
      policy_version: approvedVersion ? String(approvedVersion.id) : '',
      rationale: '',
      effective_from: '',
    })
  }, [policyVersions])

  const resetExceptionForm = useCallback(() => {
    setExceptionForm({
      requested_patch_text: prettyJson({ mandatory_attachment_for_cash: false }),
      rationale: '',
      effective_from: '',
      effective_to: '',
    })
  }, [])

  const resetGovernanceProfileForm = useCallback((profile = selectedGovernanceProfile) => {
    setGovernanceProfileForm({
      id: profile?.id || null,
      farm: String(profile?.farm || selectedFarmId || ''),
      tier: profile?.tier || 'MEDIUM',
      rationale: profile?.rationale || '',
    })
  }, [selectedFarmId, selectedGovernanceProfile])

  const resetDelegationForm = useCallback((delegation = null) => {
    setDelegationForm({
      id: delegation?.id || null,
      farm: String(selectedFarmId || delegation?.farm || ''),
      principal_user: delegation?.principal_user ? String(delegation.principal_user) : '',
      delegate_user: delegation?.delegate_user ? String(delegation.delegate_user) : '',
      role: delegation?.role || '',
      reason: delegation?.reason || '',
      starts_at: delegation?.starts_at ? String(delegation.starts_at).slice(0, 16) : '',
      ends_at: delegation?.ends_at ? String(delegation.ends_at).slice(0, 16) : '',
      is_active: delegation?.is_active ?? true,
    })
    setDelegateSearchTerm('')
  }, [selectedFarmId])

  const loadConsoleData = useCallback(async () => {
    if (!selectedFarmId) {
      setSettingsRecord(null)
      setPolicyPackages([])
      setPolicyVersions([])
      setActivationRequests([])
      setExceptionRequests([])
      setDelegations([])
      setGovernanceProfiles([])
      setFarmMembers([])
      setMembershipMeta({})
      setDelegationMeta({})
      setDelegationRoles([])
      return
    }

    setLoading(true)
    setError('')
    setSectionErrors({})
    try {
      const nextSectionErrors = {}
      const registerSectionError = (keys, err, fallback) => {
        const message = normalizeRequestError(err, fallback)
        for (const key of keys) {
          if (!nextSectionErrors[key]) nextSectionErrors[key] = message
        }
      }
      const optionalGet = async (keys, requestFactory, fallback, fallbackMessage) => {
        try {
          return await requestFactory()
        } catch (err) {
          console.error(`Governance section request failed [${keys.join(', ')}]`, err)
          registerSectionError(keys, err, fallbackMessage)
          return { data: fallback }
        }
      }

      const [settingsRes, packagesRes, versionsRes, activationsRes, exceptionsRes, delegationsRes, profileRes, membershipRes, delegationRolesRes, usageRes, timelineRes, pressureRes, releaseHealthRes, releaseHealthDetailRes, outboxHealthRes, outboxHealthDetailRes, attachmentHealthRes, attachmentHealthDetailRes] = await Promise.all([
        api.get(`/farm-settings/?farm=${selectedFarmId}`),
        optionalGet(['packages', 'versions'], () => api.get('/policy-packages/'), [], 'تعذر تحميل حزم السياسات.'),
        optionalGet(['versions', 'activations'], () => api.get('/policy-versions/'), [], 'تعذر تحميل إصدارات السياسات.'),
        optionalGet(['activations', 'timeline'], () => api.get(`/policy-activation-requests/?farm=${selectedFarmId}`), [], 'تعذر تحميل طلبات التفعيل.'),
        optionalGet(['exceptions', 'pressure'], () => api.get(`/policy-exception-requests/?farm=${selectedFarmId}`), [], 'تعذر تحميل طلبات الاستثناء.'),
        optionalGet(['delegations'], () => api.get(`/governance/role-delegations/?farm=${selectedFarmId}`), [], 'تعذر تحميل التفويضات.'),
        optionalGet(['profile'], () => api.get(`/governance/farm-profiles/?farm=${selectedFarmId}`), [], 'تعذر تحميل ملف الحوكمة.'),
        optionalGet(['delegations', 'profile'], () => api.get(`/memberships/?farm=${selectedFarmId}`), { results: [], meta: {} }, 'تعذر تحميل عضويات المزرعة.'),
        optionalGet(['delegations'], () => api.get('/memberships/roles/'), { results: [] }, 'تعذر تحميل أدوار المزرعة.'),
        optionalGet(['usage'], () => api.get('/policy-packages/usage-snapshot/'), { packages: [], summary: {} }, 'تعذر تحميل استخدام الحزم.'),
        optionalGet(['timeline'], () => api.get('/policy-activation-requests/timeline-snapshot/'), { counts_by_status: {}, maker_checker: {}, latest_requests: [], latest_events: [] }, 'تعذر تحميل الخط الزمني للتفعيل.'),
        optionalGet(['pressure'], () => api.get('/policy-exception-requests/pressure-snapshot/'), { open_by_farm: [], open_by_field_family: {}, forbidden_field_rejections: 0, expiring_soon: [] }, 'تعذر تحميل ضغط الاستثناءات.'),
        optionalGet(['ops'], () => api.get('/dashboard/release-health/'), {}, 'تعذر تحميل صحة الإصدار.'),
        optionalGet(['ops'], () => api.get('/dashboard/release-health/detail/'), {}, 'تعذر تحميل تفاصيل صحة الإصدار.'),
        optionalGet(['ops'], () => api.get('/dashboard/outbox-health/'), {}, 'تعذر تحميل صحة صندوق الإرسال.'),
        optionalGet(['ops'], () => api.get('/dashboard/outbox-health/detail/', { params: { farm_id: selectedFarmId, limit: 25 } }), { detail_rows: [], filtered_total: 0 }, 'تعذر تحميل تفاصيل صندوق الإرسال.'),
        optionalGet(['ops'], () => api.get('/dashboard/attachment-runtime-health/'), {}, 'تعذر تحميل صحة المرفقات.'),
        optionalGet(['ops'], () => api.get('/dashboard/attachment-runtime-health/detail/', { params: { farm_id: selectedFarmId, limit: 25 } }), { detail_rows: [], filtered_total: 0 }, 'تعذر تحميل تفاصيل المرفقات.'),
      ])

      const nextSettings = extractList(settingsRes.data)[0] || null
      const nextPackages = extractList(packagesRes.data)
      const nextVersions = extractList(versionsRes.data)
      const [impactRes, runtimeHealthRes, farmOpsRes] = await Promise.all([
        optionalGet(['impact'], () => api.get(`/finance/approval-requests/farm-governance/?farm=${selectedFarmId}`), null, 'تعذر تحميل أثر المزرعة من دورة الموافقات.'),
        optionalGet(['ops'], () => api.get('/finance/approval-requests/runtime-governance/'), {}, 'تعذر تحميل صحة التشغيل من دورة الموافقات.'),
        optionalGet(['ops'], () => api.get(`/finance/approval-requests/farm-ops/?farm=${selectedFarmId}`), null, 'تعذر تحميل تشغيل المزرعة من دورة الموافقات.'),
      ])

      setSettingsRecord(nextSettings)
      setPolicyPackages(nextPackages)
      setPolicyVersions(nextVersions)
      setActivationRequests(extractList(activationsRes.data))
      setExceptionRequests(extractList(exceptionsRes.data))
      setDelegations(extractList(delegationsRes.data))
      setGovernanceProfiles(extractList(profileRes.data))
      setFarmMembers(extractList(membershipRes.data))
      setMembershipMeta(membershipRes.data?.meta || {})
      setDelegationMeta(delegationsRes.data?.meta || {})
      setDelegationRoles(extractList(delegationRolesRes.data))
      setPackageUsage(usageRes.data || { packages: [], summary: {} })
      setActivationTimeline(timelineRes.data || { counts_by_status: {}, maker_checker: {}, latest_requests: [], latest_events: [] })
      setExceptionPressure(pressureRes.data || { open_by_farm: [], open_by_field_family: {}, forbidden_field_rejections: 0, expiring_soon: [] })
      setFarmImpact(impactRes.data || null)
      setOperationalHealth({
        release: releaseHealthRes.data || {},
        releaseDetail: releaseHealthDetailRes.data || {},
        outbox: outboxHealthRes.data || {},
        outboxDetail: outboxHealthDetailRes.data || { detail_rows: [], filtered_total: 0 },
        attachment: attachmentHealthRes.data || {},
        attachmentDetail: attachmentHealthDetailRes.data || { detail_rows: [], filtered_total: 0 },
        runtime: runtimeHealthRes.data || {},
        farmOps: farmOpsRes.data || null,
      })
      setSectionErrors(nextSectionErrors)

      setVersionDiff(null)
      setVersionSimulation(null)
      setDiffVersionId('')
      setCompareToVersionId('')
      setOutboxActionIdsText('')
      setAttachmentActionIdsText('')
      resetPackageForm()
      setVersionForm(buildVersionForm(nextPackages, nextSettings, prettyJson(nextSettings?.effective_policy_payload || {})))
      setActivationForm({
        policy_version: nextVersions.find((item) => item.status === 'approved')?.id?.toString?.() || '',
        rationale: '',
        effective_from: '',
      })
      resetExceptionForm()
      resetGovernanceProfileForm(extractList(profileRes.data).find((item) => String(item.farm) === String(selectedFarmId)) || extractList(profileRes.data)[0] || null)
      resetDelegationForm()
    } catch (err) {
      console.error('Failed to load governance console data', err)
      setError(err?.response?.data?.detail || 'تعذر تحميل بيانات منصة الحوكمة والسياسات.')
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId, resetDelegationForm, resetExceptionForm, resetGovernanceProfileForm, resetPackageForm])

  useEffect(() => {
    resetGovernanceProfileForm(selectedGovernanceProfile)
  }, [resetGovernanceProfileForm, selectedGovernanceProfile])

  useEffect(() => {
    if (!delegationForm.principal_user) return
    const principalRole = principalRoleMap[delegationForm.principal_user]
    if (principalRole && principalRole !== delegationForm.role) {
      setDelegationForm((prev) => ({ ...prev, role: principalRole }))
    }
  }, [delegationForm.principal_user, delegationForm.role, principalRoleMap])

  useEffect(() => {
    loadConsoleData()
  }, [loadConsoleData])

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const queryTab = params.get('governanceTab')
    if (queryTab && TAB_DEFS.some((item) => item.key === queryTab)) {
      setActiveTab(queryTab)
    }
  }, [location.search])

  const handleApiAction = useCallback(
    async (label, callback) => {
      setSubmitting(true)
      setError('')
      setMessage('')
      try {
        await callback()
        setMessage(label)
        await loadConsoleData()
      } catch (err) {
        console.error(label, err)
        setError(err?.response?.data?.detail || err?.message || 'تعذر تنفيذ الإجراء المطلوب.')
      } finally {
        setSubmitting(false)
      }
    },
    [loadConsoleData],
  )

  const policyMutationAction = async (endpoint, successMessage, body = {}) => {
    await handleApiAction(successMessage, async () => {
      await api.post(endpoint, body, ACTION_HEADERS(endpoint.replace(/[^\w-]+/g, '-')))
    })
  }

  const handlePackageSubmit = async (event) => {
    event.preventDefault()
    await handleApiAction('تم حفظ حزمة السياسة بنجاح.', async () => {
      const payload = {
        name: packageForm.name.trim(),
        slug: packageForm.slug.trim(),
        description: packageForm.description,
        is_active: packageForm.is_active,
      }
      if (packageForm.id) await api.patch(`/policy-packages/${packageForm.id}/`, payload)
      else await api.post('/policy-packages/', payload)
      resetPackageForm()
    })
  }

  const handleVersionSubmit = async (event) => {
    event.preventDefault()
    await handleApiAction('تم حفظ إصدار السياسة بنجاح.', async () => {
      const payload = {
        package: Number(versionForm.package),
        version_label: versionForm.version_label.trim(),
        payload: parseJsonText(versionForm.payloadText, {}),
      }
      if (versionForm.id) await api.patch(`/policy-versions/${versionForm.id}/`, payload)
      else await api.post('/policy-versions/', payload)
      resetVersionForm()
    })
  }

  const handleActivationCreate = async (event) => {
    event.preventDefault()
    await handleApiAction('تم إنشاء طلب التفعيل بنجاح.', async () => {
      await api.post('/policy-activation-requests/', {
        farm: Number(selectedFarmId),
        policy_version: Number(activationForm.policy_version),
        rationale: activationForm.rationale,
        effective_from: activationForm.effective_from ? new Date(activationForm.effective_from).toISOString() : undefined,
      })
      resetActivationForm()
    })
  }

  const handleExceptionCreate = async (event) => {
    event.preventDefault()
    await handleApiAction('تم إنشاء طلب الاستثناء بنجاح.', async () => {
      const requestedPatch = parseJsonText(exceptionForm.requested_patch_text, {})
      const forbiddenFields = Object.keys(requestedPatch).filter((field) => !settingsRecord?.policy_field_catalog?.[field])
      if (forbiddenFields.length) throw new Error(`حقول غير معروفة في الاستثناء: ${forbiddenFields.join(', ')}`)
      await api.post('/policy-exception-requests/', {
        farm: Number(selectedFarmId),
        requested_patch: requestedPatch,
        rationale: exceptionForm.rationale,
        effective_from: exceptionForm.effective_from ? new Date(exceptionForm.effective_from).toISOString() : undefined,
        effective_to: exceptionForm.effective_to ? new Date(exceptionForm.effective_to).toISOString() : undefined,
      })
      resetExceptionForm()
    })
  }

  const handleOutboxRetry = async () => {
    await handleApiAction('تمت إعادة جدولة صفوف outbox المحددة.', async () => {
      if (!selectedOutboxActionIds.length) throw new Error('أدخل IDs صريحة لصفوف outbox.')
      await api.post('/dashboard/outbox-health/retry/', { event_ids: selectedOutboxActionIds }, ACTION_HEADERS('ops-outbox-retry'))
      setOutboxActionIdsText('')
    })
  }

  const handleAttachmentRescan = async () => {
    await handleApiAction('تمت إعادة فحص المرفقات المحددة.', async () => {
      if (!selectedAttachmentActionIds.length) throw new Error('أدخل IDs صريحة للمرفقات.')
      await api.post('/dashboard/attachment-runtime-health/rescan/', { attachment_ids: selectedAttachmentActionIds }, ACTION_HEADERS('ops-attachment-rescan'))
      setAttachmentActionIdsText('')
    })
  }

  const handleMaintenanceDryRun = async () => {
    await handleApiAction('تم تشغيل dry-run لدورة governance maintenance.', async () => {
      await api.post('/finance/approval-requests/runtime-governance/dry-run-maintenance/', {}, ACTION_HEADERS('ops-maintenance-dry-run'))
    })
  }

  const handleGovernanceProfileSubmit = async (event) => {
    event.preventDefault()
    await handleApiAction('تم حفظ ملف الحوكمة بنجاح.', async () => {
      const payload = {
        farm: Number(governanceProfileForm.farm || selectedFarmId),
        tier: governanceProfileForm.tier,
        rationale: governanceProfileForm.rationale,
      }
      if (governanceProfileForm.id) await api.patch(`/governance/farm-profiles/${governanceProfileForm.id}/`, payload)
      else await api.post('/governance/farm-profiles/', payload)
      resetGovernanceProfileForm()
    })
  }

  const handleDelegateSearch = async () => {
    const term = delegateSearchTerm.trim()
    if (!selectedFarmId || !term) {
      setDelegateOptions([])
      return
    }
    try {
      const { data } = await api.get('/memberships/available-users/', { params: { farm: selectedFarmId, q: term } })
      setDelegateOptions(extractList(data))
    } catch (err) {
      console.error('Delegation user search failed', err)
      setError(normalizeRequestError(err, 'تعذر تحميل قائمة المستخدمين المتاحين للتفويض.'))
    }
  }

  const handleDelegationSubmit = async (event) => {
    event.preventDefault()
    await handleApiAction('تم حفظ التفويض بنجاح.', async () => {
      if (!delegationForm.principal_user || !delegationForm.delegate_user || !delegationForm.role) {
        throw new Error('أكمل بيانات المفوِّض والمفوَّض إليه والدور قبل الحفظ.')
      }
      const payload = {
        farm: Number(delegationForm.farm || selectedFarmId),
        principal_user: Number(delegationForm.principal_user),
        delegate_user: Number(delegationForm.delegate_user),
        role: delegationForm.role,
        reason: delegationForm.reason,
        starts_at: delegationForm.starts_at ? new Date(delegationForm.starts_at).toISOString() : undefined,
        ends_at: delegationForm.ends_at ? new Date(delegationForm.ends_at).toISOString() : undefined,
        is_active: delegationForm.is_active,
      }
      if (delegationForm.id) await api.patch(`/governance/role-delegations/${delegationForm.id}/`, payload)
      else await api.post('/governance/role-delegations/', payload)
      resetDelegationForm()
      setDelegateOptions([])
    })
  }

  const handleDelegationDelete = async (delegationId) => {
    await handleApiAction('تم حذف التفويض بنجاح.', async () => {
      await api.delete(`/governance/role-delegations/${delegationId}/`)
      resetDelegationForm()
    })
  }

  const handleAlertAcknowledge = async (fingerprint) => {
    await handleApiAction('تم تأكيد التنبيه التشغيلي.', async () => {
      await acknowledgeAlert(fingerprint)
      if (selectedOpsAlert?.fingerprint === fingerprint) setSelectedOpsAlert(null)
    })
  }

  const handleAlertSnooze = async (fingerprint, hours) => {
    await handleApiAction(`تم تأجيل التنبيه لمدة ${hours} ساعة.`, async () => {
      await snoozeAlert(fingerprint, hours)
      if (selectedOpsAlert?.fingerprint === fingerprint) setSelectedOpsAlert(null)
    })
  }

  const handleOutboxTrace = async (eventId) => {
    await handleApiAction('تم تحميل تتبع صندوق الإرسال.', async () => {
      const data = await loadOutboxTrace({ event_id: eventId })
      setTracePayload(data)
    })
  }

  const handleAttachmentTrace = async (attachmentId) => {
    await handleApiAction('تم تحميل تتبع المرفق.', async () => {
      const data = await loadAttachmentTrace({ attachment_id: attachmentId })
      setTracePayload(data)
    })
  }

  const handleVersionDiff = async () => {
    if (!diffVersionId) return
    setSubmitting(true)
    setError('')
    try {
      const payload = compareToVersionId ? { compare_to_version: Number(compareToVersionId) } : { farm: Number(selectedFarmId) }
      const { data } = await api.post(`/policy-versions/${diffVersionId}/diff/`, payload, ACTION_HEADERS('version-diff'))
      setVersionDiff(data)
      setMessage('تم توليد مقارنة الإصدار بنجاح.')
    } catch (err) {
      console.error('Version diff failed', err)
      setError(err?.response?.data?.detail || 'تعذر توليد الفرق بين إصدارات السياسة.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleVersionSimulation = async (versionId) => {
    setSubmitting(true)
    setError('')
    try {
      const { data } = await api.get(`/policy-versions/${versionId}/simulate/?farm=${selectedFarmId}`)
      setVersionSimulation(data)
      setMessage('تم توليد simulation للتفعيل بنجاح.')
    } catch (err) {
      console.error('Version simulation failed', err)
      setError(err?.response?.data?.detail || 'تعذر توليد simulation للتفعيل.')
    } finally {
      setSubmitting(false)
    }
  }

  const renderEffectivePolicy = () => {
    const activeBinding = settingsRecord?.active_policy_binding
    const activeException = settingsRecord?.active_policy_exception
    return (
      <div className="space-y-5">
        <div className="grid gap-4 md:grid-cols-3">
          <SummaryCard title="مصدر السياسة" value={formatPolicySource(settingsRecord?.policy_source) || 'غير متاح'} hint="المصدر الفعلي الذي حسم السياسة الحالية." />
          <SummaryCard title="الوضع" value={formatPolicyValue(settingsRecord?.mode || 'SIMPLE')} hint={formatPolicyValue(settingsRecord?.visibility_level || 'operations_only')} />
          <SummaryCard title="التحقق" value={settingsRecord?.policy_validation_errors?.length ? 'تحذيرات' : 'سليم'} hint="تحذيرات التحقق المرجعي أو التشغيل الحي." />
        </div>

        <SectionCard title="ملخص الربط والاستثناء" description="عرض مباشر للربط المركزي والاستثناء المرتبط بالمزرعة عند توفره.">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
              <div className="mb-2 text-sm font-semibold text-slate-900 dark:text-white">الربط الفعّال</div>
              {activeBinding ? (
                <div className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
                  <div>الحزمة: {activeBinding.policy_package_name}</div>
                  <div>الإصدار: {activeBinding.policy_version_label}</div>
                  <div>بداية النفاذ: {formatTimestamp(activeBinding.effective_from)}</div>
                  <div>السبب: {formatOpsReason(activeBinding.reason) || 'غير محدد'}</div>
                </div>
              ) : (
                <div className="text-sm text-slate-500 dark:text-slate-400">لا يوجد ربط مركزي فعال.</div>
              )}
            </div>
            <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
              <div className="mb-2 text-sm font-semibold text-slate-900 dark:text-white">الاستثناء الفعّال</div>
              {activeException ? (
                <div className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
                    <div>الحالة: {formatSeverityLabel(activeException.status) || activeException.status}</div>
                  <div>الحقول: {(activeException.policy_fields || []).map((field) => formatPolicyFieldLabel(field)).join('، ') || 'لا يوجد'}</div>
                  <div>من: {formatTimestamp(activeException.effective_from)}</div>
                  <div>إلى: {formatTimestamp(activeException.effective_to)}</div>
                </div>
              ) : (
                <div className="text-sm text-slate-500 dark:text-slate-400">لا يوجد استثناء فعال ضمن نطاق المزرعة.</div>
              )}
            </div>
          </div>
        </SectionCard>

        {settingsRecord?.legacy_mode_divergence?.detected ? (
          <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
            {settingsRecord.legacy_mode_divergence.warning}
          </div>
        ) : null}

        {settingsRecord?.policy_validation_errors?.length ? (
          <div className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-900/20 dark:text-red-300">
            <div className="font-semibold">تحذيرات التحقق</div>
            <ul className="mt-2 list-disc space-y-1 pr-5">
              {settingsRecord.policy_validation_errors.map((item) => (
                <li key={item}>{formatPolicyValidationMessage(item)}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <SectionCard title="حقول السياسة الفعالة" description="كل قيمة فعالة مع مصدرها ونطاقها وتاريخ نفاذها وقابلية تحريرها.">
          <div className="space-y-5">
            {Object.entries(groupedEffectiveFields).map(([section, fields]) => (
              <div key={section} className="space-y-3">
                <div className="text-sm font-semibold text-slate-900 dark:text-white">{formatPolicySection(section)}</div>
                <div className="grid gap-3 lg:grid-cols-2">
                  {fields.map((fieldMeta) => (
                    <div key={fieldMeta.field} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="text-sm font-semibold text-slate-900 dark:text-white">
                          {formatPolicyFieldLabel(settingsRecord.policy_field_catalog?.[fieldMeta.field]?.label || fieldMeta.field)}
                        </div>
                        <span className={`rounded-full px-2 py-1 text-xs font-medium ${sourceTone(fieldMeta.source)}`}>{formatPolicySource(fieldMeta.source)}</span>
                        <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">{formatPolicyValue(fieldMeta.scope || 'farm')}</span>
                      </div>
                      <div className="mt-2 text-sm text-slate-700 dark:text-slate-200">
                        القيمة: {formatPolicyValue(fieldMeta.value)}
                      </div>
                      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        قابلية التحرير: {fieldMeta.editable ? 'نعم' : 'لا'} | بداية النفاذ: {formatTimestamp(fieldMeta.effective_from)}
                      </div>
                      {fieldMeta.reason ? <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">{formatOpsReason(fieldMeta.reason)}</div> : null}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <details className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          <summary className="cursor-pointer text-sm font-semibold text-slate-900 dark:text-white">الحمولة الخام للسياسة الفعالة</summary>
          <div className="mt-4">
            <JsonBlock value={settingsRecord?.effective_policy_payload || {}} />
          </div>
        </details>
      </div>
    )
  }

  const renderPackageUsage = () => (
    <SectionCard
      title="استخدام الحزم"
      description="استهلاك الحزم والإصدارات عبر المزارع والارتباطات النشطة والمنتهية."
      actions={<ScopeBadge scope="sector" editable={false} />}
    >
      {getSectionError('usage') ? <RestrictionNotice text={getSectionError('usage')} /> : null}
      <div className="grid gap-4 md:grid-cols-4">
        <SummaryCard title="الحزم" value={String(packageUsage.summary?.packages || 0)} hint="عدد الحزم المركزية" />
        <SummaryCard title="الارتباطات النشطة" value={String(packageUsage.summary?.active_bindings || 0)} hint="ارتباطات نشطة" />
        <SummaryCard title="الارتباطات المنتهية" value={String(packageUsage.summary?.expired_bindings || 0)} hint="ارتباطات منتهية أو معطلة" />
        <SummaryCard title="مزارع مع استثناءات" value={String(packageUsage.summary?.farms_with_exceptions || 0)} hint="ضغط استثناءات فوق الحزم" />
      </div>
      <div className="mt-4 space-y-3">
        {(packageUsage.packages || []).length ? packageUsage.packages.map((item) => (
          <div key={item.package_id} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="font-semibold text-slate-900 dark:text-white">{item.package_name}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">{item.package_slug}</div>
              </div>
              <span className={`rounded-full px-2 py-1 text-xs ${statusTone(item.is_active ? 'active' : 'inactive')}`}>{item.is_active ? 'نشط' : 'معطل'}</span>
            </div>
            <div className="mt-3 grid gap-2 text-sm text-slate-600 dark:text-slate-300 md:grid-cols-5">
              <div>الإصدارات: {item.versions_count}</div>
              <div>المعتمد: {item.approved_versions_count}</div>
              <div>المزارع: {item.farm_count}</div>
              <div>الارتباطات النشطة: {item.active_bindings}</div>
              <div>مزارع الاستثناءات: {item.exception_farm_count}</div>
            </div>
          </div>
        )) : <EmptyState text="لا توجد بيانات استخدام متاحة للحزم حاليًا." />}
      </div>
    </SectionCard>
  )

  const renderActivationTimeline = () => (
    <SectionCard
      title="الخط الزمني للتفعيل"
      description="أثر طلبات التفعيل والأحداث الأخيرة مع فصل الصانع والمراجع."
      actions={<ScopeBadge scope="sector" editable={false} />}
    >
      {getSectionError('timeline') ? <RestrictionNotice text={getSectionError('timeline')} /> : null}
      <div className="grid gap-4 md:grid-cols-4">
        {Object.entries(activationTimeline.counts_by_status || {}).map(([status, count]) => (
          <SummaryCard key={status} title={formatSeverityLabel(status)} value={String(count)} hint="توزيع الطلبات حسب الحالة" />
        ))}
        <SummaryCard title="فصل الصانع والمراجع" value={String(activationTimeline.maker_checker?.split_actor_pairs || 0)} hint="المنشئ مختلف عن المعتمد" />
        <SummaryCard title="الحالات ذات الممثل نفسه" value={String(activationTimeline.maker_checker?.same_actor_pairs || 0)} hint="يجب أن تبقى منخفضة جدًا" />
      </div>
      {canObserveOps ? (
        <div className="mt-4 grid gap-4 xl:grid-cols-3">
          <SectionCard title="تنبيهات التشغيل" description="قائمة موحدة للتنبيهات مع التأكيد والتأجيل والانتقال المباشر داخل الأسطح الحالية.">
            <div className="space-y-3">
              {topAlerts.length ? topAlerts.map((alert) => (
                <div key={alert.fingerprint} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-2 py-1 text-xs ${statusTone(alert.severity)}`}>{formatSeverityLabel(alert.severity)}</span>
                    <span className={`rounded-full px-2 py-1 text-xs ${sourceTone(alert.kind)}`}>{formatAlertKindLabel(alert.kind)}</span>
                  </div>
                  <div className="mt-3 text-sm font-semibold text-slate-900 dark:text-white">{formatOpsReason(alert.title || alert.canonical_reason)}</div>
                  <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{formatOpsReason(alert.canonical_reason)} · {formatTimestamp(alert.created_at)}</div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button type="button" onClick={() => { setSelectedOpsAlert(alert); navigate(alert.deep_link || '/approvals?tab=runtime') }} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-700 dark:border-slate-600 dark:text-slate-200">فتح</button>
                    <button type="button" onClick={() => handleAlertAcknowledge(alert.fingerprint)} disabled={submitting} className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs text-white disabled:opacity-60">تأكيد</button>
                    {[1, 4, 24].map((hours) => (
                      <button key={`${alert.fingerprint}-${hours}`} type="button" onClick={() => handleAlertSnooze(alert.fingerprint, hours)} disabled={submitting} className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs text-white disabled:opacity-60">{`تأجيل ${hours}س`}</button>
                    ))}
                  </div>
                </div>
              )) : <EmptyState text="لا توجد تنبيهات تشغيلية نشطة حاليًا." />}
            </div>
          </SectionCard>
          <SectionCard title="لوحة إجراءات التشغيل" description="عرض السبب المرجعي ومصدر التنبيه دون إنشاء مسار جديد.">
            {selectedOpsAlert ? (
              <div className="space-y-3">
                <JsonBlock value={selectedOpsAlert} />
                <button type="button" onClick={() => navigate(selectedOpsAlert.deep_link || '/approvals?tab=runtime')} className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white">فتح الرابط الداخلي</button>
              </div>
            ) : (
              <EmptyState text="اختر تنبيهًا من القائمة لعرض لوحة الإجراءات." />
            )}
          </SectionCard>
          <SectionCard title="التتبع التفصيلي" description="تتبع للقراءة فقط من الواجهات الحالية لصندوق الإرسال والمرفقات.">
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => selectedOutboxPreview[0] && handleOutboxTrace(selectedOutboxPreview[0].id)} disabled={submitting || !selectedOutboxPreview[0]} className="rounded-xl bg-sky-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60">تحميل تتبع صندوق الإرسال</button>
                <button type="button" onClick={() => selectedAttachmentPreview[0] && handleAttachmentTrace(selectedAttachmentPreview[0].id)} disabled={submitting || !selectedAttachmentPreview[0]} className="rounded-xl bg-amber-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60">تحميل تتبع المرفقات</button>
              </div>
              {tracePayload ? <JsonBlock value={tracePayload} /> : <EmptyState text="اختر صفوف المعاينة ثم حمّل التتبع التفصيلي." />}
            </div>
          </SectionCard>
        </div>
      ) : null}
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <SectionCard title="أحدث الطلبات" description="آخر طلبات التفعيل.">
          {(activationTimeline.latest_requests || []).length ? (
            <div className="space-y-3">
              {activationTimeline.latest_requests.map((item) => (
                <div key={item.id} className="rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-semibold text-slate-900 dark:text-white">{item.package_name} / {item.version_label}</div>
                    <span className={`rounded-full px-2 py-1 text-xs ${statusTone(item.status)}`}>{formatSeverityLabel(item.status)}</span>
                  </div>
                  <div className="mt-2 text-slate-500 dark:text-slate-400">{item.farm_name} · {formatTimestamp(item.created_at)}</div>
                </div>
              ))}
            </div>
          ) : <EmptyState text="لا توجد طلبات تفعيل حديثة." />}
        </SectionCard>
        <SectionCard title="أحدث الأحداث" description="آخر أحداث التفعيل المضافة بشكل تتابعي.">
          {(activationTimeline.latest_events || []).length ? (
            <div className="space-y-3">
              {activationTimeline.latest_events.map((item) => (
                <div key={item.id} className="rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-semibold text-slate-900 dark:text-white">{item.action}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">{item.actor_username || 'النظام'}</div>
                  </div>
                  <div className="mt-2 text-slate-500 dark:text-slate-400">{item.farm_name} · {item.package_name} / {item.version_label}</div>
                </div>
              ))}
            </div>
          ) : <EmptyState text="لا توجد أحداث تفعيل حديثة." />}
      </SectionCard>
      </div>
    </SectionCard>
  )

  const renderExceptionPressure = () => (
    <SectionCard
      title="ضغط الاستثناءات"
      description="ضغط الاستثناءات المفتوحة حسب المزرعة وعائلات الحقول ونوافذ الانتهاء."
      actions={<ScopeBadge scope="farm" editable={false} />}
    >
      {getSectionError('pressure') ? <RestrictionNotice text={getSectionError('pressure')} /> : null}
      <div className="grid gap-4 md:grid-cols-3">
        <SummaryCard title="المزارع المفتوحة" value={String((exceptionPressure.open_by_farm || []).length)} hint="مزارع لديها ضغط استثناءات" />
        <SummaryCard title="الرفض بسبب الحقول الممنوعة" value={String(exceptionPressure.forbidden_field_rejections || 0)} hint="طلبات مرفوضة لحقول غير مسموحة" />
        <SummaryCard title="تنتهي قريبًا" value={String((exceptionPressure.expiring_soon || []).length)} hint="تنتهي خلال 7 أيام" />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <SectionCard title="المفتوح حسب المزرعة" description="الاستثناءات المفتوحة حسب المزرعة.">
          {(exceptionPressure.open_by_farm || []).length ? (
            <div className="space-y-3">
              {exceptionPressure.open_by_farm.map((item) => (
                <div key={item.farm_id} className="rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-semibold text-slate-900 dark:text-white">{item.farm_name}</div>
                    <span className="rounded-full bg-amber-100 px-2 py-1 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">{item.count}</span>
                  </div>
                  <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">{Object.keys(item.fields || {}).join(', ') || 'لا توجد حقول'}</div>
                </div>
              ))}
            </div>
          ) : <EmptyState text="لا توجد استثناءات مفتوحة حاليًا." />}
        </SectionCard>
        <SectionCard title="عائلات الحقول" description="عائلات الحقول الأكثر طلبًا في الاستثناءات.">
          {Object.keys(exceptionPressure.open_by_field_family || {}).length ? (
            <div className="space-y-2">
              {Object.entries(exceptionPressure.open_by_field_family || {}).map(([family, count]) => (
                <div key={family} className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">
                  <span>{family}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-1 text-xs dark:bg-slate-700">{count}</span>
                </div>
              ))}
            </div>
          ) : <EmptyState text="لا توجد عائلات حقول مفتوحة في الاستثناءات." />}
        </SectionCard>
      </div>
    </SectionCard>
  )

  const renderFarmImpact = () => (
    <SectionCard
      title="أثر المزرعة"
      description="الأثر الحوكمي الحالي على المزرعة المختارة من دورة الموافقات والسياسات."
      actions={<ScopeBadge scope="farm" editable={false} />}
    >
      {getSectionError('impact') ? <RestrictionNotice text={getSectionError('impact')} /> : null}
      {!farmImpact ? <EmptyState text="لا توجد بيانات أثر متاحة لهذه المزرعة." /> : (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <SummaryCard title="الوضع" value={formatPolicyValue(farmImpact.effective_mode || 'غير متاح')} hint={formatPolicySource(farmImpact.approval_profile_source) || 'مصدر السياسة'} />
            <SummaryCard title="ملف الاعتماد" value={formatPolicyValue(farmImpact.approval_profile || 'غير متاح')} hint="الملف الفعال" />
            <SummaryCard title="الطلبات المعلقة" value={String(farmImpact.lane_summary?.pending_requests || 0)} hint="ضمن نطاق المزرعة" />
            <SummaryCard title="الطلبات المتأخرة" value={String(farmImpact.lane_summary?.overdue_requests || 0)} hint="تجاوز مهلة المسار" />
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.keys(farmImpact.active_blockers || {}).length ? Object.entries(farmImpact.active_blockers || {}).map(([key, count]) => <span key={key} className="rounded-full bg-rose-100 px-3 py-1 text-xs text-rose-800 dark:bg-rose-900/30 dark:text-rose-300">{formatBlocker(key)}: {count}</span>) : <span className="rounded-full bg-green-100 px-3 py-1 text-xs text-green-800 dark:bg-green-900/30 dark:text-green-300">لا توجد معيقات نشطة</span>}
          </div>
          <div className="grid gap-4 xl:grid-cols-2">
            <JsonBlock value={farmImpact.remote_review_posture || {}} />
            <JsonBlock value={farmImpact.attachment_runtime_posture || {}} />
          </div>
        </div>
      )}
    </SectionCard>
  )

  const renderOperationalHealth = () => (
    <SectionCard
      title="الصحة التشغيلية"
      description="سطح تشغيلي مشتق من لقطات التشغيل فقط؛ ولا يعلو على الملخصات المرجعية الرسمية."
      actions={<ScopeBadge scope="sector" editable={hasOpsHealthAccess} />}
    >
      {getSectionError('ops') ? <RestrictionNotice text={getSectionError('ops')} /> : null}
      {!hasOpsHealthAccess ? <RestrictionNotice text="هذا القسم يحتاج صلاحية حوكمة أو مراقبة تشغيلية." /> : null}
      <div className="grid gap-4 md:grid-cols-4">
        <SummaryCard title="شدة صحة الإصدار" value={formatSeverityLabel(operationalHealth.release?.severity || 'unknown')} hint={`تحذيرات التقادم: ${operationalHealth.release?.stale_warning_count || 0}`} />
        <SummaryCard title="شدة صندوق الإرسال" value={formatSeverityLabel(operationalHealth.outbox?.severity || 'unknown')} hint={`الرسائل الميتة: ${operationalHealth.outbox?.dead_letter_count || 0}`} />
        <SummaryCard title="شدة المرفقات" value={formatSeverityLabel(operationalHealth.attachment?.severity || 'unknown')} hint={`المعزول: ${operationalHealth.attachment?.quarantined || 0}`} />
        <SummaryCard title="شدة التشغيل" value={formatSeverityLabel(operationalHealth.runtime?.severity || 'unknown')} hint={`المعطل: ${operationalHealth.runtime?.blocked_requests || 0}`} />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <SectionCard title="تفاصيل صحة الإصدار" description="المرجعية النهائية تبقى لملفات الأدلة الرسمية الأحدث.">
          <JsonBlock value={operationalHealth.releaseDetail || operationalHealth.release || {}} />
        </SectionCard>
        <SectionCard title="تفاصيل صندوق الإرسال" description="تشخيص صفوف الخلفية ضمن نطاق المزرعة المختارة مع معاينة آمنة لإعادة المحاولة.">
          <div className="space-y-4">
            <JsonBlock value={operationalHealth.outboxDetail || {}} />
            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">معرّفات صندوق الإرسال</label>
              <input value={outboxActionIdsText} onChange={(event) => setOutboxActionIdsText(event.target.value)} placeholder="مثال: 12, 18, 21" className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" />
              <div className="text-xs text-slate-500 dark:text-slate-400">عدد الصفوف في المعاينة: {selectedOutboxPreview.length}</div>
              {selectedOutboxPreview.length ? <JsonBlock value={selectedOutboxPreview} /> : null}
              <button type="button" onClick={handleOutboxRetry} disabled={!canManageCentralPolicy || submitting || !selectedOutboxActionIds.length} className="rounded-xl bg-sky-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
                إعادة محاولة العناصر المحددة
              </button>
            </div>
          </div>
        </SectionCard>
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <SectionCard title="تفاصيل المرفقات" description="تشخيص حالات الانتظار والعزل والاستحقاق للأرشفة مع معاينة آمنة لإعادة الفحص.">
          <div className="space-y-4">
            <JsonBlock value={operationalHealth.attachmentDetail || operationalHealth.attachment || {}} />
            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">معرّفات المرفقات</label>
              <input value={attachmentActionIdsText} onChange={(event) => setAttachmentActionIdsText(event.target.value)} placeholder="مثال: 7, 8" className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" />
              <div className="text-xs text-slate-500 dark:text-slate-400">عدد الصفوف في المعاينة: {selectedAttachmentPreview.length}</div>
              {selectedAttachmentPreview.length ? <JsonBlock value={selectedAttachmentPreview} /> : null}
              <button type="button" onClick={handleAttachmentRescan} disabled={!canManageCentralPolicy || submitting || !selectedAttachmentActionIds.length} className="rounded-xl bg-amber-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
                إعادة فحص المرفقات المحددة
              </button>
            </div>
          </div>
        </SectionCard>
        <SectionCard title="تشغيل المزرعة" description="تجميع حالة الموافقات وصندوق الإرسال والمرفقات ضمن نطاق المزرعة دون فتح مسارات جديدة.">
          <div className="grid gap-4 lg:grid-cols-2">
            <JsonBlock value={operationalHealth.farmOps || {}} />
            <div className="space-y-4">
              <JsonBlock value={operationalHealth.runtime || {}} />
              <button type="button" onClick={handleMaintenanceDryRun} disabled={!canManageCentralPolicy || submitting} className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900">
                تشغيل معاينة صيانة الحوكمة
              </button>
            </div>
          </div>
        </SectionCard>
      </div>
    </SectionCard>
  )

  const renderPackages = () => (
    <SectionCard
      title="حزم السياسات"
      description="إنشاء وتحديث وتعطيل الحزم المركزية. هذه الحزم مركزية على مستوى القطاع وليست محلية على مستوى المزرعة."
      actions={<ScopeBadge scope="sector" editable={canManageCentralPolicy} />}
    >
      {getSectionError('packages') ? <RestrictionNotice text={getSectionError('packages')} /> : null}
      {!canManageCentralPolicy ? <RestrictionNotice text="هذا القسم يحتاج صلاحية حوكمة لإدارة الحزم المركزية." /> : null}
      <div className="mb-4 grid gap-4 md:grid-cols-3">
        <SummaryCard title="إجمالي الحزم" value={String(policyPackages.length)} hint="كل الحزم المركزية المسجلة" />
        <SummaryCard title="الحزم النشطة" value={String(policyPackages.filter((pkg) => pkg.is_active).length)} hint="قابلة للاستخدام حاليًا" />
        <SummaryCard title="الحزم المعطلة" value={String(policyPackages.filter((pkg) => !pkg.is_active).length)} hint="متوقفة أو غير متاحة" />
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.2fr_1.8fr]">
        <form className="space-y-3" onSubmit={handlePackageSubmit}>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">الاسم</label>
            <input value={packageForm.name} onChange={(event) => setPackageForm((prev) => ({ ...prev, name: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" required />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">المعرّف النصي</label>
            <input value={packageForm.slug} onChange={(event) => setPackageForm((prev) => ({ ...prev, slug: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" required />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">الوصف</label>
            <textarea value={packageForm.description} onChange={(event) => setPackageForm((prev) => ({ ...prev, description: event.target.value }))} rows={4} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input type="checkbox" checked={packageForm.is_active} onChange={(event) => setPackageForm((prev) => ({ ...prev, is_active: event.target.checked }))} />
            الحزمة مفعلة
          </label>
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={!canManageCentralPolicy || submitting} className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
              {packageForm.id ? 'تحديث الحزمة' : 'إنشاء حزمة'}
            </button>
            <button type="button" onClick={resetPackageForm} className="rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-700 dark:border-slate-600 dark:text-slate-200">
              إعادة تعيين
            </button>
          </div>
        </form>

        <div className="space-y-3">
          <SectionToolbar
            searchValue={packageSearch}
            onSearchChange={setPackageSearch}
            searchPlaceholder="بحث بالاسم أو slug"
            filterValue={packageFilter}
            onFilterChange={setPackageFilter}
            filterOptions={[
              { value: 'all', label: 'الكل' },
              { value: 'active', label: 'نشط' },
              { value: 'inactive', label: 'معطل' },
            ]}
          />
          {filteredPackages.length ? (
            filteredPackages.map((pkg) => (
              <div key={pkg.id} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="font-semibold text-slate-900 dark:text-white">{pkg.name}</div>
                      <span className={`rounded-full px-2 py-1 text-xs ${statusTone(pkg.is_active ? 'active' : 'inactive')}`}>{pkg.is_active ? 'نشط' : 'معطل'}</span>
                    </div>
                    <div className="text-sm text-slate-500 dark:text-slate-400">{pkg.slug}</div>
                    <div className="text-sm text-slate-600 dark:text-slate-300">{pkg.description || 'بدون وصف'}</div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <ActionButton label="تحرير" tone="neutral" disabled={!canDo(pkg, 'can_update', canManageCentralPolicy)} disabledReason={permissionReason('إدارة الحزم المركزية')} onClick={() => setPackageForm({ ...pkg })} />
                    <ActionButton
                      label={pkg.is_active ? 'تعطيل' : 'تفعيل'}
                      tone="dark"
                      disabled={!canDo(pkg, 'can_toggle_active', canManageCentralPolicy) || submitting}
                      disabledReason={permissionReason('إدارة الحزم المركزية')}
                      onClick={() =>
                        confirmThen(
                          pkg.is_active ? 'سيتم تعطيل الحزمة المركزية. هل تريد المتابعة؟' : 'سيتم تفعيل الحزمة المركزية. هل تريد المتابعة؟',
                          () => handleApiAction('تم تحديث حالة الحزمة.', async () => { await api.patch(`/policy-packages/${pkg.id}/`, { is_active: !pkg.is_active }) }),
                        )
                      }
                    />
                  </div>
                </div>
              </div>
            ))
          ) : (
            <EmptyState text="لا توجد حزم تطابق عامل التصفية الحالي." />
          )}
        </div>
      </div>
    </SectionCard>
  )

  const renderVersions = () => (
    <div className="space-y-5">
      <SectionCard
        title="إصدارات السياسات"
        description="إدارة المسودات والموافقات ومعاينات الفرق والمحاكاة للإصدارات."
        actions={<ScopeBadge scope="sector" editable={canManageCentralPolicy} />}
      >
        {getSectionError('versions') ? <RestrictionNotice text={getSectionError('versions')} /> : null}
        {!canManageCentralPolicy ? <RestrictionNotice text="هذا القسم يحتاج صلاحية حوكمة لإدارة إصدارات السياسات." /> : null}
        <div className="mb-4 grid gap-4 md:grid-cols-4">
          <SummaryCard title="الإجمالي" value={String(policyVersions.length)} hint="كل الإصدارات المسجلة" />
          <SummaryCard title="المسودات" value={String(policyVersions.filter((item) => item.status === 'draft').length)} hint="بحاجة إلى مراجعة" />
          <SummaryCard title="المعتمدة" value={String(policyVersions.filter((item) => item.status === 'approved').length)} hint="جاهزة للتفعيل" />
          <SummaryCard title="المتقاعدة" value={String(policyVersions.filter((item) => item.status === 'retired').length)} hint="مغلقة إداريًا" />
        </div>
        <div className="grid gap-4 xl:grid-cols-[1.25fr_1.75fr]">
          <form className="space-y-3" onSubmit={handleVersionSubmit}>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">الحزمة</label>
              <select value={versionForm.package} onChange={(event) => setVersionForm((prev) => ({ ...prev, package: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" required>
                <option value="">اختر حزمة</option>
                {policyPackages.map((pkg) => <option key={pkg.id} value={pkg.id}>{pkg.name}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">وسم الإصدار</label>
              <input value={versionForm.version_label} onChange={(event) => setVersionForm((prev) => ({ ...prev, version_label: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" required />
            </div>
            <details className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
              <summary className="cursor-pointer text-sm font-medium text-slate-700 dark:text-slate-300">الإعدادات المتقدمة للإصدار</summary>
              <div className="mt-3 space-y-2">
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  المسار الافتراضي يبدأ من السياسة الفعالة الحالية. افتح هذا القسم فقط إذا كنت تحتاج تحرير الحمولة المرجعية مباشرة.
                </div>
                <textarea value={versionForm.payloadText} onChange={(event) => setVersionForm((prev) => ({ ...prev, payloadText: event.target.value }))} rows={16} className="w-full rounded-xl border border-slate-300 px-3 py-2 font-mono text-xs dark:border-slate-600 dark:bg-slate-900 dark:text-white" />
              </div>
            </details>
            <div className="flex flex-wrap gap-2">
              <button type="submit" disabled={!canManageCentralPolicy || submitting} className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
                {versionForm.id ? 'تحديث المسودة' : 'إنشاء إصدار'}
              </button>
              <button type="button" onClick={() => resetVersionForm()} className="rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-700 dark:border-slate-600 dark:text-slate-200">
                إعادة تعيين
              </button>
            </div>
          </form>

          <div className="space-y-4">
            <SectionToolbar
              searchValue={versionSearch}
              onSearchChange={setVersionSearch}
              searchPlaceholder="بحث باسم الحزمة أو وسم الإصدار"
              filterValue={versionFilter}
              onFilterChange={setVersionFilter}
              filterOptions={[
                { value: 'all', label: 'كل الحالات' },
                { value: 'draft', label: 'مسودة' },
                { value: 'approved', label: 'معتمد' },
                { value: 'retired', label: 'متقاعد' },
              ]}
            />
            <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
              <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">فرق الإصدارات</div>
              <div className="grid gap-3 md:grid-cols-2">
                <select value={diffVersionId} onChange={(event) => setDiffVersionId(event.target.value)} className="rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white">
                  <option value="">اختر الإصدار الأساسي</option>
                  {policyVersions.map((version) => <option key={version.id} value={version.id}>{version.package_name} / {version.version_label}</option>)}
                </select>
                <select value={compareToVersionId} onChange={(event) => setCompareToVersionId(event.target.value)} className="rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white">
                  <option value="">قارن مع السياسة الفعالة للمزرعة</option>
                  {policyVersions.filter((version) => String(version.id) !== String(diffVersionId)).map((version) => <option key={version.id} value={version.id}>{version.package_name} / {version.version_label}</option>)}
                </select>
              </div>
              <div className="mt-3">
                <button type="button" onClick={handleVersionDiff} disabled={!diffVersionId || submitting} className="rounded-xl bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900">
                  توليد الفرق
                </button>
              </div>
              {versionDiff ? (
                <div className="mt-4 space-y-2 text-sm text-slate-700 dark:text-slate-200">
                  <div>comparison_mode: {versionDiff.comparison_mode}</div>
                  <div>عدد التغييرات: {versionDiff.changed_count}</div>
                  <div>الحقول المتغيرة: {(versionDiff.changed_fields || []).join(', ') || 'لا يوجد'}</div>
                  <details>
                    <summary className="cursor-pointer text-xs font-semibold">الفرق الخام</summary>
                    <div className="mt-2"><JsonBlock value={versionDiff} /></div>
                  </details>
                </div>
              ) : null}
            </div>

            {filteredVersions.length ? (
              filteredVersions.map((version) => (
                <div key={version.id} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <div className="font-semibold text-slate-900 dark:text-white">{version.package_name} / {version.version_label}</div>
                        <span className={`rounded-full px-2 py-1 text-xs ${statusTone(version.status)}`}>{formatSeverityLabel(version.status)}</span>
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">approved_at: {formatTimestamp(version.approved_at)}</div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {version.status === 'draft' ? <ActionButton label="تحرير المسودة" tone="neutral" disabled={!canDo(version, 'can_edit_draft', canManageCentralPolicy)} disabledReason={permissionReason('إدارة الإصدارات')} onClick={() => setVersionForm({ id: version.id, package: String(version.package), version_label: version.version_label, payloadText: prettyJson(version.payload) })} /> : null}
                      {version.status === 'draft' ? <ActionButton label="اعتماد" tone="success" disabled={!canDo(version, 'can_approve', canManageCentralPolicy) || submitting} disabledReason={permissionReason('إدارة الإصدارات')} onClick={() => confirmThen('سيتم اعتماد هذا الإصدار وجعله مؤهلًا للتفعيل. هل تريد المتابعة؟', () => policyMutationAction(`/policy-versions/${version.id}/approve/`, 'تم اعتماد إصدار السياسة.'))} /> : null}
                      {version.status === 'approved' ? <ActionButton label="محاكاة" tone="neutral" disabled={!canDo(version, 'can_simulate', true) || submitting} onClick={() => handleVersionSimulation(version.id)} className="border border-blue-300 text-blue-700 dark:border-blue-700 dark:text-blue-300" /> : null}
                      {version.status === 'approved' ? <ActionButton label="تقاعد" tone="danger" disabled={!canDo(version, 'can_retire', canManageCentralPolicy) || submitting} disabledReason={permissionReason('إدارة الإصدارات')} onClick={() => confirmThen('سيتم تقاعد الإصدار المعتمد. هل تريد المتابعة؟', () => policyMutationAction(`/policy-versions/${version.id}/retire/`, 'تم تقاعد إصدار السياسة.'))} /> : null}
                    </div>
                  </div>
                  <details className="mt-3">
                    <summary className="cursor-pointer text-xs font-semibold text-slate-700 dark:text-slate-200">الحمولة</summary>
                    <div className="mt-2"><JsonBlock value={version.payload} /></div>
                  </details>
                </div>
              ))
            ) : (
              <EmptyState text="لا توجد إصدارات سياسة تطابق عامل البحث أو التصفية الحالي." />
            )}

            {versionSimulation ? (
              <SectionCard title="أحدث محاكاة" description="نتيجة التفعيل قبل إنشاء طلب تفعيل.">
                <JsonBlock value={versionSimulation} />
              </SectionCard>
            ) : null}
          </div>
        </div>
      </SectionCard>
    </div>
  )
  const renderActivations = () => (
      <SectionCard
        title="طلبات التفعيل"
        description="إنشاء ومتابعة الإرسال والاعتماد والرفض والتطبيق لطلبات تفعيل إصدارات السياسات."
        actions={<ScopeBadge scope="sector" editable={canManageCentralPolicy} />}
      >
      {getSectionError('activations') ? <RestrictionNotice text={getSectionError('activations')} /> : null}
      {!canManageCentralPolicy ? <RestrictionNotice text="هذا القسم يحتاج صلاحية حوكمة لإدارة طلبات التفعيل." /> : null}
      <div className="mb-4 grid gap-4 md:grid-cols-4">
        <SummaryCard title="الإجمالي" value={String(activationRequests.length)} hint="كل الطلبات المرتبطة بالمزرعة" />
        <SummaryCard title="مسودة / معلقة" value={String(activationRequests.filter((item) => ['draft', 'pending'].includes(item.status)).length)} hint="قيد الإرسال أو الاعتماد" />
        <SummaryCard title="معتمدة" value={String(activationRequests.filter((item) => item.status === 'approved').length)} hint="جاهزة للتطبيق" />
        <SummaryCard title="مطبقة" value={String(activationRequests.filter((item) => item.status === 'applied').length)} hint="أصبحت binding فعالة" />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1fr_1.6fr]">
        <form className="space-y-3" onSubmit={handleActivationCreate}>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">الإصدار المعتمد</label>
            <select value={activationForm.policy_version} onChange={(event) => setActivationForm((prev) => ({ ...prev, policy_version: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" required>
              <option value="">اختر إصدارًا معتمدًا</option>
              {policyVersions.filter((item) => item.status === 'approved').map((version) => <option key={version.id} value={version.id}>{version.package_name} / {version.version_label}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">نافذ من</label>
            <input type="datetime-local" value={activationForm.effective_from} onChange={(event) => setActivationForm((prev) => ({ ...prev, effective_from: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">المبرر</label>
            <textarea rows={4} value={activationForm.rationale} onChange={(event) => setActivationForm((prev) => ({ ...prev, rationale: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" />
          </div>
          <button type="submit" disabled={!canManageCentralPolicy || submitting} className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
            إنشاء طلب تفعيل
          </button>
        </form>

        <div className="space-y-3">
          <SectionToolbar
            searchValue={activationSearch}
            onSearchChange={setActivationSearch}
            searchPlaceholder="بحث في الطلبات أو المبرر"
            filterValue={activationFilter}
            onFilterChange={setActivationFilter}
            filterOptions={[
              { value: 'all', label: 'كل الحالات' },
              { value: 'draft', label: 'مسودة' },
              { value: 'pending', label: 'معلق' },
              { value: 'approved', label: 'معتمد' },
              { value: 'applied', label: 'مطبق' },
              { value: 'rejected', label: 'مرفوض' },
            ]}
          />
          {filteredActivations.length ? (
            filteredActivations.map((item) => (
              <div key={item.id} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="font-semibold text-slate-900 dark:text-white">{item.policy_package_name} / {item.policy_version_label}</div>
                      <span className={`rounded-full px-2 py-1 text-xs ${statusTone(item.status)}`}>{formatSeverityLabel(item.status)}</span>
                    </div>
                    <div className="text-sm text-slate-500 dark:text-slate-400">effective_from: {formatTimestamp(item.effective_from)}</div>
                    <div className="text-sm text-slate-600 dark:text-slate-300">{item.rationale || 'بدون rationale'}</div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {item.status === 'draft' ? <ActionButton label="إرسال" tone="neutral" disabled={!canDo(item, 'can_submit', canManageCentralPolicy) || submitting} disabledReason={permissionReason('إدارة طلبات التفعيل')} onClick={() => confirmThen('سيتم إرسال طلب التفعيل للمراجعة. هل تريد المتابعة؟', () => policyMutationAction(`/policy-activation-requests/${item.id}/submit/`, 'تم إرسال طلب التفعيل.'))} /> : null}
                    {['draft', 'pending'].includes(item.status) ? <ActionButton label="اعتماد" tone="success" disabled={!canDo(item, 'can_approve', canManageCentralPolicy) || submitting} disabledReason={permissionReason('إدارة طلبات التفعيل')} onClick={() => confirmThen('سيتم اعتماد طلب التفعيل. هل تريد المتابعة؟', () => policyMutationAction(`/policy-activation-requests/${item.id}/approve/`, 'تم اعتماد طلب التفعيل.'))} /> : null}
                    {item.status !== 'applied' ? <ActionButton label="رفض" tone="danger" disabled={!canDo(item, 'can_reject', canManageCentralPolicy) || submitting} disabledReason={permissionReason('إدارة طلبات التفعيل')} onClick={() => confirmThen('سيتم رفض طلب التفعيل. هل تريد المتابعة؟', () => policyMutationAction(`/policy-activation-requests/${item.id}/reject/`, 'تم رفض طلب التفعيل.', { note: 'تم الرفض من منصة الحوكمة.' }))} /> : null}
                    {item.status === 'approved' ? <ActionButton label="تطبيق" tone="dark" disabled={!canDo(item, 'can_apply', canManageCentralPolicy) || submitting} disabledReason={permissionReason('إدارة طلبات التفعيل')} onClick={() => confirmThen('سيتم تطبيق الربط الفعال على المزرعة. هل تريد المتابعة؟', () => policyMutationAction(`/policy-activation-requests/${item.id}/apply/`, 'تم تطبيق binding السياسة على المزرعة.'))} /> : null}
                  </div>
                </div>
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs font-semibold text-slate-700 dark:text-slate-200">المحاكاة والأحداث</summary>
                  <div className="mt-3 grid gap-3 lg:grid-cols-2">
                    <JsonBlock value={item.simulate_summary || {}} />
                    <JsonBlock value={item.events || []} />
                  </div>
                </details>
              </div>
            ))
          ) : (
            <EmptyState text="لا توجد طلبات تفعيل تطابق عامل البحث أو التصفية الحالي." />
          )}
        </div>
      </div>
    </SectionCard>
  )

  const renderExceptions = () => (
    <SectionCard
      title="طلبات استثناء المزرعة"
      description="استثناءات محدودة زمنيًا فوق السياسة المركزية، مع حقول مسموح بها فقط."
      actions={<ScopeBadge scope="farm" editable={canManageCentralPolicy} />}
    >
      {getSectionError('exceptions') ? <RestrictionNotice text={getSectionError('exceptions')} /> : null}
      {!canManageCentralPolicy ? <RestrictionNotice text="هذا القسم يحتاج صلاحية حوكمة لإدارة استثناءات المزرعة." /> : null}
      <div className="mb-4 grid gap-4 md:grid-cols-4">
        <SummaryCard title="الإجمالي" value={String(exceptionRequests.length)} hint="كل طلبات الاستثناء للمزرعة" />
        <SummaryCard title="المفتوحة" value={String(exceptionRequests.filter((item) => ['draft', 'pending', 'approved'].includes(item.status)).length)} hint="بحاجة متابعة أو تطبيق" />
        <SummaryCard title="المطبقة" value={String(exceptionRequests.filter((item) => item.status === 'applied').length)} hint="استثناءات فعالة" />
        <SummaryCard title="المرفوضة / المنتهية" value={String(exceptionRequests.filter((item) => ['rejected', 'expired'].includes(item.status)).length)} hint="مغلقة أو منتهية" />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1fr_1.6fr]">
        <form className="space-y-3" onSubmit={handleExceptionCreate}>
          <div className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-3 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-900/20 dark:text-amber-300">
            الحقول المسموح استثناؤها: thresholds، attachment tuning، remote review windows، وبعض toggles التشغيلية المحدودة. لا يسمح باستثناء `mode` أو أي invariant يكسر SIMPLE/STRICT.
          </div>
          <details className="rounded-xl border border-slate-200 p-3 dark:border-slate-700" open>
            <summary className="cursor-pointer text-sm font-medium text-slate-700 dark:text-slate-300">الوضع المتقدم لتصحيح الاستثناء</summary>
            <div className="mt-3 space-y-2">
              <div className="text-xs text-slate-500 dark:text-slate-400">
                استخدم هذا القسم لتعديل patch المسموحة فقط. الأفضل أن يبقى الاستخدام محدودًا ومسبقًا بمبرر واضح.
              </div>
              <textarea rows={12} value={exceptionForm.requested_patch_text} onChange={(event) => setExceptionForm((prev) => ({ ...prev, requested_patch_text: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 font-mono text-xs dark:border-slate-600 dark:bg-slate-900 dark:text-white" />
            </div>
          </details>
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">نافذ من</label>
              <input type="datetime-local" value={exceptionForm.effective_from} onChange={(event) => setExceptionForm((prev) => ({ ...prev, effective_from: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">نافذ حتى</label>
              <input type="datetime-local" value={exceptionForm.effective_to} onChange={(event) => setExceptionForm((prev) => ({ ...prev, effective_to: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">المبرر</label>
            <textarea rows={3} value={exceptionForm.rationale} onChange={(event) => setExceptionForm((prev) => ({ ...prev, rationale: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" />
          </div>
          <button type="submit" disabled={!canManageCentralPolicy || submitting} className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
            إنشاء طلب استثناء
          </button>
        </form>

        <div className="space-y-3">
          <SectionToolbar
            searchValue={exceptionSearch}
            onSearchChange={setExceptionSearch}
            searchPlaceholder="بحث في الحقول أو المبرر"
            filterValue={exceptionFilter}
            onFilterChange={setExceptionFilter}
            filterOptions={[
              { value: 'all', label: 'كل الحالات' },
              { value: 'draft', label: 'مسودة' },
              { value: 'pending', label: 'معلق' },
              { value: 'approved', label: 'معتمد' },
              { value: 'applied', label: 'مطبق' },
              { value: 'rejected', label: 'مرفوض' },
              { value: 'expired', label: 'منتهي' },
            ]}
          />
          {filteredExceptions.length ? (
            filteredExceptions.map((item) => (
              <div key={item.id} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="font-semibold text-slate-900 dark:text-white">استثناء #{item.id}</div>
                      <span className={`rounded-full px-2 py-1 text-xs ${statusTone(item.status)}`}>{formatSeverityLabel(item.status)}</span>
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">effective_from: {formatTimestamp(item.effective_from)} | effective_to: {formatTimestamp(item.effective_to)}</div>
                    <div className="text-sm text-slate-600 dark:text-slate-300">الحقول: {(item.policy_fields || []).join(', ') || 'لا يوجد'}</div>
                    <div className="text-sm text-slate-600 dark:text-slate-300">{item.rationale || 'بدون rationale'}</div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {item.status === 'draft' ? <ActionButton label="إرسال" tone="neutral" disabled={!canDo(item, 'can_submit', canManageCentralPolicy) || submitting} disabledReason={permissionReason('إدارة الاستثناءات')} onClick={() => confirmThen('سيتم إرسال طلب الاستثناء للمراجعة. هل تريد المتابعة؟', () => policyMutationAction(`/policy-exception-requests/${item.id}/submit/`, 'تم إرسال طلب الاستثناء.'))} /> : null}
                    {['draft', 'pending'].includes(item.status) ? <ActionButton label="اعتماد" tone="success" disabled={!canDo(item, 'can_approve', canManageCentralPolicy) || submitting} disabledReason={permissionReason('إدارة الاستثناءات')} onClick={() => confirmThen('سيتم اعتماد طلب الاستثناء. هل تريد المتابعة؟', () => policyMutationAction(`/policy-exception-requests/${item.id}/approve/`, 'تم اعتماد طلب الاستثناء.'))} /> : null}
                    {!['applied', 'expired'].includes(item.status) ? <ActionButton label="رفض" tone="danger" disabled={!canDo(item, 'can_reject', canManageCentralPolicy) || submitting} disabledReason={permissionReason('إدارة الاستثناءات')} onClick={() => confirmThen('سيتم رفض طلب الاستثناء. هل تريد المتابعة؟', () => policyMutationAction(`/policy-exception-requests/${item.id}/reject/`, 'تم رفض طلب الاستثناء.', { note: 'تم الرفض من منصة الحوكمة.' }))} /> : null}
                    {item.status === 'approved' ? <ActionButton label="تطبيق" tone="dark" disabled={!canDo(item, 'can_apply', canManageCentralPolicy) || submitting} disabledReason={permissionReason('إدارة الاستثناءات')} onClick={() => confirmThen('سيتم تطبيق الاستثناء المحدود على المزرعة. هل تريد المتابعة؟', () => policyMutationAction(`/policy-exception-requests/${item.id}/apply/`, 'تم تطبيق الاستثناء المحدود.'))} /> : null}
                  </div>
                </div>
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs font-semibold text-slate-700 dark:text-slate-200">التصحيح والأحداث</summary>
                  <div className="mt-3 grid gap-3 lg:grid-cols-2">
                    <JsonBlock value={item.requested_patch || {}} />
                    <JsonBlock value={item.events || []} />
                  </div>
                </details>
              </div>
            ))
          ) : (
            <EmptyState text="لا توجد استثناءات تطابق عامل البحث أو التصفية الحالي." />
          )}
        </div>
      </div>
    </SectionCard>
  )

  const renderDelegations = () => (
    <SectionCard
      title="تفويضات الأدوار"
      description="إدارة تفويضات الأدوار بزمن محدد مع بقاء الدور الأصلي والمراجعة ضمن نطاق المزرعة."
      actions={<ScopeBadge scope="farm" editable={Boolean(delegationMeta?.can_manage)} />}
    >
      {getSectionError('delegations') ? <RestrictionNotice text={getSectionError('delegations')} /> : null}
      {!delegationMeta?.can_manage ? <RestrictionNotice text="يمكنك قراءة التفويضات، لكن إدارة التفويض تتطلب صلاحية مزرعة إدارية أو صلاحيات تعديل تفويضات." /> : null}
      {!membershipMeta?.can_manage ? <RestrictionNotice text="إدارة عضويات المزرعة غير متاحة لهذا المستخدم، لذلك يقتصر اختيار المفوِّضين على ما تم تحميله للقراءة فقط." /> : null}
      <div className="mb-4 grid gap-4 md:grid-cols-4">
        <SummaryCard title="إجمالي التفويضات" value={String(delegations.length)} hint="كل التفويضات المرتبطة بالمزرعة" />
        <SummaryCard title="سارية الآن" value={String(delegations.filter((item) => item.is_currently_effective).length)} hint="ضمن نافذة التفعيل الحالية" />
        <SummaryCard title="نشطة مستقبلية" value={String(delegations.filter((item) => !item.is_currently_effective && item.is_active).length)} hint="نشطة لكنها لم تدخل نافذة السريان" />
        <SummaryCard title="عضويات المزرعة" value={String(farmMembers.length)} hint="قاعدة الاختيار للمفوِّضين" />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1fr_1.6fr]">
        <form className="space-y-3 rounded-xl border border-slate-200 p-4 dark:border-slate-700" onSubmit={handleDelegationSubmit}>
          <div className="text-sm font-semibold text-slate-900 dark:text-white">إدارة تفويض</div>
          <div className="text-xs text-slate-500 dark:text-slate-400">
            اختر مفوِّضًا يحمل الدور فعليًا داخل المزرعة، ثم حدّد المفوَّض إليه والفترة الزمنية. يبقى هذا الإجراء محكومًا بحدود الصلاحية الخلفية.
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">المفوِّض</label>
            <select
              value={delegationForm.principal_user}
              onChange={(event) => setDelegationForm((prev) => ({ ...prev, principal_user: event.target.value }))}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
              disabled={!delegationMeta?.can_create && !delegationForm.id}
            >
              <option value="">اختر عضوًا من عضويات المزرعة</option>
              {farmMembers.map((member) => (
                <option key={member.id} value={member.user_id || member.user}>
                  {(member.full_name || member.username)} - {member.role}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">الدور المفوَّض</label>
            <select
              value={delegationForm.role}
              onChange={(event) => setDelegationForm((prev) => ({ ...prev, role: event.target.value }))}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
              disabled={!delegationMeta?.can_manage}
            >
              <option value="">اختر دورًا</option>
              {delegationRoles.map((role) => (
                <option key={role.value} value={role.value}>
                  {role.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">بحث عن المفوَّض إليه</label>
            <div className="flex gap-2">
              <input
                value={delegateSearchTerm}
                onChange={(event) => setDelegateSearchTerm(event.target.value)}
                placeholder="ابحث باسم المستخدم أو الاسم الكامل"
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                disabled={!delegationMeta?.can_manage}
              />
              <ActionButton label="بحث" tone="neutral" disabled={!delegationMeta?.can_manage || !delegateSearchTerm.trim()} onClick={handleDelegateSearch} />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">المفوَّض إليه</label>
            <select
              value={delegationForm.delegate_user}
              onChange={(event) => setDelegationForm((prev) => ({ ...prev, delegate_user: event.target.value }))}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white"
              disabled={!delegationMeta?.can_manage}
            >
              <option value="">اختر مستخدمًا</option>
              {delegateUserOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {(option.full_name || option.username)}{option.email ? ` - ${option.email}` : ''}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">من</label>
              <input type="datetime-local" value={delegationForm.starts_at} onChange={(event) => setDelegationForm((prev) => ({ ...prev, starts_at: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" disabled={!delegationMeta?.can_manage} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">حتى</label>
              <input type="datetime-local" value={delegationForm.ends_at} onChange={(event) => setDelegationForm((prev) => ({ ...prev, ends_at: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" disabled={!delegationMeta?.can_manage} />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">السبب</label>
            <textarea value={delegationForm.reason} onChange={(event) => setDelegationForm((prev) => ({ ...prev, reason: event.target.value }))} rows={3} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" disabled={!delegationMeta?.can_manage} />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input type="checkbox" checked={delegationForm.is_active} onChange={(event) => setDelegationForm((prev) => ({ ...prev, is_active: event.target.checked }))} disabled={!delegationMeta?.can_manage} />
            التفويض نشط
          </label>
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={(delegationForm.id ? !delegationMeta?.can_update : !delegationMeta?.can_create) || submitting} className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
              {delegationForm.id ? 'تحديث التفويض' : 'إنشاء تفويض'}
            </button>
            <button type="button" onClick={() => resetDelegationForm()} className="rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-700 dark:border-slate-600 dark:text-slate-200">
              إعادة تعيين
            </button>
          </div>
        </form>
        <div className="space-y-3">
          <SectionToolbar
            searchValue={delegationSearch}
            onSearchChange={setDelegationSearch}
            searchPlaceholder="بحث في المفوِّض أو المفوَّض إليه أو السبب"
            filterValue={delegationFilter}
            onFilterChange={setDelegationFilter}
            filterOptions={[
              { value: 'all', label: 'كل الحالات' },
              { value: 'current', label: 'ساري الآن' },
              { value: 'active', label: 'نشط' },
              { value: 'inactive', label: 'معطل' },
            ]}
          />
          {filteredDelegations.length ? (
            <div className="space-y-3">
              {filteredDelegations.map((item) => (
                <div key={item.id} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="font-semibold text-slate-900 dark:text-white">{item.principal_username} ← {item.delegate_username}</div>
                        <span className={`rounded-full px-2 py-1 text-xs ${statusTone(item.is_currently_effective ? 'active' : item.is_active ? 'pending' : 'inactive')}`}>
                          {item.is_currently_effective ? 'ساري الآن' : item.is_active ? 'ضمن نافذة التفعيل' : 'معطل'}
                        </span>
                      </div>
                      <div className="text-sm text-slate-600 dark:text-slate-300">الدور: {item.role}</div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">من: {formatTimestamp(item.starts_at)} | حتى: {formatTimestamp(item.ends_at)}</div>
                      <div className="text-sm text-slate-500 dark:text-slate-400">{item.reason || 'بدون سبب'}</div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <ActionButton
                        label="تحرير"
                        tone="neutral"
                        disabled={!canDo(item, 'can_update', Boolean(delegationMeta?.can_update))}
                        disabledReason="يتطلب هذا الإجراء صلاحية تعديل التفويضات."
                        onClick={() => resetDelegationForm(item)}
                      />
                      <ActionButton
                        label="حذف"
                        tone="danger"
                        disabled={!canDo(item, 'can_delete', Boolean(delegationMeta?.can_delete)) || submitting}
                        disabledReason="يتطلب هذا الإجراء صلاحية حذف التفويضات."
                        onClick={() => confirmThen('سيتم حذف التفويض الحالي. هل تريد المتابعة؟', () => handleDelegationDelete(item.id))}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState text="لا توجد تفويضات تطابق عامل البحث أو التصفية الحالي." />
          )}
        </div>
      </div>
    </SectionCard>
  )

  const renderGovernanceProfile = () => (
    <div className="space-y-5">
    <SectionCard
      title="ملف الحوكمة"
      description="عرض ملف الحوكمة الحالي للمزرعة، مع تصحيح محلي محدود ومسبوق بمعاينة فرق."
      actions={<ScopeBadge scope="farm" editable={canManageGovernanceProfile} />}
    >
        {getSectionError('profile') ? <RestrictionNotice text={getSectionError('profile')} /> : null}
        {!canManageGovernanceProfile ? <RestrictionNotice text="هذا القسم يحتاج صلاحية تعديل إعدادات الحوكمة للمزرعة." /> : null}
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
          <form className="space-y-3 rounded-xl border border-slate-200 p-4 dark:border-slate-700" onSubmit={handleGovernanceProfileSubmit}>
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-semibold text-slate-900 dark:text-white">ملف حوكمة المزرعة</div>
              <span className="rounded-full bg-sky-100 px-2 py-1 text-xs text-sky-800 dark:bg-sky-900/30 dark:text-sky-300">مزرعة</span>
            </div>
            {selectedGovernanceProfile ? (
              <div className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-900/40 dark:text-slate-300">
                الفئة الحالية: {selectedGovernanceProfile.tier} | الفئة المقترحة: {selectedGovernanceProfile.suggested_tier} | تاريخ الاعتماد: {formatTimestamp(selectedGovernanceProfile.approved_at)}
              </div>
            ) : (
              <div className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-900/40 dark:text-slate-300">
                لا يوجد ملف حوكمة مسجل بعد. يمكنك إنشاء ملف أولي لهذه المزرعة من هنا.
              </div>
            )}
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">الفئة</label>
              <select value={governanceProfileForm.tier} onChange={(event) => setGovernanceProfileForm((prev) => ({ ...prev, tier: event.target.value }))} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white">
                <option value="SMALL">SMALL</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LARGE">LARGE</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">المبرر</label>
              <textarea value={governanceProfileForm.rationale} onChange={(event) => setGovernanceProfileForm((prev) => ({ ...prev, rationale: event.target.value }))} rows={4} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-white" />
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="submit" disabled={!canManageGovernanceProfile || submitting} className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
                {governanceProfileForm.id ? 'تحديث ملف الحوكمة' : 'إنشاء ملف الحوكمة'}
              </button>
              <button type="button" onClick={() => resetGovernanceProfileForm()} className="rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-700 dark:border-slate-600 dark:text-slate-200">
                إعادة تعبئة
              </button>
            </div>
          </form>

          <div className="space-y-3 rounded-xl border border-slate-200 p-4 dark:border-slate-700">
            <div className="text-sm font-semibold text-blue-900 dark:text-blue-200">إدارة إعدادات المزرعة</div>
            <div className="text-xs text-blue-600 dark:text-blue-400 mb-2">
              تم نقل التحكم بالتوجيه الاستراتيجي والتشغيلي للمزرعة إلى التبويب المخصص &quot;إعدادات المزرعة&quot; لتوفير واجهة آمنة وموجهة تلغي الحاجة للتعديل اليدوي المعقد للبيانات.
            </div>
          </div>
        </div>
      </SectionCard>
    </div>
  )

  if (!hasFarms) return <EmptyState text="حدد مزرعة أولًا حتى تظهر منصة الحوكمة والسياسات." />

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">منصة الحوكمة والسياسات</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500 dark:text-slate-400">
              منصة حوكمة تشغيلية موحدة تجمع القراءة والتشخيص والإدارة المركزية وحوكمة المزرعة داخل سطح واحد، مع إيضاح النطاق والصلاحية قبل أي إجراء.
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <SummaryCard title="المزرعة" value={selectedFarmId || 'غير متاح'} hint="نطاق المزرعة" />
            <SummaryCard title="حزم السياسات" value={String(policyPackages.length)} hint="عدد الحزم المركزية" />
            <SummaryCard title="طلبات التفعيل" value={String(activationRequests.length)} hint="طلبات التفعيل لهذه المزرعة" />
          </div>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-4">
          <SummaryCard title="الوضع الحالي" value={formatPolicyValue(settingsRecord?.mode || 'غير متاح')} hint={formatPolicySource(settingsRecord?.policy_source || 'unknown')} />
          <SummaryCard title="صلاحية الإدارة المركزية" value={canManageCentralPolicy ? 'متاحة' : 'للقراءة فقط'} hint="حزم، إصدارات، وتفعيل" />
          <SummaryCard title="صلاحية حوكمة المزرعة" value={canManageGovernanceProfile ? 'متاحة' : 'للقراءة فقط'} hint="ملف الحوكمة والإسقاط المحلي" />
          <SummaryCard title="المجموعة النشطة" value={currentTabGroup.title} hint={currentTabGroup.scope} />
        </div>
      </div>

      {message ? <div className="rounded-xl border border-green-300 bg-green-50 px-4 py-3 text-sm text-green-800 dark:border-green-900 dark:bg-green-900/20 dark:text-green-300">{message}</div> : null}
      {error ? <div className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-900/20 dark:text-red-300">{error}</div> : null}

      <div className="grid gap-4 xl:grid-cols-3">
        {TAB_GROUPS.map((group) => (
          <div key={group.key} className={`rounded-2xl border p-4 shadow-sm ${currentTabGroup.key === group.key ? 'border-primary/40 bg-primary/5 dark:border-primary/40 dark:bg-primary/10' : 'border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800'}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-slate-900 dark:text-white">{group.title}</div>
                <div className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">{group.description}</div>
              </div>
              <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] text-slate-700 dark:bg-slate-700 dark:text-slate-200">{group.scope}</span>
            </div>
            <div className="mt-3">
              <SummaryCard title={governanceSummary[group.key]?.title || 'الملخص'} value={String(governanceSummary[group.key]?.count || 0)} hint={governanceSummary[group.key]?.hint || ''} />
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {group.tabs.map((tabKey) => (
                <button
                  key={tabKey}
                  type="button"
                  onClick={() => changeTab(tabKey)}
                  className={`rounded-full px-3 py-2 text-sm font-medium transition ${activeTab === tabKey ? 'bg-primary text-white shadow' : 'bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600'}`}
                >
                  {TAB_MAP[tabKey]?.label || tabKey}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {loading ? (
        <SectionCard title="جار التحميل" description="يتم تحميل بيانات منصة الحوكمة والسياسات.">
          <div className="text-sm text-slate-500 dark:text-slate-400">جارٍ تحميل البيانات...</div>
        </SectionCard>
      ) : null}

      {!loading && activeTab === 'effective' ? renderEffectivePolicy() : null}
      {!loading && activeTab === 'usage' ? renderPackageUsage() : null}
      {!loading && activeTab === 'timeline' ? renderActivationTimeline() : null}
      {!loading && activeTab === 'pressure' ? renderExceptionPressure() : null}
      {!loading && activeTab === 'impact' ? renderFarmImpact() : null}
      {!loading && activeTab === 'ops' ? renderOperationalHealth() : null}
      {!loading && activeTab === 'packages' ? renderPackages() : null}
      {!loading && activeTab === 'versions' ? renderVersions() : null}
      {!loading && activeTab === 'activations' ? renderActivations() : null}
      {!loading && activeTab === 'exceptions' ? renderExceptions() : null}
      {!loading && activeTab === 'delegations' ? renderDelegations() : null}
      {!loading && activeTab === 'profile' ? renderGovernanceProfile() : null}
    </div>
  )
}
