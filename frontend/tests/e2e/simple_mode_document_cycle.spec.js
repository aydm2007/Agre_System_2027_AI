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

test.describe.configure({ mode: 'serial' })
test.setTimeout(120000)

let seedFarmId

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

  const token = await fetchToken(request)
  const headers = withAuthHeaders(token)
  const farmsRes = await request.get(`${endpoints.V1_BASE}/farms/`, { headers })
  expect(farmsRes.ok()).toBeTruthy()
  const farms = readResults(await farmsRes.json())
  expect(farms.length, 'HALT: no farms seeded for simple mode cycle').toBeGreaterThan(0)
  seedFarmId = farms[0].id
})

test('Simple mode documentary cycle: login -> daily log -> reports with strict route blocking', async ({
  page,
  request,
}) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await page.goto(`${BASE_URL}/daily-log`)
  await page.waitForURL(/\/daily-log(\/|$)|\/dashboard(\/|$)/, { timeout: 30000 })
  if (!/\/daily-log(\/|$)/.test(page.url())) {
    await page.goto(`${BASE_URL}/daily-log`)
  }
  await expect(page.getByTestId('daily-log-page-title')).toBeVisible({ timeout: 20000 })

  await page.getByTestId('date-input').fill('2026-02-20')
  await page.getByTestId('farm-select').selectOption(String(seedFarmId))
  await selectFirstOption(page.getByTestId('location-select'), 'location')
  await selectFirstOption(page.getByTestId('task-select'), 'task')

  await page.getByTestId('wizard-next-button').click()
  await expect(page.getByTestId('wizard-step-resources')).toBeVisible()

  await page.getByTestId('labor-entry-mode-select').selectOption('CASUAL_BATCH')
  await page.getByTestId('casual-workers-count-input').fill('5')
  await page.getByTestId('labor-surra-input').fill('1.00')
  await page.getByTestId('wizard-next-button').click()
  await expect(page.getByTestId('daily-log-save')).toBeVisible()

  if (
    await page
      .getByTestId('machine-hours-input')
      .isVisible()
      .catch(() => false)
  ) {
    const machineSelect = page.getByTestId('machine-asset-select')
    await selectFirstOption(machineSelect, 'machine-asset')
    await page.getByTestId('machine-hours-input').fill('1.50')
  }

  if (
    await page
      .getByTestId('well-reading-input')
      .isVisible()
      .catch(() => false)
  ) {
    const wellSelect = page.getByTestId('well-asset-select')
    await selectFirstOption(wellSelect, 'well-asset')
    await page.getByTestId('well-reading-input').fill('120')
  }

  const createLogResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/daily-logs/') && response.request().method() === 'POST',
  )
  const createActivityResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/activities/') && response.request().method() === 'POST',
  )

  await page.getByTestId('daily-log-save').click()

  const logResp = await createLogResponse
  expect(logResp.ok(), `HALT: daily-log create failed: ${await logResp.text()}`).toBeTruthy()

  const activityResp = await createActivityResponse
  expect(
    activityResp.ok(),
    `HALT: activity create failed: ${await activityResp.text()}`,
  ).toBeTruthy()

  await expect(page).toHaveURL(/\/daily-log-history/, { timeout: 30000 })

  await page.goto(`${BASE_URL}/reports`)
  await expect(page).toHaveURL(/\/reports(\/|$)/)

  await page.goto(`${BASE_URL}/sales`)
  await expect(page.getByTestId('sales-main-grid')).toHaveCount(0)

  await page.goto(`${BASE_URL}/finance`)
  await expect(page.getByTestId('finance-ledger-page')).toHaveCount(0)
})
