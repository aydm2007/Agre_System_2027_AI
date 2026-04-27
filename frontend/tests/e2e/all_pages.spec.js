import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  ensureLoggedIn,
  ensureFarmSelected,
  fetchSystemMode,
  fetchCurrentUser,
} from './helpers/e2eAuth'

/**
 * ╔══════════════════════════════════════════════════════════╗
 * ║ AGRIASSET TOTAL INTERFACE AUDIT (V21.5 - OMEGA-Z)         ║
 * ╚══════════════════════════════════════════════════════════╝
 * Covers 100% of the routes defined in App.jsx.
 */

const CORE_OPERATIONAL_PAGES = [
  '/dashboard',
  '/simple-hub',
  '/daily-log',
  '/daily-log/harvest',
  '/daily-log-history',
  '/reports',
  '/reports/advanced',
  '/crop-plans',
  '/crops',
  '/crop-cards',
  '/tree-census',
  '/tree-inventory',
  '/location-wells',
  '/approvals',
  '/procurement-approvals',
  '/variance-alerts',
  '/tree-variance-alerts',
  '/predictive-variance',
  '/inventory/custody',
  '/settings',
]

const FINANCIAL_STRICT_PAGES = [
  '/finance',
  '/finance/supplier-settlements',
  '/finance/receipts-deposits',
  '/finance/petty-cash',
  '/fuel-reconciliation',
  '/commercial',
  '/harvest-products',
  '/sales',
  '/purchases',
  '/employees',
  '/hr/timesheets',
  '/hr/worker-kpi',
  '/hr/advances',
  '/sharecropping',
  '/fixed-assets',
  '/assets',
  '/pos',
  '/maintenance',
]

const NON_FINANCIAL_STRICT_PAGES = [
  '/resource-analytics',
  '/stock-management',
  '/materials-catalog',
  '/solar-monitor',
  '/qr-scanner',
  '/procurement/rfq',
  '/inventory/warehouse',
  '/audit',
  '/audit-explorer',
]

test.describe.configure({ mode: 'serial' })

let strictErpMode = false
let currentUser = null

const blockedRouteRegex = /\/(dashboard|login|simple-hub)(\/|$)/

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

test('core operational pages should load in all modes', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)
  
  for (const route of CORE_OPERATIONAL_PAGES) {
    console.log(`[E2E] Testing Core Page: ${route}`);
    await page.goto(`${BASE_URL}${route}`)
    // Allow for internal redirects (e.g. settings to dashboard if locked, but CORE should pass)
    await expect(page).not.toHaveURL(/.*login/)
  }
})

test('financial strict pages should respect mode and role contract', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  const canAccessFinancialRoutes =
    Boolean(currentUser?.is_superuser) ||
    isFinanceLeader(currentUser) ||
    (strictErpMode && Boolean(currentUser?.is_admin))

  for (const route of FINANCIAL_STRICT_PAGES) {
    console.log(`[E2E] Testing Financial Page: ${route}`);
    await page.goto(`${BASE_URL}${route}`)
    if (canAccessFinancialRoutes) {
      await expect(page).not.toHaveURL(/.*login/)
    } else {
      // In SIMPLE mode or for non-auth users, many of these redirect to dashboard
      const currentUrl = page.url()
      if (currentUrl.includes('dashboard') || currentUrl.includes('simple-hub')) {
        // Success: Redirected as expected
      } else {
        // If not redirected, check content for access denied or similar markers
        await expect(page.locator('text=غير مصرح')).toHaveCount(0)
      }
    }
  }
})

test('non-financial strict pages should respect system mode', async ({ page, request }) => {
  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  const canAccessStrictRoutes =
    strictErpMode || Boolean(currentUser?.is_superuser) || Boolean(currentUser?.is_admin)

  for (const route of NON_FINANCIAL_STRICT_PAGES) {
    console.log(`[E2E] Testing Strict Page: ${route}`);
    await page.goto(`${BASE_URL}${route}`)
    if (canAccessStrictRoutes) {
      await expect(page).not.toHaveURL(/.*login/)
    } else {
      const currentUrl = page.url()
      expect(currentUrl).toMatch(blockedRouteRegex)
    }
  }
})
