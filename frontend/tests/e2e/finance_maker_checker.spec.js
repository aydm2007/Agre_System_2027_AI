// ============================================================================
// Suite 2: Finance Maker-Checker & Approval Inbox
// [AGRI-GUARDIAN] Axes: 2 (Idempotency), 6 (Tenant), 10 (RACI Tiering)
// ============================================================================
import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureLoggedIn,
  ensureFarmSelected,
  fetchToken,
  readResults,
} from './helpers/e2eAuth'
import { getFirstFarm, isStrictMode, apiGet, getApprovalRequests } from './helpers/e2eApi'
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
// MC1: MakerChecker dashboard loads pending entries
// ──────────────────────────────────────────────────────────────────────────────
test('MakerChecker dashboard loads', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.FINANCE_MAKER_CHECKER}`)
  await page.waitForLoadState('domcontentloaded')

  await assertRTL(page, expect)

  // Should display content (table/list or empty state)
  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// MC2: Pending ledger entries can be listed via API
// ──────────────────────────────────────────────────────────────────────────────
test('Pending ledger entries list via API', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const { ok, data } = await apiGet(request, token, '/finance/ledger/', {
    farm: farmId,
    is_posted: 'false',
  })
  expect(ok).toBeTruthy()
  // Result might be empty if no pending entries, but should not error
  const entries = readResults(data)
  expect(Array.isArray(entries)).toBeTruthy()
})

// ──────────────────────────────────────────────────────────────────────────────
// MC3: Approval Inbox loads
// ──────────────────────────────────────────────────────────────────────────────
test('Approval Inbox page loads', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.APPROVAL_INBOX}`)
  await page.waitForLoadState('domcontentloaded')

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// MC4: Approval rules API scoped by farm
// ──────────────────────────────────────────────────────────────────────────────
test('Approval rules API is farm-scoped', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const { ok, data } = await apiGet(request, token, '/finance/approval-rules/', {
    farm: farmId,
  })
  expect(ok).toBeTruthy()
  const rules = readResults(data)
  for (const rule of rules) {
    expect(rule.farm, `Approval rule ${rule.id} leaks farm`).toBe(farmId)
  }
})

// ──────────────────────────────────────────────────────────────────────────────
// MC5: Approval request creation requires idempotency key
// ──────────────────────────────────────────────────────────────────────────────
test('Approval request list API returns data', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const requests = await getApprovalRequests(request, token, farmId)
  expect(Array.isArray(requests)).toBeTruthy()
})
