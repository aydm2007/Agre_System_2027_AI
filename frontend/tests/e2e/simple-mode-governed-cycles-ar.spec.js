import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  endpoints,
  ensureFarmSelected,
  ensureLoggedIn,
  fetchToken,
  resolveAccessibleFarmId,
  withAuthHeaders,
} from './helpers/e2eAuth'

test.describe.configure({ mode: 'serial' })
test.setTimeout(180000)

let farmId

async function patchFarmSettings(request, token, nextValues) {
  const listResponse = await request.get(`${endpoints.V1_BASE}/farm-settings/?farm=${farmId}`, {
    headers: withAuthHeaders(token),
  })
  if (!listResponse.ok()) {
    throw new Error(`HALT: cannot load farm settings for SIMPLE cycle audit (${listResponse.status()})`)
  }
  const payload = await listResponse.json()
  const settings = payload?.results?.[0]
  if (!settings?.id) {
    throw new Error('HALT: no FarmSettings row available for SIMPLE cycle audit')
  }
  const patchResponse = await request.patch(`${endpoints.V1_BASE}/farm-settings/${settings.id}/`, {
    headers: withAuthHeaders(token),
    data: {
      mode: 'SIMPLE',
      cost_visibility: 'ratios_only',
      treasury_visibility: 'hidden',
      fixed_asset_mode: 'tracking_only',
      contract_mode: 'operational_only',
      variance_behavior: 'warn',
      enable_petty_cash: true,
      enable_sharecropping: true,
      show_finance_in_simple: false,
      show_stock_in_simple: false,
      show_employees_in_simple: false,
      ...nextValues,
    },
  })
  if (!patchResponse.ok()) {
    throw new Error(`HALT: cannot patch farm settings for SIMPLE cycle audit (${patchResponse.status()})`)
  }
}

async function expectSimpleSurface(page, config) {
  await page.goto(`${BASE_URL}${config.path}`)
  await expect(page.getByTestId(config.bannerTestId)).toContainText(config.bannerText)
  const table = page.getByTestId(config.tableTestId)
  if (await table.isVisible().catch(() => false)) {
    await expect(table).toBeVisible()
  } else if (config.emptyStateText) {
    await expect(page.getByText(config.emptyStateText)).toBeVisible()
  } else {
    await expect(table).toBeVisible()
  }
  if (config.hiddenColumnTestId) {
    await expect(page.getByTestId(config.hiddenColumnTestId)).toHaveCount(0)
  }
  if (config.smartCardTestId && config.smartCardText) {
    await expect(page.getByTestId(config.smartCardTestId)).toContainText(config.smartCardText)
  }
}

test.beforeAll(async ({ request }) => {
  farmId = await resolveAccessibleFarmId(request)
})

test('تدقيق عربي شامل للدورات الحاكمة في الوضع المبسط', async ({ page, request }) => {
  const token = await fetchToken(request)
  await patchFarmSettings(request, token)

  await ensureLoggedIn(page, request)
  await ensureFarmSelected(page)

  await expectSimpleSurface(page, {
    path: '/finance/receipts-deposits',
    bannerTestId: 'receipts-deposit-policy-banner',
    bannerText: 'operations_only',
    tableTestId: 'receipts-deposit-invoices-table',
    hiddenColumnTestId: 'receipts-deposit-amount-column',
  })

  await expectSimpleSurface(page, {
    path: '/finance/petty-cash',
    bannerTestId: 'petty-cash-visibility-banner',
    bannerText: 'operations_only',
    tableTestId: 'petty-cash-requests-table',
    hiddenColumnTestId: 'petty-cash-cost-center-column',
    emptyStateText: 'لا توجد طلبات سلفة نثرية',
  })
  await expect(page.getByTestId('petty-cash-visibility-banner')).toContainText('ratios_only')

  await expectSimpleSurface(page, {
    path: '/finance/supplier-settlements',
    bannerTestId: 'supplier-settlement-policy-banner',
    bannerText: 'الوضع المبسط',
    tableTestId: 'supplier-settlement-table',
    hiddenColumnTestId: 'supplier-settlement-amount-column',
  })

  await expectSimpleSurface(page, {
    path: '/fixed-assets',
    bannerTestId: 'fixed-assets-policy-banner',
    bannerText: 'SIMPLE',
    tableTestId: 'fixed-assets-table',
    hiddenColumnTestId: 'fixed-assets-amount-column',
  })

  await expectSimpleSurface(page, {
    path: '/fuel-reconciliation',
    bannerTestId: 'fuel-reconciliation-policy-banner',
    bannerText: 'SIMPLE',
    tableTestId: 'fuel-reconciliation-table',
    hiddenColumnTestId: 'fuel-reconciliation-amount-column',
  })

  await expectSimpleSurface(page, {
    path: '/sharecropping',
    bannerTestId: 'contract-operations-policy-banner',
    bannerText: 'operational_only',
    tableTestId: 'contract-operations-table',
    hiddenColumnTestId: 'contract-operations-amount-column',
  })
})
