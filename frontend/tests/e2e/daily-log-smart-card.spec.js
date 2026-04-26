import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureLoggedIn,
  endpoints,
  fetchToken,
  readResults,
  resolveAccessibleFarmId,
  withAuthHeaders,
} from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })
test.setTimeout(120000)

let targetFarmId
let seasonalContext
let perennialContext

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function planCoversToday(plan, today) {
  const start = String(plan?.start_date || '')
  const end = String(plan?.end_date || '')
  if (!start || !end) return false
  return start <= today && today <= end
}

function normalizePlanLocations(plan) {
  const raw = Array.isArray(plan?.locations) ? plan.locations : []
  return raw
    .map((entry) => {
      if (typeof entry === 'object' && entry !== null) return entry.id || entry.pk || null
      return entry
    })
    .filter(Boolean)
    .map((value) => Number(value))
}

function pickTask(tasks, predicate) {
  return tasks.find(predicate) || null
}

async function chooseFirstSelectableOption(selectLocator, fieldName) {
  await expect(selectLocator, `HALT: missing select for ${fieldName}`).toBeVisible()
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const options = selectLocator.locator('option')
    const count = await options.count()
    for (let i = 0; i < count; i += 1) {
      const value = await options.nth(i).getAttribute('value')
      if (value) {
        await selectLocator.selectOption(value)
        return value
      }
    }
    await selectLocator.page().waitForTimeout(250)
  }
  throw new Error(`HALT: no selectable option for ${fieldName}`)
}

async function tryChooseFirstSelectableOption(selectLocator, fieldName) {
  if (!(await selectLocator.isVisible().catch(() => false))) {
    return null
  }
  for (let attempt = 0; attempt < 10; attempt += 1) {
    const options = selectLocator.locator('option')
    const count = await options.count()
    for (let i = 0; i < count; i += 1) {
      const value = await options.nth(i).getAttribute('value')
      if (value) {
        await selectLocator.selectOption(value)
        return value
      }
    }
    await selectLocator.page().waitForTimeout(250)
  }
  return null
}

async function selectOptionWhenAvailable(selectLocator, optionValue, fieldName) {
  await expect(selectLocator, `HALT: missing select for ${fieldName}`).toBeVisible()
  const target = String(optionValue)
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const match = selectLocator.locator(`option[value="${target}"]`)
    if ((await match.count()) > 0) {
      await selectLocator.selectOption(target)
      return target
    }
    await selectLocator.page().waitForTimeout(250)
  }
  return chooseFirstSelectableOption(selectLocator, fieldName)
}

async function ensureDailyLogLoaded(page) {
  const pageTitle = page.getByTestId('daily-log-page-title')
  const pageHeading = page.getByRole('heading', { name: 'سجل النشاط اليومي' })

  for (let attempt = 0; attempt < 3; attempt += 1) {
    if (
      (await pageTitle.isVisible().catch(() => false)) ||
      (await pageHeading.isVisible().catch(() => false))
    ) {
      return
    }

    if (/\/login(\/|$)/.test(page.url())) {
      return
    }

    const retryButton = page.getByRole('button', { name: /المحاولة مرة أخرى/ })
    if (await retryButton.isVisible().catch(() => false)) {
      await retryButton.click()
      await page.waitForTimeout(1000)
      continue
    }

    await page.reload()
    await page.waitForTimeout(1000)
  }

  const resolvedTitle = (await pageTitle.isVisible().catch(() => false)) ? pageTitle : pageHeading
  await expect(resolvedTitle).toBeVisible({ timeout: 20000 })
}

async function gotoDailyLog(page) {
  await page.goto(`${BASE_URL}/daily-log`)
  await page.waitForURL(/\/daily-log(\/|$)|\/dashboard(\/|$)/, { timeout: 30000 })
  if (/\/login(\/|$)/.test(page.url())) {
    return
  }
  if (!/\/daily-log(\/|$)/.test(page.url())) {
    await page.goto(`${BASE_URL}/daily-log`)
  }
  await ensureDailyLogLoaded(page)
}

async function applyContext(page, context, label) {
  await page.getByTestId('date-input').fill(context.date)
  await page.getByTestId('farm-select').selectOption(String(targetFarmId))
  await selectOptionWhenAvailable(page.getByTestId('crop-select'), context.cropId, `${label} crop`)
  await selectOptionWhenAvailable(
    page.getByTestId('location-select'),
    context.locationId,
    `${label} location`,
  )
  await selectOptionWhenAvailable(page.getByTestId('task-select'), context.taskId, `${label} task`)
}

async function waitForSmartCardContext(page, context, label) {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const card = page.getByTestId('daily-log-smart-card')
      await expect(card, `HALT: smart card missing for ${label}`).toBeVisible({ timeout: 20000 })
      await expect(page.getByTestId('daily-log-smart-card-title')).toContainText(context.cropName, {
        timeout: 20000,
      })
      await expect(page.getByTestId('daily-log-smart-card-title')).toContainText(context.taskName, {
        timeout: 20000,
      })
      await expect(page.getByTestId('daily-log-smart-card-plan')).toBeVisible()
      await expect(page.getByTestId('daily-log-smart-card-task')).toBeVisible()
      await expect(page.getByTestId('daily-log-smart-card-audit')).toBeVisible()
      await expect(page.getByTestId('daily-log-smart-card-plan-body')).toContainText(
        context.planName,
      )
      await expect(page.getByTestId('daily-log-smart-card-schedule-status')).not.toContainText(
        'غير معروف',
      )
      return
    } catch (error) {
      if (attempt === 1) throw error
      await applyContext(page, context, `${label} retry`)
      await page.waitForTimeout(1000)
    }
  }
}

async function fillResourcesStep(page) {
  await page.getByTestId('wizard-next-button').click()
  await expect(page.getByTestId('wizard-step-resources')).toBeVisible()
  const laborModeSelect = page.getByTestId('labor-entry-mode-select')
  if (await laborModeSelect.isVisible().catch(() => false)) {
    await laborModeSelect.selectOption('CASUAL_BATCH')
    await page.getByTestId('casual-workers-count-input').fill('3')
    await page.getByTestId('labor-surra-input').fill('1.00')
  }
}

async function fillDetailsStep(page, label) {
  await page.getByTestId('wizard-next-button').click()
  await expect(page.getByTestId('daily-log-save')).toBeVisible()

  const addRowButton = page.getByTestId('service-row-add')
  if (await addRowButton.isVisible().catch(() => false)) {
    await addRowButton.click()
    const varietySelect = page.locator('[data-testid^="service-row-variety-"]').first()
    const countInput = page.locator('[data-testid^="service-row-count-"]').first()
    const varietyValue = await tryChooseFirstSelectableOption(varietySelect, `${label} variety`)
    if (varietyValue) {
      await countInput.fill('5')
    }
  }

  const machineAssetSelect = page.getByTestId('machine-asset-select')
  if (await machineAssetSelect.isVisible().catch(() => false)) {
    await tryChooseFirstSelectableOption(machineAssetSelect, `${label} machine asset`)
  }

  const machineHours = page.getByTestId('machine-hours-input')
  if (await machineHours.isVisible().catch(() => false)) {
    await machineHours.fill('1')
  }

  const wellSelect = page.getByTestId('well-asset-select')
  if (await wellSelect.isVisible().catch(() => false)) {
    const selectedWell = await tryChooseFirstSelectableOption(wellSelect, `${label} well`)
    const wellReading = page.getByTestId('well-reading-input')
    if (selectedWell && (await wellReading.isVisible().catch(() => false))) {
      await wellReading.fill('120')
    }
  }
}

async function saveDailyLogAndAssert(page, label) {
  const createLogResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/daily-logs/') && response.request().method() === 'POST',
  )
  const createActivityResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/activities/') && response.request().method() === 'POST',
  )

  await page.getByTestId('daily-log-save').click()

  const logResponse = await createLogResponse
  expect(
    logResponse.ok(),
    `HALT: ${label} daily-log create failed: ${await logResponse.text()}`,
  ).toBeTruthy()

  const activityResponse = await createActivityResponse
  expect(
    activityResponse.ok(),
    `HALT: ${label} activity create failed: ${await activityResponse.text()}`,
  ).toBeTruthy()

  await expect(page).toHaveURL(/\/daily-log-history/, { timeout: 30000 })
}

test.beforeAll(async ({ request }, testInfo) => {
  testInfo.setTimeout(120000)
  const token = await fetchToken(request)
  const headers = withAuthHeaders(token)
  const today = todayIso()

  const candidateFarmIds = []
  const resolvedFarmId = await resolveAccessibleFarmId(request).catch(() => '')
  if (resolvedFarmId) {
    candidateFarmIds.push(Number(resolvedFarmId))
  }

  const farmsResponse = await request.get(`${endpoints.V1_BASE}/farms/`, { headers })
  if (farmsResponse.ok()) {
    const farms = readResults(await farmsResponse.json())
    for (const farm of farms) {
      const farmId = Number(farm?.id || 0)
      if (farmId) {
        candidateFarmIds.push(farmId)
      }
    }
  }

  const uniqueFarmIds = [...new Set(candidateFarmIds.filter(Boolean))]
  expect(
    uniqueFarmIds.length,
    'HALT: cannot resolve any accessible farm for smart-card gate',
  ).toBeGreaterThan(0)

  for (const farmId of uniqueFarmIds) {
    if (!farmId) continue

    const [cropsResponse, plansResponse] = await Promise.all([
      request.get(`${endpoints.V1_BASE}/crops/?farm_id=${farmId}`, { headers }),
      request.get(`${endpoints.V1_BASE}/crop-plans/?farm=${farmId}`, { headers }),
    ])
    if (!cropsResponse.ok() || !plansResponse.ok()) continue

    const crops = readResults(await cropsResponse.json())
    const plans = readResults(await plansResponse.json()).filter((plan) => {
      const status = String(plan?.status || '').toUpperCase()
      return status === 'ACTIVE' && planCoversToday(plan, today)
    })

    const perennialCrop = crops.find((crop) => Boolean(crop?.is_perennial))
    const seasonalCrop = crops.find((crop) => !crop?.is_perennial)
    if (!perennialCrop || !seasonalCrop) continue

    const perennialPlan = plans.find(
      (plan) => Number(plan?.crop?.id || plan?.crop || 0) === Number(perennialCrop.id),
    )
    const seasonalPlan = plans.find(
      (plan) => Number(plan?.crop?.id || plan?.crop || 0) === Number(seasonalCrop.id),
    )
    if (!perennialPlan || !seasonalPlan) continue

    const perennialLocationId = normalizePlanLocations(perennialPlan)[0]
    const seasonalLocationId = normalizePlanLocations(seasonalPlan)[0]
    if (!perennialLocationId || !seasonalLocationId) continue

    const [perennialTasksResponse, seasonalTasksResponse] = await Promise.all([
      request.get(`${endpoints.V1_BASE}/tasks/?farm_id=${farmId}&crop=${perennialCrop.id}`, {
        headers,
      }),
      request.get(`${endpoints.V1_BASE}/tasks/?farm_id=${farmId}&crop=${seasonalCrop.id}`, {
        headers,
      }),
    ])
    if (!perennialTasksResponse.ok() || !seasonalTasksResponse.ok()) continue

    const perennialTasks = readResults(await perennialTasksResponse.json())
    const seasonalTasks = readResults(await seasonalTasksResponse.json())

    const perennialTask =
      pickTask(
        perennialTasks,
        (task) =>
          !task?.is_harvest_task &&
          !task?.requires_tree_count &&
          !task?.requires_well &&
          !task?.requires_machinery,
      ) ||
      pickTask(perennialTasks, (task) => task?.is_perennial_procedure || task?.requires_tree_count) ||
      pickTask(perennialTasks, () => true)
    const seasonalTask = pickTask(seasonalTasks, (task) => !task?.is_perennial_procedure)
    if (!perennialTask || !seasonalTask) continue

    targetFarmId = farmId
    perennialContext = {
      cropId: Number(perennialCrop.id),
      cropName: String(perennialCrop.name),
      taskId: Number(perennialTask.id),
      taskName: String(perennialTask.name),
      locationId: Number(perennialLocationId),
      planName: String(perennialPlan.name),
      date: today,
    }
    seasonalContext = {
      cropId: Number(seasonalCrop.id),
      cropName: String(seasonalCrop.name),
      taskId: Number(seasonalTask.id),
      taskName: String(seasonalTask.name),
      locationId: Number(seasonalLocationId),
      planName: String(seasonalPlan.name),
      date: today,
    }
    break
  }

  expect(
    targetFarmId,
    'HALT: no single farm has seasonal+perennial crops with active plans today',
  ).toBeTruthy()
  expect(seasonalContext, 'HALT: missing seasonal smart-card context').toBeTruthy()
  expect(perennialContext, 'HALT: missing perennial smart-card context').toBeTruthy()
})

test('smart card updates when daily-log context switches from seasonal to perennial', async ({
  page,
  request,
}) => {
  await ensureLoggedIn(page, request)
  await gotoDailyLog(page)
  if (/\/login(\/|$)/.test(page.url())) {
    await ensureLoggedIn(page, request)
    await gotoDailyLog(page)
  }

  await applyContext(page, seasonalContext, 'seasonal')
  await waitForSmartCardContext(page, seasonalContext, 'seasonal')
  const seasonalTitle = await page.getByTestId('daily-log-smart-card-title').textContent()

  await applyContext(page, perennialContext, 'perennial')
  await waitForSmartCardContext(page, perennialContext, 'perennial')
  const perennialTitle = await page.getByTestId('daily-log-smart-card-title').textContent()

  expect(perennialTitle).not.toEqual(seasonalTitle)
  await expect(page.getByTestId('daily-log-smart-card-plan-body')).toContainText(
    perennialContext.planName,
  )
})

test('smart card stays valid through saving a seasonal daily log', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await gotoDailyLog(page)
  if (/\/login(\/|$)/.test(page.url())) {
    await ensureLoggedIn(page, request)
    await gotoDailyLog(page)
  }

  await applyContext(page, seasonalContext, 'seasonal')
  await waitForSmartCardContext(page, seasonalContext, 'seasonal')
  await expect(page.getByTestId('daily-log-smart-card-control-summary')).toBeVisible()
  await expect(page.getByTestId('daily-log-smart-card-ledger-summary')).toBeVisible()

  await fillResourcesStep(page)
  await fillDetailsStep(page, 'seasonal')
  await saveDailyLogAndAssert(page, 'seasonal smart-card gate')
})

test('smart card stays valid through saving a perennial daily log', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await gotoDailyLog(page)
  if (/\/login(\/|$)/.test(page.url())) {
    await ensureLoggedIn(page, request)
    await gotoDailyLog(page)
  }

  await applyContext(page, perennialContext, 'perennial')
  await waitForSmartCardContext(page, perennialContext, 'perennial')
  await expect(page.getByTestId('daily-log-smart-card-task-variances')).toBeVisible()
  await expect(page.getByTestId('daily-log-smart-card-variance-summary')).toBeVisible()

  await fillResourcesStep(page)
  await fillDetailsStep(page, 'perennial')
  await saveDailyLogAndAssert(page, 'perennial smart-card gate')
})
