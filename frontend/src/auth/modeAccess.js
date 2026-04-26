import { ROLES } from './roles.js'

const hasFinancialRole = (hasFarmRole) =>
  Boolean(
    hasFarmRole &&
    (hasFarmRole(ROLES.SECTOR_ACCOUNTANT) ||
      hasFarmRole(ROLES.SECTOR_REVIEWER) ||
      hasFarmRole(ROLES.SECTOR_CHIEF_ACCOUNTANT) ||
      hasFarmRole(ROLES.SECTOR_FINANCE_MANAGER) ||
      hasFarmRole(ROLES.SECTOR_MANAGER) ||
      hasFarmRole(ROLES.CHIEF_ACCOUNTANT) ||
      hasFarmRole(ROLES.FARM_FINANCE_MANAGER) ||
      hasFarmRole(ROLES.FARM_ACCOUNTANT) ||
      hasFarmRole(ROLES.CASHIER) ||
      hasFarmRole(ROLES.FINANCIAL_AUDITOR))
  )

const hasAdminAuthority = (options) =>
  Boolean(options?.isAdmin || options?._isAdmin || options?.isSuperuser || options?._isSuperuser)

export function canAccessFinanceHubRoutes(options) {
  return hasAdminAuthority(options) || hasFinancialRole(options?.hasFarmRole)
}

/**
 * [AGRI-GUARDIAN Axis 6 / AGENTS.md L30]
 * Original strict-mode route gating, still limited to admin/superuser authority.
 */
export function canRegisterStrictRoutes(options) {
  return Boolean(options?.strictErpMode) && hasAdminAuthority(options)
}

export function canAccessStockManagementRoutes(options) {
  const isModeAllowed = Boolean(options?.strictErpMode) || Boolean(options?.showStockInSimple)
  return isModeAllowed && hasAdminAuthority(options)
}

/**
 * Financial authoring routes stay restricted in STRICT mode to finance or admin authority.
 */
export function canRegisterFinancialRoutes(options) {
  const isModeAllowed = Boolean(options?.strictErpMode)
  if (!isModeAllowed) return false
  return hasAdminAuthority(options) || hasFinancialRole(options?.hasFarmRole)
}

export function canAccessTreasuryRoutes(options) {
  const strictErpMode = options?.strictErpMode ?? true
  if (!strictErpMode) return false
  if (options?.treasuryVisibility === 'hidden') return false
  return hasAdminAuthority(options) || hasFinancialRole(options?.hasFarmRole)
}

export function canAccessContractRoutes(options) {
  if (options?.contractMode === 'disabled') return false
  return options?.contractMode === 'operational_only' || Boolean(options?.strictErpMode)
}

/**
 * [AGRI-GUARDIAN Axis 15 / PRD V21 §12.10]
 * Fixed assets: tracking-only in SIMPLE, full governed lifecycle in STRICT.
 */
export function canAccessFixedAssetRoutes(options) {
  if (options?.fixedAssetMode === 'disabled') return false
  // In SIMPLE mode, only tracking_only is allowed (register + health view)
  if (!options?.strictErpMode && options?.fixedAssetMode !== 'tracking_only') return false
  return true
}

/**
 * [AGRI-GUARDIAN Axis 15 / PRD V21 §12.11]
 * Fuel reconciliation: anomaly/risk view in SIMPLE, full governed reconciliation in STRICT.
 */
export function canAccessFuelReconciliationRoutes(options) {
  if (options?.fuelReconciliationMode === 'disabled') return false
  return true
}
