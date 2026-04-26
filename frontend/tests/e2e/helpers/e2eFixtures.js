/**
 * [AGRI-GUARDIAN] E2E Shared Fixtures & Constants
 * Used across all spec files for consistent test data references.
 */

// ─── Route Definitions ──────────────────────────────────────────────────────
export const ROUTES = {
  // Core (Simple Mode)
  DASHBOARD: '/dashboard',
  DAILY_LOG: '/daily-log',
  DAILY_LOG_HISTORY: '/daily-log-history',
  REPORTS: '/reports',
  CROP_PLANS: '/crop-plans',
  CROPS: '/crops',
  CROP_CARDS: '/crop-cards',
  TREE_CENSUS: '/tree-census',

  // Finance (Strict Mode)
  FINANCE: '/finance',
  FINANCE_LEDGER: '/finance/ledger',
  FINANCE_FISCAL_YEARS: '/finance/fiscal-years',
  FINANCE_FISCAL_PERIODS: '/finance/fiscal-periods',
  FINANCE_EXPENSES: '/finance/expenses',
  FINANCE_TREASURY: '/finance/treasury',
  FINANCE_MAKER_CHECKER: '/finance/maker-checker',
  FINANCE_VARIANCE: '/finance/variance-analysis',
  FINANCE_CLOSING: '/finance/closing',
  FINANCE_PAYROLL: '/finance/payroll-settlement',
  FINANCE_ADVANCED_REPORTS: '/finance/advanced-reports',

  // Sales (Strict Mode)
  SALES: '/sales',

  // Inventory (Strict Mode)
  STOCK_MANAGEMENT: '/stock-management',
  MATERIALS_CATALOG: '/materials-catalog',

  // HR
  EMPLOYEES: '/employees',
  HR_ADVANCES: '/hr/advances',
  HR_TIMESHEETS: '/hr/timesheets',
  HR_PRODUCTIVITY: '/hr/worker-productivity',

  // Commercial (Strict Mode)
  COMMERCIAL: '/commercial',
  PREDICTIVE_VARIANCE: '/predictive-variance',
  SOLAR_MONITOR: '/solar-monitor',

  // Settings & Admin
  FARMS: '/farms',
  SETTINGS: '/settings',
  AUDIT: '/audit',
  APPROVAL_INBOX: '/approvals',
  HARVEST_PRODUCTS: '/harvest-products',
  QR_SCANNER: '/qr-scanner',
  WELLS: '/wells',
}

// ─── Simple-mode pages (always accessible) ──────────────────────────────────
export const SIMPLE_PAGES = [
  ROUTES.DASHBOARD,
  ROUTES.DAILY_LOG,
  ROUTES.DAILY_LOG_HISTORY,
  ROUTES.REPORTS,
  ROUTES.CROP_PLANS,
  ROUTES.CROPS,
  ROUTES.CROP_CARDS,
  ROUTES.TREE_CENSUS,
]

// ─── Strict-mode pages (only in ERP mode) ───────────────────────────────────
export const STRICT_PAGES = [
  ROUTES.SALES,
  ROUTES.FINANCE,
  ROUTES.EMPLOYEES,
  ROUTES.HARVEST_PRODUCTS,
  ROUTES.STOCK_MANAGEMENT,
  ROUTES.MATERIALS_CATALOG,
  ROUTES.COMMERCIAL,
  ROUTES.PREDICTIVE_VARIANCE,
  ROUTES.QR_SCANNER,
  ROUTES.SOLAR_MONITOR,
]

// ─── Test Data Constants ────────────────────────────────────────────────────
export const TEST_AMOUNTS = {
  SMALL: '1000.0000',
  MEDIUM: '25000.0000',
  LARGE: '150000.0000',
  SALARY: '5000.0000',
  ADVANCE: '2000.0000',
}

// ─── AGENTS.md Account Codes ────────────────────────────────────────────────
export const ACCOUNT_CODES = {
  CASH: '1000-CASH',
  INVENTORY: '1200-INVENTORY',
  WIP: '1400-WIP',
  PAYABLE_SALARIES: '2000-PAY-SAL',
  REVENUE: '4000-REVENUE',
  MATERIAL: '5100-MATERIAL',
  LABOR: '5200-LABOR',
  MACHINERY: '5300-MACHINERY',
  OVERHEAD: '5400-OVERHEAD',
  COGS: '5500-COGS',
}

// ─── Selectors ──────────────────────────────────────────────────────────────
export const SEL = {
  // Common
  FARM_SELECTOR: '[data-testid="farm-selector-button"]',
  SUBMIT_BTN: 'button[type="submit"]',
  TOAST: '.go3958317564, .go2072408551, [role="status"]',
  LOADING: '[data-testid="loading-spinner"], .animate-spin',
  EMPTY_STATE: '[data-testid="empty-state"]',

  // DailyLog
  LOG_DATE: '#daily-log-date, input[type="date"]',
  LOG_FARM: '#daily-log-farm',

  // Finance
  LEDGER_TABLE: '[data-testid="ledger-table"]',
  FISCAL_BADGE: '[data-testid^="fiscal-status-"]',
  MAKER_CHECKER_LIST: '[data-testid="pending-entries-list"]',

  // Sales
  SALES_GRID: '[data-testid="sales-main-grid"]',
  INVOICE_TABLE: '[data-testid="invoice-table"]',
}

// ─── Utility: wait for API response ─────────────────────────────────────────
export async function waitForApi(page, urlPattern, timeout = 10000) {
  return page.waitForResponse((res) => res.url().includes(urlPattern) && res.status() < 400, {
    timeout,
  })
}

// ─── Utility: skip if not strict mode ───────────────────────────────────────
export function skipIfSimple(test, strictErpMode) {
  if (!strictErpMode) {
    test.skip(true, 'Skipped: requires Strict ERP mode')
  }
}

// ─── Utility: assert RTL ────────────────────────────────────────────────────
export async function assertRTL(page, expect) {
  const dir = await page.getAttribute('html', 'dir')
  expect(dir).toBe('rtl')
}

// ─── Utility: assert no console errors ──────────────────────────────────────
export function collectConsoleErrors(page) {
  const errors = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text())
  })
  return errors
}
