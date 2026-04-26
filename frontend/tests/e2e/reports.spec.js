
// ============================================================================
// Agri-Guardian E2E Tests - Reports Module
// Purpose: Validate Reports generation and visibility
// Protocol: Agri-Guardian Section 4.II - Frontend Contract
// ============================================================================
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:5173'
const TEST_USER = {
    username: 'ibrahim',
    password: '123456',
}

// ============================================================================
// Helper: Login Flow
// ============================================================================
async function login(page) {
    await page.goto(`${BASE_URL}/login`)
    await page.waitForSelector('#username', { timeout: 10000 })
    await page.fill('#username', TEST_USER.username)
    await page.fill('#password', TEST_USER.password)
    await page.click('button[type="submit"]')
    await page.waitForURL('**/dashboard', { timeout: 15000 })
}

// ============================================================================
// Test Suite: Reports Navigation
// ============================================================================
test.describe('Reports Module', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('should navigate to reports page', async ({ page }) => {
        await page.goto(`${BASE_URL}/reports`)
        // Adjust regex if URL is different (e.g. /reporting or /reports)
        await expect(page).toHaveURL(/reports/i)
        await page.waitForLoadState('domcontentloaded')
    })

    test('should display reports header', async ({ page }) => {
        await page.goto(`${BASE_URL}/reports`)
        await page.waitForLoadState('domcontentloaded')

        // Check for reports header
        const header = page.locator('h1, h2').filter({ hasText: /تقارير|تقرير|Report/i })
        await expect(header.first()).toBeVisible({ timeout: 10000 })
    })

    test('should display date range inputs', async ({ page }) => {
        await page.goto(`${BASE_URL}/reports`)
        await page.waitForTimeout(2000)

        // Check for date inputs
        const dateInputs = page.locator('input[type="date"]')

        // Report pages usually have start and end date
        if (await dateInputs.count() > 0) {
            await expect(dateInputs.first()).toBeVisible()
        } else {
            // Or at least a filter section
            const filter = page.locator('text=/تاريخ|بحث|Filter/i')
            await expect(filter.first()).toBeVisible()
        }
    })

    test('should have generate report button', async ({ page }) => {
        await page.goto(`${BASE_URL}/reports`)
        await page.waitForLoadState('domcontentloaded')

        // Look for generate/print/export buttons
        const actionButton = page.locator('button').filter({ hasText: /توليد|عرض|طباعة|Generate|View/i })
        await expect(actionButton.first()).toBeVisible({ timeout: 10000 })
    })
})
