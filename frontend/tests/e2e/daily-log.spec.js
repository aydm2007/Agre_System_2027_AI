import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureLoggedIn,
  fetchToken,
  withAuthHeaders,
  endpoints,
  readResults,
} from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })

let seedFarmId

test.beforeAll(async ({ request }) => {
  const token = await fetchToken(request)
  const headers = withAuthHeaders(token)

  const farmsRes = await request.get(`${endpoints.V1_BASE}/farms/`, { headers })
  expect(farmsRes.ok()).toBeTruthy()
  const farms = readResults(await farmsRes.json())
  expect(farms.length, 'HALT: no farms seeded for daily log tests').toBeGreaterThan(0)

  seedFarmId = farms[0].id
})

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

async function ensureDailyLogLoaded(page) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const title = page.getByTestId('daily-log-page-title')
    if (await title.isVisible().catch(() => false)) return

    const retryButton = page.getByRole('button', { name: /المحاولة مرة أخرى/ })
    if (await retryButton.isVisible().catch(() => false)) {
      await retryButton.click()
      await page.waitForTimeout(1000)
      continue
    }

    const refreshButton = page.getByRole('button', { name: /تحديث الصفحة/ })
    if (await refreshButton.isVisible().catch(() => false)) {
      await refreshButton.click()
      await page.waitForTimeout(1000)
      continue
    }

    await page.reload()
    await page.waitForTimeout(1000)
  }

  await expect(page.getByTestId('daily-log-page-title')).toBeVisible()
}

async function moveToResourcesStep(page) {
  await page.goto(`${BASE_URL}/daily-log`)
  await ensureDailyLogLoaded(page)

  await page.getByTestId('date-input').fill('2026-02-20')
  await selectFarmWithUsableSetup(page)
  await selectFirstOption(page.getByTestId('location-select'), 'location')
  await selectFirstOption(page.getByTestId('task-select'), 'task')

  await page.getByTestId('wizard-next-button').click()
  await expect(page.getByTestId('wizard-step-resources')).toBeVisible()
}

async function hasSelectableOption(selectLocator) {
  const options = selectLocator.locator('option')
  const count = await options.count()
  for (let i = 0; i < count; i += 1) {
    const value = await options.nth(i).getAttribute('value')
    if (value) return true
  }
  return false
}

async function selectFarmWithUsableSetup(page) {
  const farmSelect = page.getByTestId('farm-select')
  await expect(farmSelect).toBeVisible()
  const farmOptions = farmSelect.locator('option')
  const farmCount = await farmOptions.count()
  const candidateValues = []

  for (let i = 0; i < farmCount; i += 1) {
    const value = await farmOptions.nth(i).getAttribute('value')
    if (value) candidateValues.push(value)
  }

  if (seedFarmId && candidateValues.includes(String(seedFarmId))) {
    candidateValues.unshift(String(seedFarmId))
  }

  for (const farmValue of [...new Set(candidateValues)]) {
    await farmSelect.selectOption(farmValue)

    for (let attempt = 0; attempt < 20; attempt += 1) {
      const hasLocation = await hasSelectableOption(page.getByTestId('location-select'))
      const hasTask = await hasSelectableOption(page.getByTestId('task-select'))
      if (hasLocation && hasTask) return farmValue
      await page.waitForTimeout(200)
    }
  }

  throw new Error('HALT: no farm in setup has selectable location+task options')
}

test.describe('Daily Log Contracts', () => {
  test.beforeEach(async ({ page, request }) => {
    await ensureLoggedIn(page, request)
  })

  test('wizard setup selectors are stable', async ({ page }) => {
    await page.goto(`${BASE_URL}/daily-log`)
    await ensureDailyLogLoaded(page)
    await expect(page.getByTestId('date-input')).toBeVisible()
    await expect(page.getByTestId('farm-select')).toBeVisible()
    await expect(page.getByTestId('location-select')).toBeVisible()
    await expect(page.getByTestId('task-select')).toBeVisible()
  })

  test('surra doctrine: daily labor uses shifts and no labor hours input', async ({ page }) => {
    await moveToResourcesStep(page)

    await expect(page.locator('[data-testid="labor-hours-input"]')).toHaveCount(0)

    await expect(page.getByTestId('team-input')).toBeVisible()
    await page.getByTestId('team-input').click()
    const employeeOptions = page.locator('[data-testid^="employee-option-"]')
    await expect(employeeOptions.first()).toBeVisible()
    await employeeOptions.first().click()

    const surraInput = page.getByTestId('labor-surra-input')
    await expect(surraInput).toBeVisible()
    await surraInput.fill('1.25')

    await expect(page.getByTestId('labor-estimate-panel')).toBeVisible()
    await expect(page.getByTestId('equivalent-hours-per-worker')).toBeVisible()
    await expect(page.getByTestId('equivalent-hours-total')).toBeVisible()
    await expect(page.getByTestId('estimated-labor-cost')).toBeVisible()

    await page.getByTestId('wizard-next-button').click()
    await expect(page.getByTestId('daily-log-save')).toBeVisible()
  })

  test('casual batch mode shows equivalent hours and estimated labor cost', async ({ page }) => {
    await moveToResourcesStep(page)

    await page.getByTestId('labor-entry-mode-select').selectOption('CASUAL_BATCH')
    await page.getByTestId('casual-workers-count-input').fill('10')
    await page.getByTestId('labor-surra-input').fill('1.5')

    await expect(page.getByTestId('labor-estimate-panel')).toBeVisible()
    await expect(page.getByTestId('equivalent-hours-per-worker')).toContainText('12')
    await expect(page.getByTestId('equivalent-hours-total')).toContainText('120')
    const estimatedText = await page.getByTestId('estimated-labor-cost').innerText()
    expect(estimatedText.trim().startsWith('0.00')).toBeFalsy()
  })

  test('machine hours remain technical input when machinery card is present', async ({ page }) => {
    await moveToResourcesStep(page)
    await page.getByTestId('team-input').click()
    const employeeOptions = page.locator('[data-testid^="employee-option-"]')
    await expect(employeeOptions.first()).toBeVisible()
    await employeeOptions.first().click()
    await page.getByTestId('labor-surra-input').fill('1.00')
    await page.getByTestId('wizard-next-button').click()

    const machineHours = page.getByTestId('machine-hours-input')
    if (await machineHours.isVisible()) {
      await machineHours.fill('2')
      await expect(machineHours).toHaveValue('2')
    }
  })
})
