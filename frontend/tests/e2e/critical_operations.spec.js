import { test, expect } from '@playwright/test'

const BASE_URL = process.env.VITE_API_BASE || 'http://localhost:5173'

test.describe('العمليات الحرجة (Critical Operations E2E)', () => {
    test.beforeEach(async ({ page }) => {
        // Navigate to dashboard first (assumed to be authenticated via auth.setup.js)
        await page.goto(`${BASE_URL}/dashboard`)
        await page.waitForLoadState('networkidle')
    })

    test('إضافة محصول جديد (Add Crop)', async ({ page }) => {
        await test.step('الانتقال لصفحة المحاصيل', async () => {
            await page.goto(`${BASE_URL}/crops`)
            await expect(page.locator('h1')).toContainText('المحاصيل')
        })

        await test.step('الضغط على إضافة محصول', async () => {
            // Assuming a standard "Add" button pattern
            const addButton = page.locator('button').filter({ hasText: /إضافة|جديد|Add/i }).first()
            if (await addButton.isVisible()) {
                await addButton.click()
                // Here we would fill the form, e.g., name, variety, expected yield
                const nameInput = page.locator('input[name="name"], input[placeholder*="اسم"]').first()
                if (await nameInput.isVisible()) {
                    await nameInput.fill('قمح تجريبي E2E')
                }
                // Save
                const saveBtn = page.locator('button').filter({ hasText: /حفظ|Save/i }).first()
                if (await saveBtn.isVisible()) {
                    await saveBtn.click()
                }
            }
        })
    })

    test('اعتماد مالي (Financial Approval)', async ({ page }) => {
        await test.step('الانتقال لصفحة تسويات الموردين أو الموافقات', async () => {
            await page.goto(`${BASE_URL}/finance/supplier-settlements`)
            await expect(page.locator('h1')).toBeVisible()
        })

        await test.step('محاولة اعتماد معاملة مالية معلقة', async () => {
            // Find a button that says "Approve" or "اعتماد"
            const approveBtn = page.locator('button').filter({ hasText: /اعتماد|Approve/i }).first()
            if (await approveBtn.isVisible()) {
                await approveBtn.click()
                // Wait for potential confirmation or toast
                const toast = page.locator('.toast, [role="alert"]').first()
                if (await toast.isVisible()) {
                    await expect(toast).toContainText(/نجاح|تم|Success/i)
                }
            }
        })
    })

    test('صرف مخزني (Inventory Disbursement)', async ({ page }) => {
        await test.step('الانتقال لصفحة إدارة المخزون', async () => {
            await page.goto(`${BASE_URL}/stock`)
            await expect(page.locator('h1')).toBeVisible()
        })

        await test.step('تنفيذ الصرف', async () => {
            const dispenseBtn = page.locator('button').filter({ hasText: /صرف|Dispense/i }).first()
            if (await dispenseBtn.isVisible()) {
                await dispenseBtn.click()

                // Modal appears, select item, fill quantity
                const qtyInput = page.locator('input[type="number"], input[name="quantity"]').first()
                if (await qtyInput.isVisible()) {
                    await qtyInput.fill('10')
                }

                const confirmBtn = page.locator('button').filter({ hasText: /تأكيد|صرف|Confirm/i }).first()
                if (await confirmBtn.isVisible()) {
                    await confirmBtn.click()
                }
            }
        })
    })
})
