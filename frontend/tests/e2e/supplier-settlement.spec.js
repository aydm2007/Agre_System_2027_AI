import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  resolveAccessibleFarmId,
  ensureFarmSelected,
  ensureLoggedIn,
  fetchToken,
  endpoints,
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

  await ensureFarmSelected(page)
}

async function gotoSupplierSettlements(page) {
  await page.goto(`${BASE_URL}/finance/supplier-settlements`)
  await page.waitForURL(/\/finance\/supplier-settlements(\/|$)|\/dashboard(\/|$)/, {
    timeout: 30000,
  })
  await ensureTargetFarmSelected(page)

  const banner = page.getByTestId('supplier-settlement-policy-banner')
  if (!(await banner.isVisible().catch(() => false))) {
    await page.goto(`${BASE_URL}/dashboard`)
    await ensureTargetFarmSelected(page)
    await page.goto(`${BASE_URL}/finance/supplier-settlements`)
    await page.waitForURL(/\/finance\/supplier-settlements(\/|$)|\/dashboard(\/|$)/, {
      timeout: 30000,
    })
    await ensureTargetFarmSelected(page)
  }
}

async function patchFarmSettings(request, token, nextValues) {
  const listResponse = await request.get(`${endpoints.V1_BASE}/farm-settings/?farm=${farmId}`, {
    headers: withAuthHeaders(token),
  })
  if (!listResponse.ok()) {
    throw new Error(
      `HALT: cannot load farm settings for supplier-settlement gate (${listResponse.status()})`,
    )
  }
  const payload = await listResponse.json()
  const settings = payload?.results?.[0]
  if (!settings?.id) {
    throw new Error('HALT: no FarmSettings row available for supplier-settlement gate')
  }
  const patchResponse = await request.patch(`${endpoints.V1_BASE}/farm-settings/${settings.id}/`, {
    headers: withAuthHeaders(token),
    data: nextValues,
  })
  if (!patchResponse.ok()) {
    throw new Error(
      `HALT: cannot patch farm settings for supplier-settlement gate (${patchResponse.status()})`,
    )
  }
}

test.beforeAll(async ({ request }) => {
  farmId = await resolveAccessibleFarmId(request)
  const token = await fetchToken(request)
  const farmsResponse = await request.get(`${endpoints.V1_BASE}/farms/`, {
    headers: withAuthHeaders(token),
  })
  const farmsPayload = farmsResponse.ok() ? await farmsResponse.json() : {}
  const farms = Array.isArray(farmsPayload?.results) ? farmsPayload.results : []
  farmName = farms.find((row) => String(row?.id) === String(farmId))?.name || ''
})

test('supplier settlement shows simple control posture then strict reconciliation trace', async ({
  page,
  request,
}) => {
  const token = await fetchToken(request)
  await patchFarmSettings(request, token, {
    mode: 'SIMPLE',
    cost_visibility: 'ratios_only',
    treasury_visibility: 'hidden',
  })

  await ensureLoggedIn(page, request)
  await gotoSupplierSettlements(page)
  await expect(page.getByTestId('supplier-settlement-policy-banner')).toContainText('المبسط')
  await expect(page.getByTestId('supplier-settlement-table')).toBeVisible()

  await patchFarmSettings(request, token, {
    mode: 'STRICT',
    cost_visibility: 'full_amounts',
    treasury_visibility: 'visible',
  })

  await gotoSupplierSettlements(page)
  await expect(page.getByTestId('supplier-settlement-policy-banner')).toContainText('STRICT')
  await expect(page.getByTestId('supplier-settlement-table')).toBeVisible()
  await expect(page.getByTestId('supplier-settlement-amount-column')).toBeVisible()
})
