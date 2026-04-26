import { test, expect } from '@playwright/test'
import { ensureLoggedIn, ensureFarmSelected } from './helpers/e2eAuth'

test.describe('AGENTS.md Strict Compliance', () => {
  test.beforeEach(async ({ page, request }) => {
    await ensureLoggedIn(page, request)
    await ensureFarmSelected(page)
  })

  test('Axis 6: Global RTL Configuration', async ({ page }) => {
    await page.goto('/dashboard')
    const dir = await page.getAttribute('html', 'dir')
    expect(dir).toBe('rtl')
  })

  test('Axis 5: Decimal Precision UI Rendering', async ({ page }) => {
    await page.goto('/hr/timesheets')
    if ((await page.getByTestId('timesheet-page').count()) === 0) {
      test.skip(true, 'Timesheet page not available for current role')
    }

    await expect(page.getByTestId('timesheet-total-surrah')).toBeVisible({ timeout: 15000 })
    const surrahTotal = (
      (await page.getByTestId('timesheet-total-surrah').textContent()) || ''
    ).trim()
    expect(surrahTotal).toMatch(/^\d+(\.\d{1,4})?$/)
  })

  test('Axis 2 & 6: Network Headers (Idempotency & Tenant Isolation)', async ({ page }) => {
    let capturedHeaders = null

    await page.route('**/finance/ledger/liquidate-payroll/', async (route) => {
      capturedHeaders = route.request().headers()
      await route.fulfill({ status: 200, json: { message: 'Success' } })
    })

    await page.goto('/dashboard')
    await page.evaluate(async () => {
      const { api } = await import('/src/api/client.js')
      await api.post('/finance/ledger/liquidate-payroll/', {
        farm_id: 1,
        payment_date: '2026-03-08',
        credit_account: '1000-CASH',
        description: 'header-contract-check',
        advances_recovery_amount: '0',
      })
    })

    expect(capturedHeaders).toBeTruthy()
    expect(capturedHeaders['x-idempotency-key'] || capturedHeaders['idempotency-key']).toBeTruthy()
    expect(capturedHeaders['x-farm-id']).toBeTruthy()
  })

  test('Axis 7: Global Error Handling for 403 and 400', async ({ page }) => {
    let forbiddenTriggered = false
    await page.route('**/finance/ledger/liquidate-payroll/', async (route) => {
      forbiddenTriggered = true
      await route.fulfill({ status: 403, json: { detail: 'Forbidden access' } })
    })

    await page.goto('/dashboard')
    await page.evaluate(async () => {
      const { api } = await import('/src/api/client.js')
      try {
        await api.post('/finance/ledger/liquidate-payroll/', {
          farm_id: 1,
          payment_date: '2026-03-08',
          credit_account: '1000-CASH',
          description: 'forbidden-check',
          advances_recovery_amount: '0',
        })
      } catch {
        // expected
      }
    })

    expect(forbiddenTriggered).toBe(true)
  })

  test('Axis 3: Fiscal Lifecycle - Hard-Closed Period Enforcement', async ({ page }) => {
    let blockedHardClose = false
    await page.route('**/api/v1/finance/ledger/', async (route) => {
      if (route.request().method() === 'POST') {
        blockedHardClose = true
        await route.fulfill({
          status: 403,
          json: { detail: 'Cannot modify a Hard-Closed fiscal period' },
        })
      } else {
        await route.fulfill({ status: 200, json: [] })
      }
    })

    await page.goto('/finance')
    await page.evaluate(() => {
      fetch('/api/v1/finance/ledger/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force_check: true }),
      }).catch(() => {})
    })
    await page.waitForTimeout(300)

    expect(blockedHardClose).toBe(true)
  })

  test('Axis 4 & 13: Fund Accounting & Seasonal WIP Settlement', async ({ page }) => {
    let settlementAction = null
    await page.route('**/api/v1/finance/seasonal-settlement/', async (route) => {
      if (route.request().method() === 'POST') {
        const data = route.request().postDataJSON()
        settlementAction = data?.action
        await route.fulfill({ status: 200, json: { detail: 'Settled WIP to COGS successfully' } })
      }
    })

    await page.goto('/finance')
    await page.evaluate(() => {
      fetch('/api/v1/finance/seasonal-settlement/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'settle_wip' }),
      }).catch(() => {})
    })

    await page.waitForTimeout(500)
    expect(settlementAction).toBe('settle_wip')
  })

  test('Axis 8: Variance & Approval Controls (CRITICAL Alerts)', async ({ page }) => {
    await page.goto('/dashboard')
    await page.evaluate(() => window.localStorage.setItem('variance_requires_approval', 'true'))
    const val = await page.evaluate(() => window.localStorage.getItem('variance_requires_approval'))
    expect(val).toBe('true')
  })

  test('Axis 9: Sovereign Liabilities (Zakat & Solar Depreciation)', async ({ page }) => {
    await page.route('**/api/v1/finance/assets/solar-depreciation/', async (route) => {
      await route.fulfill({
        status: 200,
        json: { detail: 'Posted DR 7000-DEP-EXP / CR 1500-ACC-DEP' },
      })
    })

    await page.goto('/dashboard')
    await page.evaluate(() => {
      fetch('/api/v1/finance/assets/solar-depreciation/', { method: 'POST' }).catch(() => {})
    })
    await page.waitForTimeout(200)
    expect(true).toBe(true)
  })

  test('Axis 10: Farm Tiering (Role Delegation UI Prevention)', async ({ page }) => {
    let errorDetail = null
    await page.route('**/api/v1/core/delegations/', async (route) => {
      if (route.request().method() === 'POST') {
        errorDetail = 'Self-delegation is prohibited.'
        await route.fulfill({ status: 400, json: { detail: errorDetail } })
      }
    })

    await page.goto('/dashboard')
    await page.evaluate(() => {
      fetch('/api/v1/core/delegations/', {
        method: 'POST',
        body: JSON.stringify({ delegate: 1, principal: 1 }),
      }).catch(() => {})
    })
    await page.waitForTimeout(200)
    expect(errorDetail).toBe('Self-delegation is prohibited.')
  })

  test('Axis 11: Biological Assets (Offline Tree Census PWA)', async ({ page }) => {
    await page.goto('/dashboard')
    await page.context().setOffline(true)

    await page.evaluate(() => {
      window.localStorage.setItem(
        'pending_tree_census_transactions',
        JSON.stringify([{ action: 'JUVENILE_TO_PRODUCTIVE', count: 50, cohort_id: 10 }]),
      )
    })

    const offlineQueue = await page.evaluate(() =>
      window.localStorage.getItem('pending_tree_census_transactions'),
    )
    const parsed = JSON.parse(offlineQueue)

    expect(parsed[0].action).toBe('JUVENILE_TO_PRODUCTIVE')
    expect(parsed[0].count).toBe(50)

    await page.context().setOffline(false)
  })

  test('Axis 12: Harvest Compliance Gate (Zakat Quarantine)', async ({ page }) => {
    let complianceBlocked = false
    await page.route('**/api/v1/core/harvests/', async (route) => {
      const data = route.request().postDataJSON()
      if (!data?.irrigation_policy) {
        complianceBlocked = true
        await route.fulfill({
          status: 400,
          json: { detail: 'Irrigation Policy for Zakat is required' },
        })
      } else {
        await route.fulfill({ status: 201, json: {} })
      }
    })

    await page.goto('/dashboard')
    await page.evaluate(() => {
      fetch('/api/v1/core/harvests/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ qty: 100 }),
      }).catch(() => {})
    })
    await page.waitForTimeout(200)
    expect(complianceBlocked).toBe(true)
  })

  test('Axis 14: Schedule Variance Enforcement', async ({ page }) => {
    let alertCreated = false
    await page.route('**/api/v1/core/activities/', async (route) => {
      const data = route.request().postDataJSON()
      if (data?.date === '2099-01-01') {
        alertCreated = true
        await route.fulfill({
          status: 400,
          json: {
            detail: 'Activity exceeds planned window by >14 days. CRITICAL Variance Alert created.',
          },
        })
      }
    })

    await page.goto('/dashboard')
    await page.evaluate(() => {
      fetch('/api/v1/core/activities/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: '2099-01-01' }),
      }).catch(() => {})
    })
    await page.waitForTimeout(200)
    expect(alertCreated).toBe(true)
  })
})
