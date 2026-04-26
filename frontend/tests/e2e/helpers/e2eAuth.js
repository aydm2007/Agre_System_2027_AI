import { expect } from '@playwright/test'
import { spawn } from 'node:child_process'
import path from 'node:path'

export const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
export const API_BASE = process.env.E2E_API_BASE || 'http://127.0.0.1:8000'
export const E2E_USER = process.env.E2E_USER || 'e2e_proof_user'
export const E2E_PASS = process.env.E2E_PASS || 'E2EProof#2026'
export const E2E_APP_VERSION = process.env.E2E_APP_VERSION || '2.0.0'
export const E2E_ACCESS_TOKEN = process.env.E2E_ACCESS_TOKEN || ''
export const E2E_REFRESH_TOKEN = process.env.E2E_REFRESH_TOKEN || ''

const API_ROOT = API_BASE.replace(/\/+$/, '')
const AUTH_BASE = API_ROOT.endsWith('/api') ? API_ROOT : `${API_ROOT}/api`
const V1_BASE = `${AUTH_BASE}/v1`
const BACKEND_PYTHON = process.env.PLAYWRIGHT_BACKEND_PYTHON || process.env.PYTHON || 'python'
const REPO_ROOT = path.resolve(import.meta.dirname, '..', '..', '..', '..')

export const endpoints = { AUTH_BASE, V1_BASE }
export const SARDOOD_FARM_REGEX = /سردود|sardood/i

let farmSelectionDone = false
let localBootstrapPromise = null

export function isLocalApiBase(apiBase = API_BASE) {
  try {
    const { hostname } = new URL(apiBase)
    return hostname === '127.0.0.1' || hostname === 'localhost'
  } catch {
    return apiBase.includes('127.0.0.1') || apiBase.includes('localhost')
  }
}

export function isInfrastructureBootstrapError(error) {
  const message = error instanceof Error ? error.message : String(error)
  return /ECONNREFUSED|ECONNRESET|ENOTFOUND|EHOSTUNREACH|socket hang up|network/i.test(message)
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function runBackendManageCommand(args) {
  await new Promise((resolve, reject) => {
    const child = spawn(BACKEND_PYTHON, args, {
      cwd: REPO_ROOT,
      env: process.env,
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (chunk) => {
      stdout += String(chunk)
    })
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk)
    })
    child.on('error', reject)
    child.on('close', (code) => {
      if (code === 0) {
        resolve()
        return
      }
      reject(
        new Error(
          `prepare_e2e_auth_v21 failed (exit=${code}) ${`${stdout}\n${stderr}`.trim().slice(0, 800)}`,
        ),
      )
    })
  })
}

export async function ensureLocalProofAuthBootstrap() {
  if (!isLocalApiBase()) return
  if (!localBootstrapPromise) {
    localBootstrapPromise = runBackendManageCommand(['backend/manage.py', 'prepare_e2e_auth_v21']).catch(
      (error) => {
        localBootstrapPromise = null
        throw error
      },
    )
  }
  await localBootstrapPromise
}

async function postAuthToken(request) {
  return request.post(`${AUTH_BASE}/auth/token/`, {
    headers: { 'X-App-Version': E2E_APP_VERSION },
    data: { username: E2E_USER, password: E2E_PASS },
  })
}

function formatAuthBootstrapError(lastStatus, lastBody, lastError) {
  if (lastError) {
    return `error=${lastError.message}`
  }
  return `status=${lastStatus} body=${lastBody.slice(0, 400)}`
}

function formatSeedContractFailure(status, body) {
  return `seed_auth_contract_failure status=${status} body=${body.slice(0, 400)}`
}

export async function ensureBackendAuthReadiness({
  request,
  postAuth = postAuthToken,
  runLocalBootstrap = ensureLocalProofAuthBootstrap,
  sleepFn = sleep,
  maxAttempts = 15,
} = {}) {
  await runLocalBootstrap()

  let lastStatus = null
  let lastBody = ''
  let lastError = null

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const response = await postAuth(request)
      if (response.ok()) {
        const body = await response.json()
        expect(body?.access).toBeTruthy()
        expect(body?.refresh).toBeTruthy()
        return body
      }

      lastStatus = response.status()
      lastBody = await response.text()
      lastError = null

      if ([400, 401, 403].includes(lastStatus)) {
        throw new Error(
          `HALT: backend auth endpoint reachable but E2E auth bootstrap is invalid (${formatSeedContractFailure(lastStatus, lastBody)})`,
        )
      }
      if ([404, 405].includes(lastStatus)) {
        throw new Error(
          `HALT: backend auth endpoint contract is broken (status=${lastStatus} body=${lastBody.slice(0, 400)})`,
        )
      }
    } catch (error) {
      if (!(error instanceof Error)) {
        throw error
      }
      if (!isInfrastructureBootstrapError(error)) {
        throw error
      }
      lastError = error
    }

    if (attempt < maxAttempts) {
      await sleepFn(1000 * attempt)
    }
  }

  throw new Error(
    `HALT: backend auth readiness failed after retries (infrastructure_bootstrap_failure ${formatAuthBootstrapError(lastStatus, lastBody, lastError)})`,
  )
}

export async function loginViaUI(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 180000 })
  await page.getByTestId('login-username').waitFor({ state: 'visible', timeout: 15000 })
  await page.getByTestId('login-username').fill(E2E_USER)
  await page.getByTestId('login-password').waitFor({ state: 'visible', timeout: 15000 })
  await page.getByTestId('login-password').fill(E2E_PASS)
  await page.getByTestId('login-submit').click()
  await expect(page).toHaveURL(/dashboard|\/$/, { timeout: 15000 })
}

export async function fetchToken(request) {
  if (E2E_ACCESS_TOKEN) return E2E_ACCESS_TOKEN
  const tokens = await fetchTokens(request)
  return tokens.access
}

export async function fetchTokens(request) {
  if (E2E_ACCESS_TOKEN && E2E_REFRESH_TOKEN) {
    return { access: E2E_ACCESS_TOKEN, refresh: E2E_REFRESH_TOKEN }
  }
  const body = await ensureBackendAuthReadiness({ request })
  return { access: body.access, refresh: body.refresh }
}

export async function loginViaApi(page, request) {
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
    if (!loginVisible) return
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded', timeout: 180000 })
    await page.waitForTimeout(1000)
  }
  await expect(page).not.toHaveURL(/\/login(\/|$)/, { timeout: 30000 })
  await page.locator('#root').waitFor({ state: 'attached', timeout: 30000 })
  await expect(page.locator('#root')).toBeVisible({ timeout: 30000 })
}

export async function ensureLoggedIn(page, request) {
  // Prefer the shared storageState generated by auth.setup before attempting any fresh login.
  await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'domcontentloaded', timeout: 180000 })
  if (!/\/login(\/|$)/.test(page.url())) return

  try {
    await loginViaUI(page)
  } catch {
    await loginViaApi(page, request)
  }
}

export function withAuthHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    'X-App-Version': E2E_APP_VERSION,
  }
}

export function readResults(payload) {
  if (Array.isArray(payload?.results)) return payload.results
  if (Array.isArray(payload)) return payload
  return []
}

export async function fetchSystemMode(request) {
  let lastStatus = null
  let lastBody = ''

  for (let attempt = 1; attempt <= 3; attempt += 1) {
    const response = await request.get(`${V1_BASE}/system-mode/`)
    if (response.ok()) return response.json()
    lastStatus = response.status()
    lastBody = await response.text()
    await new Promise((resolve) => setTimeout(resolve, 400 * attempt))
  }

  const token = await fetchToken(request)
  const response = await request.get(`${V1_BASE}/system-mode/`, { headers: withAuthHeaders(token) })
  if (response.ok()) return response.json()

  lastStatus = response.status()
  lastBody = await response.text()
  // Contract fallback: when system-mode endpoint is unavailable/throttled, default to Simple mode.
  if (lastStatus === 429 || lastStatus >= 500 || lastStatus === 0 || lastStatus == null) {
    return {
      strict_erp_mode: false,
      _fallback_reason: `system-mode-unavailable-${lastStatus ?? 'unknown'}`,
      _fallback_body: lastBody.slice(0, 200),
    }
  }

  throw new Error(
    `HALT: cannot load /system-mode/ after retries (status=${lastStatus}) body=${lastBody.slice(0, 400)}`,
  )
}

export async function fetchCurrentUser(request) {
  let lastStatus = null
  let lastBody = ''

  for (let attempt = 1; attempt <= 3; attempt += 1) {
    const token = await fetchToken(request)
    const response = await request.get(`${V1_BASE}/auth/users/me/`, {
      headers: withAuthHeaders(token),
    })
    if (response.ok()) return response.json()
    lastStatus = response.status()
    lastBody = await response.text()
    await new Promise((resolve) => setTimeout(resolve, 400 * attempt))
  }

  throw new Error(
    `HALT: cannot load /auth/users/me/ after retries (status=${lastStatus}) body=${lastBody.slice(0, 400)}`,
  )
}

export async function resolveAccessibleFarmId(request) {
  const token = await fetchToken(request)
  const headers = withAuthHeaders(token)

  const farmsResponse = await request.get(`${V1_BASE}/farms/`, { headers })
  if (farmsResponse.ok()) {
    const farmsPayload = await farmsResponse.json()
    const farms = readResults(farmsPayload)
    if (farms.length) {
      const preferredFarm =
        farms.find((farm) => SARDOOD_FARM_REGEX.test(farm?.name || '') || farm?.slug === 'sardood-farm') ||
        farms[0]
      return String(preferredFarm?.id || preferredFarm?.farm_id || '')
    }
  }

  const farmSettingsResponse = await request.get(`${V1_BASE}/farm-settings/`, { headers })
  if (farmSettingsResponse.ok()) {
    const farmSettingsPayload = await farmSettingsResponse.json()
    const settingsRows = readResults(farmSettingsPayload)
    const first = settingsRows[0]
    const farmId = first?.farm?.id || first?.farm || first?.farm_id || ''
    if (farmId) {
      return String(farmId)
    }
  }

  const me = await fetchCurrentUser(request).catch(() => null)
  const scopedFarm =
    me?.default_farm?.id ||
    me?.default_farm ||
    me?.farm?.id ||
    me?.farm ||
    me?.farms?.[0]?.id ||
    me?.farms?.[0]?.farm_id
  if (scopedFarm) {
    return String(scopedFarm)
  }

  throw new Error('HALT: unable to resolve an accessible farm id for E2E bootstrap')
}

export async function ensureFarmSelected(page, targetFarmRegex = SARDOOD_FARM_REGEX) {
  const selector = page.getByTestId('farm-selector-button')
  if (await selector.isVisible().catch(() => false)) {
    const currentLabel = ((await selector.textContent().catch(() => '')) || '').trim()
    if (currentLabel && targetFarmRegex.test(currentLabel)) {
      farmSelectionDone = true
      return
    }

    await selector.click()
    const options = page.locator('[data-testid^="farm-option-"]')
    const optionCount = await options.count()
    if (optionCount > 0) {
      for (let idx = 0; idx < optionCount; idx += 1) {
        const option = options.nth(idx)
        const label = (await option.textContent().catch(() => '')) || ''
        if (targetFarmRegex.test(label)) {
          await option.click()
          farmSelectionDone = true
          return
        }
      }
      await options.first().click()
      farmSelectionDone = true
    }
    return
  }

  const pageFarmFilters = page.locator('[data-testid$="farm-filter"]')
  const filterCount = await pageFarmFilters.count()
  for (let idx = 0; idx < filterCount; idx += 1) {
    const filter = pageFarmFilters.nth(idx)
    const selectedLabel =
      ((await filter.locator('option:checked').textContent().catch(() => '')) || '').trim()
    if (selectedLabel && targetFarmRegex.test(selectedLabel)) {
      farmSelectionDone = true
      return
    }
    const options = filter.locator('option')
    const optionCount = await options.count()
    for (let i = 0; i < optionCount; i += 1) {
      const optionValue = await options.nth(i).getAttribute('value')
      const optionLabel = (await options.nth(i).textContent().catch(() => '')) || ''
      if (optionValue && optionValue !== 'all' && targetFarmRegex.test(optionLabel)) {
        await filter.selectOption(optionValue)
        farmSelectionDone = true
        return
      }
    }
    for (let i = 0; i < optionCount; i += 1) {
      const optionValue = await options.nth(i).getAttribute('value')
      if (optionValue && optionValue !== 'all') {
        await filter.selectOption(optionValue)
        farmSelectionDone = true
        return
      }
    }
  }
}
