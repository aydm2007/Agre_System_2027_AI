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

async function patchFarmSettings(request, token, nextValues) {
  const listResponse = await request.get(`${endpoints.V1_BASE}/farm-settings/?farm=${farmId}`, {
    headers: withAuthHeaders(token),
  })
  if (!listResponse.ok()) {
    throw new Error(`HALT: cannot load farm settings for fuel gate (${listResponse.status()})`)
  }
  const payload = await listResponse.json()
  const settings = payload?.results?.[0]
  if (!settings?.id) throw new Error('HALT: no FarmSettings row available for fuel gate')
  const patchResponse = await request.patch(`${endpoints.V1_BASE}/farm-settings/${settings.id}/`, {
    headers: withAuthHeaders(token),
    data: nextValues,
  })
  if (!patchResponse.ok()) {
    throw new Error(`HALT: cannot patch farm settings for fuel gate (${patchResponse.status()})`)
  }
}

test.beforeAll(async ({ request }) => {
  farmId = await resolveAccessibleFarmId(request)
})

test('fuel reconciliation shows simple risk posture then strict trace', async ({
  page,
  request,
}) => {
  const token = await fetchToken(request)
  await patchFarmSettings(request, token, {
    mode: 'SIMPLE',
    cost_visibility: 'ratios_only',
    variance_behavior: 'warn',
    treasury_visibility: 'hidden',
  })

  await ensureLoggedIn(page, request)
  await page.goto(`${BASE_URL}/fuel-reconciliation`)
  await expect(page.getByTestId('fuel-reconciliation-policy-banner')).toContainText('الوضع المبسط')

  await patchFarmSettings(request, token, {
    mode: 'STRICT',
    cost_visibility: 'full_amounts',
    variance_behavior: 'block',
    treasury_visibility: 'visible',
  })

  await page.goto(`${BASE_URL}/fuel-reconciliation`)
  await expect(page.getByTestId('fuel-reconciliation-policy-banner')).toContainText('STRICT')
  await expect(page.getByTestId('fuel-reconciliation-table')).toBeVisible()
  await expect(page.getByTestId('fuel-reconciliation-amount-column')).toBeVisible()
})
