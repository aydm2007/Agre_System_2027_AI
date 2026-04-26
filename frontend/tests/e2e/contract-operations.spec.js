import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureLoggedIn,
  fetchToken,
  endpoints,
  resolveAccessibleFarmId,
  withAuthHeaders,
} from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })
test.setTimeout(90000)

let farmId
let farmName

async function ensureTargetFarmSelected(page) {
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

async function patchFarmSettings(request, token, nextValues) {
  const listResponse = await request.get(`${endpoints.V1_BASE}/farm-settings/?farm=${farmId}`, {
    headers: withAuthHeaders(token),
  })
  if (!listResponse.ok()) {
    throw new Error(
      `HALT: cannot load farm settings for contract-operations gate (${listResponse.status()})`,
    )
  }
  const payload = await listResponse.json()
  const settings = payload?.results?.[0]
  if (!settings?.id) {
    throw new Error('HALT: no FarmSettings row available for contract-operations gate')
  }
  const patchResponse = await request.patch(`${endpoints.V1_BASE}/farm-settings/${settings.id}/`, {
    headers: withAuthHeaders(token),
    data: nextValues,
  })
  if (!patchResponse.ok()) {
    throw new Error(
      `HALT: cannot patch farm settings for contract-operations gate (${patchResponse.status()})`,
    )
  }
}

test.beforeAll(async ({ request }) => {
  const token = await fetchToken(request)
  farmId = Number(await resolveAccessibleFarmId(request))
  const farmsResponse = await request.get(`${endpoints.V1_BASE}/farms/`, {
    headers: withAuthHeaders(token),
  })
  const farmsPayload = farmsResponse.ok() ? await farmsResponse.json() : {}
  const farms = Array.isArray(farmsPayload?.results) ? farmsPayload.results : []
  farmName = farms.find((row) => Number(row?.id) === Number(farmId))?.name || ''
})

test('contract operations shows simple risk posture then strict settlement trace', async ({
  page,
  request,
}) => {
  const token = await fetchToken(request)
  await patchFarmSettings(request, token, {
    mode: 'SIMPLE',
    cost_visibility: 'ratios_only',
    contract_mode: 'operational_only',
    treasury_visibility: 'hidden',
  })

  await ensureLoggedIn(page, request)
  await page.goto(`${BASE_URL}/sharecropping`)
  await ensureTargetFarmSelected(page)
  await expect(page.getByTestId('contract-operations-policy-banner')).toContainText('المبسط')
  await expect(page.getByTestId('contract-operations-table')).toBeVisible()

  await patchFarmSettings(request, token, {
    mode: 'STRICT',
    cost_visibility: 'full_amounts',
    contract_mode: 'full_erp',
    treasury_visibility: 'visible',
  })

  await page.goto(`${BASE_URL}/sharecropping`)
  await ensureTargetFarmSelected(page)
  await expect(page.getByTestId('contract-operations-policy-banner')).toContainText('الصارم')
  await expect(page.getByTestId('contract-operations-table')).toBeVisible()
})
