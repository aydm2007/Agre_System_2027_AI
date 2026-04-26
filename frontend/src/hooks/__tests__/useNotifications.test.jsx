import { renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const getAccessTokenValueMock = vi.fn()

vi.mock('../../api/tokenStorage', () => ({
  getAccessTokenValue: () => getAccessTokenValueMock(),
}))

import { useNotifications } from '../useNotifications'

describe('useNotifications', () => {
  const originalEventSource = global.EventSource

  beforeEach(() => {
    getAccessTokenValueMock.mockReset()
    global.EventSource = vi.fn(() => ({
      close: vi.fn(),
      onopen: null,
      onmessage: null,
      onerror: null,
    }))
  })

  afterEach(() => {
    global.EventSource = originalEventSource
  })

  it('does not start SSE when disabled', () => {
    getAccessTokenValueMock.mockReturnValue('token-123')

    renderHook(() => useNotifications(null, { enabled: false }))

    expect(global.EventSource).not.toHaveBeenCalled()
  })

  it('does not start SSE before an access token exists', () => {
    getAccessTokenValueMock.mockReturnValue('')

    renderHook(() => useNotifications(null, { enabled: true }))

    expect(global.EventSource).not.toHaveBeenCalled()
  })

  it('starts SSE only after auth is ready and token is present', () => {
    getAccessTokenValueMock.mockReturnValue('token-123')

    renderHook(() => useNotifications(31, { enabled: true }))

    expect(global.EventSource).toHaveBeenCalledTimes(1)
    expect(global.EventSource.mock.calls[0][0]).toContain('/api/v1/notifications/stream/')
    expect(global.EventSource.mock.calls[0][0]).toContain('farm_id=31')
    expect(global.EventSource.mock.calls[0][0]).toContain('access_token=token-123')
  })
})
