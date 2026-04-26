import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureFarmSelected,
  ensureLoggedIn,
  fetchSystemMode,
  SARDOOD_FARM_REGEX,
} from './helpers/e2eAuth'

test.describe('SIMPLE Mode Isolation', () => {
  let strictErpMode = false

  test.beforeAll(async ({ request }) => {
    const modeBody = await fetchSystemMode(request)
    strictErpMode = Boolean(modeBody?.strict_erp_mode)
  })

  test('Strict-only finance authoring stays hidden while SIMPLE posture routes remain available', async ({
    page,
    request,
  }) => {
    if (strictErpMode) {
      test.skip('System is in STRICT mode, skipping SIMPLE isolation test.')
      return
    }

    await ensureLoggedIn(page, request)
    await ensureFarmSelected(page, SARDOOD_FARM_REGEX)

    // SIMPLE may still expose posture-first finance navigation, but strict authoring
    // routes must remain hidden and blocked.
    await expect(page.locator('a[href="/finance/ledger"]')).toHaveCount(0)

    await page.goto(`${BASE_URL}/finance/supplier-settlements`)
    await expect(page).toHaveURL(/\/finance\/supplier-settlements(?:\?|$)/)
    await expect(page.getByTestId('supplier-settlement-policy-banner')).toBeVisible()

    await page.goto(`${BASE_URL}/fuel-reconciliation`)
    await expect(page).toHaveURL(/\/fuel-reconciliation(?:\?|$)/)
    await expect(page.getByTestId('fuel-reconciliation-policy-banner')).toBeVisible()

    await page.goto(`${BASE_URL}/finance`)
    await expect(page).toHaveURL(/\/dashboard(?:\?|$)/)
    await expect(page.getByTestId('dashboard-title')).toBeVisible()

    await page.goto(`${BASE_URL}/finance/ledger`)
    await expect(page).toHaveURL(/\/dashboard(?:\?|$)/)
    await expect(page.getByTestId('dashboard-title')).toBeVisible()
  })
})
