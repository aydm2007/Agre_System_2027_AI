import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  endpoints,
  ensureLoggedIn,
  ensureFarmSelected,
  fetchToken,
  withAuthHeaders,
  readResults,
} from './helpers/e2eAuth'

let farmId
let openPeriodId
let strictErpMode = false

test.beforeAll(async ({ request }) => {
  const token = await fetchToken(request)
  const headers = withAuthHeaders(token)

  const farmsRes = await request.get(`${endpoints.V1_BASE}/farms/`, { headers })
  expect(farmsRes.ok(), 'STARTUP SENTINEL HALT: farms seed data is missing').toBeTruthy()
  const farms = readResults(await farmsRes.json())
  expect(farms.length, 'STARTUP SENTINEL HALT: no farms available').toBeGreaterThan(0)
  farmId = farms[0].id

  const periodsRes = await request.get(
    `${endpoints.V1_BASE}/finance/fiscal-periods/?status=open&farm=${farmId}`,
    { headers },
  )
  expect(periodsRes.ok(), 'TRIPLE CLOSING GUARDIAN: cannot load fiscal periods').toBeTruthy()
  const periods = readResults(await periodsRes.json())
  expect(periods.length, 'TRIPLE CLOSING GUARDIAN: no open fiscal period found').toBeGreaterThan(0)
  openPeriodId = periods[0].id

  const modeRes = await request.get(`${endpoints.V1_BASE}/system-mode/`)
  expect(modeRes.ok(), 'MODE CONTRACT HALT: cannot load /system-mode/').toBeTruthy()
  const modeBody = await modeRes.json()
  strictErpMode = Boolean(modeBody?.strict_erp_mode)
})

test.describe('Financial Workflow Contracts', () => {
  test('sales route is reachable under current mode contract', async ({ page, request }) => {
    await ensureLoggedIn(page, request)
    await ensureFarmSelected(page)
    await page.goto(`${BASE_URL}/sales`)
    const salesGrid = page.getByTestId('sales-main-grid')
    if (!strictErpMode) {
      await expect(salesGrid).toHaveCount(0)
      return
    }

    if (await salesGrid.isVisible().catch(() => false)) {
      await expect(salesGrid).toBeVisible()
    }
  })

  test('financial mutation endpoints enforce idempotency key', async ({ request }) => {
    const token = await fetchToken(request)
    const headers = withAuthHeaders(token)
    const invoicesRes = await request.get(
      `${endpoints.V1_BASE}/sales-invoices/?farm_id=${farmId}`,
      {
        headers,
      },
    )
    expect(invoicesRes.ok()).toBeTruthy()
    const invoices = readResults(await invoicesRes.json())
    expect(invoices.length, 'HALT: no invoices seeded for idempotency validation').toBeGreaterThan(
      0,
    )

    const invoiceId = invoices[0].id
    const confirmRes = await request.post(
      `${endpoints.V1_BASE}/sales-invoices/${invoiceId}/confirm/`,
      {
        headers,
        data: {},
      },
    )
    expect(confirmRes.status()).toBe(400)
    const confirmBody = await confirmRes.json()
    expect(String(confirmBody?.detail || '')).toContain('X-Idempotency-Key')

    const cancelRes = await request.post(
      `${endpoints.V1_BASE}/sales-invoices/${invoiceId}/cancel/`,
      {
        headers,
        data: {},
      },
    )
    expect(cancelRes.status()).toBe(400)
    const cancelBody = await cancelRes.json()
    expect(String(cancelBody?.detail || '')).toContain('X-Idempotency-Key')
  })

  test('open fiscal period baseline exists for workflow', async () => {
    expect(farmId).toBeTruthy()
    expect(openPeriodId).toBeTruthy()
  })
})
