import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureLoggedIn,
  ensureFarmSelected,
  fetchSystemMode,
  fetchCurrentUser,
} from './helpers/e2eAuth'

const SIMPLE_PAGES = [
  '/dashboard',
  '/daily-log',
  '/daily-log-history',
  '/reports',
  '/crop-plans',
  '/crops',
  '/crop-cards',
  '/tree-census',
]

const FINANCIAL_STRICT_PAGES = [
  '/sales',
  '/finance',
  '/employees',
  '/commercial',
  '/harvest-products',
  '/predictive-variance',
]

const NON_FINANCIAL_STRICT_PAGES = [
  '/stock-management',
  '/materials-catalog',
  '/qr-scanner',
  '/solar-monitor',
]

test.describe.configure({ mode: 'serial' })

let strictErpMode = false
let currentUser = null

const blockedRouteRegex = /\/(dashboard|login)(\/|$)/

const isFinanceLeader = (profile) => {
  const roles = Array.isArray(profile?.farms)
    ? profile.farms.map((farm) => String(farm?.role || ''))
    : []
  return roles.some(
    (role) =>
      role.includes('المدير المالي') ||
      role.includes('مدير النظام') ||
      role.toLowerCase().includes('finance'),
  )
}

test.beforeAll(async ({ request }) => {
  const modeBody = await fetchSystemMode(request)
  currentUser = await fetchCurrentUser(request)
  strictErpMode = Boolean(modeBody?.strict_erp_mode)
})

test('simple pages should load in all modes', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)
  await page.goto(`${BASE_URL}/dashboard`)
  await expect(page.getByTestId('farm-selector-button')).toHaveCount(0)

  for (const route of SIMPLE_PAGES) {
    await page.goto(`${BASE_URL}${route}`)
    await expect(page).toHaveURL(new RegExp(route.replace('/', '\\/')))
  }
})

test('strict pages should respect mode contract', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  const canAccessFinancialRoutes =
    Boolean(currentUser?.is_superuser) ||
    isFinanceLeader(currentUser) ||
    (strictErpMode && Boolean(currentUser?.is_admin))

  const canAccessNonFinancialStrictRoutes =
    strictErpMode && (Boolean(currentUser?.is_admin) || Boolean(currentUser?.is_superuser))

  for (const route of FINANCIAL_STRICT_PAGES) {
    await page.goto(`${BASE_URL}${route}`)
    if (canAccessFinancialRoutes) {
      await expect(page).toHaveURL(new RegExp(route.replace('/', '\\/')))
    } else {
      await expect(page).toHaveURL(blockedRouteRegex)
    }
  }

  for (const route of NON_FINANCIAL_STRICT_PAGES) {
    await page.goto(`${BASE_URL}${route}`)
    if (canAccessNonFinancialStrictRoutes) {
      await expect(page).toHaveURL(new RegExp(route.replace('/', '\\/')))
    } else {
      await expect(page).toHaveURL(blockedRouteRegex)
    }
  }
})
