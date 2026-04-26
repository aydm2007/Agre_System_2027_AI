import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import { expect, test } from '@playwright/test'
import { BASE_URL, endpoints, readResults, withAuthHeaders } from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })
test.setTimeout(120000)

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const pythonBin = process.env.PLAYWRIGHT_BACKEND_PYTHON || 'python'
const RABOUIA_USER = 'rab_system_admin'
const SARIMA_USER = 'sar_system_admin'
const PASSWORD = 'RabSarUAT#2026'

let rabouiaId
let sarimaId

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

async function fetchTokens(request, username) {
  const response = await request.post(`${endpoints.AUTH_BASE}/auth/token/`, {
    data: { username, password: PASSWORD },
  })
  expect(response.ok(), `HALT: cannot authenticate ${username}`).toBeTruthy()
  const body = await response.json()
  expect(body?.access).toBeTruthy()
  expect(body?.refresh).toBeTruthy()
  return body
}

async function selectFarmOnSurface(page, farmId) {
  const globalSelector = page.getByTestId('farm-selector-button')
  if (await globalSelector.isVisible().catch(() => false)) {
    await globalSelector.click()
    await page.getByTestId(`farm-option-${farmId}`).click()
    return
  }

  const pageFarmFilter = page.getByTestId('page-farm-filter')
  if (await pageFarmFilter.isVisible().catch(() => false)) {
    await pageFarmFilter.selectOption(String(farmId))
  }
}

async function loginViaTokens(page, tokens) {
  await page.goto(`${BASE_URL}/login`)
  await page.evaluate(
    ({ accessToken, refreshToken }) => {
      window.localStorage.setItem('accessToken', accessToken)
      window.localStorage.setItem('refreshToken', refreshToken)
    },
    { accessToken: tokens.access, refreshToken: tokens.refresh },
  )
  await page.goto(`${BASE_URL}/dashboard`)
  await expect(page).toHaveURL(/dashboard|\/$/, { timeout: 30000 })
}

test.beforeAll(async ({ request }) => {
  test.setTimeout(180000)
  seedPack()
  const rabouiaTokens = await fetchTokens(request, RABOUIA_USER)
  const farmsResponse = await request.get(`${endpoints.V1_BASE}/farms/`, { headers: withAuthHeaders(rabouiaTokens.access) })
  expect(farmsResponse.ok()).toBeTruthy()
  const farms = readResults(await farmsResponse.json())
  rabouiaId = farms.find((row) => row?.slug === 'al-rabouia')?.id
  sarimaId = farms.find((row) => row?.slug === 'al-sarima')?.id
  expect(rabouiaId).toBeTruthy()
  expect(sarimaId).toBeTruthy()
})

test('Rabouia reports stay usable without forbidden strict finance leakage', async ({ page, request }) => {
  const tokens = await fetchTokens(request, RABOUIA_USER)
  const headers = withAuthHeaders(tokens.access)
  const response = await request.get(
    `${endpoints.V1_BASE}/advanced-report/?farm=${rabouiaId}&start=2026-01-01&end=2026-12-31`,
    { headers },
  )
  expect(response.ok()).toBeTruthy()
  const body = await response.json()
  const serialized = JSON.stringify(body)
  expect(serialized.includes('exact_amount')).toBeFalsy()
  expect(serialized.includes('financial_trace')).toBeFalsy()
  await loginViaTokens(page, tokens)
  await page.goto(`${BASE_URL}/reports`)
  await expect(page.getByTestId('reports-farm-filter')).toBeVisible()
})

test('Sarima advanced reports screen remains available for STRICT governance surface', async ({ page, request }) => {
  const tokens = await fetchTokens(request, SARIMA_USER)
  await loginViaTokens(page, tokens)
  await selectFarmOnSurface(page, sarimaId)
  await page.goto(`${BASE_URL}/finance/advanced-reports`)
  if (!(await page.getByTestId('advanced-reports-page').isVisible().catch(() => false))) {
    await page.goto(`${BASE_URL}/dashboard`)
    await selectFarmOnSurface(page, sarimaId)
    await page.goto(`${BASE_URL}/finance/advanced-reports`)
  }
  await expect(page.getByTestId('advanced-reports-page')).toBeVisible()
  await expect(page.getByTestId('generate-report-button')).toBeVisible()
})
