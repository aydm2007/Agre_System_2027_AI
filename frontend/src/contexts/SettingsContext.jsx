import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import { useFarmContext } from '../api/farmContext'
import { useAuth } from '../auth/AuthContext'

const SettingsContext = createContext(null)

export function SettingsProvider({ children }) {
  const { selectedFarmId } = useFarmContext()
  const { setStrictErpModeValue, refreshSystemMode, isAuthenticated } = useAuth()
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const buildSimpleFallback = useCallback(
    () => ({
      farm: selectedFarmId,
      mode: 'SIMPLE',
      mode_label: 'نظام مبسط (Shadow)',
      visibility_level: 'operations_only',
      enable_zakat: true,
      enable_depreciation: true,
      enable_sharecropping: false,
      sharecropping_mode: 'FINANCIAL',
      enable_petty_cash: true,
      variance_behavior: 'warn',
      cost_visibility: 'summarized_amounts',
      approval_profile: 'tiered',
      contract_mode: 'operational_only',
      treasury_visibility: 'hidden',
      fixed_asset_mode: 'tracking_only',
      procurement_committee_threshold: 500000,
      remote_site: false,
      single_finance_officer_allowed: false,
      local_finance_threshold: 100000,
      sector_review_threshold: 250000,
      mandatory_attachment_for_cash: true,
      weekly_remote_review_required: false,
      attachment_transient_ttl_days: 30,
      approved_attachment_archive_after_days: 7,
      attachment_max_upload_size_mb: 10,
      attachment_scan_mode: 'heuristic',
      attachment_require_clean_scan_for_strict: true,
      attachment_enable_cdr: false,
      offline_cache_retention_days: 7,
      synced_draft_retention_days: 3,
      dead_letter_retention_days: 14,
      enable_offline_media_purge: false,
      enable_offline_conflict_resolution: false,
      enable_predictive_alerts: false,
      enable_local_purge_audit: false,
      allow_overlapping_crop_plans: false,
      allow_multi_location_activities: true,
      allow_cross_plan_activities: false,
      allow_creator_self_variance_approval: false,
      show_daily_log_smart_card: true,
      show_advanced_reports: false,
      policy_source: 'fallback:farm_settings_table_missing',
      active_policy_binding: null,
      active_policy_exception: null,
      policy_field_catalog: {},
      legacy_mode_divergence: { detected: false, warning: '' },
      policy_validation_errors: [],
      effective_policy_fields: [],
      policy_snapshot: {
        mode: 'SIMPLE',
        mode_label: 'نظام مبسط (Shadow)',
        visibility_level: 'operations_only',
        variance_behavior: 'warn',
        cost_visibility: 'summarized_amounts',
        approval_profile: 'tiered',
        contract_mode: 'operational_only',
        treasury_visibility: 'hidden',
        fixed_asset_mode: 'tracking_only',
        enable_zakat: true,
        enable_depreciation: true,
        enable_sharecropping: false,
        sharecropping_mode: 'FINANCIAL',
        enable_petty_cash: true,
        remote_site: false,
        single_finance_officer_allowed: false,
        local_finance_threshold: 100000,
        sector_review_threshold: 250000,
        mandatory_attachment_for_cash: true,
        weekly_remote_review_required: false,
        attachment_transient_ttl_days: 30,
        approved_attachment_archive_after_days: 7,
        attachment_max_upload_size_mb: 10,
        attachment_scan_mode: 'heuristic',
        attachment_require_clean_scan_for_strict: true,
        attachment_enable_cdr: false,
        offline_cache_retention_days: 7,
        synced_draft_retention_days: 3,
        dead_letter_retention_days: 14,
        enable_offline_media_purge: false,
        enable_offline_conflict_resolution: false,
        enable_predictive_alerts: false,
        enable_local_purge_audit: false,
        allow_overlapping_crop_plans: false,
        allow_multi_location_activities: true,
        allow_cross_plan_activities: false,
        allow_creator_self_variance_approval: false,
        show_daily_log_smart_card: true,
        show_advanced_reports: false,
      },
      effective_policy_payload: {
        dual_mode_policy: {},
        finance_threshold_policy: {},
        attachment_policy: {},
        contract_policy: {},
        agronomy_execution_policy: {},
        remote_review_policy: {},
      },
      effective_policy_flat: {},
    }),
    [selectedFarmId],
  )

  const fetchSettings = useCallback(async () => {
    if (!selectedFarmId || !isAuthenticated) {
      setSettings(null)
      setError(null)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const { data } = await api.get(`/farm-settings/`, { params: { farm: selectedFarmId, _t: Date.now() } })
      if (Array.isArray(data?.results) && data.results.length > 0) {
        const resolved = data.results[0]
        setSettings(resolved)
        setStrictErpModeValue(resolved.mode === 'STRICT')
      } else {
        const fallback = buildSimpleFallback()
        setSettings(fallback)
        setStrictErpModeValue(false)
      }
    } catch (err) {
      const status = err?.response?.status
      if (status === 403 || status === 404 || status === 500) {
        console.warn('Farm settings unavailable; falling back to SIMPLE defaults.', err)
      } else {
        console.error('Failed to fetch farm settings', err)
      }
      setError('???? ????? ??????? ???????? ?? ????? ????? ?????? ??????.')
      const fallback = buildSimpleFallback()
      setSettings(fallback)
      setStrictErpModeValue(false)
    } finally {
      setLoading(false)
    }
  }, [selectedFarmId, isAuthenticated, setStrictErpModeValue, buildSimpleFallback])

  useEffect(() => {
    fetchSettings()
  }, [fetchSettings])

  const updateSettings = async (payload) => {
    if (!selectedFarmId) {
      throw new Error('Farm context is required before updating settings')
    }

    let settingsId = settings?.id
    if (!settingsId) {
      const lookup = await api.get(`/farm-settings/`, { params: { farm: selectedFarmId, _t: Date.now() } })
      settingsId = lookup.data?.results?.[0]?.id
      if (!settingsId) {
        throw new Error('FarmSettings bootstrap failed')
      }
    }

    const { data } = await api.patch(`/farm-settings/${settingsId}/`, payload)
    setSettings(data)
    setStrictErpModeValue(data.mode === 'STRICT')
    await refreshSystemMode(selectedFarmId)
    return data
  }

  const fetchPolicyDiff = async (payload) => {
    if (!selectedFarmId) {
      throw new Error('Farm context is required before diffing settings')
    }
    let settingsId = settings?.id
    if (!settingsId) {
      const lookup = await api.get(`/farm-settings/`, { params: { farm: selectedFarmId, _t: Date.now() } })
      settingsId = lookup.data?.results?.[0]?.id
      if (!settingsId) {
        throw new Error('FarmSettings bootstrap failed')
      }
    }
    const { data } = await api.post(`/farm-settings/${settingsId}/policy-diff/`, payload)
    return data
  }

  const isStrictMode = settings?.mode === 'STRICT'
  const isZakatEnabled = settings?.enable_zakat ?? true
  const isDepreciationEnabled = settings?.enable_depreciation ?? true
  const isSharecroppingEnabled = settings?.enable_sharecropping ?? false
  const isPettyCashEnabled = settings?.enable_petty_cash ?? true

  return (
    <SettingsContext.Provider
      value={{
        settings,
        loading,
        error,
        fetchSettings,
        updateSettings,
        fetchPolicyDiff,
        isStrictMode,
        isZakatEnabled,
        isDepreciationEnabled,
        isSharecroppingEnabled,
        isPettyCashEnabled,
        modeLabel: settings?.mode_label ?? 'نظام مبسط (Shadow)',
        visibilityLevel: settings?.visibility_level ?? 'operations_only',
        varianceBehavior: settings?.variance_behavior ?? 'warn',
        costVisibility: settings?.cost_visibility ?? 'summarized_amounts',
        approvalProfile: settings?.approval_profile ?? 'tiered',
        contractMode: settings?.contract_mode ?? 'operational_only',
        treasuryVisibility: settings?.treasury_visibility ?? 'hidden',
        fixedAssetMode: settings?.fixed_asset_mode ?? 'tracking_only',
        policySnapshot: settings?.policy_snapshot ?? buildSimpleFallback().policy_snapshot,
        effectivePolicyPayload:
          settings?.effective_policy_payload ?? buildSimpleFallback().effective_policy_payload,
        effectivePolicyFlat:
          settings?.effective_policy_flat ?? buildSimpleFallback().effective_policy_flat,
        policySource: settings?.policy_source ?? 'farm_settings',
        activePolicyBinding: settings?.active_policy_binding ?? null,
        activePolicyException: settings?.active_policy_exception ?? null,
        policyFieldCatalog: settings?.policy_field_catalog ?? {},
        policyValidationErrors: settings?.policy_validation_errors ?? [],
        effectivePolicyFields: settings?.effective_policy_fields ?? [],
        legacyModeDivergence:
          settings?.legacy_mode_divergence ?? { detected: false, warning: '' },
        allowOverlappingPlans: settings?.allow_overlapping_crop_plans ?? false,
        allowMultiLocationActivities: settings?.allow_multi_location_activities ?? true,
        allowCrossPlanActivities: settings?.allow_cross_plan_activities ?? false,
        allowCreatorSelfVarianceApproval:
          settings?.allow_creator_self_variance_approval ?? false,
        showDailyLogSmartCard: settings?.show_daily_log_smart_card ?? true,
        showAdvancedReports: settings?.show_advanced_reports ?? false,
        remoteSite: settings?.remote_site ?? false,
        singleFinanceOfficerAllowed: settings?.single_finance_officer_allowed ?? false,
        localFinanceThreshold: settings?.local_finance_threshold ?? 100000,
        sectorReviewThreshold: settings?.sector_review_threshold ?? 250000,
        mandatoryAttachmentForCash: settings?.mandatory_attachment_for_cash ?? true,
        weeklyRemoteReviewRequired: settings?.weekly_remote_review_required ?? false,
        attachmentTransientTtlDays: settings?.attachment_transient_ttl_days ?? 30,
        approvedAttachmentArchiveAfterDays:
          settings?.approved_attachment_archive_after_days ?? 7,
        attachmentMaxUploadSizeMb: settings?.attachment_max_upload_size_mb ?? 10,
        attachmentScanMode: settings?.attachment_scan_mode ?? 'heuristic',
        attachment_require_clean_scan_for_strict:
          settings?.attachment_require_clean_scan_for_strict ?? true,
        attachment_enable_cdr: settings?.attachment_enable_cdr ?? false,
        offlineCacheRetentionDays: settings?.offline_cache_retention_days ?? 7,
        syncedDraftRetentionDays: settings?.synced_draft_retention_days ?? 3,
        deadLetterRetentionDays: settings?.dead_letter_retention_days ?? 14,
        enableOfflineMediaPurge: settings?.enable_offline_media_purge ?? false,
        enableOfflineConflictResolution: settings?.enable_offline_conflict_resolution ?? false,
        enablePredictiveAlerts: settings?.enable_predictive_alerts ?? false,
        enableLocalPurgeAudit: settings?.enable_local_purge_audit ?? false,
      }}
    >
      {children}
    </SettingsContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSettings() {
  const context = useContext(SettingsContext)
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider')
  }
  return context
}
