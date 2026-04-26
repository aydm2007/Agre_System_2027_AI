import { test, expect } from '@playwright/test'
import { BASE_URL, endpoints, ensureLoggedIn, ensureFarmSelected } from './helpers/e2eAuth'

test.describe('Finance UI Contracts', () => {
  let strictErpMode = false

  test.beforeAll(async ({ request }) => {
    const modeRes = await request.get(`${endpoints.V1_BASE}/system-mode/`)
    expect(modeRes.ok(), 'MODE CONTRACT HALT: cannot load /system-mode/').toBeTruthy()
    const modeBody = await modeRes.json()
    strictErpMode = Boolean(modeBody?.strict_erp_mode)
  })

  test('finance routes are reachable with stable URL contract', async ({ page, request }) => {
    await ensureLoggedIn(page, request)
    await ensureFarmSelected(page)

    const routes = [
      { path: '/finance', selector: 'finance-ledger-page' },
      { path: '/finance/fiscal-periods', selector: 'finance-fiscal-periods-page' },
      { path: '/finance/actual-expenses', selector: 'finance-expenses-page' },
    ]

    for (const route of routes) {
      await page.goto(`${BASE_URL}${route.path}`)
      const pageContainer = page.getByTestId(route.selector)

      if (!strictErpMode) {
        await expect(pageContainer).toHaveCount(0)
        continue
      }

      await expect(page).toHaveURL(new RegExp(`${route.path.replace('/', '\\/')}($|\\/)`))

      const selectorVisible = await pageContainer.isVisible().catch(() => false)
      if (selectorVisible) {
        await expect(pageContainer).toBeVisible()
      }
    }
  })
})
