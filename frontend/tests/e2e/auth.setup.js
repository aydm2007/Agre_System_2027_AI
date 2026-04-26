/**
 * Global Auth Setup — Playwright Best Practice
 * Creates a shared authenticated state (storageState) that all tests can reuse.
 * This avoids repeating the login flow in every test file.
 * @see https://playwright.dev/docs/auth
 */
import { test as setup, expect } from '@playwright/test'
import fs from 'fs'
import path from 'path'
import { BASE_URL, fetchTokens } from './helpers/e2eAuth'

const artifactRoot = process.env.PLAYWRIGHT_ARTIFACT_ROOT
  ? path.resolve(process.env.PLAYWRIGHT_ARTIFACT_ROOT)
  : path.join(import.meta.dirname, '..', '..', '.pw-results')
const authFile = path.join(artifactRoot, '.auth', 'user.json')
fs.mkdirSync(path.dirname(authFile), { recursive: true })
setup.setTimeout(180000)

setup('authenticate', async ({ page, request }) => {
  const { access, refresh } = await fetchTokens(request)
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 180000 })
  await page.evaluate(
    ({ accessToken, refreshToken }) => {
      window.localStorage.setItem('accessToken', accessToken)
      window.localStorage.setItem('refreshToken', refreshToken)
    },
    { accessToken: access, refreshToken: refresh },
  )
  await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded', timeout: 180000 })

  for (let attempt = 0; attempt < 3; attempt += 1) {
    const loginVisible = await page.getByTestId('login-username').isVisible().catch(() => false)
    if (!loginVisible) break
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded', timeout: 180000 })
    await page.waitForTimeout(1000)
  }

  await expect(page).not.toHaveURL(/\/login(\/|$)/, { timeout: 30000 })
  await page.locator('#root').waitFor({ state: 'attached', timeout: 30000 })
  await expect(page.locator('#root')).toBeVisible({ timeout: 30000 })

  await page.context().storageState({ path: authFile })
})
