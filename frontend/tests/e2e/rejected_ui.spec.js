import { test, expect } from '@playwright/test'
import path from 'path'
import * as fs from 'fs'

test('Verify Rejected Log Sticky Note and Timeline', async ({ page }) => {
  const artifactDir =
    'C:\\Users\\ibrahim\\.gemini\\antigravity\\brain\\d8992235-e4d2-4a0d-8724-5e4bd7519c3b'

  // 1. Log in
  console.log('Logging in as admin...')
  await page.goto('http://localhost:5173/login')
  await page.fill('input[type="text"]', 'admin')
  await page.fill('input[type="password"]', 'ADMIN123')
  await page.click('button[type="submit"]')
  await page.waitForTimeout(2000)

  // 2. Setting up data via API to skip manual UI flakiness
  const token = await page.evaluate(() => localStorage.getItem('access_token'))
  expect(token).toBeTruthy()

  const logPayload = {
    log_date: new Date().toISOString().split('T')[0],
    farm: 1,
    status: 'SUBMITTED',
    notes: 'Test Perennial Log via API tests',
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

  // Reject
  const rejectReason = 'عذراً، يجب إضافة التكاليف للمحاصيل المعمرة بدقة'
  await page.evaluate(
    async ({ url, token, reason }) => {
      await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ reason }),
      })
    },
    { url: `${apiUrl}${logId}/reject/`, token, reason: rejectReason },
  )

  // 3. Verify Timeline in History
  console.log('Opening History...')
  await page.goto('http://localhost:5173/history')
  await page.waitForTimeout(2000)

  // Ensure the history list is populated, then click the correct log
  await page.waitForSelector('.cursor-pointer')
  await page.click(`.cursor-pointer:has-text("سجل ${logPayload.log_date}") >> nth=0`)
  await page.waitForTimeout(1000) // Wait for details panel

  // Timeline Check
  await expect(page.locator('h4:has-text("التتبع الزمني")')).toBeVisible()
  const timelinePath = path.join(artifactDir, `timeline_verification_${Date.now()}.png`)
  await page.screenshot({ path: timelinePath })
  console.log(`Timeline screenshot saved to ${timelinePath}`)

  // 4. Verify Sticky Note in Reopen
  console.log('Reopening Log...')
  await page.click('button:has-text("إعادة فتح وتعديل")')
  await page.waitForTimeout(3000) // wait for routing and data hydration

  await expect(page.locator('.bg-red-50')).toContainText(rejectReason)
  const stickyPath = path.join(artifactDir, `sticky_note_verification_${Date.now()}.png`)
  await page.screenshot({ path: stickyPath })
  console.log(`Sticky Note screenshot saved to ${stickyPath}`)
})
