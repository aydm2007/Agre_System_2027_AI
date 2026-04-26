import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import { expect, test } from '@playwright/test'
import { BASE_URL, endpoints } from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })
test.setTimeout(120000)

const RABOUIA_USER = 'rab_system_admin'
const PASSWORD = 'RabSarUAT#2026'
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const pythonBin = process.env.PLAYWRIGHT_BACKEND_PYTHON || 'python'

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
    data: { username: RABOUIA_USER, password: PASSWORD },
  })
  expect(response.ok(), 'HALT: cannot authenticate Rabouia UAT user').toBeTruthy()
  return response.json()
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

test.beforeAll(async () => {
  test.setTimeout(180000)
  seedPack()
})

test('Reports hub routes harvest entry into DailyLog alias instead of allowing write-side input', async ({
  page,
  request,
}) => {
  const tokens = await fetchTokens(request)
  await loginViaTokens(page, tokens)

  await page.goto(`${BASE_URL}/reports`)
  await expect(page.getByTestId('reports-diagnostics-panel')).toBeVisible()
  await expect(page.getByText('شاشة التقارير مخصّصة للقراءة والتحليل والتوليد فقط.')).toBeVisible()

  await page.getByTestId('reports-harvest-entry-link').click()
  await page.waitForURL(/\/daily-log(\/|$)/)

  await expect(page.getByTestId('daily-log-page-title')).toBeVisible()
  await expect(page.getByTestId('daily-log-launch-banner')).toBeVisible()
  await expect(page.getByTestId('daily-log-launch-banner')).toContainText(
    'الإدخال التنفيذي للحصاد يتم من هنا',
  )
})
