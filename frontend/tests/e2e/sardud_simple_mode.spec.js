import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureFarmSelected,
  ensureLoggedIn,
  fetchSystemMode,
  SARDOOD_FARM_REGEX,
} from './helpers/e2eAuth'
import { ROUTES } from './helpers/e2eFixtures'

test.describe.configure({ mode: 'serial' })
test.setTimeout(180000)

async function selectOptionByText(selectLocator, matcher, fieldName) {
  await expect(selectLocator).toBeVisible({ timeout: 20000 })

  for (let attempt = 0; attempt < 30; attempt += 1) {
    const options = selectLocator.locator('option')
    const count = await options.count()
    for (let idx = 0; idx < count; idx += 1) {
      const option = options.nth(idx)
      const value = await option.getAttribute('value')
      const label = (await option.textContent().catch(() => '')) || ''
      if (value && matcher.test(label)) {
        await selectLocator.selectOption(value)
        return value
      }
    }
    await selectLocator.page().waitForTimeout(250)
  }

  throw new Error(`HALT: no selectable option found for ${fieldName}`)
}

async function selectFirstOption(selectLocator, fieldName) {
  await expect(selectLocator).toBeVisible({ timeout: 20000 })

  for (let attempt = 0; attempt < 30; attempt += 1) {
    const options = selectLocator.locator('option')
    const count = await options.count()
    for (let idx = 0; idx < count; idx += 1) {
      const value = await options.nth(idx).getAttribute('value')
      if (value) {
        await selectLocator.selectOption(value)
        return value
      }
    }
    await selectLocator.page().waitForTimeout(250)
  }

  throw new Error(`HALT: no selectable option found for ${fieldName}`)
}

async function advanceWizardUntilSave(page, maxSteps = 4) {
  for (let step = 0; step < maxSteps; step += 1) {
    const saveButton = page.getByTestId('daily-log-save')
    if (await saveButton.isVisible().catch(() => false)) {
      return
    }
    await page.getByTestId('wizard-next-button').click()
  }
  await expect(page.getByTestId('daily-log-save')).toBeVisible({ timeout: 10000 })
}

test.beforeAll(async ({ request }) => {
  const modeBody = await fetchSystemMode(request)
  expect(Boolean(modeBody?.strict_erp_mode)).toBeFalsy()
})

test('Sardood SIMPLE smoke: dashboard, governance settings, and tree census load', async ({
  page,
  request,
}) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page, SARDOOD_FARM_REGEX)

  await page.goto(`${BASE_URL}${ROUTES.DASHBOARD}`)
  await expect(page.getByText('وضع مبسط')).toBeVisible({ timeout: 15000 })

  await page.goto(`${BASE_URL}/settings?tab=governance&farm=28`)
  await expect(
    page.getByRole('button', { name: 'السياسة الفعالة' }),
  ).toBeVisible({ timeout: 20000 })
  await expect(page.getByRole('button', { name: 'الصحة التشغيلية' })).toBeVisible()

  await page.goto(`${BASE_URL}${ROUTES.TREE_CENSUS}`)
  if (/\/login(?:\/|$)/.test(page.url())) {
    await ensureLoggedIn(page, request)
    await ensureFarmSelected(page, SARDOOD_FARM_REGEX)
    await page.goto(`${BASE_URL}${ROUTES.TREE_CENSUS}`)
  }
  await expect(page.getByText('جرد الدفعات الشجرية')).toBeVisible({ timeout: 20000 })
})

test('Sardood SIMPLE seasonal daily log saves with labor inputs and smart card context', async ({
  page,
  request,
}) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page, SARDOOD_FARM_REGEX)

  await page.goto(`${BASE_URL}${ROUTES.DAILY_LOG}`)
  await expect(page.getByTestId('daily-log-page-title')).toBeVisible({ timeout: 20000 })

  await page.getByTestId('date-input').fill('2026-03-10')
  await selectOptionByText(page.getByTestId('farm-select'), SARDOOD_FARM_REGEX, 'farm')
  await selectOptionByText(page.getByTestId('crop-select'), /طماطم/i, 'crop')
  await selectOptionByText(
    page.getByTestId('location-select'),
    /حقل الخضروات.*القطاع الجنوبي/i,
    'location',
  )
  await selectOptionByText(page.getByTestId('task-select'), /عملية موسمية E2E/i, 'task')

  await expect(page.getByTestId('linked-crop-plan-indicator')).toContainText(
    'خطة طماطم - سردود 2026',
    { timeout: 15000 },
  )

  await page.getByTestId('wizard-next-button').click()
  await expect(page.getByTestId('wizard-step-resources')).toBeVisible()

  await page.getByTestId('labor-entry-mode-select').selectOption('CASUAL_BATCH')
  await page.getByTestId('casual-workers-count-input').fill('15')
  await page.getByTestId('labor-surra-input').fill('1.5')

  await advanceWizardUntilSave(page)

  const createLogPromise = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/daily-logs/') && response.request().method() === 'POST',
    { timeout: 15000 },
  )

  await page.getByTestId('daily-log-save').click()

  const logResp = await createLogPromise
  expect(logResp.ok(), `HALT: daily-log POST failed: ${await logResp.text()}`).toBeTruthy()
  await expect(page).toHaveURL(/\/daily-log-history/, { timeout: 30000 })
})

test('Sardood SIMPLE perennial smart contract loads with farm-scoped plan and controls', async ({
  page,
  request,
}) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page, SARDOOD_FARM_REGEX)

  await page.goto(`${BASE_URL}${ROUTES.DAILY_LOG}`)
  await expect(page.getByTestId('daily-log-page-title')).toBeVisible({ timeout: 20000 })

  await page.getByTestId('date-input').fill('2026-03-12')
  await selectOptionByText(page.getByTestId('farm-select'), SARDOOD_FARM_REGEX, 'farm')
  await selectOptionByText(page.getByTestId('crop-select'), /بن|قات/i, 'perennial crop')
  await selectOptionByText(
    page.getByTestId('location-select'),
    /حقل البن|حقل القات/i,
    'perennial location',
  )
  await selectOptionByText(page.getByTestId('task-select'), /خدمة معمرة E2E/i, 'perennial task')

  await expect(page.getByTestId('linked-crop-plan-indicator')).toContainText(
    /خطة بن - سردود 2026|خطة قات - سردود 2026/,
    { timeout: 15000 },
  )
  await expect(page.getByText('الخدمة المعمرة')).toBeVisible()

  const treeDeltaInput = page.getByTestId('tree-count-delta-input')
  if (await treeDeltaInput.isVisible().catch(() => false)) {
    await treeDeltaInput.fill('2')
  }

  await page.getByTestId('wizard-next-button').click()
  await expect(page.getByTestId('wizard-step-resources')).toBeVisible()

  const serviceRowAdd = page.getByTestId('service-row-add')
  if (await serviceRowAdd.isVisible().catch(() => false)) {
    await serviceRowAdd.click()

    const varietySelect = page.locator('select[data-testid^="service-row-variety-"]').first()
    await selectFirstOption(varietySelect, 'service variety')
    await page.locator('input[data-testid^="service-row-count-"]').first().fill('3')
  }
})
