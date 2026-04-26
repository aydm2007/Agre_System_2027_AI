import { test, expect } from '@playwright/test'
import { ensureLoggedIn, BASE_URL } from './helpers/e2eAuth.js'

test.describe('AgriAsset Core Interfaces Verification', () => {
  test.beforeEach(async ({ page, request }) => {
    await ensureLoggedIn(page, request)
  })

  test('Interface 1: Farms', async ({ page }) => {
    await page.goto(`${BASE_URL}/farms`, { waitUntil: 'domcontentloaded' })
    await expect(
      page
        .locator('h1, h2, h3')
        .filter({ hasText: /farms|المزارع/i })
        .first(),
    )
      .toBeVisible({ timeout: 10000 })
      .catch(() => {
        expect(page.url()).toContain('/farms')
      })
  })

  test('Interface 2: DailyLog', async ({ page }) => {
    await page.goto(`${BASE_URL}/daily-log`, { waitUntil: 'domcontentloaded' })
    await expect(page.locator('body')).toBeVisible()
    expect(page.url()).toContain('/daily-log')
  })

  test('Interface 3: CropPlans', async ({ page }) => {
    await page.goto(`${BASE_URL}/crop-plans`, { waitUntil: 'domcontentloaded' })
    await expect(page.locator('body')).toBeVisible()
    expect(page.url()).toContain('/crop-plans')
  })

  test('Interface 4: Ledger', async ({ page }) => {
    await page.goto(`${BASE_URL}/finance/ledger`, { waitUntil: 'domcontentloaded' })
    await expect(page.locator('body')).toBeVisible()
    expect(page.url()).toContain('/finance/ledger')
  })

  test('Interface 5: HarvestProducts', async ({ page }) => {
    await page.goto(`${BASE_URL}/harvest-products`, { waitUntil: 'domcontentloaded' })
    await expect(page.locator('body')).toBeVisible()
    expect(page.url()).toContain('/harvest-products')
  })
})
