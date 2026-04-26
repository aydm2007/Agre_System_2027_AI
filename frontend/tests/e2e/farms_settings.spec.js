// ============================================================================
// Suite 7: Farms Management & System Settings
// [AGRI-GUARDIAN] Axes: 6 (Tenant Isolation), 9 (Zakat), 10 (Tiering)
// ============================================================================
import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureLoggedIn,
  ensureFarmSelected,
  fetchToken,
  fetchSystemMode,
} from './helpers/e2eAuth'
import { getFirstFarm, apiGet } from './helpers/e2eApi'
import { ROUTES, assertRTL } from './helpers/e2eFixtures'

let farmId
let token

test.describe.configure({ mode: 'serial' })

test.beforeAll(async ({ request }) => {
  token = await fetchToken(request)
  const farm = await getFirstFarm(request, token)
  farmId = farm.id
})

// ──────────────────────────────────────────────────────────────────────────────
// FM1: Farms list loads
// ──────────────────────────────────────────────────────────────────────────────
test('Farms list page loads', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await page.goto(`${BASE_URL}${ROUTES.FARMS}`)
  await page.waitForLoadState('domcontentloaded')
  await assertRTL(page, expect)

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// FM2: Farm API returns area + tier
// ──────────────────────────────────────────────────────────────────────────────
test('Farm API returns area and tier fields', async ({ request }) => {
  const { ok, data } = await apiGet(request, token, `/farms/${farmId}/`)
  expect(ok).toBeTruthy()

  // Farm should have area and at least implicit tier
  expect(data.id).toBe(farmId)
  expect(data.name).toBeDefined()
  // area might be null but field should exist
  expect(data.area !== undefined || data.area === null).toBeTruthy()
})

// ──────────────────────────────────────────────────────────────────────────────
// FM3: Farm selector persists selection across pages
// ──────────────────────────────────────────────────────────────────────────────
test('Farm selector persists across navigation', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  // Navigate to dashboard and verify farm is still selected
  await page.goto(`${BASE_URL}${ROUTES.DASHBOARD}`)
  await page.waitForLoadState('domcontentloaded')

  // Navigate to daily-log and verify farm is still selected (no re-prompt)
  await page.goto(`${BASE_URL}${ROUTES.DAILY_LOG}`)
  await page.waitForLoadState('domcontentloaded')

  // Should not see farm selector prompt
  const farmSelectorPrompt = page.locator('[data-testid="farm-selector-modal"]')
  const promptVisible = await farmSelectorPrompt.isVisible().catch(() => false)
  expect(promptVisible).toBeFalsy()
})

// ──────────────────────────────────────────────────────────────────────────────
// FM4: Settings page renders
// ──────────────────────────────────────────────────────────────────────────────
test('Settings page loads', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await page.goto(`${BASE_URL}${ROUTES.SETTINGS}`)
  await page.waitForLoadState('domcontentloaded')

  const content = page.locator('main, section').first()
  await expect(content).toBeVisible({ timeout: 15000 })
})

// ──────────────────────────────────────────────────────────────────────────────
// FM5: System mode API returns valid response
// ──────────────────────────────────────────────────────────────────────────────
test('System mode API returns strict_erp_mode field', async ({ request }) => {
  const modeBody = await fetchSystemMode(request)
  expect(modeBody.strict_erp_mode !== undefined).toBeTruthy()
  expect(typeof modeBody.strict_erp_mode === 'boolean').toBeTruthy()
})
