import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureFarmSelected,
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
    throw new Error(`HALT: cannot load farm settings for dual-mode gate (${listResponse.status()})`)
  }
  const payload = await listResponse.json()
  const settings = payload?.results?.[0]
  if (!settings?.id) throw new Error('HALT: no FarmSettings row available for dual-mode gate')
  const patchResponse = await request.patch(`${endpoints.V1_BASE}/farm-settings/${settings.id}/`, {
    headers: withAuthHeaders(token),
    data: nextValues,
  })
  if (!patchResponse.ok()) {
    throw new Error(
      `HALT: cannot patch farm settings for dual-mode gate (${patchResponse.status()})`,
    )
  }
  const patchedJson = await patchResponse.json()
  console.log('PATCH response data:', patchedJson)
}

test.beforeAll(async ({ request }) => {
  farmId = await resolveAccessibleFarmId(request)
})

test('mode switch changes surfaces without changing route-level truth', async ({
  page,
  request,
}) => {
  const token = await fetchToken(request)
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await patchFarmSettings(request, token, {
    mode: 'SIMPLE',
    cost_visibility: 'summarized_amounts',
    fixed_asset_mode: 'tracking_only',
    contract_mode: 'operational_only',
    treasury_visibility: 'hidden',
  })
  // Navigate and reload on the target page to force SettingsContext re-fetch
  await page.goto(`${BASE_URL}/fixed-assets`, { waitUntil: 'commit' })
  await page.reload({ waitUntil: 'commit' })
  await expect(page.getByTestId('fixed-assets-policy-banner')).toContainText('تتبع فقط', { timeout: 10000 })
  await page.goto(`${BASE_URL}/fuel-reconciliation`, { waitUntil: 'commit' })
  await page.reload({ waitUntil: 'commit' })
  await expect(page.getByTestId('fuel-reconciliation-policy-banner')).toContainText('الوضع المبسط', { timeout: 10000 })

  await patchFarmSettings(request, token, {
    mode: 'STRICT',
    cost_visibility: 'full_amounts',
    fixed_asset_mode: 'full_capitalization',
    contract_mode: 'full_erp',
    treasury_visibility: 'visible',
  })
  // Navigate and reload on the target page to force SettingsContext re-fetch
  await page.goto(`${BASE_URL}/fixed-assets`, { waitUntil: 'commit' })
  await page.reload({ waitUntil: 'commit' })
  await expect(page.getByTestId('fixed-assets-policy-banner')).toContainText('الرسملة الكاملة', { timeout: 10000 })
  await page.goto(`${BASE_URL}/fuel-reconciliation`, { waitUntil: 'commit' })
  await page.reload({ waitUntil: 'commit' })
  await expect(page.getByTestId('fuel-reconciliation-policy-banner')).toContainText('STRICT', { timeout: 10000 })
})
