import { test, expect } from '@playwright/test';

test.describe('Crop Plan Detail Page', () => {
    test.beforeEach(async ({ page }) => {
        // Login functionality - Fixed Selectors
        await page.goto('http://localhost:5173/login');

        // Wait for inputs to be visible
        await page.waitForSelector('input[type="text"]');

        // Use type selectors since name attributes are missing
        await page.locator('input[type="text"]').first().fill('admin');
        await page.locator('input[type="password"]').fill('password123');
        await page.click('button[type="submit"]');
        // Wait for navigation relative to base URL (regex for looser matching)
        await page.waitForURL(/\/dashboard/);
    });

    test('should navigate to detail page and display critical components', async ({ page }) => {
        // 1. Navigate to Crop Plans List
        await page.goto('http://localhost:5173/crop-plans');
        await page.waitForLoadState('networkidle');
        await expect(page.locator('h1')).toContainText('خطط المحاصيل');

        // 2. Click the first plan
        // Wait for table rows - handle case where data might take a moment
        const row = page.locator('table tbody tr').first();
        await row.waitFor({ state: 'visible', timeout: 10000 });

        const planName = await row.locator('td').first().textContent();
        await row.click();

        // 3. Verify Detail Page Loaded
        await expect(page).toHaveURL(/\/crop-plans\/\d+/);
        await expect(page.locator('h2')).toContainText(planName.trim());

        // 4. Verify Critical Sections
        // Variance Cards
        await expect(page.getByText('إجمالي الميزانية')).toBeVisible();
        await expect(page.getByText('الأنشطة المرتبطة')).toBeVisible();

        // Budget Table
        await expect(page.getByText('الميزانية التفصيلية')).toBeVisible();

        // Check for Charts (Canvas)
        const chart = page.locator('canvas');
        if (await chart.count() > 0) {
            await expect(chart.first()).toBeVisible();
        }
    });

    test('should allow adding a budget line', async ({ page }) => {
        await page.goto('http://localhost:5173/crop-plans');
        await page.waitForLoadState('networkidle');
        await page.waitForSelector('table tbody tr');
        await page.locator('table tbody tr').first().click();

        await expect(page.getByText('الميزانية التفصيلية')).toBeVisible();

        // Specific Selectors for "New Line"
        // It's the first row of the first table body found within the budget section (or the only table in that section)

        // Find the table that contains "المهمة" (Task) header
        const table = page.locator('table', { hasText: 'المهمة' }).first();
        const tbody = table.locator('tbody').first();
        const newRow = tbody.locator('tr').first();

        // Qty Input (First number input in the new line row)
        const qtyInput = newRow.locator('input[type="number"]').nth(0);
        await qtyInput.fill('10');

        // UOM (Placeholder: وحدة)
        await newRow.getByPlaceholder('وحدة').fill('KG');

        // Rate Input (Second number input in the row)
        const rateInput = newRow.locator('input[type="number"]').nth(1);
        await rateInput.fill('50');

        // Currency (Placeholder: العملة)
        // Check if exists before filling (conditional logic in component)
        const currencyInput = newRow.locator('input[placeholder="العملة"]');
        if (await currencyInput.count() > 0) {
            await currencyInput.fill('YER');
        }

        // Total Auto-calc verification (Third number input)
        const totalInput = newRow.locator('input[type="number"]').nth(2);
        await expect(totalInput).toHaveValue('500');

        // Click Add
        await newRow.getByRole('button', { name: 'إضافة' }).click();

        // Verify Success Toast or Row Addition
        // The toast might appear
        await expect(page.getByText('تم حفظ سطر الميزانية')).toBeVisible();
    });
});
