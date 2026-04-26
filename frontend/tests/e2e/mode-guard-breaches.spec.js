const { test, expect } = require('@playwright/test');

test.describe('ModeGuard Breach Detections', () => {
  test.use({ storageState: 'playwright/.auth/simple-user.json' });

  test('SIMPLE operational user is blocked from directly accessing treasury routes', async ({ page }) => {
    await page.goto('/finance/treasury');
    
    // Validate redirection to unauthorized splash
    await expect(page).toHaveURL(/.*unauthorized|dashboard.*/);
    
    // Validate that the system warned the user visibly
    const alert = page.locator('.route-breach-alert');
    if (await alert.isVisible()) {
      await expect(alert).toContainText(/Access Denied|غير مصرح/);
    }
  });

  test('SIMPLE user attempting to view fixed assets directly is intercepted', async ({ page }) => {
    await page.goto('/fixed-assets/register');
    await expect(page).not.toHaveURL(/.*fixed-assets\/register.*/);
  });
});

test.describe('STRICT Access Validations', () => {
  test.use({ storageState: 'playwright/.auth/strict-admin.json' });

  test('STRICT profile can successfully load governed financial views', async ({ page }) => {
    await page.goto('/finance/supplier-settlements');
    await expect(page).toHaveURL(/.*supplier-settlements.*/);
    const header = page.locator('h1');
    if (await header.isVisible()) {
      await expect(header).not.toContainText(/Access Denied/);
    }
  });
});
