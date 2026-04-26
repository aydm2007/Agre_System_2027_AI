import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import { expect, test } from '@playwright/test'
import { BASE_URL, E2E_PASS, E2E_USER, endpoints } from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })
test.setTimeout(120000)

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
    data: { username: E2E_USER, password: E2E_PASS },
  })
  expect(response.ok(), 'HALT: cannot authenticate settings proof user').toBeTruthy()
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

test('Settings permission templates stay Arabic-first while technical slugs stay hidden from the main cards', async ({
  page,
  request,
}) => {
  const tokens = await fetchTokens(request)
  await loginViaTokens(page, tokens)

  await page.goto(`${BASE_URL}/settings?tab=templates`)
  await expect(page.getByRole('button', { name: 'قوالب الصلاحيات والربط' })).toBeVisible({
    timeout: 30000,
  })
  await page.getByRole('button', { name: 'قوالب الصلاحيات والربط' }).click()
  await expect(page.getByTestId('role-template-matrix-page')).toBeVisible()

  const firstCard = page.locator('[data-testid^="role-template-card-"]').first()
  await expect(firstCard).toBeVisible()
  const nameText = (await firstCard.locator('[data-testid^="role-template-name-"]').textContent()) || ''
  expect(/[\u0600-\u06FF]/.test(nameText)).toBeTruthy()
  await expect(firstCard.locator('[data-testid^="role-template-slug-"]')).toHaveCount(0)
})
