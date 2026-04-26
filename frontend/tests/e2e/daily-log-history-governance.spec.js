import { test, expect } from '@playwright/test'
import { BASE_URL, ensureLoggedIn } from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })

async function mockHistoryApis(page, logPayload) {
  await page.route('**/api/v1/auth/users/me/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user: { id: 1, username: 'ibrahim' },
        farms: [{ farm_id: 1, role: 'manager' }],
        permissions: [],
        groups: ['Manager'],
        is_admin: true,
        is_superuser: false,
      }),
    })
  })

  await page.route('**/api/v1/daily-logs/**', async (route) => {
    const request = route.request()
    if (request.method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ results: [logPayload] }),
      })
      return
    }
    await route.continue()
  })

  await page.route('**/api/v1/activities/**', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ results: [] }),
      })
      return
    }
    await route.continue()
  })
}

test('WARNING variance requires note before approval button is enabled', async ({
  page,
  request,
}) => {
  await mockHistoryApis(page, {
    id: 9101,
    farm: 1,
    farm_name: 'Ø³Ø±Ø¯ÙˆØ¯',
    log_date: '2026-02-27',
    status: 'submitted',
    variance_status: 'WARNING',
    variance_note: '',
    variance_approved_by: null,
  })

  await ensureLoggedIn(page, request)
  await page.goto(`${BASE_URL}/daily-log-history`)

  await page.locator('button', { hasText: '2026-02-27' }).first().click()
  await expect(page.getByTestId('dailylog-approve-button')).toBeDisabled()
  await expect(page.getByTestId('dailylog-warning-note-button')).toBeVisible()
})

test('CRITICAL variance requires manager variance approval first', async ({ page, request }) => {
  await mockHistoryApis(page, {
    id: 9102,
    farm: 1,
    farm_name: 'Ø³Ø±Ø¯ÙˆØ¯',
    log_date: '2026-02-27',
    status: 'submitted',
    variance_status: 'CRITICAL',
    variance_note: '',
    variance_approved_by: null,
  })

  await ensureLoggedIn(page, request)
  await page.goto(`${BASE_URL}/daily-log-history`)

  await page.locator('button', { hasText: '2026-02-27' }).first().click()
  await expect(page.getByTestId('dailylog-approve-button')).toBeDisabled()
  await expect(page.getByTestId('dailylog-approve-variance-button')).toBeVisible()
})
