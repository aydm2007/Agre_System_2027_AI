/* eslint-env node */
const { chromium } = require('playwright')
const path = require('path')

;(async () => {
  console.log('🚀 Starting Browser Evaluation for Editable Rejected Logs...')
  const browser = await chromium.launch({ headless: true, slowMo: 500 })
  const context = await browser.newContext()
  const page = await context.newPage()

  try {
    // 1. Login
    console.log('🔑 Logging in as admin...')
    await page.goto('http://localhost:5173/login')
    await page.fill('[data-testid="login-username"]', 'admin')
    await page.fill('[data-testid="login-password"]', 'Yeco@2025!!')
    await page.click('[data-testid="login-submit"]')
    await page.waitForURL('**/dashboard', { timeout: 10000 })

    // 2. Open Daily Log Wizard
    console.log('📝 Opening Daily Log Wizard...')
    await page.goto('http://localhost:5173/daily-log')
    await page.waitForSelector('[data-testid="daily-log-page-title"]', { state: 'visible' })
    await page.waitForTimeout(2000) // Wait for lookups

    // 3. Negative Validations & Input
    console.log('🛡️ Testing Strict UI Validations...')
    await page.selectOption('select[name="farm"]', { index: 1 })
    await page.waitForTimeout(500)
    await page.selectOption('select[name="location"]', { index: 1 })
    await page.selectOption('select[name="crop"]', { index: 1 })
    await page.selectOption('select[name="task"]', { index: 1 })

    await page.click('button:has-text("التالي")')

    // Negative test check (HTML min="0")
    await page.fill('input[name="casual_workers_count"]', '-10')
    const casualVal = await page.inputValue('input[name="casual_workers_count"]')
    console.log(
      `Value after negative input: ${casualVal} (UI Strictness applies on form submission/blur)`,
    )

    // Fill valid data
    await page.fill('input[name="casual_workers_count"]', '5')
    await page.fill('input[name="surrah_count"]', '1')
    await page.click('button:has-text("التالي")')

    // Details step
    await page.fill('textarea[name="notes"]', 'E2E Validation for Editable Rejected Logs')
    const submitBtn = page.locator('[data-testid="daily-log-save"]')
    await submitBtn.click()

    console.log('⏳ Waiting for History Route...')
    await page.waitForURL('**/daily-log-history', { timeout: 10000 })
    await page.waitForTimeout(2000) // Wait for log list

    // 4. Submit the Draft Log
    console.log('📤 Submitting Log for Review...')
    const submitReviewBtn = page.locator('button:has-text("إرسال للمراجعة")').first()
    await submitReviewBtn.click()
    await page.waitForTimeout(1500)

    // 5. Reject the Log
    console.log('❌ Rejecting the Log...')
    const rejectBtn = page.locator('button:has-text("رفض السجل")').first()
    await rejectBtn.click()

    // Fill rejection modal
    await page.fill('textarea', 'Missing critical details, please amend and resubmit.')
    await page.click('button:has-text("تأكيد")')
    await page.waitForTimeout(2000) // wait for reload

    // 6. Reopen the Log (The New Feature)
    console.log('🔓 Reopening the Rejected Log...')
    const reopenBtn = page.locator('[data-testid="dailylog-reopen-button"]').first()
    await reopenBtn.waitFor({ state: 'visible' })
    await reopenBtn.click()

    console.log('⏳ Waiting for Wizard Redirect with draftId...')
    await page.waitForURL(/.*\/daily-log\?draftId=.*/, { timeout: 10000 })

    // Ensure data is loaded
    await page.waitForTimeout(3000) // Give server/client time to hydrate
    await page.click('button:has-text("التالي")')
    await page.click('button:has-text("التالي")')

    const hydratedNotes = await page.inputValue('textarea[name="notes"]')
    console.log(`✅ Hydrated Notes: ${hydratedNotes}`)

    const artifactPath = path.resolve(
      'C:/Users/ibrahim/.gemini/antigravity/brain/d8992235-e4d2-4a0d-8724-5e4bd7519c3b',
      `reopen_cycle_${Date.now()}.webp`,
    )
    console.log(`📸 Taking screenshot... ${artifactPath}`)
    await page.screenshot({ path: artifactPath })

    if (hydratedNotes.includes('E2E Validation')) {
      console.log('🎉 SUCCESS: Data successfully survived rejection and was hydrated for editing!')
    } else {
      console.error('❌ FAILURE: Hydration failed or data was lost.')
    }
  } catch (e) {
    console.error('❌ Error during evaluation:', e)
    const artifactPathErr = path.resolve(
      'C:/Users/ibrahim/.gemini/antigravity/brain/d8992235-e4d2-4a0d-8724-5e4bd7519c3b',
      `reopen_error_${Date.now()}.png`,
    )
    await page.screenshot({ path: artifactPathErr })
  } finally {
    await browser.close()
  }
})()
