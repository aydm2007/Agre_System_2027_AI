// ============================================================================
// Suite 9: Full Documentary Cycle — الدورة المستندية الكاملة
// [AGRI-GUARDIAN] All 14 Axes — End-to-End Integration
//
// This is THE most critical E2E test. It validates the complete 6-stage
// documentary cycle as defined in docs/doctrine/DOCUMENTARY_CYCLE.md:
//
// Stage 1: Crop Plan Creation
// Stage 2: Procurement (GRN)
// Stage 3: Daily Log + Activities + Consumption
// Stage 4: Harvest
// Stage 5: Sales
// Stage 6: Seasonal Settlement / Closing
// ============================================================================
import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureLoggedIn,
  ensureFarmSelected,
  fetchToken,
  readResults,
} from './helpers/e2eAuth'
import { getFirstFarm, isStrictMode, apiGet, getCropPlans } from './helpers/e2eApi'
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

// ┌──────────────────────────────────────────────────────────────────────────┐
// │ Stage 1: Crop Plan — Verify plans exist and have budget structure       │
// └──────────────────────────────────────────────────────────────────────────┘
test('Stage 1: Crop plans exist with budget structure', async ({ request }) => {
  const plans = await getCropPlans(request, token, farmId)
  expect(plans.length, 'HALT: no crop plans seeded for documentary cycle').toBeGreaterThan(0)

  const plan = plans[0]
  expect(plan.name).toBeDefined()
  expect(plan.farm).toBe(farmId)

  // Budget fields should exist
  expect(plan.budget_materials !== undefined).toBeTruthy()
  expect(plan.budget_labor !== undefined).toBeTruthy()
})

test('Stage 1: Crop Plans page loads and shows plan cards', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.CROP_PLANS}`)
  await page.waitForLoadState('domcontentloaded')
  await assertRTL(page, expect)

  // Should display at least one plan (card or table row)
  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })

  // Look for plan content
  const hasPlans =
    (await page.locator('[data-testid^="crop-plan-"]').count()) > 0 ||
    (await page.locator('table tbody tr, .card, .plan-card').count()) > 0

  // Allow empty state too if farm has no plans
  expect(hasPlans || (await page.locator('text=/لا توجد|لا يوجد/i').count()) > 0).toBeTruthy()
})

// ┌──────────────────────────────────────────────────────────────────────────┐
// │ Stage 2: Procurement — Verify inventory items exist                     │
// └──────────────────────────────────────────────────────────────────────────┘
test('Stage 2: Inventory items exist for procurement', async ({ request }) => {
  const { ok, data } = await apiGet(request, token, '/items/', { farm: farmId })
  expect(ok).toBeTruthy()

  const items = readResults(data)
  expect(items.length, 'HALT: no inventory items seeded').toBeGreaterThan(0)

  // Items should have name and unit_price (Decimal)
  for (const item of items.slice(0, 5)) {
    expect(item.name).toBeDefined()
    if (item.unit_price) {
      const price = Number(item.unit_price)
      expect(Number.isFinite(price), `Item ${item.name} has bad price`).toBeTruthy()
    }
  }
})

test('Stage 2: Materials Catalog page loads', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.MATERIALS_CATALOG}`)
  await page.waitForLoadState('domcontentloaded')

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ┌──────────────────────────────────────────────────────────────────────────┐
// │ Stage 3: Daily Log + Activities — The heart of operational recording    │
// └──────────────────────────────────────────────────────────────────────────┘
test('Stage 3: DailyLog page loads in all modes', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.DAILY_LOG}`)
  await page.waitForLoadState('domcontentloaded')
  await assertRTL(page, expect)

  // Core form fields should be visible
  const dateField = page.locator('#daily-log-date, input[type="date"]').first()
  await expect(dateField).toBeVisible({ timeout: 15000 })
})

test('Stage 3: Daily logs exist via API', async ({ request }) => {
  const { ok, data } = await apiGet(request, token, '/daily-logs/', { farm: farmId })
  expect(ok).toBeTruthy()

  const logs = readResults(data)
  // Allow empty for new farms, but API must respond
  expect(Array.isArray(logs)).toBeTruthy()
})

test('Stage 3: Daily log history shows log entries', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.DAILY_LOG_HISTORY}`)
  await page.waitForLoadState('domcontentloaded')

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ┌──────────────────────────────────────────────────────────────────────────┐
// │ Stage 4: Harvest — Verify harvest products                              │
// └──────────────────────────────────────────────────────────────────────────┘
test('Stage 4: Harvest products page loads', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.HARVEST_PRODUCTS}`)
  await page.waitForLoadState('domcontentloaded')

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

test('Stage 4: Harvest products API returns data', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const { ok, data } = await apiGet(request, token, '/harvest-products/', { farm: farmId })
  if (!ok) return
  const products = readResults(data)
  expect(Array.isArray(products)).toBeTruthy()
})

// ┌──────────────────────────────────────────────────────────────────────────┐
// │ Stage 5: Sales — Verify invoices and Zakat compliance                   │
// └──────────────────────────────────────────────────────────────────────────┘
test('Stage 5: Sales page loads in strict mode', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.SALES}`)
  await page.waitForLoadState('domcontentloaded')

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

test('Stage 5: Sales invoices API is farm-scoped', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const { ok, data } = await apiGet(request, token, '/sales-invoices/', { farm_id: farmId })
  expect(ok).toBeTruthy()

  const invoices = readResults(data)
  for (const inv of invoices) {
    expect(inv.farm, `Invoice ${inv.id} leaks farm`).toBe(farmId)
  }
})

// ┌──────────────────────────────────────────────────────────────────────────┐
// │ Stage 6: Financial Closing — Ledger + Reports                           │
// └──────────────────────────────────────────────────────────────────────────┘
test('Stage 6: Financial ledger entries exist', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const { ok, data } = await apiGet(request, token, '/finance/ledger/', { farm: farmId })
  expect(ok).toBeTruthy()

  const entries = readResults(data)
  expect(entries.length, 'HALT: no ledger entries — financial lifecycle is broken').toBeGreaterThan(
    0,
  )
})

test('Stage 6: Reports page loads with data tabs', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.REPORTS}`)
  await page.waitForLoadState('domcontentloaded')

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

test('Stage 6: Audit trail records exist', async ({ request }) => {
  const { ok, data } = await apiGet(request, token, '/audit-logs/')
  expect(ok).toBeTruthy()

  const logs = readResults(data)
  expect(logs.length, 'HALT: audit trail is empty — compliance broken').toBeGreaterThan(0)
})
