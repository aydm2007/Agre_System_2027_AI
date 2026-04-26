import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import { expect, test } from '@playwright/test'
import { BASE_URL, endpoints, readResults, withAuthHeaders } from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })
test.setTimeout(120000)

const RABOUIA_SLUG = 'al-rabouia'
const RABOUIA_USER = 'rab_system_admin'
const RABOUIA_PASS = 'RabSarUAT#2026'
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const pythonBin = process.env.PLAYWRIGHT_BACKEND_PYTHON || 'python'

let farmId
let farmName
let cornContext

function seedPack() {
  execFileSync(
    pythonBin,
    [
      'backend/manage.py',
      'run_rabouia_sarima_uat',
      '--clean-seed',
      '--artifact-root',
      'docs/evidence/uat/rabouia-sarima/playwright',
    ],
    { cwd: repoRoot, stdio: 'inherit' },
  )
}

async function fetchTokens(request) {
  const response = await request.post(`${endpoints.AUTH_BASE}/auth/token/`, {
    data: { username: RABOUIA_USER, password: RABOUIA_PASS },
  })
  expect(response.ok(), 'HALT: cannot authenticate Rabouia UAT user').toBeTruthy()
  const body = await response.json()
  expect(body?.access).toBeTruthy()
  expect(body?.refresh).toBeTruthy()
  return body
}

async function ensureLoggedIn(page, request) {
  const { access, refresh } = await fetchTokens(request)
  await page.goto(`${BASE_URL}/login`)
  await page.evaluate(
    ({ accessToken, refreshToken }) => {
      window.localStorage.setItem('accessToken', accessToken)
      window.localStorage.setItem('refreshToken', refreshToken)
    },
    { accessToken: access, refreshToken: refresh },
  )
  await page.goto(`${BASE_URL}/dashboard`)
  await expect(page).toHaveURL(/dashboard|\/$/, { timeout: 30000 })
}

async function selectOptionWhenAvailable(selectLocator, optionValue, fieldName) {
  await expect(selectLocator, `HALT: missing select for ${fieldName}`).toBeVisible()
  const target = String(optionValue)
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const match = selectLocator.locator(`option[value="${target}"]`)
    if ((await match.count()) > 0) {
      await selectLocator.selectOption(target)
      return
    }
    await selectLocator.page().waitForTimeout(250)
  }
  throw new Error(`HALT: option ${target} not available for ${fieldName}`)
}

async function selectFarmOnSurface(page) {
  const globalSelector = page.getByTestId('farm-selector-button')
  if (await globalSelector.isVisible().catch(() => false)) {
    await globalSelector.click()
    await page.getByTestId(`farm-option-${farmId}`).click()
    return
  }
  const namedFarmCombobox = page.getByRole('combobox', { name: 'المزرعة' })
  if (await namedFarmCombobox.isVisible().catch(() => false)) {
    await namedFarmCombobox.selectOption({ label: farmName })
    return
  }
  const pageFarmFilter = page.getByTestId('page-farm-filter')
  if (await pageFarmFilter.isVisible().catch(() => false)) {
    await pageFarmFilter.selectOption(String(farmId))
  }
}

test.beforeAll(async ({ request }) => {
  test.setTimeout(180000)
  seedPack()
  const { access } = await fetchTokens(request)
  const headers = withAuthHeaders(access)

  const farmsResponse = await request.get(`${endpoints.V1_BASE}/farms/`, { headers })
  expect(farmsResponse.ok()).toBeTruthy()
  const farms = readResults(await farmsResponse.json())
  const farm = farms.find((row) => row?.slug === RABOUIA_SLUG)
  expect(farm, 'HALT: Rabouia farm missing from API').toBeTruthy()
  farmId = farm.id
  farmName = farm.name

  const [cropsResponse, plansResponse, tasksResponse] = await Promise.all([
    request.get(`${endpoints.V1_BASE}/crops/?farm_id=${farmId}`, { headers }),
    request.get(`${endpoints.V1_BASE}/crop-plans/?farm=${farmId}`, { headers }),
    request.get(`${endpoints.V1_BASE}/tasks/`, { headers }),
  ])
  expect(cropsResponse.ok()).toBeTruthy()
  expect(plansResponse.ok()).toBeTruthy()
  expect(tasksResponse.ok()).toBeTruthy()

  const crops = readResults(await cropsResponse.json())
  const plans = readResults(await plansResponse.json())
  const tasks = readResults(await tasksResponse.json())

  const cornCrop = crops.find((row) => String(row?.name || '').includes('ذرة'))
  const cornPlan = plans.find((row) => String(row?.name || '').includes('Corn'))
  const cornTask = tasks.find((row) => String(row?.name || '').includes('خدمة ذرة'))
  const locationId = cornPlan?.locations?.[0]?.id || cornPlan?.locations?.[0]
  expect(cornCrop).toBeTruthy()
  expect(cornPlan).toBeTruthy()
  expect(cornTask).toBeTruthy()
  expect(locationId).toBeTruthy()

  cornContext = {
    cropId: String(cornCrop.id),
    cropName: cornCrop.name,
    locationId: String(locationId),
    taskId: String(cornTask.id),
  }
})

test('Rabouia SIMPLE renders smart-card technical daily log surface', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await page.goto(`${BASE_URL}/daily-log`)
  await selectOptionWhenAvailable(page.getByTestId('farm-select'), farmId, 'Rabouia farm')
  await selectOptionWhenAvailable(page.getByTestId('crop-select'), cornContext.cropId, 'corn crop')
  await selectOptionWhenAvailable(page.getByTestId('location-select'), cornContext.locationId, 'corn location')
  await selectOptionWhenAvailable(page.getByTestId('task-select'), cornContext.taskId, 'corn task')
  await expect(page.getByTestId('daily-log-smart-card')).toBeVisible()
  await expect(page.getByTestId('daily-log-smart-card-title')).toContainText(cornContext.cropName)
})

test('Rabouia SIMPLE fixed assets stay posture-only', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await selectFarmOnSurface(page)
  await page.goto(`${BASE_URL}/fixed-assets`)
  if (!(await page.getByTestId('fixed-assets-policy-banner').isVisible().catch(() => false))) {
    await page.goto(`${BASE_URL}/dashboard`)
    await selectFarmOnSurface(page)
    await page.goto(`${BASE_URL}/fixed-assets`)
  }
  await expect(page.getByTestId('fixed-assets-policy-banner')).toContainText('تتبع فقط')
})
