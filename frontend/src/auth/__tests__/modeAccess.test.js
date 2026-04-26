import { describe, it, expect, vi } from 'vitest'
import {
  canRegisterFinancialRoutes,
  canAccessTreasuryRoutes,
  canAccessFixedAssetRoutes,
  canAccessFuelReconciliationRoutes,
} from '../modeAccess'
import { ROLES } from '../roles'

describe('modeAccess Guards [AGRI-GUARDIAN Axis 6, 15 / PRD V21 §7, §12]', () => {
  describe('canRegisterFinancialRoutes', () => {
    it('denies access if strictErpMode is false (SIMPLE mode)', () => {
      const options = { strictErpMode: false, hasFarmRole: () => true }
      expect(canRegisterFinancialRoutes(options)).toBe(false)
    })

    it('denies access in STRICT mode if user lacks financial or admin roles', () => {
      const options = { strictErpMode: true, hasFarmRole: () => false, isAdmin: false }
      expect(canRegisterFinancialRoutes(options)).toBe(false)
    })

    it('grants access in STRICT mode if user has a financial role', () => {
      const hasFarmRole = vi.fn().mockImplementation((role) => role === ROLES.SECTOR_ACCOUNTANT)
      const options = { strictErpMode: true, hasFarmRole, isAdmin: false }
      expect(canRegisterFinancialRoutes(options)).toBe(true)
    })

    it('grants access in STRICT mode if user is Admin', () => {
      const options = { strictErpMode: true, hasFarmRole: () => false, isAdmin: true }
      expect(canRegisterFinancialRoutes(options)).toBe(true)
    })
  })

  describe('canAccessFixedAssetRoutes', () => {
    it('denies access if fixedAssetMode is disabled', () => {
      const options = { fixedAssetMode: 'disabled', strictErpMode: true }
      expect(canAccessFixedAssetRoutes(options)).toBe(false)
    })

    it('denies access in SIMPLE mode if fixedAssetMode is not tracking_only', () => {
      const options = { fixedAssetMode: 'full', strictErpMode: false }
      expect(canAccessFixedAssetRoutes(options)).toBe(false)
    })

    it('grants access in SIMPLE mode if fixedAssetMode is tracking_only', () => {
      const options = { fixedAssetMode: 'tracking_only', strictErpMode: false }
      expect(canAccessFixedAssetRoutes(options)).toBe(true)
    })

    it('grants access in STRICT mode regardless of tracking_only flag', () => {
      const options = { fixedAssetMode: 'full', strictErpMode: true }
      expect(canAccessFixedAssetRoutes(options)).toBe(true)
    })
  })

  describe('canAccessFuelReconciliationRoutes', () => {
    it('denies access if fuelReconciliationMode is disabled', () => {
      const options = { fuelReconciliationMode: 'disabled', strictErpMode: true }
      expect(canAccessFuelReconciliationRoutes(options)).toBe(false)
    })

    it('allows posture-first reconciliation access in SIMPLE mode', () => {
      const options = { fuelReconciliationMode: 'enabled', strictErpMode: false }
      expect(canAccessFuelReconciliationRoutes(options)).toBe(true)
    })

    it('grants full reconciliation access in STRICT mode', () => {
      const options = { fuelReconciliationMode: 'enabled', strictErpMode: true }
      expect(canAccessFuelReconciliationRoutes(options)).toBe(true)
    })
  })

  describe('canAccessTreasuryRoutes', () => {
    it('denies access if strictErpMode is explicitly false', () => {
      // Default behavior tests for treasury which assumes strict mode true by default if omitted
      const options = { strictErpMode: false, hasFarmRole: () => true }
      expect(canAccessTreasuryRoutes(options)).toBe(false)
    })

    it('denies access if treasuryVisibility is hidden', () => {
      const options = { strictErpMode: true, treasuryVisibility: 'hidden', hasFarmRole: () => true }
      expect(canAccessTreasuryRoutes(options)).toBe(false)
    })

    it('grants access to financial role in STRICT mode', () => {
      const hasFarmRole = vi.fn().mockImplementation((role) => role === ROLES.CASHIER)
      const options = { strictErpMode: true, treasuryVisibility: 'visible', hasFarmRole }
      expect(canAccessTreasuryRoutes(options)).toBe(true)
    })
  })
})
