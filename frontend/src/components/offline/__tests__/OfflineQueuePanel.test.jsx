import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

const useOfflineQueueMock = vi.fn()
const getOfflineQueueDetailsMock = vi.fn()
const getQueueOwnerKeyMock = vi.fn()
const dailyLogToArrayMock = vi.fn()
const dailyLogUpdateMock = vi.fn()
const userDataPutMock = vi.fn()
const uuidV4Mock = vi.fn()

vi.mock('../../../offline/OfflineQueueProvider.jsx', () => ({
  useOfflineQueue: () => useOfflineQueueMock(),
}))

vi.mock('../../../api/client.js', () => ({
  getOfflineQueueDetails: (...args) => getOfflineQueueDetailsMock(...args),
  clearOfflineQueue: vi.fn(),
  requeueFailedItems: vi.fn(),
  removeOfflineQueueItem: vi.fn(),
}))

vi.mock('../../../api/offlineQueueStore.js', () => ({
  getQueueOwnerKey: (...args) => getQueueOwnerKeyMock(...args),
}))

vi.mock('../../../offline/dexie_db.js', () => ({
  db: {
    daily_log_queue: {
      toArray: (...args) => dailyLogToArrayMock(...args),
      update: (...args) => dailyLogUpdateMock(...args),
    },
    userData: {
      put: (...args) => userDataPutMock(...args),
    },
  },
}))

vi.mock('uuid', () => ({
  v4: (...args) => uuidV4Mock(...args),
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
    getQueueOwnerKeyMock.mockResolvedValue('user:47')
    dailyLogToArrayMock.mockResolvedValue([])
    dailyLogUpdateMock.mockResolvedValue(1)
    userDataPutMock.mockResolvedValue(undefined)
    uuidV4Mock.mockReturnValue('rotated-http-key')
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

  it('repairs daily-log sequence without replacing payload identity', async () => {
    const addToast = vi.fn()
    const refreshCounts = vi.fn()
    useOfflineQueueMock.mockReturnValue({
      queuedRequests: 0,
      queuedHarvests: 0,
      queuedDailyLogs: 0,
      queuedCustody: 0,
      failedRequests: 0,
      failedHarvests: 0,
      failedDailyLogs: 1,
      failedCustody: 0,
      syncing: false,
      lastSync: '2026-04-11T10:00:00.000Z',
      syncNow: vi.fn(),
      addToast,
      refreshCounts,
    })
    dailyLogToArrayMock.mockResolvedValue([
      {
        id: 22,
        owner_key: 'user:47',
        status: 'dead_letter',
        dead_letter: true,
        payload_uuid: 'payload-22',
        uuid: 'old-http-key',
        idempotency_key: 'old-http-key',
        created_at: '2026-04-27T14:12:27.180Z',
      },
    ])

    render(
      <MemoryRouter>
        <OfflineQueuePanel />
      </MemoryRouter>,
    )

    const repairButton = screen.getAllByRole('button')[1]
    fireEvent.click(repairButton)

    await waitFor(() => expect(dailyLogUpdateMock).toHaveBeenCalledWith(22, expect.any(Object)))
    const update = dailyLogUpdateMock.mock.calls[0][1]
    expect(update).toMatchObject({
      client_seq: 1,
      status: 'pending',
      dead_letter: false,
      idempotency_key: 'rotated-http-key',
      previous_idempotency_key: 'old-http-key',
      retry_count: 0,
    })
    expect(update.uuid).toBeUndefined()
    expect(update.payload_uuid).toBeUndefined()
    expect(update.meta.previous_idempotency_key).toBe('old-http-key')
    expect(userDataPutMock).toHaveBeenCalled()
    expect(refreshCounts).toHaveBeenCalled()
  })
})
