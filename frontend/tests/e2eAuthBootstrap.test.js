import { describe, expect, it, vi } from 'vitest'

import {
  ensureBackendAuthReadiness,
  isInfrastructureBootstrapError,
  isLocalApiBase,
} from './e2e/helpers/e2eAuth'

function okResponse(body) {
  return {
    ok: () => true,
    json: async () => body,
    status: () => 200,
    text: async () => JSON.stringify(body),
  }
}

function errorResponse(status, body) {
  return {
    ok: () => false,
    status: () => status,
    text: async () => body,
  }
}

describe('e2eAuth bootstrap helpers', () => {
  it('detects local API bases deterministically', () => {
    expect(isLocalApiBase('http://127.0.0.1:8000')).toBe(true)
    expect(isLocalApiBase('http://localhost:8000')).toBe(true)
    expect(isLocalApiBase('https://agriasset.example.com')).toBe(false)
  })

  it('classifies infrastructure bootstrap errors', () => {
    expect(isInfrastructureBootstrapError(new Error('connect ECONNREFUSED 127.0.0.1:8000'))).toBe(true)
    expect(isInfrastructureBootstrapError(new Error('network socket hang up'))).toBe(true)
    expect(isInfrastructureBootstrapError(new Error('401 unauthorized'))).toBe(false)
  })

  it('waits through transient infrastructure failures and returns tokens', async () => {
    const runLocalBootstrap = vi.fn(async () => {})
    const sleepFn = vi.fn(async () => {})
    const postAuth = vi
      .fn()
      .mockRejectedValueOnce(new Error('connect ECONNREFUSED 127.0.0.1:8000'))
      .mockResolvedValueOnce(okResponse({ access: 'access-token', refresh: 'refresh-token' }))

    const body = await ensureBackendAuthReadiness({
      request: {},
      postAuth,
      runLocalBootstrap,
      sleepFn,
      maxAttempts: 3,
    })

    expect(body).toEqual({ access: 'access-token', refresh: 'refresh-token' })
    expect(runLocalBootstrap).toHaveBeenCalledTimes(1)
    expect(postAuth).toHaveBeenCalledTimes(2)
    expect(sleepFn).toHaveBeenCalledTimes(1)
  })

  it('fails fast when auth bootstrap credentials are missing', async () => {
    await expect(
      ensureBackendAuthReadiness({
        request: {},
        postAuth: vi.fn(async () => errorResponse(401, 'No active account found')),
        runLocalBootstrap: vi.fn(async () => {}),
        sleepFn: vi.fn(async () => {}),
        maxAttempts: 2,
      }),
    ).rejects.toThrow(/seed_auth_contract_failure/)
  })
})
