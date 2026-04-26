import { test, expect } from '@playwright/test'

test.use({ storageState: { cookies: [], origins: [] } })

test.describe('Alhussainiya Farm Simple Mode E2E Cycle', () => {
  test('Full operational cycle in Simple Mode', async ({ page }) => {
    // 1. Setup: Login
    await page.goto('/login')
    await page.fill('[data-testid="login-username"]', 'playwright')
    await page.fill('[data-testid="login-password"]', 'playwright123')
    await page.click('[data-testid="login-submit"]')
    await page.waitForURL('**/dashboard**', { timeout: 15000 })

    // Verify Simple Mode or force it
    // Wait until nav is loaded
    await page.waitForSelector('nav')

    // Switch to Simple mode if Strict is active
    const modeSelect = await page.$('select[title="تغيير وضع النظام"]')
    if (modeSelect) {
      const val = await modeSelect.inputValue()
      if (val !== 'SIMPLE') {
        await page.selectOption('select[title="تغيير وضع النظام"]', 'SIMPLE')
        await page.waitForTimeout(1000) // Give time for state update
      }
    }

    // Capture initial visibility - Verify Treasury and Sales are hidden in Simple Mode
    // Instead of looking for them directly which might fail, we check they don't exist.
    const treasuryMenu = await page.$('text=الخزينة والحسابات')
    const salesMenu = await page.$('text=المبيعات والتسويق')
    expect(treasuryMenu).toBeNull()
    expect(salesMenu).toBeNull()

    // 2. Setup: Create Farm
    await page.click('text=المزارع والموارد')
    await page.click('a[href="/farms"]')
    await page.waitForURL('**/farms')

    await page.click('button:has-text("إضافة مزرعة")')
    await page.fill('#farm-name', 'الحسينية')
    await page.fill('#farm-region', 'Test Region')
    await page.fill('input[id="farm-area"]', '50')
    await page.click('button:has-text("حفظ")')
    await page.waitForTimeout(2000)

    // 2.5 Programmatic Setup: Add a location and a crop to this farm so the Crop Plan wizard works
    const setupResult = await page.evaluate(async () => {
      try {
        const token = localStorage.getItem('accessToken')
        const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

        const getPostHeaders = () => ({
          ...headers,
          'X-Idempotency-Key': crypto.randomUUID(),
        })

        // Get the newly created farm (the last one if there are duplicates)
        const farmsRes = await fetch('/api/v1/farms/', { headers })
        const farmsData = await farmsRes.json()
        const farms = farmsData.results || farmsData
        const matchingFarms = farms.filter((f) => f.name === 'الحسينية')
        const farm =
          matchingFarms.length > 0
            ? matchingFarms[matchingFarms.length - 1]
            : farms[farms.length - 1]
        if (!farm) return { success: false, error: 'Farm not found' }

        // Add a Location
        const locRes = await fetch('/api/v1/locations/', {
          method: 'POST',
          headers: getPostHeaders(),
          body: JSON.stringify({
            name: `الحقل الرئيسي ${Date.now()}`,
            type: 'Field',
            farm: farm.id,
            code: `LOC-${Date.now()}`,
          }),
        })
        if (!locRes.ok) {
          const body = await locRes.text()
          return { success: false, error: 'Location creation failed: ' + body }
        }

        // Add a Global Crop (if it doesn't exist)
        const cropRes = await fetch('/api/v1/crops/', {
          method: 'POST',
          headers: getPostHeaders(),
          body: JSON.stringify({ name: 'قمح تجريبي', mode: 'Open', is_perennial: false }),
        })

        let cropData
        if (cropRes.ok) {
          cropData = await cropRes.json()
        } else {
          const body = await cropRes.text()
          console.error('POST /api/v1/crops/ failed:', cropRes.status, body)
          const existRes = await fetch('/api/v1/crops/', { headers })
          const existData = await existRes.json()
          const existCrops = existData.results || existData
          cropData = existCrops[0]
          if (!cropData) {
            return { success: false, error: 'No crops exist and could not create one. ' + body }
          }
        }

        // Link Crop to Farm
        const linkRes = await fetch('/api/v1/farm-crops/', {
          method: 'POST',
          headers: getPostHeaders(),
          body: JSON.stringify({ farm: farm.id, crop: cropData.id }),
        })

        if (!linkRes.ok) {
          return { success: false, error: 'Failed to link crop: ' + (await linkRes.text()) }
        }

        // Verify Crop appears in Farm Crops
        const verifyRes = await fetch(`/api/v1/crops/?farm_id=${farm.id}`, { headers })
        const verifyData = await verifyRes.json()
        const finalCrops = verifyData.results || verifyData
        if (!finalCrops || finalCrops.length === 0) {
          return {
            success: false,
            error:
              'Crop was linked, but GET /api/v1/crops/?farm_id= returned empty! LinkRes Status: ' +
              linkRes.status +
              ' cropId: ' +
              cropData.id,
          }
        }

        return { success: true, cropId: cropData.id, linkedCrops: finalCrops.length }
      } catch (err) {
        return { success: false, error: err.toString() }
      }
    })

    if (!setupResult.success) {
      throw new Error(`Programmatic Setup Failed: ${setupResult.error}`)
    }
    console.log(
      `Setup complete. Created location, linked crop ID ${setupResult.cropId}. Total farm crops: ${setupResult.linkedCrops}`,
    )

    // 3. Wizard Planning: Create Crop Plan
    await page.click('text=إدارة المحاصيل')
    await page.click('a[href="/crop-plans"]')
    await page.waitForURL('**/crop-plans')

    await page.click('button:has-text("خطة جديدة")')

    // Step 1: Basic details
    await page.selectOption('select:has-text("اختر المزرعة")', { label: 'الحسينية' })
    await page.waitForTimeout(1000) // Wait for locations and crops to load

    // Choose the first location checkbox
    await page.click('input[type="checkbox"] >> nth=0')

    // Choose the first crop option (skip index 0 which is empty)
    await page.locator('select:has-text("اختر المحصول")').first().selectOption({ index: 1 })

    await page.fill('input[placeholder="مثال: خطة القمح الموسم الشتوي"]', 'خطة الحسينية 2026')
    await page.fill('input[type="date"] >> nth=0', '2026-01-01')
    await page.fill('input[type="date"] >> nth=1', '2026-12-31')

    await page.click('button:has-text("التالي")') // Next step to Step 2

    // Step 2: Template
    await page.click('button:has-text("التالي")') // Next step to Step 3

    // Step 3: Review
    await page.click('button:has-text("إنشاء الخطة ✅")') // Save
    await page.waitForTimeout(2000)

    // 4. Daily Logs: Quick action from dashboard
    await page.click('a[href="/dashboard"]')
    await page.waitForURL('**/dashboard')
    await page.click('button:has-text("إضافة سجل يومي"), a[href="/daily-log"]')
    await page.waitForURL('**/daily-log')

    // Verify Labels (Expert UI Terminology)
    await expect(page.locator('text=المواقع (Sites)')).toBeVisible()

    // Fill basic info
    await page.selectOption('.step-content select', { label: 'الحسينية' })

    // Note: this script focuses on structure.
    // Wait for task fields to render and click through to Resources
    await page.click('button:has-text("التالي")') // To locations
    await page.click('button:has-text("التالي")') // To tasks/resources

    // Verify Surra -> وردية
    await expect(page.locator('text=وردية')).toBeVisible()

    // Verify Machine Hours -> ساعة عمل
    await page.click('button:has-text("التالي")') // To machinery/Service details
    await expect(page.locator('text=(ساعة عمل)')).toBeVisible()

    // Verify Submit is possible without Service Details
    await page.click('button:has-text("التالي")') // To Review
    const submitBtn = page.locator('button:has-text("حفظ السجل اليومي")')
    await expect(submitBtn).toBeVisible()

    console.log('Alhussainiya Full Cycle E2E UI verification completed successfully.')
  })
})
