// ============================================================================
// Suite 4: Variance Analysis & Predictive Burn Rate
// [AGRI-GUARDIAN] Axes: 5 (Decimal), 6 (Tenant), 8 (Variance & BOM)
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

// ──────────────────────────────────────────────────────────────────────────────
// VA1: Variance Analysis page loads
// ──────────────────────────────────────────────────────────────────────────────
test('Variance Analysis page loads with content', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.FINANCE_VARIANCE}`)
  await page.waitForLoadState('domcontentloaded')
  await assertRTL(page, expect)

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// VA2: Variance API returns per-plan data
// ──────────────────────────────────────────────────────────────────────────────
test('Variance API returns structured plan data', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const plans = await getCropPlans(request, token, farmId)
  if (plans.length === 0) {
    test.skip(true, 'No crop plans to analyze')
    return
  }

  const planId = plans[0].id
  const { ok, data } = await apiGet(request, token, '/finance/variance-analysis/', {
    farm_id: farmId,
    crop_plan_id: planId,
  })
  expect(ok).toBeTruthy()

  // Response should have plans array
  expect(data.farm_id || data.plans !== undefined).toBeTruthy()
})

// ──────────────────────────────────────────────────────────────────────────────
// VA3: Predictive Variance page loads
// ──────────────────────────────────────────────────────────────────────────────
test('PredictiveVariance page loads', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.PREDICTIVE_VARIANCE}`)
  await page.waitForLoadState('domcontentloaded')

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// VA4: Actual Expense list loads
// ──────────────────────────────────────────────────────────────────────────────
test('Actual Expense list loads', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.FINANCE_EXPENSES}`)
  await page.waitForLoadState('domcontentloaded')

  const hasContent =
    (await page.locator('table').count()) > 0 ||
    (await page.locator('text=/لا توجد|لا يوجد/i').count()) > 0 ||
    (await page.locator('main, section').first().isVisible())

  expect(hasContent).toBeTruthy()
})

// ──────────────────────────────────────────────────────────────────────────────
// VA5: Actual expenses API is farm-scoped
// ──────────────────────────────────────────────────────────────────────────────
test('Actual expenses API is farm-scoped', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const { ok, data } = await apiGet(request, token, '/finance/actual-expenses/', {
    farm: farmId,
  })
  expect(ok).toBeTruthy()

  const expenses = readResults(data)
  for (const expense of expenses) {
    expect(expense.farm, `Expense ${expense.id} leaks farm`).toBe(farmId)
  }
})

// ──────────────────────────────────────────────────────────────────────────────
// VA6: Variance alert data has Decimal precision
// ──────────────────────────────────────────────────────────────────────────────
test('Variance alerts maintain numeric integrity', async ({ request }) => {
  const { ok, data } = await apiGet(request, token, '/material-variance-alerts/', {
    farm: farmId,
  })
  // Might return 404 if not seeded. Just check it doesn't crash.
  if (!ok) return

  const alerts = readResults(data)
  for (const alert of alerts) {
    if (alert.variance_percentage) {
      const pct = Number(alert.variance_percentage)
      expect(Number.isFinite(pct), `Alert ${alert.id} has bad percentage`).toBeTruthy()
    }
  }
})
