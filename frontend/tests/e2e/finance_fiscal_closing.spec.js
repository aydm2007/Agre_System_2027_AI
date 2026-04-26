// ============================================================================
// Suite 3: Fiscal Period Lifecycle & Closing Wizard
// [AGRI-GUARDIAN] Axes: 3 (Fiscal Lock), 4 (Fund Accounting), 13 (Settlement)
// ============================================================================
import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureLoggedIn,
  ensureFarmSelected,
  fetchToken,
  readResults,
} from './helpers/e2eAuth'
import { getFirstFarm, isStrictMode, apiGet, getOpenPeriod } from './helpers/e2eApi'
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
// FC1: Fiscal year list loads
// ──────────────────────────────────────────────────────────────────────────────
test('Fiscal year list page loads', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.FINANCE_FISCAL_YEARS}`)
  await page.waitForLoadState('domcontentloaded')
  await assertRTL(page, expect)

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// FC2: Fiscal periods API returns structured data
// ──────────────────────────────────────────────────────────────────────────────
test('Fiscal periods API returns status fields', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const { ok, data } = await apiGet(request, token, '/finance/fiscal-periods/', {
    farm: farmId,
  })
  expect(ok).toBeTruthy()

  const periods = readResults(data)
  expect(periods.length).toBeGreaterThan(0)

  // Each period should have status and month
  for (const period of periods) {
    expect(period.month).toBeDefined()
    expect(period.status).toBeDefined()
    expect(['open', 'soft_close', 'hard_close']).toContain(period.status.toLowerCase())
  }
})

// ──────────────────────────────────────────────────────────────────────────────
// FC3: Open fiscal period exists (baseline check)
// ──────────────────────────────────────────────────────────────────────────────
test('At least one open fiscal period exists', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const period = await getOpenPeriod(request, token, farmId)
  expect(period.id).toBeTruthy()
  expect(period.status.toLowerCase()).toBe('open')
})

// ──────────────────────────────────────────────────────────────────────────────
// FC4: Fiscal periods page renders status badges
// ──────────────────────────────────────────────────────────────────────────────
test('Fiscal periods page renders', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.FINANCE_FISCAL_PERIODS}`)
  await page.waitForLoadState('domcontentloaded')

  // Either table with periods or content section
  const hasContent =
    (await page.locator('table, [data-testid="fiscal-periods-table"]').count()) > 0 ||
    (await page.locator('main, section').first().isVisible())

  expect(hasContent).toBeTruthy()
})

// ──────────────────────────────────────────────────────────────────────────────
// FC5: Closing wizard page loads (if in strict mode)
// ──────────────────────────────────────────────────────────────────────────────
test('Closing wizard page loads', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.FINANCE_CLOSING}`)
  await page.waitForLoadState('domcontentloaded')

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// FC6: Fiscal year API is farm-scoped
// ──────────────────────────────────────────────────────────────────────────────
test('Fiscal years are farm-scoped', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const { ok, data } = await apiGet(request, token, '/finance/fiscal-years/', {
    farm: farmId,
  })
  expect(ok).toBeTruthy()

  const years = readResults(data)
  for (const fy of years) {
    expect(fy.farm, `FiscalYear ${fy.id} leaks farm`).toBe(farmId)
  }
})
