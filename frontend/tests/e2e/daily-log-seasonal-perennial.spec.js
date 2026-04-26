import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureLoggedIn,
  endpoints,
  fetchSystemMode,
  fetchToken,
  readResults,
  withAuthHeaders,
} from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })
test.setTimeout(180000)

let seedFarmId
let seasonalCropId
let seasonalTaskId
let seededPlans = []
let seasonalPlanDate
let cropVarietyIdsByCrop = {}
let perennialExecutions = []

const PERENNIAL_NAMES = ['مانجو', 'موز']
const SEASONAL_NAMES = ['قمح', 'ذرة صفراء', 'ذرة بيضاء']

function hasAnyName(target, names) {
  const normalized = String(target || '').toLowerCase()
  return names.some((name) => normalized.includes(String(name).toLowerCase()))
}

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function addDaysIso(offset) {
  const value = new Date()
  value.setUTCDate(value.getUTCDate() + offset)
  return value.toISOString().slice(0, 10)
}

function normalizePlanCropId(plan) {
  return Number(plan?.crop?.id || plan?.crop || 0)
}

function normalizePlanLocationIds(plan) {
  const fromArray = Array.isArray(plan?.locations) ? plan.locations : []
  const ids = fromArray
    .map((entry) => {
      if (typeof entry === 'object' && entry !== null) return entry.id || entry.pk || null
      return entry
    })
    .filter(Boolean)
    .map((value) => Number(value))

  const direct = Number(plan?.location?.id || plan?.location || 0)
  if (direct) ids.push(direct)
  return [...new Set(ids)]
}

function resolveUsablePlanDate(plan) {
  if (!plan) return null
  const today = todayIso()
  const start = String(plan?.start_date || '')
  const end = String(plan?.end_date || '')

  if (!start && !end) return today
  if (start && start > today) return null
  if ((!start || start <= today) && (!end || today <= end)) {
    return today
  }
  return null
}

async function loadActivePlans(request, headers, farmId) {
  const plansRes = await request.get(`${endpoints.V1_BASE}/crop-plans/?farm_id=${farmId}`, {
    headers,
  })
  if (!plansRes.ok()) return []
  return readResults(await plansRes.json()).filter((plan) => String(plan?.status || '').toUpperCase() === 'ACTIVE')
}

async function loadFarmLocations(request, headers, farmId) {
  const locationsRes = await request.get(`${endpoints.V1_BASE}/locations/?farm_id=${farmId}`, {
    headers,
  })
  if (!locationsRes.ok()) return []
  return readResults(await locationsRes.json())
}

async function loadCropScopedVarietyIds(request, headers, farmId, cropId) {
  if (!farmId || !cropId) return []
  const response = await request.get(
    `${endpoints.V1_BASE}/crop-varieties/?farm_id=${farmId}&crop=${cropId}`,
    { headers },
  )
  if (!response.ok()) return []
  return readResults(await response.json())
    .filter((entry) => {
      const entryCropId = entry?.crop?.id || entry?.crop || entry?.crop_id || null
      return entryCropId != null && String(entryCropId) === String(cropId)
    })
    .map((entry) => entry?.id)
    .filter(Boolean)
}

async function ensureCropScopedVarietyIds(request, headers, farmId, crop) {
  const cropId = Number(crop?.id || 0)
  let ids = await loadCropScopedVarietyIds(request, headers, farmId, cropId)
  if (ids.length > 0) {
    return ids
  }

  const createResponse = await request.post(`${endpoints.V1_BASE}/crop-varieties/`, {
    headers: {
      ...headers,
      'X-Idempotency-Key': `e2e-crop-variety-${farmId}-${cropId}-${Date.now()}`,
    },
    data: {
      crop: cropId,
      name: `${crop?.name || 'محصول'} صنف إثباتي`,
      code: `E2E-${cropId}-${Date.now()}`,
      description: 'Seeded by documentary E2E to guarantee crop-scoped perennial execution.',
    },
  })
  expect(
    createResponse.ok(),
    `HALT: failed to create crop-scoped variety for ${crop?.name || cropId}: ${await createResponse.text()}`,
  ).toBeTruthy()

  ids = await loadCropScopedVarietyIds(request, headers, farmId, cropId)
  return ids
}

async function ensureUsableActivePlanForCrop(request, headers, farmId, crop, existingPlans) {
  const cropId = Number(crop?.id || 0)
  expect(cropId, `HALT: missing crop id while preparing plan for ${crop?.name || 'unknown crop'}`).toBeTruthy()

  const usableExisting = existingPlans.find(
    (plan) => normalizePlanCropId(plan) === cropId && resolveUsablePlanDate(plan),
  )
  if (usableExisting) {
    return { plan: usableExisting, plans: existingPlans }
  }

  const cropPlansRes = await request.get(
    `${endpoints.V1_BASE}/crop-plans/?farm_id=${farmId}&crop=${cropId}`,
    { headers },
  )
  expect(cropPlansRes.ok(), `HALT: cannot inspect crop plans for ${crop?.name}`).toBeTruthy()
  const cropPlans = readResults(await cropPlansRes.json())

  const locations = await loadFarmLocations(request, headers, farmId)
  expect(locations.length, `HALT: no locations available for farm ${farmId}`).toBeGreaterThan(0)
  const defaultLocationIds = [...new Set(locations.map((location) => Number(location?.id || 0)).filter(Boolean))]
  expect(defaultLocationIds.length, `HALT: no usable location ids for farm ${farmId}`).toBeGreaterThan(0)

  const startDate = todayIso()
  const endDate = addDaysIso(30)
  const keyPrefix = `e2e-plan-${farmId}-${cropId}-${Date.now()}`
  const candidatePlan = cropPlans[0] || null

  if (candidatePlan?.id) {
    const patchRes = await request.patch(`${endpoints.V1_BASE}/crop-plans/${candidatePlan.id}/`, {
      headers: {
        ...headers,
        'X-Idempotency-Key': `${keyPrefix}-patch`,
      },
      data: {
        farm: farmId,
        crop: cropId,
        name: candidatePlan?.name || `خطة ${crop?.name || cropId} E2E`,
        start_date: startDate,
        end_date: endDate,
        area: String(candidatePlan?.area || '1.00'),
        season: String(new Date().getUTCFullYear()),
        location_ids: normalizePlanLocationIds(candidatePlan).length
          ? normalizePlanLocationIds(candidatePlan)
          : defaultLocationIds,
      },
    })
    expect(
      patchRes.ok(),
      `HALT: failed to refresh crop plan ${candidatePlan.id} for ${crop?.name}: ${await patchRes.text()}`,
    ).toBeTruthy()

    const approveRes = await request.post(`${endpoints.V1_BASE}/crop-plans/${candidatePlan.id}/approve/`, {
      headers: {
        ...headers,
        'X-Idempotency-Key': `${keyPrefix}-approve`,
      },
    })
    expect(
      approveRes.ok(),
      `HALT: failed to activate crop plan ${candidatePlan.id} for ${crop?.name}: ${await approveRes.text()}`,
    ).toBeTruthy()
  } else {
    const createRes = await request.post(`${endpoints.V1_BASE}/crop-plans/`, {
      headers: {
        ...headers,
        'X-Idempotency-Key': `${keyPrefix}-create`,
      },
      data: {
        farm: farmId,
        crop: cropId,
        name: `خطة ${crop?.name || cropId} E2E`,
        start_date: startDate,
        end_date: endDate,
        area: '1.00',
        season: String(new Date().getUTCFullYear()),
        location_ids: defaultLocationIds,
      },
    })
    expect(
      createRes.ok(),
      `HALT: failed to create crop plan for ${crop?.name}: ${await createRes.text()}`,
    ).toBeTruthy()
  }

  const refreshedPlans = await loadActivePlans(request, headers, farmId)
  const refreshedPlan = refreshedPlans.find(
    (plan) => normalizePlanCropId(plan) === cropId && resolveUsablePlanDate(plan),
  )
  expect(refreshedPlan, `HALT: no usable active crop plan available after remediation for ${crop?.name}`).toBeTruthy()
  return { plan: refreshedPlan, plans: refreshedPlans }
}

async function findEligibleFarm(request, headers, farms) {
  let fallbackFarm = null
  let dualCropFallback = null
  let dualPerennialFallback = null
  let exactDualCrop = null
  let exactDualPerennial = null
  for (const farm of farms) {
    const farmId = Number(farm?.id || 0)
    if (!farmId) continue
    const cropsRes = await request.get(`${endpoints.V1_BASE}/crops/?farm_id=${farmId}`, {
      headers,
    })
    if (!cropsRes.ok()) continue
    const crops = readResults(await cropsRes.json())
    const plans = await loadActivePlans(request, headers, farmId)
    if (!fallbackFarm && crops.length > 0) fallbackFarm = { farmId, crops, plans }

    const perennialCandidates = crops.filter((crop) => hasAnyName(crop.name, PERENNIAL_NAMES))
    const perennialCrop = perennialCandidates[0]
    const seasonalCrop = crops.find((crop) => hasAnyName(crop.name, SEASONAL_NAMES))
    if (!dualCropFallback && perennialCrop && seasonalCrop) {
      dualCropFallback = { farmId, crops, plans, perennialCrop, perennialCandidates, seasonalCrop }
    }
    if (!dualPerennialFallback && perennialCandidates.length >= 2 && seasonalCrop) {
      dualPerennialFallback = {
        farmId,
        crops,
        plans,
        perennialCrop,
        perennialCandidates,
        seasonalCrop,
      }
    }
    if (
      perennialCandidates.length >= 2 &&
      seasonalCrop &&
      (farm?.slug === 'sardood-farm' || hasAnyName(farm?.name, ['سردود', 'sardood']))
    ) {
      return {
        farmId,
        crops,
        plans,
        perennialCrop,
        perennialCandidates,
        seasonalCrop,
      }
    }
    const perennialPlan = plans.find((plan) =>
      perennialCandidates.some(
        (candidate) =>
          normalizePlanCropId(plan) === Number(candidate?.id || 0) && resolveUsablePlanDate(plan),
      ),
    )
    const seasonalPlan = plans.find(
      (plan) => normalizePlanCropId(plan) === Number(seasonalCrop?.id || 0) && resolveUsablePlanDate(plan),
    )

    if (!exactDualPerennial && perennialCandidates.length >= 2 && seasonalCrop && perennialPlan && seasonalPlan) {
      exactDualPerennial = {
        farmId,
        crops,
        plans,
        perennialCrop,
        perennialCandidates,
        seasonalCrop,
        perennialPlan,
        seasonalPlan,
      }
    }
    if (!exactDualCrop && perennialCrop && seasonalCrop && perennialPlan && seasonalPlan) {
      exactDualCrop = {
        farmId,
        crops,
        plans,
        perennialCrop,
        perennialCandidates,
        seasonalCrop,
        perennialPlan,
        seasonalPlan,
      }
    }
  }
  return exactDualPerennial || exactDualCrop || dualPerennialFallback || dualCropFallback || fallbackFarm
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

  const available = await selectLocator.locator('option').allTextContents()
  throw new Error(
    `HALT: no selectable option for ${fieldName}. options=${JSON.stringify(available)}`,
  )
}

async function selectOptionWhenAvailable(selectLocator, optionValue, fieldName) {
  await expect(selectLocator, `HALT: missing select for ${fieldName}`).toBeVisible()
  const wanted = String(optionValue)
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const matching = selectLocator.locator(`option[value="${wanted}"]`)
    if ((await matching.count()) > 0) {
      await selectLocator.selectOption(wanted)
      return wanted
    }
    await selectLocator.page().waitForTimeout(250)
  }
  return chooseFirstSelectableOption(selectLocator, fieldName)
}

async function fillServiceRowForCropIfVisible(page, allowedVarietyIds = []) {
  const addRowButton = page.getByTestId('service-row-add')
  if (!(await addRowButton.isVisible().catch(() => false))) return null

  await addRowButton.click()

  const countInput = page.locator('[data-testid^="service-row-count-"]').first()
  const varietySelect = page.locator('[data-testid^="service-row-variety-"]').first()

  await expect(varietySelect, 'HALT: perennial service row missing variety select').toBeVisible()
  await expect(countInput, 'HALT: perennial service row missing count input').toBeVisible()

  const normalizedAllowedIds = new Set((allowedVarietyIds || []).map((value) => String(value)))
  if (normalizedAllowedIds.size > 0) {
    const options = varietySelect.locator('option')
    const count = await options.count()
    for (let i = 0; i < count; i += 1) {
      const value = await options.nth(i).getAttribute('value')
      if (value && normalizedAllowedIds.has(String(value))) {
        await varietySelect.selectOption(String(value))
        await countInput.fill('5')
        return true
      }
    }
  }

  await chooseFirstSelectableOption(varietySelect, 'perennial variety')
  await countInput.fill('5')
  return true
}

async function fillPositiveTreeDeltaIfVisible(page, value = '5') {
  const deltaInput = page
    .locator('label:has-text("تغير العدد")')
    .locator('..')
    .locator('input[type="number"]')
    .first()
  if (await deltaInput.isVisible().catch(() => false)) {
    await deltaInput.fill(value)
  }
}

async function saveDailyLogAndAssert(page, label) {
  const createLogResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/daily-logs/') && response.request().method() === 'POST',
  )
  const createActivityRequest = page.waitForRequest(
    (request) =>
      request.url().includes('/api/v1/activities/') && request.method() === 'POST',
  )
  const createActivityResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/activities/') && response.request().method() === 'POST',
  )

  await page.getByTestId('daily-log-save').click()

  const logResp = await createLogResponse
  expect(
    logResp.ok(),
    `HALT: ${label} daily-log create failed: ${await logResp.text()}`,
  ).toBeTruthy()

  const activityRequest = await createActivityRequest
  const actResp = await createActivityResponse
  expect(
    actResp.ok(),
    `HALT: ${label} activity create failed: ${await actResp.text()} | payload=${activityRequest.postData() || ''}`,
  ).toBeTruthy()

  await expect(page).toHaveURL(/\/daily-log-history/, { timeout: 30000 })
}

async function createDailyLogForCrop(page, cropId, dateValue, label, preferredTaskId = null) {
  await page.goto(`${BASE_URL}/daily-log`)
  await page.waitForURL(/\/daily-log(\/|$)|\/dashboard(\/|$)/, { timeout: 30000 })
  if (!/\/daily-log(\/|$)/.test(page.url())) {
    await page.goto(`${BASE_URL}/daily-log`)
  }
  await expect(page.getByTestId('daily-log-page-title')).toBeVisible({ timeout: 20000 })

  await page.getByTestId('date-input').fill(dateValue)
  await page.getByTestId('farm-select').selectOption(String(seedFarmId))
  await selectOptionWhenAvailable(page.getByTestId('crop-select'), cropId, `${label} crop`)
  const locationSelect = page.getByTestId('location-select')
  const candidatePlan = seededPlans
    .filter((plan) => Number(plan?.crop?.id || plan?.crop || 0) === Number(cropId))
    .find((plan) => {
      const start = String(plan?.start_date || '')
      const end = String(plan?.end_date || '')
      return !start || !end || (dateValue >= start && dateValue <= end)
    })
  const plannedLocationId = candidatePlan?.location?.id || candidatePlan?.location || null
  if (plannedLocationId) {
    const targetValue = String(plannedLocationId)
    const matchingOption = locationSelect.locator(`option[value="${targetValue}"]`)
    if ((await matchingOption.count()) > 0) {
      await locationSelect.selectOption(targetValue)
    } else {
      await chooseFirstSelectableOption(locationSelect, `${label} location`)
    }
  } else {
    await chooseFirstSelectableOption(locationSelect, `${label} location`)
  }
  const taskSelect = page.getByTestId('task-select')
  if (preferredTaskId) {
    const preferred = taskSelect.locator(`option[value="${String(preferredTaskId)}"]`)
    if ((await preferred.count()) > 0) {
      await taskSelect.selectOption(String(preferredTaskId))
    } else {
      await chooseFirstSelectableOption(taskSelect, `${label} task`)
    }
  } else {
    await chooseFirstSelectableOption(taskSelect, `${label} task`)
  }

  await page.getByTestId('wizard-next-button').click()
  await expect(page.getByTestId('wizard-step-resources')).toBeVisible()

  const laborModeSelect = page.getByTestId('labor-entry-mode-select')
  if (await laborModeSelect.isVisible().catch(() => false)) {
    await laborModeSelect.selectOption('CASUAL_BATCH')
    await page.getByTestId('casual-workers-count-input').fill('3')
    await page.getByTestId('labor-surra-input').fill('1.00')
  }

  await page.getByTestId('wizard-next-button').click()
  await expect(page.getByTestId('daily-log-save')).toBeVisible()

  await fillPositiveTreeDeltaIfVisible(page)
  await fillServiceRowForCropIfVisible(page, cropVarietyIdsByCrop[String(cropId)] || [])

  const machineAssetSelect = page.getByTestId('machine-asset-select')
  if (await machineAssetSelect.isVisible().catch(() => false)) {
    await chooseFirstSelectableOption(machineAssetSelect, `${label} machine asset`)
  }

  const machineHours = page.getByTestId('machine-hours-input')
  if (await machineHours.isVisible().catch(() => false)) {
    await machineHours.fill('1')
  }

  const wellSelect = page.getByTestId('well-asset-select')
  if (await wellSelect.isVisible().catch(() => false)) {
    await chooseFirstSelectableOption(wellSelect, `${label} well`)
  }

  const wellReading = page.getByTestId('well-reading-input')
  if (await wellReading.isVisible().catch(() => false)) {
    await wellReading.fill('120')
  }

  await saveDailyLogAndAssert(page, label)
}

test.beforeAll(async ({ request }) => {
  const modeBody = await fetchSystemMode(request)
  expect(Boolean(modeBody?.strict_erp_mode), 'HALT: this scenario requires Simple Mode').toBeFalsy()

  const token = await fetchToken(request)
  const headers = withAuthHeaders(token)
  const treeSeedRes = await request.post(`${endpoints.V1_BASE}/seed-tree-inventory/`, {
    headers: {
      ...headers,
      'X-Idempotency-Key': `e2e-tree-seed-${Date.now()}`,
    },
  })
  expect(treeSeedRes.ok(), `HALT: failed to seed tree inventory: ${await treeSeedRes.text()}`).toBeTruthy()

  const farmsRes = await request.get(`${endpoints.V1_BASE}/farms/`, { headers })
  expect(farmsRes.ok(), 'HALT: cannot load farms').toBeTruthy()
  const farms = readResults(await farmsRes.json())
  expect(farms.length, 'HALT: no farms seeded').toBeGreaterThan(0)

  const selectedFarm = await findEligibleFarm(request, headers, farms)
  expect(
    selectedFarm?.farmId,
    'HALT: no farm with usable crops found for documentary scenario',
  ).toBeTruthy()
  seedFarmId = selectedFarm.farmId
  const crops = selectedFarm.crops || []
  expect(crops.length, 'HALT: no crops available').toBeGreaterThan(0)

  const perennialCandidates =
    selectedFarm.perennialCandidates || crops.filter((crop) => hasAnyName(crop.name, PERENNIAL_NAMES))
  const orderedPerennialCandidates = [
    ...PERENNIAL_NAMES.flatMap((preferredName) =>
      perennialCandidates.filter((crop) => hasAnyName(crop.name, [preferredName])),
    ),
    ...perennialCandidates,
  ].filter(
    (crop, index, collection) =>
      collection.findIndex((entry) => Number(entry?.id || 0) === Number(crop?.id || 0)) === index,
  )

  perennialExecutions = []
  for (const candidate of orderedPerennialCandidates) {
    const scopedIds = await ensureCropScopedVarietyIds(request, headers, seedFarmId, candidate)
    if (scopedIds.length === 0) continue
    cropVarietyIdsByCrop[String(candidate.id)] = scopedIds
    perennialExecutions.push({
      crop: candidate,
      cropId: candidate.id,
      label: candidate.name || `perennial-${candidate.id}`,
    })
    if (perennialExecutions.length >= 2) break
  }

  if (perennialExecutions.length === 0) {
    const fallbackPerennial = selectedFarm.perennialCrop || orderedPerennialCandidates[0] || null
    expect(fallbackPerennial, 'HALT: no perennial crop found (expected mango/banana)').toBeTruthy()
    const scopedIds = await ensureCropScopedVarietyIds(request, headers, seedFarmId, fallbackPerennial)
    cropVarietyIdsByCrop[String(fallbackPerennial.id)] = scopedIds
    perennialExecutions.push({
      crop: fallbackPerennial,
      cropId: fallbackPerennial.id,
      label: fallbackPerennial.name || `perennial-${fallbackPerennial.id}`,
    })
  }

  const seasonalCrop = selectedFarm.seasonalCrop || crops.find((crop) => hasAnyName(crop.name, SEASONAL_NAMES))
  seasonalCropId = seasonalCrop?.id

  seededPlans = selectedFarm.plans || []

  expect(perennialExecutions.length, 'HALT: no perennial crop found (expected mango/banana)').toBeGreaterThan(0)
  expect(seasonalCropId, 'HALT: no seasonal crop found (expected wheat/maize)').toBeTruthy()

  for (const execution of perennialExecutions) {
    const perennialPlanSeed = await ensureUsableActivePlanForCrop(
      request,
      headers,
      seedFarmId,
      execution.crop,
      seededPlans,
    )
    seededPlans = perennialPlanSeed.plans
    execution.planDate = resolveUsablePlanDate(perennialPlanSeed.plan)
    expect(
      execution.planDate,
      `HALT: no usable active perennial crop plan date found for ${execution.label}`,
    ).toBeTruthy()
  }

  const seasonalPlanSeed = await ensureUsableActivePlanForCrop(
    request,
    headers,
    seedFarmId,
    seasonalCrop,
    seededPlans,
  )
  seededPlans = seasonalPlanSeed.plans

  seasonalPlanDate = resolveUsablePlanDate(seasonalPlanSeed.plan || selectedFarm.seasonalPlan)
  expect(seasonalPlanDate, 'HALT: no usable active seasonal crop plan date found').toBeTruthy()

  const seasonalTasksRes = await request.get(
    `${endpoints.V1_BASE}/tasks/?farm_id=${seedFarmId}&crop=${seasonalCropId}`,
    {
      headers,
    },
  )
  expect(seasonalTasksRes.ok(), 'HALT: cannot load seasonal tasks').toBeTruthy()

  const seasonalTasks = readResults(await seasonalTasksRes.json())

  seasonalTaskId =
    seasonalTasks.find((task) => !task?.is_perennial_procedure)?.id || seasonalTasks[0]?.id || null

  for (const execution of perennialExecutions) {
    const perennialTasksRes = await request.get(
      `${endpoints.V1_BASE}/tasks/?farm_id=${seedFarmId}&crop=${execution.cropId}`,
      {
        headers,
      },
    )
    expect(
      perennialTasksRes.ok(),
      `HALT: cannot load perennial tasks for ${execution.label}`,
    ).toBeTruthy()
    const perennialTasks = readResults(await perennialTasksRes.json())
    execution.taskId =
      perennialTasks.find((task) => task?.is_perennial_procedure)?.id || perennialTasks[0]?.id || null
    expect(execution.taskId, `HALT: no usable perennial task found for ${execution.label}`).toBeTruthy()
  }

  cropVarietyIdsByCrop = {
    ...cropVarietyIdsByCrop,
    [String(seasonalCropId)]: await loadCropScopedVarietyIds(request, headers, seedFarmId, seasonalCropId),
  }

  expect(seasonalTaskId, 'HALT: no usable seasonal task found').toBeTruthy()
  for (const execution of perennialExecutions) {
    expect(
      cropVarietyIdsByCrop[String(execution.cropId)]?.length,
      `HALT: no crop-scoped perennial varieties found for ${execution.label}`,
    ).toBeGreaterThan(0)
  }
})

test('documentary scenario: save perennial and seasonal daily logs with diagnostics', async ({
  page,
  request,
}) => {
  await ensureLoggedIn(page, request)

  for (const execution of perennialExecutions) {
    await createDailyLogForCrop(
      page,
      execution.cropId,
      execution.planDate,
      execution.label,
      execution.taskId,
    )
  }
  await createDailyLogForCrop(page, seasonalCropId, seasonalPlanDate, 'seasonal', seasonalTaskId)
})
