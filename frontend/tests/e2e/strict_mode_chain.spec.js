import { test, expect } from '@playwright/test'
import {
    BASE_URL,
    endpoints,
    ensureLoggedIn,
    ensureFarmSelected,
    fetchToken,
    withAuthHeaders,
} from './helpers/e2eAuth'

test.describe('STRICT Mode Chain Verification', () => {
    let strictErpMode = false

    test.beforeAll(async ({ request }) => {
        const modeRes = await request.get(`${endpoints.V1_BASE}/system-mode/`)
        if (modeRes.ok()) {
            const modeBody = await modeRes.json()
            strictErpMode = Boolean(modeBody?.strict_erp_mode)
        }
    })

    test('Finance menus exist and Maker-Checker chain is accessible in STRICT mode', async ({ page, request }) => {
        if (!strictErpMode) {
            test.skip('System is in SIMPLE mode, skipping STRICT chain test.')
            return
        }

        await ensureLoggedIn(page, request)
        await ensureFarmSelected(page)

        // Check navigation for finance links
        const financeLink = page.locator('a[href*="/finance"]').first()
        await expect(financeLink).toBeVisible()
        await financeLink.click()

        // Assuming there is a Maker/Checker lane or Ledger view
        const ledgerHeader = page.locator('h1, h2').filter({ hasText: 'دفتر الأستاذ' })
        await expect(ledgerHeader).toBeVisible()
    })
})
