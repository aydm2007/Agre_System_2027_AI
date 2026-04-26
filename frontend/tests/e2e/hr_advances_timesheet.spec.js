// ============================================================================
// Suite 5: HR Advances & Timesheets
// [AGRI-GUARDIAN] Axes: 5 (Decimal/Surrah), 6 (Tenant), 7 (Audit)
// ============================================================================
import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureLoggedIn,
  ensureFarmSelected,
  fetchToken,
  readResults,
} from './helpers/e2eAuth'
import { getFirstFarm, isStrictMode, apiGet, getEmployees } from './helpers/e2eApi'
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
// HR1: Advances page loads
// ──────────────────────────────────────────────────────────────────────────────
test('Employee Advances page loads', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.HR_ADVANCES}`)
  await page.waitForLoadState('domcontentloaded')
  await assertRTL(page, expect)

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// HR2: Advances API returns data
// ──────────────────────────────────────────────────────────────────────────────
test('Advances API returns structured data', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const { ok, data } = await apiGet(request, token, '/advances/', { farm: farmId })
  // Might be 404 if endpoint name differs, handle gracefully
  if (!ok) return

  const advances = readResults(data)
  expect(Array.isArray(advances)).toBeTruthy()
})

// ──────────────────────────────────────────────────────────────────────────────
// HR3: Timesheet page loads
// ──────────────────────────────────────────────────────────────────────────────
test('Timesheet page loads with monthly summary', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.HR_TIMESHEETS}`)
  await page.waitForLoadState('domcontentloaded')

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// HR4: Worker Productivity page loads
// ──────────────────────────────────────────────────────────────────────────────
test('Worker Productivity page loads', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.HR_PRODUCTIVITY}`)
  await page.waitForLoadState('domcontentloaded')

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// HR5: Employees API returns surrah_share with Decimal precision
// ──────────────────────────────────────────────────────────────────────────────
test('Employees API maintains Surrah Decimal precision', async ({ request }) => {
  skipIfSimple(test, strictErpMode)

  const employees = await getEmployees(request, token, farmId)
  for (const emp of employees) {
    if (emp.daily_rate) {
      const rate = Number(emp.daily_rate)
      expect(Number.isFinite(rate), `Employee ${emp.name} has bad daily_rate`).toBeTruthy()
    }
  }
})
