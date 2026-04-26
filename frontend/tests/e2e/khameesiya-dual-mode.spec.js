import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  endpoints,
  readResults,
  withAuthHeaders,
} from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })
test.setTimeout(120000)

const KHAMEESIYA_SLUG = process.env.KHAMEESIYA_FARM_SLUG || 'al-khameesiya'
const KHAMEESIYA_E2E_USER = process.env.KHAMEESIYA_E2E_USER || 'system_admin'
const KHAMEESIYA_E2E_PASS = process.env.KHAMEESIYA_E2E_PASS || 'KhameesiyaUAT#2026'
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const pythonBin = process.env.PLAYWRIGHT_BACKEND_PYTHON || 'python'

let farmId
let farmName
let tomatoContext

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

function seedKhameesiya() {
  execFileSync(
    pythonBin,
    [
      'backend/manage.py',
      'run_khameesiya_uat',
      '--clean-seed',
      '--artifact-root',
      'docs/evidence/uat/khameesiya/playwright',
    ],
    {
      cwd: repoRoot,
      stdio: 'inherit',
    },
  )
}

async function selectKhameesiyaFarm(page) {
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

async function patchFarmSettings(request, token, nextValues) {
  const listResponse = await request.get(`${endpoints.V1_BASE}/farm-settings/?farm=${farmId}`, {
    headers: withAuthHeaders(token),
  })
  expect(listResponse.ok(), 'HALT: cannot load Khameesiya farm settings').toBeTruthy()
  const payload = await listResponse.json()
  const settings = payload?.results?.[0]
  expect(settings?.id, 'HALT: missing Khameesiya FarmSettings row').toBeTruthy()
  const patchResponse = await request.patch(`${endpoints.V1_BASE}/farm-settings/${settings.id}/`, {
    headers: withAuthHeaders(token),
    data: nextValues,
  })
  expect(patchResponse.ok(), 'HALT: cannot patch Khameesiya farm settings').toBeTruthy()
}

async function fetchKhameesiyaTokens(request) {
  const response = await request.post(`${endpoints.AUTH_BASE}/auth/token/`, {
    data: {
      username: KHAMEESIYA_E2E_USER,
      password: KHAMEESIYA_E2E_PASS,
    },
  })
  expect(response.ok(), 'HALT: cannot authenticate Khameesiya UAT user').toBeTruthy()
  const body = await response.json()
  expect(body?.access, 'HALT: missing Khameesiya access token').toBeTruthy()
  expect(body?.refresh, 'HALT: missing Khameesiya refresh token').toBeTruthy()
  return body
}

async function ensureKhameesiyaLoggedIn(page, request) {
  const { access, refresh } = await fetchKhameesiyaTokens(request)
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

async function setShellMode(page, mode) {
  const switcher = page.getByRole('combobox', { name: 'تغيير وضع النظام' })
  if (!(await switcher.isVisible().catch(() => false))) return
  if (mode === 'STRICT') {
    await switcher.selectOption({ label: 'الوضع الصارم' })
    return
  }
  await switcher.selectOption({ label: 'الوضع المبسط' })
}

test.beforeAll(async ({ request }) => {
  seedKhameesiya()
  const { access: token } = await fetchKhameesiyaTokens(request)
  const headers = withAuthHeaders(token)

  const farmsResponse = await request.get(`${endpoints.V1_BASE}/farms/`, { headers })
  expect(farmsResponse.ok(), 'HALT: cannot load farms for Khameesiya UAT').toBeTruthy()
  const farms = readResults(await farmsResponse.json())
  const farm = farms.find((row) => row?.slug === KHAMEESIYA_SLUG)
  expect(farm, 'HALT: Khameesiya farm missing from API').toBeTruthy()
  farmId = farm.id
  farmName = farm.name

  const [cropsResponse, plansResponse, tasksResponse] = await Promise.all([
    request.get(`${endpoints.V1_BASE}/crops/?farm_id=${farmId}`, { headers }),
    request.get(`${endpoints.V1_BASE}/crop-plans/?farm=${farmId}`, { headers }),
    request.get(`${endpoints.V1_BASE}/tasks/`, { headers }),
  ])
  expect(cropsResponse.ok(), 'HALT: crops API unavailable').toBeTruthy()
  expect(plansResponse.ok(), 'HALT: crop-plans API unavailable').toBeTruthy()
  expect(tasksResponse.ok(), 'HALT: tasks API unavailable').toBeTruthy()

  const crops = readResults(await cropsResponse.json())
  const plans = readResults(await plansResponse.json())
  const tasks = readResults(await tasksResponse.json())

  const tomatoCrop = crops.find((row) => String(row?.name || '').includes('طماطم'))
  const tomatoPlan = plans.find((row) => String(row?.name || '').includes('Khameesiya Tomato'))
  const tomatoTask = tasks.find((row) => String(row?.name || '').includes('خدمة طماطم الخميسية'))

  expect(tomatoCrop, 'HALT: tomato crop missing').toBeTruthy()
  expect(tomatoPlan, 'HALT: tomato plan missing').toBeTruthy()
  expect(tomatoTask, 'HALT: tomato task missing').toBeTruthy()

  const locationId =
    tomatoPlan?.locations?.[0]?.id ||
    tomatoPlan?.locations?.[0] ||
    tomatoPlan?.plan_locations?.[0]?.id
  expect(locationId, 'HALT: tomato location missing').toBeTruthy()

  tomatoContext = {
    cropId: String(tomatoCrop.id),
    cropName: tomatoCrop.name,
    locationId: String(locationId),
    taskId: String(tomatoTask.id),
  }
})

test('Khameesiya SIMPLE posture renders smart-card technical surface only', async ({
  page,
  request,
}) => {
  const { access: token } = await fetchKhameesiyaTokens(request)
  await patchFarmSettings(request, token, {
    mode: 'SIMPLE',
    cost_visibility: 'summarized_amounts',
    fixed_asset_mode: 'tracking_only',
    contract_mode: 'operational_only',
    treasury_visibility: 'hidden',
  })
  const serviceCardsResponse = await request.get(
    `${endpoints.V1_BASE}/service-cards/?farm_id=${farmId}`,
    { headers: withAuthHeaders(token) },
  )
  expect(serviceCardsResponse.ok(), 'HALT: service-cards API unavailable for Khameesiya').toBeTruthy()
  const serviceCards = readResults(await serviceCardsResponse.json())
  expect(serviceCards.length, 'HALT: Khameesiya service cards payload is empty').toBeGreaterThan(0)
  await ensureKhameesiyaLoggedIn(page, request)
  await setShellMode(page, 'SIMPLE')

  await page.goto(`${BASE_URL}/daily-log`)
  await selectOptionWhenAvailable(page.getByTestId('farm-select'), farmId, 'Khameesiya farm')
  await selectOptionWhenAvailable(page.getByTestId('crop-select'), tomatoContext.cropId, 'tomato crop')
  await selectOptionWhenAvailable(
    page.getByTestId('location-select'),
    tomatoContext.locationId,
    'tomato location',
  )
  await selectOptionWhenAvailable(page.getByTestId('task-select'), tomatoContext.taskId, 'tomato task')
  await expect(page.getByTestId('daily-log-smart-card')).toBeVisible()
  await expect(page.getByTestId('daily-log-smart-card-title')).toContainText(tomatoContext.cropName)

  await page.goto(`${BASE_URL}/fixed-assets`)
  await selectKhameesiyaFarm(page)
  await expect(page.getByTestId('fixed-assets-policy-banner')).toContainText('تتبع فقط')
  await expect(page.getByText('قيم مالية محجوبة وملخصة')).toBeVisible()
})

test('Khameesiya STRICT posture exposes governed surfaces over the same farm truth', async ({
  page,
  request,
}) => {
  const { access: token } = await fetchKhameesiyaTokens(request)
  await patchFarmSettings(request, token, {
    mode: 'STRICT',
    cost_visibility: 'full_amounts',
    fixed_asset_mode: 'full_capitalization',
    contract_mode: 'full_erp',
    treasury_visibility: 'visible',
  })
  await ensureKhameesiyaLoggedIn(page, request)
  await setShellMode(page, 'STRICT')

  await page.goto(`${BASE_URL}/fixed-assets`)
  await selectKhameesiyaFarm(page)
  await expect(page.getByTestId('fixed-assets-policy-banner')).toContainText('الرسملة الكاملة')

  await page.goto(`${BASE_URL}/fuel-reconciliation`)
  await selectKhameesiyaFarm(page)
  await expect(page.getByTestId('fuel-reconciliation-policy-banner')).toContainText('STRICT')

  await page.goto(`${BASE_URL}/sharecropping`)
  await selectKhameesiyaFarm(page)
  await expect(page.getByTestId('contract-operations-policy-banner')).toContainText('الوضع الصارم')

  await page.goto(`${BASE_URL}/finance/supplier-settlements`)
  await selectKhameesiyaFarm(page)
  await expect(page.getByTestId('supplier-settlement-policy-banner')).toContainText('STRICT')
})
