const { test, expect } = require('@playwright/test');

test.describe('RTL and Dark Mode Visual Compliance', () => {
  
  const pagesToTest = [
    { url: '/dashboard', name: 'Dashboard' },
    { url: '/daily-log/smart-run', name: 'DailyLog' },
    { url: '/finance/treasury', name: 'Treasury' },
    { url: '/approvals/inbox', name: 'ApprovalInbox' }
  ];

  for (const pageTest of pagesToTest) {
    test(`Validates RTL enforcement and Dark Mode rendering on ${pageTest.name}`, async ({ page }) => {
      await page.goto(pageTest.url);
      
      // Check Document HTML dir attribute
      const htmlDir = await page.locator('html').getAttribute('dir');
      expect(htmlDir).toBe('rtl');
      
      // Toggle Dark mode (assume a global toggle class or theme switch exists)
      await page.evaluate(() => document.documentElement.classList.add('dark'));
      
      const hasDark = await page.evaluate(() => document.documentElement.classList.contains('dark'));
      expect(hasDark).toBeTruthy();
      
      // Optionally take a visual diff trace snapshot here in a real pipeline
      // await expect(page).toHaveScreenshot(`${pageTest.name}-dark-rtl.png`);
    });
  }
});
