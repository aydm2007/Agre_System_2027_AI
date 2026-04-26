// ============================================================================
// Agri-Guardian E2E Tests - Invoice Printing
// Purpose: Validate Invoice Print functionality
// ============================================================================
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:5173'
const TEST_USER = {
    username: 'ibrahim',
    password: '123456',
}

async function login(page) {
    await page.goto(`${BASE_URL}/login`)
    await page.fill('#username', TEST_USER.username)
    await page.fill('#password', TEST_USER.password)
    await page.click('button[type="submit"]')
    await page.waitForURL('**/dashboard')
}

test.describe('Invoice Printing', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('should have print button on sales list', async ({ page }) => {
        await page.goto(`${BASE_URL}/sales`)

        // Hover over a row to see actions if needed, or just check for presence
        const printButton = page.locator('button[title="طباعة الفاتورة"]').first()

        // It might be hidden until hover, so we force access or hover first
        const row = page.locator('tbody tr').first()
        if (await row.isVisible()) {
            await row.hover()
            await expect(printButton).toBeVisible()
        }
    })

    test('print page should display correct invoice details', async ({ page }) => {
        // Navigate to sales list
        await page.goto(`${BASE_URL}/sales`)

        // Find an invoice ID (simplification: assume at least one exists from extension script)
        // Click print button
        const row = page.locator('tbody tr').first()
        if (await row.isVisible()) {
            await row.hover()
            const printButton = page.locator('button[title="طباعة الفاتورة"]').first()
            await printButton.click()

            // Should match URL /sales/:id/print
            await expect(page).toHaveURL(/\/sales\/\d+\/print/)

            // Check for print template elements
            await expect(page.locator('text=فاتورة مبيعات')).toBeVisible()
            await expect(page.locator('text=Sales Invoice')).toBeVisible()

            // Check for Print and Back buttons
            await expect(page.locator('button:has-text("طباعة")')).toBeVisible()
            await expect(page.locator('button:has-text("العودة")')).toBeVisible()
        }
    })
})
