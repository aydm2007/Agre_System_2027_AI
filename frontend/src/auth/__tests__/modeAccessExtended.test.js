import { describe, expect, it } from 'vitest'
import {
  canAccessContractRoutes,
  canAccessFixedAssetRoutes,
  canAccessFuelReconciliationRoutes,
  canRegisterFinancialRoutes,
  canRegisterStrictRoutes,
} from '../modeAccess'
import { ROLES } from '../roles'

describe('canRegisterStrictRoutes', () => {
  it('handles null strictErpMode as simple mode', () => {
    expect(
      canRegisterStrictRoutes({ strictErpMode: null, isAdmin: true, isSuperuser: true }),
    ).toBe(false)
  })

  it('denies access in SIMPLE mode even for admin', () => {
    expect(canRegisterStrictRoutes({ strictErpMode: false, isAdmin: true })).toBe(false)
  })

  it('denies access in SIMPLE mode for superuser', () => {
    expect(canRegisterStrictRoutes({ strictErpMode: false, isSuperuser: true })).toBe(false)
  })

  it('grants access in STRICT mode for admin', () => {
    expect(canRegisterStrictRoutes({ strictErpMode: true, isAdmin: true })).toBe(true)
  })

  it('grants access in STRICT mode for superuser', () => {
    expect(canRegisterStrictRoutes({ strictErpMode: true, isSuperuser: true })).toBe(true)
  })

  it('denies access in STRICT mode for non-admin users', () => {
    expect(
      canRegisterStrictRoutes({ strictErpMode: true, isAdmin: false, isSuperuser: false }),
    ).toBe(false)
  })

  it('handles undefined options gracefully', () => {
    expect(canRegisterStrictRoutes(undefined)).toBe(false)
    expect(canRegisterStrictRoutes({})).toBe(false)
  })
})

describe('canRegisterFinancialRoutes', () => {
  const sectorFinanceManager = (role) => role === ROLES.SECTOR_FINANCE_MANAGER
  const farmAccountant = (role) => role === ROLES.FARM_ACCOUNTANT
  const cashier = (role) => role === ROLES.CASHIER

  it('allows sector finance manager in strict mode', () => {
    expect(
      canRegisterFinancialRoutes({
        strictErpMode: true,
        isAdmin: false,
        isSuperuser: false,
        hasFarmRole: sectorFinanceManager,
      }),
    ).toBe(true)
  })

  it('superuser does not get financial routes in simple mode', () => {
    expect(
      canRegisterFinancialRoutes({
        strictErpMode: false,
        isAdmin: false,
        isSuperuser: true,
        hasFarmRole: () => false,
      }),
    ).toBe(false)
  })

  it('superuser in strict mode gets access', () => {
    expect(
      canRegisterFinancialRoutes({
        strictErpMode: true,
        isAdmin: false,
        isSuperuser: true,
        hasFarmRole: () => false,
      }),
    ).toBe(true)
  })

  it('finance roles do not get financial routes in simple mode', () => {
    expect(
      canRegisterFinancialRoutes({
        strictErpMode: false,
        isAdmin: false,
        isSuperuser: false,
        hasFarmRole: sectorFinanceManager,
      }),
    ).toBe(false)
    expect(
      canRegisterFinancialRoutes({
        strictErpMode: false,
        isAdmin: false,
        isSuperuser: false,
        hasFarmRole: farmAccountant,
      }),
    ).toBe(false)
    expect(
      canRegisterFinancialRoutes({
        strictErpMode: false,
        isAdmin: false,
        isSuperuser: false,
        hasFarmRole: cashier,
      }),
    ).toBe(false)
  })

  it('admin does not get financial routes in simple mode', () => {
    expect(
      canRegisterFinancialRoutes({
        strictErpMode: false,
        isAdmin: true,
        isSuperuser: false,
        hasFarmRole: () => false,
      }),
    ).toBe(false)
  })

  it('regular user in strict mode without financial role gets no route tree', () => {
    expect(
      canRegisterFinancialRoutes({
        strictErpMode: true,
        isAdmin: false,
        isSuperuser: false,
        hasFarmRole: () => false,
      }),
    ).toBe(false)
  })
})

describe('policy route helpers', () => {
  it('allows contract posture routes in SIMPLE with operational_only', () => {
    expect(
      canAccessContractRoutes({
        contractMode: 'operational_only',
        strictErpMode: false,
        isAdmin: false,
        isSuperuser: false,
        hasFarmRole: () => true,
      }),
    ).toBe(true)
  })

  it('denies contract routes when contractMode is disabled', () => {
    expect(
      canAccessContractRoutes({ contractMode: 'disabled', strictErpMode: true, isAdmin: true }),
    ).toBe(false)
  })

  it('allows contract routes in STRICT mode even without operational_only', () => {
    expect(canAccessContractRoutes({ contractMode: 'full', strictErpMode: true })).toBe(true)
  })

  it('allows fixed asset routes in SIMPLE tracking mode', () => {
    expect(
      canAccessFixedAssetRoutes({
        fixedAssetMode: 'tracking_only',
        strictErpMode: false,
        isAdmin: false,
        isSuperuser: false,
        hasFarmRole: () => false,
      }),
    ).toBe(true)
  })

  it('allows fixed asset routes in STRICT', () => {
    expect(
      canAccessFixedAssetRoutes({
        fixedAssetMode: 'tracking_only',
        strictErpMode: true,
        isAdmin: false,
        isSuperuser: false,
        hasFarmRole: () => false,
      }),
    ).toBe(true)
  })

  it('allows fuel reconciliation posture routes in SIMPLE mode', () => {
    expect(
      canAccessFuelReconciliationRoutes({
        strictErpMode: false,
        isAdmin: false,
        isSuperuser: false,
        hasFarmRole: () => false,
      }),
    ).toBe(true)
  })

  it('allows fuel reconciliation in STRICT', () => {
    expect(
      canAccessFuelReconciliationRoutes({
        strictErpMode: true,
        isAdmin: false,
        isSuperuser: false,
        hasFarmRole: () => false,
      }),
    ).toBe(true)
  })
})
