import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import { expect, test } from '@playwright/test'
import { BASE_URL, endpoints, readResults, withAuthHeaders } from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })
test.setTimeout(120000)

const SARIMA_SLUG = 'al-sarima'
const SARIMA_USER = 'sar_system_admin'
const SARIMA_PASS = 'RabSarUAT#2026'
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const pythonBin = process.env.PLAYWRIGHT_BACKEND_PYTHON || 'python'

let farmId
let farmName

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
    data: { username: SARIMA_USER, password: SARIMA_PASS },
  })
  expect(response.ok(), 'HALT: cannot authenticate Sarima UAT user').toBeTruthy()
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
  const farm = farms.find((row) => row?.slug === SARIMA_SLUG)
  expect(farm, 'HALT: Sarima farm missing from API').toBeTruthy()
  farmId = farm.id
  farmName = farm.name
})

test('Sarima STRICT exposes governed fixed-assets and fuel surfaces', async ({ page, request }) => {
  await ensureLoggedIn(page, request)

  await page.goto(`${BASE_URL}/fixed-assets`)
  await selectFarmOnSurface(page)
  await expect(page.getByTestId('fixed-assets-policy-banner')).toContainText('الرسملة الكاملة')

  await page.goto(`${BASE_URL}/fuel-reconciliation`)
  await selectFarmOnSurface(page)
  await expect(page.getByTestId('fuel-reconciliation-policy-banner')).toContainText('STRICT')
})

test('Sarima STRICT exposes governed contract and supplier settlement surfaces', async ({ page, request }) => {
  await ensureLoggedIn(page, request)

  await page.goto(`${BASE_URL}/sharecropping`)
  await selectFarmOnSurface(page)
  await expect(page.getByTestId('contract-operations-policy-banner')).toContainText('الوضع الصارم')

  await page.goto(`${BASE_URL}/finance/supplier-settlements`)
  await selectFarmOnSurface(page)
  await expect(page.getByTestId('supplier-settlement-policy-banner')).toContainText('STRICT')
})
