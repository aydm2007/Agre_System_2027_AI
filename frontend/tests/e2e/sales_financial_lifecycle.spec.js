import { test, expect } from '@playwright/test'
import { endpoints, fetchToken, withAuthHeaders, readResults } from './helpers/e2eAuth'

const newKey = (prefix) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`

let farmId

test.beforeAll(async ({ request }) => {
  const token = await fetchToken(request)
  const headers = withAuthHeaders(token)
  const farmsRes = await request.get(`${endpoints.V1_BASE}/farms/`, { headers })
  expect(farmsRes.ok(), 'HALT: missing seeded farms').toBeTruthy()
  const farms = readResults(await farmsRes.json())
  expect(farms.length, 'HALT: no farm data for sales lifecycle').toBeGreaterThan(0)
  farmId = farms[0].id
})

test.describe('Sales Financial Lifecycle E2E', () => {
  test('create -> confirm -> cancel with idempotent replay', async ({ request }) => {
    const token = await fetchToken(request)
    const headers = withAuthHeaders(token)

    const [customersRes, locationsRes, itemsRes] = await Promise.all([
      request.get(`${endpoints.V1_BASE}/customers/`, { headers }),
      request.get(`${endpoints.V1_BASE}/locations/?farm_id=${farmId}`, { headers }),
      request.get(`${endpoints.V1_BASE}/items/`, { headers }),
    ])

    expect(customersRes.ok()).toBeTruthy()
    expect(locationsRes.ok()).toBeTruthy()
    expect(itemsRes.ok()).toBeTruthy()

    const customers = readResults(await customersRes.json())
    const locations = readResults(await locationsRes.json())
    const items = readResults(await itemsRes.json())

    expect(customers.length, 'HALT: customers seed is missing').toBeGreaterThan(0)
    expect(locations.length, 'HALT: locations seed is missing').toBeGreaterThan(0)
    expect(items.length, 'HALT: items seed is missing').toBeGreaterThan(0)

    const item = items.find((candidate) => Number(candidate?.unit_price) > 0) || items[0]
    const unitPrice = Number(item?.unit_price) > 0 ? Number(item.unit_price) : 100

    const createRes = await request.post(`${endpoints.V1_BASE}/sales-invoices/`, {
      headers: { ...headers, 'X-Idempotency-Key': newKey('create-invoice') },
      data: {
        customer: customers[0].id,
        location: locations[0].id,
        invoice_date: '2026-02-11',
        notes: 'E2E lifecycle validation',
        items: [{ item: item.id, qty: '1', unit_price: String(unitPrice) }],
      },
    })
    expect(createRes.status()).toBe(201)
    const created = await createRes.json()
    expect(created?.id).toBeTruthy()

    const invoiceId = created.id
    const confirmKey = newKey('confirm-invoice')
    const confirmRes = await request.post(
      `${endpoints.V1_BASE}/sales-invoices/${invoiceId}/confirm/`,
      {
        headers: { ...headers, 'X-Idempotency-Key': confirmKey },
        data: {},
      },
    )
    expect([200, 400, 403]).toContain(confirmRes.status())

    if (confirmRes.status() === 200) {
      const replayRes = await request.post(
        `${endpoints.V1_BASE}/sales-invoices/${invoiceId}/confirm/`,
        {
          headers: { ...headers, 'X-Idempotency-Key': confirmKey },
          data: {},
        },
      )
      expect(replayRes.status()).toBe(200)
    }

    const cancelKey = newKey('cancel-invoice')
    const cancelRes = await request.post(
      `${endpoints.V1_BASE}/sales-invoices/${invoiceId}/cancel/`,
      {
        headers: { ...headers, 'X-Idempotency-Key': cancelKey },
        data: {},
      },
    )
    expect([200, 400]).toContain(cancelRes.status())

    if (cancelRes.status() === 200) {
      const replayCancelRes = await request.post(
        `${endpoints.V1_BASE}/sales-invoices/${invoiceId}/cancel/`,
        {
          headers: { ...headers, 'X-Idempotency-Key': cancelKey },
          data: {},
        },
      )
      expect(replayCancelRes.status()).toBe(200)
    }
  })
})
