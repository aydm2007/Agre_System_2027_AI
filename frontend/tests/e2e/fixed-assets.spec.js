import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import { expect, test } from '@playwright/test'
import { BASE_URL, endpoints, readResults, withAuthHeaders } from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })
test.setTimeout(120000)

const RABOUIA_SLUG = 'al-rabouia'
const RABOUIA_USER = 'rab_system_admin'
const SARIMA_SLUG = 'al-sarima'
const SARIMA_USER = 'sar_system_admin'
const SHARED_PASS = 'RabSarUAT#2026'
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const pythonBin = process.env.PLAYWRIGHT_BACKEND_PYTHON || 'python'
const uatArtifactRoot = process.env.PLAYWRIGHT_ARTIFACT_ROOT
  ? path.join(path.resolve(process.env.PLAYWRIGHT_ARTIFACT_ROOT), 'rabouia-sarima-uat')
  : path.join(repoRoot, 'docs', 'evidence', 'uat', 'rabouia-sarima', 'playwright')

let rabouiaFarmId
let rabouiaFarmName
let sarimaFarmId
let sarimaFarmName

function seedPack() {
  execFileSync(
    pythonBin,
    [
      'backend/manage.py',
      'run_rabouia_sarima_uat',
      '--clean-seed',
      '--artifact-root',
      uatArtifactRoot,
    ],
    { cwd: repoRoot, stdio: 'inherit' },
  )
}

async function fetchTokens(request, username) {
  const response = await request.post(`${endpoints.AUTH_BASE}/auth/token/`, {
    data: { username, password: SHARED_PASS },
  })
  expect(response.ok(), `HALT: cannot authenticate ${username} for fixed-assets gate`).toBeTruthy()
  const body = await response.json()
  expect(body?.access).toBeTruthy()
  expect(body?.refresh).toBeTruthy()
  return body
}

async function ensureLoggedIn(page, request, username) {
  const { access, refresh } = await fetchTokens(request, username)
  await page.goto(`${BASE_URL}/login`)
  await page.evaluate(
    ({ accessToken, refreshToken }) => {
      window.localStorage.setItem('accessToken', accessToken)
      window.localStorage.setItem('refreshToken', refreshToken)
    },
    { accessToken: access, refreshToken: refresh },
  )
  await page.goto(`${BASE_URL}/dashboard`)
  await expect(page.locator('body')).toBeVisible()
}

async function persistFarmSelection(page, farmId) {
  await page.evaluate((targetFarmId) => {
    const value = String(targetFarmId)
    window.localStorage.setItem('selected_farm_id', value)
    window.localStorage.setItem('page_farm.dashboard', value)
    window.localStorage.setItem('page_farm.fixed-assets', value)
  }, farmId)
}

async function selectFarmOnSurface(page, farmId, farmName) {
  const globalSelector = page.getByTestId('farm-selector-button')
  if (await globalSelector.isVisible().catch(() => false)) {
    await globalSelector.click()
    await page.getByTestId(`farm-option-${farmId}`).click()
    await persistFarmSelection(page, farmId)
    await expect(globalSelector).toContainText(farmName, { timeout: 10000 })
    return
  }

  const namedFarmCombobox = page.getByRole('combobox', { name: 'المزرعة' })
  if (await namedFarmCombobox.isVisible().catch(() => false)) {
    await namedFarmCombobox.selectOption({ label: farmName })
    await persistFarmSelection(page, farmId)
    return
  }

  const pageFarmFilter = page.getByTestId('page-farm-filter')
  if (await pageFarmFilter.isVisible().catch(() => false)) {
    await pageFarmFilter.selectOption(String(farmId))
    await persistFarmSelection(page, farmId)
  }
}

async function gotoFixedAssets(page, farmId, farmName) {
  await persistFarmSelection(page, farmId)
  await page.goto(`${BASE_URL}/dashboard`)
  await selectFarmOnSurface(page, farmId, farmName)
  await persistFarmSelection(page, farmId)
  await page.goto(`${BASE_URL}/fixed-assets`)
  await page.waitForURL(/\/fixed-assets(\/|$)|\/dashboard(\/|$)/, { timeout: 30000 })
  await selectFarmOnSurface(page, farmId, farmName)
  await persistFarmSelection(page, farmId)

  const banner = page.getByTestId('fixed-assets-policy-banner')
  if (!(await banner.isVisible().catch(() => false))) {
    await persistFarmSelection(page, farmId)
    await page.goto(`${BASE_URL}/dashboard`)
    await selectFarmOnSurface(page, farmId, farmName)
    await persistFarmSelection(page, farmId)
    await page.goto(`${BASE_URL}/fixed-assets`)
    await page.waitForURL(/\/fixed-assets(\/|$)|\/dashboard(\/|$)/, { timeout: 30000 })
    await selectFarmOnSurface(page, farmId, farmName)
    await persistFarmSelection(page, farmId)
  }
}

test.beforeAll(async ({ request }) => {
  test.setTimeout(180000)
  seedPack()

  const { access } = await fetchTokens(request, SARIMA_USER)
  const headers = withAuthHeaders(access)
  const farmsResponse = await request.get(`${endpoints.V1_BASE}/farms/`, { headers })
  expect(farmsResponse.ok()).toBeTruthy()
  const farms = readResults(await farmsResponse.json())

  const rabouiaFarm = farms.find((row) => row?.slug === RABOUIA_SLUG)
  const sarimaFarm = farms.find((row) => row?.slug === SARIMA_SLUG)
  expect(rabouiaFarm, 'HALT: Rabouia farm missing from API').toBeTruthy()
  expect(sarimaFarm, 'HALT: Sarima farm missing from API').toBeTruthy()

  rabouiaFarmId = rabouiaFarm.id
  rabouiaFarmName = rabouiaFarm.name
  sarimaFarmId = sarimaFarm.id
  sarimaFarmName = sarimaFarm.name
})

test('fixed assets stays posture-only for Rabouia SIMPLE', async ({ page, request }) => {
  await ensureLoggedIn(page, request, RABOUIA_USER)
  await gotoFixedAssets(page, rabouiaFarmId, rabouiaFarmName)
  await expect(page.getByTestId('fixed-assets-policy-banner')).toContainText('تتبع فقط')
})

test('fixed assets exposes governed capitalization for Sarima STRICT', async ({ page, request }) => {
  await ensureLoggedIn(page, request, SARIMA_USER)
  await gotoFixedAssets(page, sarimaFarmId, sarimaFarmName)
  await expect(page.getByTestId('fixed-assets-policy-banner')).toContainText('الرسملة الكاملة')
  await expect(page.getByTestId('fixed-assets-table')).toBeVisible()
  await expect(page.getByTestId('fixed-assets-amount-column')).toBeVisible()
})
