// ============================================================================
// Suite 8: Commercial Dashboard & Assets
// [AGRI-GUARDIAN] Axes: 6 (Tenant), 11 (Biological Assets)
// ============================================================================
import { test, expect } from '@playwright/test'
import { BASE_URL, ensureLoggedIn, ensureFarmSelected, fetchToken } from './helpers/e2eAuth'
import { getFirstFarm, isStrictMode } from './helpers/e2eApi'
import { ROUTES, skipIfSimple, assertRTL } from './helpers/e2eFixtures'

let strictErpMode = false
let token

test.describe.configure({ mode: 'serial' })

test.beforeAll(async ({ request }) => {
  token = await fetchToken(request)
  await getFirstFarm(request, token)
  strictErpMode = await isStrictMode(request, token)
})

// ──────────────────────────────────────────────────────────────────────────────
// CD1: Commercial dashboard loads in strict mode
// ──────────────────────────────────────────────────────────────────────────────
test('Commercial dashboard loads in strict mode', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.COMMERCIAL}`)
  await page.waitForLoadState('domcontentloaded')
  await assertRTL(page, expect)

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// CD2: Commercial dashboard blocked in simple mode
// ──────────────────────────────────────────────────────────────────────────────
test('Commercial dashboard blocked in simple mode', async ({ page, request }) => {
  if (strictErpMode) {
    test.skip(true, 'Skipped: requires Simple mode for this test')
    return
  }

  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.COMMERCIAL}`)

  // Should redirect to dashboard or login
  await expect(page).toHaveURL(/\/(dashboard|login)(\/|$)/, { timeout: 10000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// CD3: Wells page loads
// ──────────────────────────────────────────────────────────────────────────────
test('Wells page loads', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.WELLS}`)
  await page.waitForLoadState('domcontentloaded')

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// CD4: Solar monitor page loads (strict mode)
// ──────────────────────────────────────────────────────────────────────────────
test('Solar monitor page loads', async ({ page, request }) => {
  skipIfSimple(test, strictErpMode)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.SOLAR_MONITOR}`)
  await page.waitForLoadState('domcontentloaded')

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})
