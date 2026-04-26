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
  expect(response.ok(), 'HALT: cannot authenticate Rabouia SIMPLE user').toBeTruthy()
  return response.json()
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
  await expect(page.locator('body')).toBeVisible()
}

test.beforeAll(async ({ request }) => {
  test.setTimeout(180000)
  seedPack()
  const { access } = await fetchTokens(request)
  const farmsResponse = await request.get(`${endpoints.V1_BASE}/farms/`, {
    headers: withAuthHeaders(access),
  })
  expect(farmsResponse.ok()).toBeTruthy()
  const farms = readResults(await farmsResponse.json())
  const farm = farms.find((row) => row?.slug === RABOUIA_SLUG)
  expect(farm, 'HALT: Rabouia farm missing from API').toBeTruthy()
  farmId = String(farm.id)
})

test('Rabouia SIMPLE uses one integrated operations hub cycle', async ({ page, request }) => {
  await ensureLoggedIn(page, request)

  await page.goto(`${BASE_URL}/simple-hub`)
  await expect(page.getByTestId('simple-hub-title')).toBeVisible()
  await expect(page.getByTestId('simple-hub-mode-badge')).toContainText(/مبسط|SIMPLE/i)
  await expect(page.getByTestId('simple-hub-farm-select')).toHaveValue(farmId)

  await page.getByTestId('simple-hub-card-daily-log-cta').click()
  await expect(page).toHaveURL(/\/daily-log$/)
  await expect(page.getByTestId('daily-log-simple-operations-banner')).toBeVisible()
  await page.getByTestId('daily-log-open-custody-shortcut').click()

  await expect(page).toHaveURL(/\/inventory\/custody$/)
  await expect(page.getByTestId('custody-workspace-page')).toBeVisible()
  await expect(page.getByTestId('custody-daily-log-context-banner')).toBeVisible()
  await page.getByTestId('custody-open-reports-cta').click()

  await expect(page).toHaveURL(/\/reports$/)
  await expect(page.getByTestId('simple-report-presets-panel')).toBeVisible()
  await expect(page.getByTestId('reports-diagnostics-panel')).toBeVisible()
  await page.getByTestId('reports-open-daily-log-link').click()

  await expect(page).toHaveURL(/\/daily-log$/)
  await page.goto(`${BASE_URL}/simple-hub`)
  await page.getByTestId('simple-hub-card-harvest-cta').click()

  await expect(page).toHaveURL(/\/daily-log$/)
  await expect(page.getByTestId('daily-log-launch-banner')).toBeVisible()
  await expect(page.getByTestId('daily-log-page-title')).toBeVisible()
})
