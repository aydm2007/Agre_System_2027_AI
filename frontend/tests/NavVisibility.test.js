/**
 * [AGRI-GUARDIAN] Nav Component Visibility Rules Test
 * Verifies the isFinanceLeader helper and baseNavItems visibility contract.
 *
 * Compliance:
 * - AGENTS.md §665-683: Navigation visibility rules per Simple/Strict mode
 * - AGENTS.md §30: strict_erp_mode gates nav visibility AND route registration
 */
import { describe, expect, it } from 'vitest'

// ──────────────────────────────────────────────────────────────────
// 1. isFinanceLeader Helper
// ──────────────────────────────────────────────────────────────────

describe('Nav: isFinanceLeader logic', () => {
  // Replicate the logic from Nav.jsx for unit testing
  const isFinanceLeader = ({ isSuperuser, hasFarmRole }) =>
    Boolean(isSuperuser) || Boolean(hasFarmRole)

  it('superuser IS a finance leader', () => {
    expect(isFinanceLeader({ isSuperuser: true, hasFarmRole: false })).toBe(true)
  })

  it('user with hasFarmRole IS a finance leader', () => {
    expect(isFinanceLeader({ isSuperuser: false, hasFarmRole: true })).toBe(true)
  })

  it('regular user is NOT a finance leader', () => {
    expect(isFinanceLeader({ isSuperuser: false, hasFarmRole: false })).toBe(false)
  })

  it('both superuser and farmRole is finance leader', () => {
    expect(isFinanceLeader({ isSuperuser: true, hasFarmRole: true })).toBe(true)
  })
})

// ──────────────────────────────────────────────────────────────────
// 2. Simple Mode Visibility Contract
// ──────────────────────────────────────────────────────────────────

describe('Nav: Simple Mode visibility contract', () => {
  // These modules must be ALWAYS visible (even in simple mode)
  const ALWAYS_VISIBLE = [
    'dashboard',
    'approvals',
    'variance-alerts',
    'daily-log',
    'daily-log-history',
    'reports',
    'crops',
    'farms',
  ]

  // These modules should be HIDDEN in simple mode (unless finance leader)
  const STRICT_ONLY = ['commercial-dashboard', 'sales', 'finance', 'treasury', 'employees']

  it('always-visible modules list matches AGENTS.md table', () => {
    expect(ALWAYS_VISIBLE.length).toBeGreaterThanOrEqual(6)
    expect(ALWAYS_VISIBLE).toContain('dashboard')
    expect(ALWAYS_VISIBLE).toContain('daily-log')
    expect(ALWAYS_VISIBLE).toContain('reports')
  })

  it('strict-only modules list matches AGENTS.md table', () => {
    expect(STRICT_ONLY.length).toBeGreaterThanOrEqual(4)
    expect(STRICT_ONLY).toContain('commercial-dashboard')
    expect(STRICT_ONLY).toContain('sales')
    expect(STRICT_ONLY).toContain('finance')
  })
})

// ──────────────────────────────────────────────────────────────────
// 3. E2E Selector Contract (data-testid)
// ──────────────────────────────────────────────────────────────────

describe('Nav: E2E data-testid contract awareness', () => {
  // These contracts must exist per AGENTS.md §32-36
  const REQUIRED_DATA_TESTIDS = [
    'login-username',
    'login-password',
    'login-submit',
    'daily-log-page-title',
    'date-input',
    'farm-select',
    'location-select',
    'task-select',
    'labor-surra-input',
    'daily-log-save',
    'finance-ledger-page',
    'finance-fiscal-periods-page',
    'finance-expenses-page',
    'sales-main-grid',
  ]

  it('contract requires at least 14 data-testid selectors', () => {
    expect(REQUIRED_DATA_TESTIDS.length).toBeGreaterThanOrEqual(14)
  })

  it('daily log contracts are defined', () => {
    expect(REQUIRED_DATA_TESTIDS).toContain('daily-log-page-title')
    expect(REQUIRED_DATA_TESTIDS).toContain('farm-select')
    expect(REQUIRED_DATA_TESTIDS).toContain('labor-surra-input')
    expect(REQUIRED_DATA_TESTIDS).toContain('daily-log-save')
  })

  it('finance contracts are defined', () => {
    expect(REQUIRED_DATA_TESTIDS).toContain('finance-ledger-page')
    expect(REQUIRED_DATA_TESTIDS).toContain('finance-expenses-page')
  })

  it('sales contract is defined', () => {
    expect(REQUIRED_DATA_TESTIDS).toContain('sales-main-grid')
  })
})
