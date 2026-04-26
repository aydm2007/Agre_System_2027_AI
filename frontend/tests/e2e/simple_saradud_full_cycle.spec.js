// ============================================================================
// [AGRI-GUARDIAN] Strict Verification: Simple Mode Documentary Cycle (Saradud)
// Validates:
// 1. Shadow Mode Isolation (Sales & Finance blocked).
// 2. Crop Plan interaction.
// 3. Daily Log Wizard (Labor/Surra, Materials).
// 4. Harvest Recording.
// 5. Reports Verification.
// ============================================================================
import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  endpoints,
  ensureLoggedIn,
  ensureFarmSelected,
  fetchSystemMode,
  fetchToken,
  readResults,
  withAuthHeaders,
} from './helpers/e2eAuth'
import { ROUTES, STRICT_PAGES } from './helpers/e2eFixtures'

test.describe.configure({ mode: 'serial' })
test.setTimeout(180000)

let seedFarmId
let token
let headers

async function selectFirstOption(selectLocator, fieldName) {
  await expect(selectLocator).toBeVisible()

  for (let attempt = 0; attempt < 30; attempt += 1) {
    const options = selectLocator.locator('option')
    const count = await options.count()
    for (let i = 0; i < count; i += 1) {
      const value = await options.nth(i).getAttribute('value')
      if (value) {
        await selectLocator.selectOption(value)
        return value
      }
    }
    await selectLocator.page().waitForTimeout(250)
  }

  throw new Error(`HALT: no selectable option found for ${fieldName}`)
}

test.beforeAll(async ({ request }) => {
  const modeBody = await fetchSystemMode(request)
  expect(Boolean(modeBody?.strict_erp_mode)).toBeFalsy()

  token = await fetchToken(request)
  headers = withAuthHeaders(token)

  const farmsRes = await request.get(`${endpoints.V1_BASE}/farms/`, { headers })
  expect(farmsRes.ok()).toBeTruthy()
  const farms = readResults(await farmsRes.json())
  expect(farms.length, 'HALT: no farms seeded for simple mode cycle').toBeGreaterThan(0)
  seedFarmId = farms[0].id
})

test('Step 1: Shadow Mode Isolation (Strict Pages Blocked)', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  for (const route of STRICT_PAGES) {
    await page.goto(`${BASE_URL}${route}`)
    // In Simple Mode, strict pages should either redirect to dashboard or show 403 / blank.
    // We expect the URL to bounce back or not display the strict grids.
    if (route === ROUTES.SALES) {
      await expect(page.getByTestId('sales-main-grid')).toHaveCount(0)
    } else if (route === ROUTES.FINANCE) {
      await expect(page.getByTestId('finance-ledger-page')).toHaveCount(0)
    }
  }
})

test('Step 2: Crop Plans accessible and visible', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.CROP_PLANS}`)
  await page.waitForLoadState('domcontentloaded')

  const title = page.locator('h1, [data-testid="page-title"]').first()
  await expect(title).toBeVisible({ timeout: 15000 })
})

test('Step 3: Daily Log - Recording Labor and Materials', async ({ page, request }) => {
  page.on('console', (msg) => {
    if (
      msg.type() === 'error' ||
      msg.type() === 'warning' ||
      msg.text().includes('Validation') ||
      msg.text().includes('TypeError')
    ) {
      console.log(`[BROWSER] ${msg.type().toUpperCase()}: ${msg.text()}`)
    }
  })
  page.on('pageerror', (err) => {
    console.log(`[BROWSER Bx ERROR] ${err.message}`)
  })

  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.DAILY_LOG}`)
  await expect(page.getByTestId('daily-log-page-title')).toBeVisible({ timeout: 20000 })

  await page.getByTestId('date-input').fill('2026-03-01')
  await page.getByTestId('farm-select').selectOption(String(seedFarmId))
  console.log('[DEBUG] Step 3: Filled date and farm')
  await selectFirstOption(page.getByTestId('crop-select'), 'crop')
  await selectFirstOption(page.getByTestId('location-select'), 'location')
  await selectFirstOption(page.getByTestId('task-select'), 'task')
  console.log('[DEBUG] Step 3: Selected location and task')

  await page.getByTestId('wizard-next-button').click()
  await expect(page.getByTestId('wizard-step-resources')).toBeVisible()
  console.log('[DEBUG] Step 3: At resources step')

  // Verify Surra (Labor) Inputs
  await page.getByTestId('labor-entry-mode-select').selectOption('CASUAL_BATCH')
  await page.getByTestId('casual-workers-count-input').fill('10')
  await page.getByTestId('labor-surra-input').fill('1.0')
  console.log('[DEBUG] Step 3: Filled labor inputs')

  // Move directly to save to verify baseline logging works
  await page.getByTestId('wizard-next-button').click()
  await expect(page.getByTestId('daily-log-save')).toBeVisible()
  console.log('[DEBUG] Step 3: Reached save summary')

  // Handle Perennial if required
  if (
    await page
      .getByTestId('service-row-add')
      .isVisible({ timeout: 1000 })
      .catch(() => false)
  ) {
    await page.getByTestId('service-row-add').click()
    const varietySelect = page.locator('select[data-testid^="service-row-variety-"]').first()
    await expect(varietySelect).toBeVisible()
    const varOpts = varietySelect.locator('option')
    const varCount = await varOpts.count()
    for (let i = 0; i < varCount; i += 1) {
      const value = await varOpts.nth(i).getAttribute('value')
      if (value) {
        await varietySelect.selectOption(value)
        break
      }
    }
    await page.locator('input[data-testid^="service-row-count-"]').first().fill('5')
  }

  // Handle machinery if required
  if (
    await page
      .getByTestId('machine-asset-select')
      .isVisible({ timeout: 500 })
      .catch(() => false)
  ) {
    const macSelect = page.getByTestId('machine-asset-select')
    const opts = macSelect.locator('option')
    const count = await opts.count()
    for (let i = 0; i < count; i += 1) {
      const val = await opts.nth(i).getAttribute('value')
      if (val) {
        await macSelect.selectOption(val)
        break
      }
    }
    await page.getByTestId('machine-hours-input').fill('2')
  }

  const createLogPromise = page
    .waitForResponse(
      (response) =>
        response.url().includes('/api/v1/daily-logs/') && response.request().method() === 'POST',
      { timeout: 15000 },
    )
    .catch(() => null)

  const createActivityPromise = page
    .waitForResponse(
      (response) =>
        response.url().includes('/api/v1/activities/') && response.request().method() === 'POST',
      { timeout: 15000 },
    )
    .catch(() => null)

  await page.getByTestId('daily-log-save').click()

  const logResp = await createLogPromise
  if (!logResp) {
    // If it didn't trigger an API request, an error must be visible on the UI
    const errorText = await page
      .locator('[role="alert"]')
      .first()
      .textContent({ timeout: 5000 })
      .catch(() => 'Unknown Validation Error')
    throw new Error(`HALT: daily-log POST never fired. UI Error: ${errorText}`)
  }
  expect(logResp.ok(), `HALT: daily-log POST failed: ${await logResp.text()}`).toBeTruthy()

  const activityResp = await createActivityPromise
  if (activityResp) {
    expect(
      activityResp.ok(),
      `HALT: activity POST failed: ${await activityResp.text()}`,
    ).toBeTruthy()
  }

  // Ensure redirect to history
  await expect(page).toHaveURL(/\/daily-log-history/, { timeout: 30000 })
})

test('Step 4: Daily Log - Recording Harvest (Axis 9 & 11)', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.DAILY_LOG}`)
  await expect(page.getByTestId('daily-log-page-title')).toBeVisible({ timeout: 20000 })

  await page.getByTestId('date-input').fill('2026-03-02')
  await page.getByTestId('farm-select').selectOption(String(seedFarmId))
  await selectFirstOption(page.getByTestId('crop-select'), 'crop')
  await selectFirstOption(page.getByTestId('location-select'), 'location')

  // Attempt to select a Harvest Task
  const taskSelect = page.getByTestId('task-select')
  await expect(taskSelect).toBeVisible()

  // Choose harvest task if available, fallback to first option
  let hasHarvest = false
  const options = taskSelect.locator('option')
  const count = await options.count()
  for (let i = 0; i < count; i += 1) {
    const text = await options.nth(i).textContent()
    const value = await options.nth(i).getAttribute('value')
    if (text?.toLowerCase().includes('harvest') || text?.includes('حصاد')) {
      await taskSelect.selectOption(value)
      hasHarvest = true
      break
    }
  }
  if (!hasHarvest) {
    await selectFirstOption(taskSelect, 'task-fallback-to-first')
  }

  await page.getByTestId('wizard-next-button').click()
  await expect(page.getByTestId('wizard-step-resources')).toBeVisible()

  // Pass Step 2 validation
  await page.getByTestId('labor-entry-mode-select').selectOption('CASUAL_BATCH')
  await page.getByTestId('casual-workers-count-input').fill('10')
  await page.getByTestId('labor-surra-input').fill('1.0')

  await page.getByTestId('wizard-next-button').click()

  // Submit the log
  await expect(page.getByTestId('daily-log-save')).toBeVisible()

  // Handle Harvest Product if required
  if (
    await page
      .getByTestId('harvest-product-select')
      .isVisible({ timeout: 1000 })
      .catch(() => false)
  ) {
    const pSelect = page.getByTestId('harvest-product-select')
    const pOpts = pSelect.locator('option')
    const pCount = await pOpts.count()
    let pSelected = false
    for (let i = 0; i < pCount; i += 1) {
      const val = await pOpts.nth(i).getAttribute('value')
      if (val) {
        await pSelect.selectOption(val)
        pSelected = true
        break
      }
    }

    // If we found a product, fill the quantities
    if (pSelected) {
      await page.getByTestId('harvested-qty-input').fill('150')
      // Try filling the secondary quantity if it exists (but use generic selector)
      if (
        await page
          .getByTestId('harvest-quantity-input')
          .isVisible({ timeout: 500 })
          .catch(() => false)
      ) {
        await page.getByTestId('harvest-quantity-input').fill('15')
      }
    }
  }

  // Handle Perennial if required in harvest
  if (
    await page
      .getByTestId('service-row-add')
      .isVisible({ timeout: 500 })
      .catch(() => false)
  ) {
    await page.getByTestId('service-row-add').click()
    const varietySelect = page.locator('select[data-testid^="service-row-variety-"]').first()
    await expect(varietySelect).toBeVisible()
    const varOpts = varietySelect.locator('option')
    const varCount = await varOpts.count()
    for (let i = 0; i < varCount; i += 1) {
      const val = await varOpts.nth(i).getAttribute('value')
      if (val) {
        await varietySelect.selectOption(val)
        break
      }
    }
    await page.locator('input[data-testid^="service-row-count-"]').first().fill('5')
  }

  const createHarvestLogPromise = page
    .waitForResponse(
      (response) =>
        response.url().includes('/api/v1/daily-logs/') && response.request().method() === 'POST',
      { timeout: 15000 },
    )
    .catch(() => null)

  await page.getByTestId('daily-log-save').click()

  const harvestLogResp = await createHarvestLogPromise
  if (!harvestLogResp) {
    const errorText = await page
      .locator('.text-red-500, [role="alert"]')
      .first()
      .textContent({ timeout: 5000 })
      .catch(() => 'Unknown Validation Error')
    throw new Error(`HALT: Harvest daily-log POST never fired. UI Error: ${errorText}`)
  }
  expect(
    harvestLogResp.ok(),
    `HALT: daily-log Harvest POST failed: ${await harvestLogResp.text()}`,
  ).toBeTruthy()
})

test('Step 5: Reports accessible', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}${ROUTES.REPORTS}`)
  await page.waitForLoadState('domcontentloaded')

  const title = page.locator('h1, [data-testid="page-title"]').first()
  await expect(title).toBeVisible({ timeout: 15000 })
})
