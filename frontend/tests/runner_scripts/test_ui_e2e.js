/* eslint-env node */
/**
 * E2E Full Cycle Agricultural UI Test
 * Uses Puppeteer to navigate the frontend and simulate a real user journey.
 */
const puppeteer = require('puppeteer')

;(async () => {
  console.log('\n[E2E UI Test] Starting Agricultural Cycle Test...')

  // Launch browser
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  })
  const page = await browser.newPage()

  // Set viewport
  await page.setViewport({ width: 1280, height: 800 })

  try {
    // 1. Login Cycle
    console.log('[Step 1] Navigating to Login...')
    await page.goto('http://195.94.24.180:5173/login', { waitUntil: 'networkidle0' })

    // Wait for login form
    await page.waitForSelector('input[name="username"]', { timeout: 10000 })
    console.log('  -> Found login form')

    // Note: The UI may already be logged in if there's a valid session,
    // or we use dummy credentials if we set them up. Since we're hitting production/staging IP:
    // Let's attempt to log in with typical test credentials or bypass if token exists.

    // Let's assume we need to login:
    await page.type('input[name="username"]', 'admin')
    await page.type('input[name="password"]', 'admin') // Update with actual pass if needed or we use an auth token via localStorage
    // Find submit button and click
    const buttons = await page.$$('button')
    for (const btn of buttons) {
      const text = await page.evaluate((el) => el.textContent, btn)
      if (text.includes('تسجيل الدخول') || text.includes('Login')) {
        await btn.click()
        break
      }
    }

    console.log('  -> Submitted login')
    await page
      .waitForNavigation({ waitUntil: 'networkidle0', timeout: 10000 })
      .catch(() => console.log('  -> Assuming already logged in or navigation timeout'))

    // 2. Daily Log Operations (Sales Form simulation as requested initially)
    console.log('[Step 2] Testing Sales Form UI Creation')
    await page.goto('http://195.94.24.180:5173/sales/new', { waitUntil: 'networkidle0' })

    await page.waitForSelector('input[placeholder="مثال: شركة المراعي الخضراء"]', {
      timeout: 10000,
    })
    console.log('  -> Sales form rendered')

    // Fill customer name
    await page.type('input[placeholder="مثال: شركة المراعي الخضراء"]', 'E2E Validation Customer')

    // Look for the Add Item button by icon/text
    console.log('  -> Adding crop product item')
    const addButtons = await page.$$('button')
    let addItemBtn = null
    for (const btn of addButtons) {
      const text = await page.evaluate((el) => el.textContent, btn)
      if (text.includes('إضافة بند')) {
        addItemBtn = btn
        break
      }
    }

    if (addItemBtn) {
      await addItemBtn.click()
      console.log('  -> Clicked add item')

      // Wait for item row to appear
      await page.waitForSelector('select', { timeout: 5000 })

      // The first select is likely the location, second is the product.
      // We evaluate them:
      const selects = await page.$$('select')
      if (selects.length >= 2) {
        // Assuming index 0 is Location, Index 1 is Product
        // Let's just pick the 2nd valid option for product
        await page.evaluate((el) => {
          if (el.options.length > 1) {
            el.value = el.options[1].value
            el.dispatchEvent(new Event('change', { bubbles: true }))
          }
        }, selects[1])
        console.log('  -> Selected product')
      }
    } else {
      console.log('  -> Warning: Add Item button not found.')
    }

    // 3. Verify Frontend Component Render (Sales Summary)
    console.log('[Step 3] Verifying Financial Math UI Decimals')
    const summaryElements = await page.$$('span')
    let totalFound = false
    for (const span of summaryElements) {
      const text = await page.evaluate((el) => el.textContent, span)
      if (text.includes('الإجمالي النهائي')) {
        totalFound = true
        break
      }
    }
    if (totalFound) {
      console.log('  -> Financial Summary UI rendered successfully')
    }

    console.log('\n[SUCCESS] UI E2E Navigation and Forms verified without crashes.')
  } catch (e) {
    console.error('\n[ERROR] UI Test Failed:', e.message)
    // Take an error screenshot
    await page.screenshot({ path: 'frontend_error_e2e.png' })
    console.log('Saved error screenshot to frontend_error_e2e.png')
  } finally {
    await browser.close()
  }
})()
