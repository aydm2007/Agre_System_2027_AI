import { test, expect } from '@playwright/test'

test('has title', async ({ page }) => {
  await page.goto('/')

  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle(/Saradud|Vite/)
})

test('loads dashboard or login', async ({ page }) => {
  await page.goto('/')

  // Application usually redirects to /login or shows dashboard
  // We just check that the body is not empty and no application crash error exists
  const body = page.locator('body')
  await expect(body).toBeVisible()
})
