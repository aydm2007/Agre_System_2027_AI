/**
 * [AGRI-GUARDIAN] E2E API Helpers
 * Provides API-level operations for seed, verify, and assertion in E2E tests.
 */
import { expect } from '@playwright/test'
import { endpoints, withAuthHeaders, readResults } from './e2eAuth'

// ─── API GET with auth ──────────────────────────────────────────────────────
export async function apiGet(request, token, path, params = {}) {
  const qs = new URLSearchParams(params).toString()
  const url = `${endpoints.V1_BASE}${path}${qs ? '?' + qs : ''}`
  const res = await request.get(url, { headers: withAuthHeaders(token) })
  return { ok: res.ok(), status: res.status(), data: await res.json().catch(() => ({})) }
}

// ─── API POST with auth + idempotency ───────────────────────────────────────
export async function apiPost(request, token, path, data = {}) {
  const headers = {
    ...withAuthHeaders(token),
    'X-Idempotency-Key': `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  }
  const res = await request.post(`${endpoints.V1_BASE}${path}`, { headers, data })
  return { ok: res.ok(), status: res.status(), data: await res.json().catch(() => ({})) }
}

// ─── Verify farm exists ─────────────────────────────────────────────────────
export async function getFirstFarm(request, token) {
  const { data } = await apiGet(request, token, '/farms/')
  const farms = readResults(data)
  expect(farms.length, 'HALT: no farms seeded').toBeGreaterThan(0)
  return farms[0]
}

// ─── Verify open fiscal period ──────────────────────────────────────────────
export async function getOpenPeriod(request, token, farmId) {
  const { data } = await apiGet(request, token, '/finance/fiscal-periods/', {
    status: 'open',
    farm: farmId,
  })
  const periods = readResults(data)
  expect(periods.length, 'HALT: no open fiscal period').toBeGreaterThan(0)
  return periods[0]
}

// ─── Verify ledger balance ──────────────────────────────────────────────────
export async function getLedgerBalance(request, token, farmId, accountCode) {
  const { data } = await apiGet(request, token, '/finance/ledger/balances/', {
    farm: farmId,
  })
  const balances = data?.balances || data || {}
  return balances[accountCode] || '0.0000'
}

// ─── Verify AuditLog exists ─────────────────────────────────────────────────
export async function verifyAuditLogExists(request, token, action, objectId) {
  const { data } = await apiGet(request, token, '/audit-logs/', {
    action,
    object_id: objectId,
  })
  const logs = readResults(data)
  return logs.length > 0
}

// ─── Get crop plans ─────────────────────────────────────────────────────────
export async function getCropPlans(request, token, farmId) {
  const { data } = await apiGet(request, token, '/crop-plans/', { farm_id: farmId })
  return readResults(data)
}

// ─── Get sales invoices ─────────────────────────────────────────────────────
export async function getSalesInvoices(request, token, farmId) {
  const { data } = await apiGet(request, token, '/sales-invoices/', { farm_id: farmId })
  return readResults(data)
}

// ─── Get employees ──────────────────────────────────────────────────────────
export async function getEmployees(request, token, farmId) {
  const { data } = await apiGet(request, token, '/employees/', { farm: farmId })
  return readResults(data)
}

// ─── Check system mode ──────────────────────────────────────────────────────
export async function isStrictMode(request, token) {
  const { data } = await apiGet(request, token, '/system-mode/')
  return Boolean(data?.strict_erp_mode)
}

// ─── Verify approval request ────────────────────────────────────────────────
export async function getApprovalRequests(request, token, farmId) {
  const { data } = await apiGet(request, token, '/finance/approval-requests/', { farm: farmId })
  return readResults(data)
}
