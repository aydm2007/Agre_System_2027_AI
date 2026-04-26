/* eslint-env node */
const { chromium } = require('playwright')
const path = require('path')

;(async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } })
  const page = await context.newPage()

  const artifactDir =
    'C:\\Users\\ibrahim\\.gemini\\antigravity\\brain\\d8992235-e4d2-4a0d-8724-5e4bd7519c3b'

  try {
    console.log('1. Logging in as admin...')
    await page.goto('http://localhost:5173/login')
    await page.fill('input[type="text"]', 'admin')
    await page.fill('input[type="password"]', 'ADMIN123')
    await page.click('button[type="submit"]')
    await page.waitForTimeout(2000)

    // Quick log submission bypass via API since the UI is complex and flaky with playwright locators
    // We log in, capture the token from localStorage, and hit the API directly to set up the data state.
    const token = await page.evaluate(() => localStorage.getItem('access_token'))
    if (!token) throw new Error('Could not find access token')

    console.log('Token grabbed. Setting up robust API data for UI tests...')

    // Create Farm/Supervisor IDs - assuming typical dev DB IDs, adjust if needed.
    // We'll create a log, submit it, reject it, and then test the REOPEN and TIMELINE flows in the UI.
    const logPayload = {
      log_date: new Date().toISOString().split('T')[0],
      farm: 1, // typically 1 or 2
      status: 'SUBMITTED',
      notes: 'Test Perennial Log via API',
    }

    const apiUrl = 'http://localhost:8000/api/v1/daily-logs/'
    const response = await page.evaluate(
      async ({ url, token, payload }) => {
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        })
        return res.json()
      },
      { url: apiUrl, token, payload: logPayload },
    )

    const logId = response.id
    console.log(`Created Log ID: ${logId}`)

    // Create an Activity for the log to prevent empty log errors
    const actPayload = {
      log: logId,
      task: 1,
      location: 1,
      crop: 1,
      cost_total: 1500,
      worker_count: 2,
    }
    await page.evaluate(
      async ({ url, token, payload }) => {
        await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        })
      },
      { url: 'http://localhost:8000/api/v1/activities/', token, payload: actPayload },
    )

    // Reject the Log via API
    console.log(`Rejecting Log ID: ${logId}`)
    await page.evaluate(
      async ({ url, token }) => {
        await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ reason: 'عذراً، يجب إضافة التكاليف للمحاصيل المعمرة بدقة' }),
        })
      },
      { url: `${apiUrl}${logId}/reject/`, token },
    )

    console.log('2. Opening Log History as Admin...')
    await page.goto('http://localhost:5173/history')
    await page.waitForTimeout(2000)

    // Find the rejected log and click it
    await page.click(`.cursor-pointer:has-text("سجل ${logPayload.log_date}") >> nth=0`)
    await page.waitForTimeout(1000)

    // Check Timeline UI
    console.log('Taking screenshot of Timeline...')
    const timelinePath = path.join(artifactDir, `timeline_verification_${Date.now()}.png`)
    await page.screenshot({ path: timelinePath })
    console.log(`Screenshot saved to ${timelinePath}`)

    // Reopen Log
    console.log('3. Reopening the Rejected Log...')
    await page.click('button:has-text("إعادة فتح")')
    await page.waitForTimeout(3000) // giving it time to route and mount DailyLog

    // Check Sticky Note UI
    console.log('Taking screenshot of Sticky Note...')
    const stickyPath = path.join(artifactDir, `sticky_note_verification_${Date.now()}.png`)
    await page.screenshot({ path: stickyPath })
    console.log(`Screenshot saved to ${stickyPath}`)

    console.log('✅ Flow Testing Completed Successfully')
  } catch (error) {
    console.error('Test Failed:', error)
    process.exit(1)
  } finally {
    await browser.close()
  }
})()
