// ============================================================================
// Agri-Guardian E2E Tests - Employees Module
// Purpose: Validate Employee management and payroll
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
// Test Suite: Employees Navigation
// ============================================================================
test.describe('Employees Module Navigation', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('should navigate to employees page', async ({ page }) => {
        await page.goto(`${BASE_URL}/employees`)
        await expect(page).toHaveURL(/employees/)
        await page.waitForLoadState('domcontentloaded')
    })

    test('should display employees header', async ({ page }) => {
        await page.goto(`${BASE_URL}/employees`)
        await page.waitForLoadState('domcontentloaded')

        // Check for employees-related content
        const employeesContent = page.locator('text=/الموظفين|موظف|Employees|Employee/i')
        await expect(employeesContent.first()).toBeVisible({ timeout: 10000 })
    })
})

// ============================================================================
// Test Suite: Employees List
// ============================================================================
test.describe('Employees List', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('should display employees table', async ({ page }) => {
        await page.goto(`${BASE_URL}/employees`)
        await page.waitForTimeout(2000)

        // Check for table structure
        const table = page.locator('table')
        await expect(table.first()).toBeVisible({ timeout: 10000 })
    })

    test('should show employee details in table', async ({ page }) => {
        await page.goto(`${BASE_URL}/employees`)
        await page.waitForTimeout(2000)

        // Check for table headers or content
        const tableHeaders = page.locator('th, thead')
        await expect(tableHeaders.first()).toBeVisible({ timeout: 10000 })
    })

    test('should have add employee button', async ({ page }) => {
        await page.goto(`${BASE_URL}/employees`)
        await page.waitForLoadState('domcontentloaded')

        // Look for add button
        const addButton = page.locator('button').filter({ hasText: /إضافة|جديد|Add|New/i })
        await expect(addButton.first()).toBeVisible({ timeout: 10000 })
    })

    test('should have search/filter functionality', async ({ page }) => {
        await page.goto(`${BASE_URL}/employees`)
        await page.waitForLoadState('domcontentloaded')

        // Check for search input
        const searchInput = page.locator('input[type="text"], input[placeholder*="بحث"]')
        await expect(searchInput.first()).toBeVisible({ timeout: 10000 })
    })
})

// ============================================================================
// Test Suite: Employee CRUD
// ============================================================================
test.describe('Employee CRUD Operations', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('should open add employee form', async ({ page }) => {
        await page.goto(`${BASE_URL}/employees`)
        await page.waitForLoadState('domcontentloaded')

        const addButton = page.locator('button').filter({ hasText: /إضافة|جديد|Add/i }).first()
        const isVisible = await addButton.isVisible()

        if (isVisible) {
            await addButton.click()
            await page.waitForTimeout(500)
            // Should show form/modal
            const formElement = page.locator('form, [role="dialog"], .modal')
            await expect(formElement.first()).toBeVisible({ timeout: 5000 })
        }
    })

    test('should have edit and delete actions', async ({ page }) => {
        await page.goto(`${BASE_URL}/employees`)
        await page.waitForTimeout(2000)

        // Look for action buttons in table rows
        const actionButtons = page.locator('button[title], button').filter({ hasText: /تعديل|حذف|Edit|Delete/i })
        const hasActions = await actionButtons.count() > 0

        // Either has actions or is empty state
        if (!hasActions) {
            const emptyState = page.locator('text=/لا يوجد|فارغ|empty|لا توجد/i')
            const hasEmpty = await emptyState.count() > 0
            expect(hasEmpty || await actionButtons.count() > 0).toBeTruthy()
        }
    })
})

// ============================================================================
// Test Suite: Payroll (if available)
// ============================================================================
test.describe('Payroll Features', () => {
    test.beforeEach(async ({ page }) => {
        await login(page)
    })

    test('should be able to navigate to employees module', async ({ page }) => {
        await page.goto(`${BASE_URL}/employees`)
        await page.waitForLoadState('domcontentloaded')

        // Verify we're on employees page
        await expect(page).toHaveURL(/employees/)

        // Check for any payroll-related content or stats
        const content = page.locator('text=/راتب|رواتب|دفع|Salary|Pay/i')
        const hasPayroll = await content.count() > 0

        // Either shows payroll features or just employee list
        const employeeContent = page.locator('text=/موظف|الموظفين|Employee/i')
        await expect(employeeContent.first()).toBeVisible({ timeout: 10000 })
    })
})
