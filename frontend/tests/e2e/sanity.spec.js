import { test, expect } from '@playwright/test';

test('Daily Log loads without crashing', async ({ page }) => {
    // 1. تسجيل الدخول
    await page.goto('/login');
    await page.fill('input[name="username"]', 'ibrahim');
    await page.fill('input[name="password"]', '123456');
    await page.click('button[type="submit"]');

    // 2. الذهاب لصفحة السجل
    await page.goto('/daily-log');

    // 3. التحقق من عدم وجود رسالة خطأ
    const errorOverlay = page.locator('text=Uncaught ReferenceError');
    await expect(errorOverlay).not.toBeVisible();

    // 4. التحقق من ظهور عنصر رئيسي
    await expect(page.locator('h2, h1, .daily-log-header')).toBeVisible(); // Flexible selector
});
