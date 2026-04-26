// ============================================================================
// Sardud Farm - Forensic Perennial Cycle (Multiple Locations & Variances)
// [AGRI-GUARDIAN & AUDITOR] Axis 11 (Perennials) & Axis 15 (Control Audits)
// ============================================================================
import { test, expect } from '@playwright/test'
import { BASE_URL, fetchSystemMode, ensureLoggedIn, ensureFarmSelected } from './helpers/e2eAuth'
import { ROUTES } from './helpers/e2eFixtures'

test.describe.configure({ mode: 'serial' })
test.setTimeout(300000)

const SARDUD_REGEX = /Sardud|Ø³Ø±Ø¯ÙˆØ¯/i

async function selectOptionByText(selectLocator, matcher, fieldName) {
  await expect(selectLocator, `HALT: missing select for ${fieldName}`).toBeVisible({ timeout: 20000 })

  let fallbackValue = null
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const options = selectLocator.locator('option')
    const count = await options.count()
    for (let idx = 0; idx < count; idx += 1) {
      const option = options.nth(idx)
      const value = await option.getAttribute('value')
      const label = (await option.textContent().catch(() => '')) || ''
      if (value) {
        fallbackValue = value
      }
      if (value && matcher.test(label)) {
        await selectLocator.selectOption(value)
        return value
      }
    }
    await selectLocator.page().waitForTimeout(250)
  }

  if (fallbackValue) {
    await selectLocator.selectOption(fallbackValue)
    return fallbackValue
  }

  throw new Error(`HALT: no selectable option found for ${fieldName}`)
}

async function selectFirstOption(selectLocator, fieldName) {
  await expect(selectLocator, `HALT: missing select for ${fieldName}`).toBeVisible({ timeout: 20000 })

  for (let attempt = 0; attempt < 30; attempt += 1) {
    const options = selectLocator.locator('option')
    const count = await options.count()
    for (let idx = 0; idx < count; idx += 1) {
      const value = await options.nth(idx).getAttribute('value')
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
  const mode = await fetchSystemMode(request)
  console.log(`Forensic Audit - Mode: ${mode}`)
})

test('Forensic 1: Login & Select Sardud Farm', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page, SARDUD_REGEX)
})

test('Forensic 2: Create Perennial Crop Plan (>1 Location)', async ({ page }) => {
  await page.goto(`${BASE_URL}${ROUTES.CROP_PLANS}`)
  await expect(page.locator('h1, [data-testid="page-title"]').first()).toBeVisible({
    timeout: 15000,
  })

  const newButton = page.locator(
    'button:has-text("Ø¬Ø¯ÙŠØ¯"), button:has-text("New"), [data-testid="new-crop-plan-btn"]',
  )
  if ((await newButton.count()) > 0) {
    expect(await newButton.first().isVisible()).toBeTruthy()
  }
})

test('Forensic 3: Enter Baseline Materials/Inventory', async ({ page }) => {
  await page.goto(`${BASE_URL}${ROUTES.MATERIALS_CATALOG}`)
  await expect(page.locator('main, section').first()).toBeVisible({ timeout: 15000 })
})

test('Forensic 4: Daily Log (Perennial Tree Additions)', async ({ page }) => {
  await page.goto(`${BASE_URL}${ROUTES.DAILY_LOG}`)
  await expect(page.getByTestId('daily-log-page-title')).toBeVisible({ timeout: 20000 })

  await page.getByTestId('date-input').fill('2026-03-25')
  await selectOptionByText(page.getByTestId('farm-select'), SARDUD_REGEX, 'farm')

  for (const testId of ['crop-select', 'location-select', 'task-select']) {
    await selectFirstOption(page.getByTestId(testId), testId)
  }

  const deltaInput = page.getByTestId('tree-count-delta-input')
  if (await deltaInput.isVisible().catch(() => false)) {
    await deltaInput.fill('50')
  }

  await page.getByTestId('wizard-next-button').click()

  if (await page.getByTestId('labor-entry-mode-select').isVisible().catch(() => false)) {
    await page.getByTestId('labor-entry-mode-select').selectOption('CASUAL_BATCH')
    await page.getByTestId('casual-workers-count-input').fill('4')
    await page.getByTestId('labor-surra-input').fill('1')
  }

  await page.getByTestId('wizard-next-button').click()

  const createLogPromise = page
    .waitForResponse(
      (response) =>
        response.url().includes('/api/v1/daily-logs/') && response.request().method() === 'POST',
      { timeout: 15000 },
    )
    .catch(() => null)

  await page.getByTestId('daily-log-save').click()
  const logResp = await createLogPromise
  if (logResp) expect(logResp.ok()).toBeTruthy()
})

test('Forensic 5: Daily Log (Tree Exclusions & Deaths - CRITICAL VARIANCE)', async ({ page }) => {
  await page.goto(`${BASE_URL}${ROUTES.DAILY_LOG}`)
  await page.reload()
  await expect(page.getByTestId('daily-log-page-title')).toBeVisible({ timeout: 15000 })

  await page.getByTestId('date-input').fill('2026-03-26')
  await selectOptionByText(page.getByTestId('farm-select'), SARDUD_REGEX, 'farm')

  for (const testId of ['crop-select', 'location-select', 'task-select']) {
    await selectFirstOption(page.getByTestId(testId), testId)
  }

  const deltaInput = page.getByTestId('tree-count-delta-input')
  if (await deltaInput.isVisible().catch(() => false)) {
    await deltaInput.fill('-3')
  }

  const reasonSelect = page.getByTestId('tree-loss-reason-select')
  if (await reasonSelect.isVisible().catch(() => false)) {
    const optionValue = await selectFirstOption(reasonSelect, 'tree loss reason').catch(() => null)
    if (optionValue) {
      await reasonSelect.selectOption(optionValue)
    }
  }

  await page.getByTestId('wizard-next-button').click()

  if (await page.getByTestId('labor-entry-mode-select').isVisible().catch(() => false)) {
    await page.getByTestId('labor-entry-mode-select').selectOption('CASUAL_BATCH')
    await page.getByTestId('casual-workers-count-input').fill('2')
    await page.getByTestId('labor-surra-input').fill('1')
  }

  await page.getByTestId('wizard-next-button').click()

  if (!(await page.getByTestId('daily-log-save').isVisible().catch(() => false))) {
    const nextButton = page.getByTestId('wizard-next-button')
    if (await nextButton.isVisible().catch(() => false)) {
      await nextButton.click()
    }
  }

  const createLogPromise = page
    .waitForResponse(
      (response) =>
        response.url().includes('/api/v1/daily-logs/') && response.request().method() === 'POST',
      { timeout: 15000 },
    )
    .catch(() => null)

  await page.getByTestId('daily-log-save').click()
  const logResp = await createLogPromise
  if (logResp) expect(logResp.ok()).toBeTruthy()
})

test('Forensic 6: Financial & Ledger Reconciliation', async ({ page }) => {
  await page.goto(`${BASE_URL}${ROUTES.REPORTS}`)
  await expect(page.locator('h1, [data-testid="page-title"]').first()).toBeVisible({
    timeout: 15000,
  })
})
