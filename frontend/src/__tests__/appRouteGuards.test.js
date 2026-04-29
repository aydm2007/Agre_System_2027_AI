import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('app route guards', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/app.jsx'), 'utf8')

  it('guards direct finance and fuel routes with mode-aware policy checks', () => {
    expect(source).toContain('<Route element={<ModeGuard policyCheck="canAccessFinanceHubRoutes" />}>')
    expect(source).toContain('path="finance/supplier-settlements"')
    expect(source).toContain('path="finance/receipts-deposits"')
    expect(source).toContain('path="finance/petty-cash"')
    expect(source).toContain('path="finance/ledger"')
    expect(source).toContain('<Route element={<ModeGuard requiredMode={null} policyCheck="canAccessFuelReconciliationRoutes" />}>')
    expect(source).toContain('path="fuel-reconciliation"')

    const supplierIndex = source.indexOf('path="finance/supplier-settlements"')
    const financeGuardIndex = source.lastIndexOf(
      '<Route element={<ModeGuard policyCheck="canAccessFinanceHubRoutes" />}>',
      supplierIndex,
    )
    expect(financeGuardIndex).toBeGreaterThan(-1)

    const strictLedgerIndex = source.indexOf('path="finance/ledger"')
    const strictFinanceGuardIndex = source.lastIndexOf(
      '<Route element={<ModeGuard policyCheck="canRegisterFinancialRoutes" />}>',
      strictLedgerIndex,
    )
    expect(strictFinanceGuardIndex).toBeGreaterThan(-1)

    const fuelIndex = source.indexOf('path="fuel-reconciliation"')
    const fuelGuardIndex = source.lastIndexOf(
      '<Route element={<ModeGuard requiredMode={null} policyCheck="canAccessFuelReconciliationRoutes" />}>',
      fuelIndex,
    )
    expect(fuelGuardIndex).toBeGreaterThan(-1)
  })
})
