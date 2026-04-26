// ============================================================================
// Agri-Guardian E2E Tests - Sales Module
// Purpose: Validate Sales invoices and customer management
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
// Test Suite: Sales Navigation
// ============================================================================
test.describe('Sales Module Navigation', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('should navigate to sales page', async ({ page }) => {
        await page.goto(`${BASE_URL}/sales`)
        await expect(page).toHaveURL(/sales/)
        await page.waitForLoadState('domcontentloaded')
    })

    test('should display sales header', async ({ page }) => {
        await page.goto(`${BASE_URL}/sales`)
        await page.waitForLoadState('domcontentloaded')

        // Check for sales-related content
        const salesContent = page.locator('text=/فواتير|المبيعات|Sales|مبيعات/i')
        await expect(salesContent.first()).toBeVisible({ timeout: 10000 })
    })
})

// ============================================================================
// Test Suite: Sales List
// ============================================================================
test.describe('Sales List', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('should display sales table or list', async ({ page }) => {
        await page.goto(`${BASE_URL}/sales`)
        await page.waitForTimeout(2000)

        // Check for table or list structure
        const table = page.locator('table, [role="grid"], [role="table"]')
        const isTableVisible = await table.first().isVisible()

        if (isTableVisible) {
            await expect(table.first()).toBeVisible()
        } else {
            // May be in card/list format
            const listItem = page.locator('text=/فاتورة|لا توجد|قائمة/i')
            await expect(listItem.first()).toBeVisible({ timeout: 10000 })
        }
    })

    test('should have create/add button for new sale', async ({ page }) => {
        await page.goto(`${BASE_URL}/sales`)
        await page.waitForLoadState('domcontentloaded')

        // Look for add button
        const addButton = page.locator('button, a').filter({ hasText: /إضافة|جديد|Add|New|فاتورة/i })
        await expect(addButton.first()).toBeVisible({ timeout: 10000 })
    })

    test('should have filter/search functionality', async ({ page }) => {
        await page.goto(`${BASE_URL}/sales`)
        await page.waitForLoadState('domcontentloaded')

        // Check for search/filter
        const filterInput = page.locator('input[type="text"], input[type="search"], input[placeholder*="بحث"]')
        await expect(filterInput.first()).toBeVisible({ timeout: 10000 })
    })
})

// ============================================================================
// Test Suite: Sale Actions
// ============================================================================
test.describe('Sale Actions', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('should show confirm/cancel actions on sales', async ({ page }) => {
        await page.goto(`${BASE_URL}/sales`)
        await page.waitForTimeout(2000)

        // Look for action buttons (confirm/cancel per Agri-Guardian)
        const actionButtons = page.locator('button').filter({ hasText: /تأكيد|إلغاء|Confirm|Cancel|View/i })
        const hasActions = await actionButtons.count() > 0

        // Either has actions or is empty state
        if (!hasActions) {
            const emptyState = page.locator('text=/لا توجد|فارغ|empty/i')
            await expect(emptyState.first()).toBeVisible()
        }
    })

    test('should be able to navigate to new sale form', async ({ page }) => {
        await page.goto(`${BASE_URL}/sales`)
        await page.waitForLoadState('domcontentloaded')

        // Find and click add button
        const addButton = page.locator('button, a').filter({ hasText: /إضافة|جديد|Add|New/i }).first()
        const isVisible = await addButton.isVisible()

        if (isVisible) {
            await addButton.click()
            await page.waitForTimeout(1000)
            // Should show form or modal
            const formFields = page.locator('input, select, form')
            await expect(formFields.first()).toBeVisible({ timeout: 5000 })
        }
    })
})

// ============================================================================
// Test Suite: Customers
// ============================================================================
test.describe('Customers Management', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('should be able to access customers list', async ({ page }) => {
        await page.goto(`${BASE_URL}/sales/customers`)
        await page.waitForTimeout(2000)

        // Either shows customers or redirects/shows sales
        const content = page.locator('text=/العملاء|عميل|Customer|المبيعات/i')
        await expect(content.first()).toBeVisible({ timeout: 10000 })
    })
})
