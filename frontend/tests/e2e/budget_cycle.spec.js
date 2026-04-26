/**
 * Budget E2E Cycle — CropPlan Budget Line CRUD
 *
 * Pre-condition: Authenticated via auth.setup.js (storageState).
 * Tests the full budget line creation flow on the CropPlanDetail page.
 */
import { test, expect } from '@playwright/test'

test.describe('Budget E2E Cycle', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a known crop plan
    await page.goto('/crop-plans/103')

    // Wait for the budget section to be visible
    await expect(page.locator('h3:has-text("الميزانية التفصيلية")')).toBeVisible({ timeout: 15000 })
  })

  test('should add a budget line and verify total calculation', async ({ page }) => {
    // 1. Select Task (first available option other than the default empty one)
    const taskSelect = page.locator('select:has(option:text("اختر مهمة"))').first()
    await taskSelect.selectOption({ index: 1 })

    // 2. Select Category "materials"
    const categorySelect = page.locator('select:has(option[value="materials"])').first()
    await categorySelect.selectOption('materials')

    // 3. Fill Qty Budget
    const qtyInput = page.locator('input[placeholder="الكمية"]').first()
    await qtyInput.fill('15')

    // 4. Fill Rate Budget
    const rateInput = page.locator('input[placeholder="السعر"]').first()
    await rateInput.fill('100')

    // 5. Verify auto calculation of total (15 × 100 = 1500)
    const totalInput = page.locator('input[type="number"]').nth(2)
    const totalValue = await totalInput.inputValue()
    expect(Number(totalValue)).toBe(1500)

    // 6. Save
    const addButton = page.locator('button:has-text("إضافة")')
    await addButton.click()

    // 7. Verify Toast Success Message
    const toast = page.locator('text="تم حفظ سطر الميزانية"')
    await expect(toast).toBeVisible({ timeout: 5000 })

    console.log('✅ UI E2E Budget Scenario Passed')
  })
})
