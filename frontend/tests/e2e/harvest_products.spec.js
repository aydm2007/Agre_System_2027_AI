
// ============================================================================
// Agri-Guardian E2E Tests - Harvest Products Module
// Purpose: Validate Harvest Products Catalog & Management
// Protocol: Agri-Guardian Section 4.II - Frontend Contract
// ============================================================================
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:5173'
const TEST_USER = {
    username: 'ibrahim',
    password: '123456',
}

async function login(page) {
    await page.goto(`${BASE_URL}/login`)
    await page.waitForSelector('#username', { state: 'visible', timeout: 10000 })
    await page.fill('#username', TEST_USER.username)
    await page.fill('#password', TEST_USER.password)
    await page.click('button[type="submit"]')
    await page.waitForURL('**/dashboard', { timeout: 15000 })
}

test.describe('Harvest Products Module', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('should navigate to harvest products page', async ({ page }) => {
        await page.goto(`${BASE_URL}/harvest-products`)
        await expect(page).toHaveURL(/harvest-products/)
        await page.waitForLoadState('domcontentloaded')
    })

    test('should display main header', async ({ page }) => {
        await page.goto(`${BASE_URL}/harvest-products`)

        // Header title check
        const header = page.locator('h1').first()
        await expect(header).toBeVisible()
        // Content might vary based on translation, checking visibility is key step 1
    })

    test('should show create form', async ({ page }) => {
        await page.goto(`${BASE_URL}/harvest-products`)
        await page.waitForTimeout(1000)

        // Check for farm selection or crop selection inputs
        const farmSelect = page.locator('select, [role="combobox"]').first()
        await expect(farmSelect).toBeVisible()
    })

    test('should display product table/catalog', async ({ page }) => {
        await page.goto(`${BASE_URL}/harvest-products`)
        await page.waitForTimeout(1000)

        const table = page.locator('table')
        await expect(table.first()).toBeVisible()
    })
})
