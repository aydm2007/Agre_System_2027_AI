import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import { expect, test } from '@playwright/test'
import { BASE_URL, endpoints } from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })
test.setTimeout(120000)

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const pythonBin = process.env.PLAYWRIGHT_BACKEND_PYTHON || 'python'
const PASSWORD = 'RabSarUAT#2026'

const USERS = {
  rab: 'rab_system_admin',
  sar: 'sar_system_admin',
}

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

test('Rabouia SIMPLE shows custody as accepted-balance workspace without issue form', async ({
  page,
  request,
}) => {
  const tokens = await fetchTokens(request, USERS.rab)
  await loginViaTokens(page, tokens)

  await page.goto(`${BASE_URL}/inventory/custody`)
  await expect(page.getByRole('heading', { name: 'مساحة عهدة المشرف' })).toBeVisible({
    timeout: 30000,
  })
  await page.locator('select').first().selectOption({ label: 'الربوعية' })
  await expect(page.getByText('في المود البسيط تظهر العهدة كمصدر صرف فني فقط')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'الرصيد المقبول' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'حركات العهدة' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'إصدار عهدة جديدة' })).toHaveCount(0)
})

test('Sarima STRICT exposes full custody issuance surface on the same workflow truth', async ({
  page,
  request,
}) => {
  const tokens = await fetchTokens(request, USERS.sar)
  await loginViaTokens(page, tokens)

  await page.goto(`${BASE_URL}/inventory/custody`)
  await expect(page.getByRole('heading', { name: 'مساحة عهدة المشرف' })).toBeVisible({
    timeout: 30000,
  })
  await page.locator('select').first().selectOption({ label: 'الصارمة' })
  await expect(page.getByRole('heading', { name: 'إصدار عهدة جديدة' })).toBeVisible()
  await expect(page.getByTestId('custody-item-select')).toBeVisible()
  await expect(page.getByTestId('custody-location-select')).toBeVisible()
})
