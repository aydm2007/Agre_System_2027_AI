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

async function patchFarmSettings(request, token, nextValues) {
  const listResponse = await request.get(`${endpoints.V1_BASE}/farm-settings/?farm=${farmId}`, {
    headers: withAuthHeaders(token),
  })
  if (!listResponse.ok()) {
    throw new Error(
      `HALT: cannot load farm settings for petty-cash gate (${listResponse.status()})`,
    )
  }
  const payload = await listResponse.json()
  const settings = payload?.results?.[0]
  if (!settings?.id) throw new Error('HALT: no FarmSettings row available for petty-cash gate')
  const patchResponse = await request.patch(`${endpoints.V1_BASE}/farm-settings/${settings.id}/`, {
    headers: withAuthHeaders(token),
    data: nextValues,
  })
  if (!patchResponse.ok()) {
    throw new Error(
      `HALT: cannot patch farm settings for petty-cash gate (${patchResponse.status()})`,
    )
  }
}

test.beforeAll(async ({ request }) => {
  farmId = await resolveAccessibleFarmId(request)
})

async function expectRequestSurface(page) {
  const requestsTable = page.getByTestId('petty-cash-requests-table')
  const emptyState = page.getByText('No petty cash requests have been created for this farm yet.')
  await expect(requestsTable.or(emptyState)).toBeVisible()
}

async function expectSettlementSurface(page) {
  await page.getByRole('button', { name: 'Settlements' }).click()
  const settlementsTable = page.getByTestId('petty-cash-settlements-table')
  const emptyState = page.getByText('No settlements exist for this farm yet.')
  await expect(settlementsTable.or(emptyState)).toBeVisible()
}

test('petty cash shows simple operational posture then strict workflow surface', async ({
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
  await page.goto(`${BASE_URL}/finance/petty-cash`)
  await ensureFarmSelected(page)
  await expect(page.getByTestId('petty-cash-visibility-banner')).toContainText('operations_only')
  await expect(page.getByTestId('petty-cash-visibility-banner')).toContainText('ratios_only')
  await expect(page.getByRole('button', { name: 'New request' })).toBeVisible()
  await expectRequestSurface(page)

  await patchFarmSettings(request, token, {
    mode: 'STRICT',
    cost_visibility: 'full_amounts',
    treasury_visibility: 'visible',
  })

  await page.goto(`${BASE_URL}/finance/petty-cash`)
  await ensureFarmSelected(page)
  await expect(page.getByTestId('petty-cash-visibility-banner')).toContainText('full_erp')
  await expect(page.getByTestId('petty-cash-visibility-banner')).toContainText('full_amounts')
  await expect(page.getByRole('button', { name: 'New request' })).toBeVisible()
  await expectSettlementSurface(page)
})
