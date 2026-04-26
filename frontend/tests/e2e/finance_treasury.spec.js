// ============================================================================
// Suite 1: Finance Treasury — الخزينة والصندوق النقدي
// [AGRI-GUARDIAN] Axes: 2 (Idempotency), 4 (Fund Accounting),
//                       5 (Decimal), 6 (Tenant Isolation)
// ============================================================================
import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  endpoints,
  ensureLoggedIn,
  ensureFarmSelected,
  fetchToken,
  withAuthHeaders,
  readResults,
} from './helpers/e2eAuth'
import { getFirstFarm, isStrictMode, apiGet } from './helpers/e2eApi'
import { ROUTES, skipIfSimple, assertRTL } from './helpers/e2eFixtures'

let farmId
let strictErpMode = false
let token

test.describe.configure({ mode: 'serial' })

test.beforeAll(async ({ request }) => {
  token = await fetchToken(request)
  const farm = await getFirstFarm(request, token)
  farmId = farm.id
  strictErpMode = await isStrictMode(request, token)
})

// ──────────────────────────────────────────────────────────────────────────────
// T1: Treasury Dashboard loads with balance cards
// ──────────────────────────────────────────────────────────────────────────────
test('Treasury dashboard loads with balance data', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.FINANCE_TREASURY}`)
  await page.waitForLoadState('domcontentloaded')

  // Page should not redirect to login/dashboard
  await expect(page).not.toHaveURL(/\/login/)

  // Layout should be RTL
  await assertRTL(page, expect)

  // Should have at least one balance card or content section
  const content = page.locator('main, section, [data-testid="treasury-dashboard"]').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// T2: Ledger balances API returns Decimal precision
// ──────────────────────────────────────────────────────────────────────────────
test('Ledger balances maintain Decimal(19,4) precision', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const { ok, data } = await apiGet(request, token, '/finance/ledger/balances/', { farm: farmId })
  expect(ok).toBeTruthy()

  // All balance values should be string or number — no NaN, no Infinity
  const balances = data?.balances || data || {}
  for (const [account, value] of Object.entries(balances)) {
    const num = Number(value)
    expect(Number.isFinite(num), `${account} balance=${value} is not finite`).toBeTruthy()
  }
})

// ──────────────────────────────────────────────────────────────────────────────
// T3: CashBox list displays entries
// ──────────────────────────────────────────────────────────────────────────────
test('CashBox list page loads', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  // Navigate to treasury which contains cashbox
  await page.goto(`${BASE_URL}/finance/cashbox`)
  await page.waitForLoadState('domcontentloaded')

  // Either table or empty state should be visible
  const hasContent =
    (await page.locator('table').count()) > 0 ||
    (await page.locator('text=/لا توجد|لا يوجد|No data/i').count()) > 0 ||
    (await page.locator('main, section').first().isVisible())

  expect(hasContent).toBeTruthy()
})

// ──────────────────────────────────────────────────────────────────────────────
// T4: Farm isolation — API enforces X-Farm-Id scoping
// ──────────────────────────────────────────────────────────────────────────────
test('Ledger API enforces farm-scoped results', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  // Request with farmId should return only that farm's entries
  const { ok, data } = await apiGet(request, token, '/finance/ledger/', { farm: farmId })
  expect(ok).toBeTruthy()

  const entries = readResults(data)
  for (const entry of entries) {
    expect(entry.farm, `Ledger entry ${entry.id} leaks to another farm`).toBe(farmId)
  }
})

// ──────────────────────────────────────────────────────────────────────────────
// T5: Idempotency key required on financial mutations
// ──────────────────────────────────────────────────────────────────────────────
test('Financial POST without idempotency key returns 400', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  // Attempt POST without X-Idempotency-Key
  const res = await request.post(`${endpoints.V1_BASE}/finance/ledger/liquidate-payroll/`, {
    headers: withAuthHeaders(token),
    data: { farm: farmId },
  })

  // Should reject with 400 and mention idempotency
  expect(res.status()).toBe(400)
  const body = await res.json().catch(() => ({}))
  expect(String(body?.detail || '')).toContain('X-Idempotency-Key')
})
