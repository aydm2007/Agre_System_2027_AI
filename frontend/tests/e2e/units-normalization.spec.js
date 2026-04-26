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

test('Canonical units stay derived on governed authoring surfaces without free-text UOM entry', async ({
  page,
  request,
}) => {
  const tokens = await fetchTokens(request)
  await loginViaTokens(page, tokens)

  await page.goto(`${BASE_URL}/materials-catalog`)
  await expect(page.getByText('كتالوج المواد والخامات')).toBeVisible({ timeout: 30000 })
  await expect(page.getByTestId('materials-catalog-unit-select')).toBeVisible({ timeout: 30000 })

  const unitSelect = page.getByTestId('materials-catalog-unit-select')
  const options = unitSelect.locator('option')
  const optionCount = await options.count()
  let selectedUnit = null
  for (let i = 0; i < optionCount; i += 1) {
    const value = await options.nth(i).getAttribute('value')
    if (value) {
      selectedUnit = value
      break
    }
  }
  expect(selectedUnit, 'HALT: no selectable canonical unit found').toBeTruthy()
  await unitSelect.selectOption(String(selectedUnit))
  const catalogUom = page.getByTestId('materials-catalog-uom-input')
  await expect(catalogUom).toHaveAttribute('readonly', '')
  await expect(catalogUom).not.toHaveValue('')
})
