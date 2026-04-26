import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

const useOfflineQueueMock = vi.fn()
const getOfflineQueueDetailsMock = vi.fn()

vi.mock('../../../offline/OfflineQueueProvider.jsx', () => ({
  useOfflineQueue: () => useOfflineQueueMock(),
}))

vi.mock('../../../api/client.js', () => ({
  getOfflineQueueDetails: (...args) => getOfflineQueueDetailsMock(...args),
  clearOfflineQueue: vi.fn(),
  requeueFailedItems: vi.fn(),
  removeOfflineQueueItem: vi.fn(),
}))

vi.mock('../OfflineQueueRow.jsx', () => ({
  default: ({ summary }) => <div data-testid={`queue-row-${summary.id}`}>{summary.title}</div>,
}))

import OfflineQueuePanel from '../OfflineQueuePanel.jsx'

describe('OfflineQueuePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useOfflineQueueMock.mockReturnValue({
      queuedRequests: 1,
      queuedHarvests: 1,
      queuedDailyLogs: 2,
      queuedCustody: 1,
      failedRequests: 0,
      failedHarvests: 1,
      failedDailyLogs: 1,
      failedCustody: 0,
      syncing: false,
      lastSync: '2026-04-11T10:00:00.000Z',
      syncNow: vi.fn(),
      addToast: vi.fn(),
      refreshCounts: vi.fn(),
    })
    getOfflineQueueDetailsMock.mockResolvedValue({
      requests: [],
      harvests: [],
      dailyLogs: [],
      custody: [],
      failedRequests: [],
      failedHarvests: [],
      failedDailyLogs: [],
      failedCustody: [],
      meta: {},
    })
  })

  it('shows diagnostics and unified queue taxonomy in Arabic', async () => {
    render(
      <MemoryRouter>
        <OfflineQueuePanel />
      </MemoryRouter>,
    )

    await waitFor(() => expect(getOfflineQueueDetailsMock).toHaveBeenCalled())

    expect(screen.getByRole('heading', { level: 3 })).toBeTruthy()
    expect(screen.getAllByText((_, node) => node?.textContent?.includes('آخر مزامنة')).length).toBeGreaterThan(0)
    expect(screen.getByText(/generic_queue/i)).toBeTruthy()
    expect(screen.getByText(/harvest_queue/i)).toBeTruthy()
    expect(screen.getByText(/daily_log_queue/i)).toBeTruthy()
    expect(screen.getByText(/custody_queue/i)).toBeTruthy()
    expect(screen.getByTestId('queue-row-harvests')).toBeTruthy()
    expect(screen.getAllByText((_, node) => node?.textContent?.includes('تحتاج معالجة')).length).toBeGreaterThan(0)
  })

  it('shows successful daily log replay records after local queue is cleared', async () => {
    useOfflineQueueMock.mockReturnValue({
      queuedRequests: 0,
      queuedHarvests: 0,
      queuedDailyLogs: 0,
      queuedCustody: 0,
      failedRequests: 0,
      failedHarvests: 0,
      failedDailyLogs: 0,
      failedCustody: 0,
      syncing: false,
      lastSync: '2026-04-11T10:00:00.000Z',
      syncNow: vi.fn(),
      addToast: vi.fn(),
      refreshCounts: vi.fn(),
    })
    getOfflineQueueDetailsMock.mockResolvedValue({
      requests: [],
      harvests: [],
      dailyLogs: [],
      custody: [],
      failedRequests: [],
      failedHarvests: [],
      failedDailyLogs: [],
      failedCustody: [],
      syncRecords: [
        {
          id: 'local-sync-1',
          category: 'daily_log',
          reference: 'payload-1',
          status: 'success',
          local: true,
        },
      ],
      syncConflicts: [],
      quarantines: [],
      meta: {},
    })

    render(
      <MemoryRouter>
        <OfflineQueuePanel />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getAllByText('Sync Records').length).toBeGreaterThan(0))
    expect(screen.getByText(/daily_log \/ payload-1/i)).toBeTruthy()
    expect(screen.getAllByText((_, node) => node?.textContent?.includes('success')).length).toBeGreaterThan(0)
  })
})
