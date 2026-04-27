// @ts-check
import { test, expect } from '@playwright/test';

test.describe('Daily Log: Draft Reverse Hydration & Integrity [ZENITH 11.5]', () => {
  test('should completely restore HR, Items, and Smart Cards from draft to UI state', async ({ page }) => {
    // 1. Arrange: Login
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/');

    // 2. Navigate to Daily Log (الانجاز اليومي)
    await page.click('text=الانجاز اليومي');
    await expect(page).toHaveURL(/.*\/daily-log/);

    // 3. Start New Log and fill basic details
    await page.click('button:has-text("سجل جديد")');
    await page.selectOption('select[name="farm"]', '21'); // Farm ID example
    await page.locator('input[name="locations"]').click();
    // Assuming a Multi-select or Checkbox
    await page.locator('text=123').click(); 
    await page.click('body'); // Click outside

    // 4. Fill HR Details (الموارد البشرية)
    await page.click('button:has-text("التالي")'); // Next step
    await page.selectOption('select[name="labor_entry_mode"]', 'CASUAL_BATCH');
    await page.fill('input[name="casual_workers_count"]', '5');
    await page.fill('input[name="casual_batch_label"]', 'عمالة حصاد جديدة');

    // 5. Fill Items (المواد)
    await page.click('button:has-text("إضافة مادة")');
    await page.selectOption('select[name="item_id"]', '14'); 
    await page.fill('input[name="qty"]', '10.5');

    // 6. Fill Smart Card (الكارت الذكي)
    await page.click('button:has-text("إضافة خدمة")');
    await page.selectOption('select[name="varietyId"]', '100');
    await page.fill('input[name="serviceCount"]', '50');

    // 7. Save Draft and Leave
    await page.click('button:has-text("حفظ كمسودة")');
    // Wait for the draft to save (e.g. snackbar or toast)
    await expect(page.locator('text=تم الحفظ')).toBeVisible();

    // 8. Go somewhere else, then come back and Resume Draft
    await page.goto('/');
    await page.goto('/daily-log');
    
    // Resume the newest draft
    await page.click('[data-testid="resume-draft-btn"]'); // Example selector

    // 9. Assert Hydration Integrity (100% Evaluation Check)
    // Step 2 inputs
    await page.click('button:has-text("التالي")'); // Go to step 2

    // Verify HR
    await expect(page.locator('select[name="labor_entry_mode"]')).toHaveValue('CASUAL_BATCH');
    await expect(page.locator('input[name="casual_workers_count"]')).toHaveValue('5');

    // Verify Items
    await expect(page.locator('input[name="qty"]')).toHaveValue('10.5');

    // Verify Smart Cards
    await expect(page.locator('input[name="serviceCount"]')).toHaveValue('50');
  });
});
