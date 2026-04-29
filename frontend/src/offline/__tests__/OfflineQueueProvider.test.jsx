import { render, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const flushQueueMock = vi.fn()
const getOfflineQueueCountsMock = vi.fn()

vi.mock('../../api/client', () => ({
  flushQueue: (...args) => flushQueueMock(...args),
  getOfflineQueueCounts: (...args) => getOfflineQueueCountsMock(...args),
}))

vi.mock('../../components/ToastProvider', () => ({
  useToast: () => vi.fn(),
}))

vi.mock('../../contexts/SettingsContext', () => ({
  useSettings: () => ({
    offlineCacheRetentionDays: 7,
    syncedDraftRetentionDays: 7,
    deadLetterRetentionDays: 14,
  }),
}))

vi.mock('../dexie_db', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    performOfflinePurge: vi.fn().mockResolvedValue({ purged: 0 }),
  }
})

import { OfflineQueueProvider } from '../OfflineQueueProvider.jsx'

describe('OfflineQueueProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true })
    getOfflineQueueCountsMock.mockResolvedValue({
      requests: 0,
      harvests: 0,
      dailyLogs: 1,
      custody: 0,
      failedRequests: 0,
      failedHarvests: 0,
      failedDailyLogs: 0,
      failedCustody: 0,
    })
    flushQueueMock.mockResolvedValue({
      totalProcessed: 1,
      syncedDailyLogs: [],
    })
  })

  it('auto-syncs pending daily logs when the app is online', async () => {
    render(
      <OfflineQueueProvider>
        <div>child</div>
      </OfflineQueueProvider>,
    )

    await waitFor(() => expect(flushQueueMock).toHaveBeenCalled())
  })

  it('schedules sync when the page becomes visible online', async () => {
    render(
      <OfflineQueueProvider>
        <div>child</div>
      </OfflineQueueProvider>,
    )
    flushQueueMock.mockClear()

    Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true })
    document.dispatchEvent(new Event('visibilitychange'))

    await waitFor(() => expect(flushQueueMock).toHaveBeenCalled())
  })
})
