// Quick test for Daily Log save functionality
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:5173'

test.describe('Daily Log Save Test', () => {
  test('should login and save a daily log', async ({ page }) => {
    // Step 1: Login
    await page.goto(`${BASE_URL}/login`)
    await page.waitForLoadState('networkidle')

    // Fill login form
    await page.fill('input[name="username"], input[type="text"]', 'ibrahim')
    await page.fill('input[name="password"], input[type="password"]', '123456')

    // Click login button
    await page.click('button[type="submit"], button:has-text("تسجيل"), button:has-text("دخول")')

    // Wait for redirect
    await page.waitForURL(/\/(dashboard|daily-log|$)/, { timeout: 10000 })
    console.log('Login successful, current URL:', page.url())

    // Step 2: Navigate to Daily Log
    await page.goto(`${BASE_URL}/daily-log`)
    await page.waitForLoadState('networkidle')

    // Take screenshot before filling
    await page.screenshot({ path: 'test-results/daily-log-before.png' })
    console.log('Daily Log page loaded')

    // Step 3: Check for form elements
    const farmSelect = page.locator('select, [role="combobox"]').first()
    if (await farmSelect.isVisible()) {
      console.log('Farm dropdown is visible')

      // Try to select first option
      const options = await page.locator('select option, [role="option"]').all()
      if (options.length > 1) {
        await farmSelect.selectOption({ index: 1 })
        console.log('Selected first farm')
      }
    }

    // Wait a bit for cascading dropdowns
    await page.waitForTimeout(2000)

    // Take screenshot after selection
    await page.screenshot({ path: 'test-results/daily-log-filled.png' })

    // Step 4: Try to find and click save button
    const saveButton = page.locator(
      'button:has-text("حفظ"), button:has-text("إرسال"), button[type="submit"]',
    )
    if (await saveButton.isVisible()) {
      console.log('Save button found, clicking...')
      await saveButton.click()

      // Wait for response
      await page.waitForTimeout(3000)

      // Take screenshot after save attempt
      await page.screenshot({ path: 'test-results/daily-log-after-save.png' })

      // Check for success or error message
      const successMessage = page.locator('text=/نجح|تم الحفظ|success/i')
      const errorMessage = page.locator('text=/خطأ|error|فشل/i')

      if (await successMessage.isVisible()) {
        console.log('SUCCESS: Save completed successfully!')
      } else if (await errorMessage.isVisible()) {
        console.log('ERROR: Save failed with error message')
      } else {
        console.log('Unknown result after save')
      }
    } else {
      console.log('Save button not found/visible')
    }

    // Final screenshot
    await page.screenshot({ path: 'test-results/daily-log-final.png' })
  })
})
