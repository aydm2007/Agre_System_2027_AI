import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const upsertDailyLogDraft = vi.fn()
const getDailyLogDraft = vi.fn()
const getLatestDailyLogDraft = vi.fn()
const listDailyLogDrafts = vi.fn()
const deleteDailyLogDraft = vi.fn()
const nextOfflineClientSeq = vi.fn()
const toArrayMock = vi.fn()

vi.mock('idb-keyval', () => ({
  get: vi.fn().mockResolvedValue(null),
  del: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('../../offline/dexie_db', () => ({
  db: {
    daily_log_queue: {
      toArray: (...args) => toArrayMock(...args),
    },
  },
  upsertDailyLogDraft: (...args) => upsertDailyLogDraft(...args),
  getDailyLogDraft: (...args) => getDailyLogDraft(...args),
  getLatestDailyLogDraft: (...args) => getLatestDailyLogDraft(...args),
  listDailyLogDrafts: (...args) => listDailyLogDrafts(...args),
  deleteDailyLogDraft: (...args) => deleteDailyLogDraft(...args),
  nextOfflineClientSeq: (...args) => nextOfflineClientSeq(...args),
}))

vi.mock('../../api/offlineQueueStore', () => ({
  getQueueOwnerKey: vi.fn().mockResolvedValue('owner-1'),
}))

vi.mock('../../utils/serviceCoveragePayload', () => ({
  normalizeServiceCountsList: (rows) => rows,
}))

vi.mock('../../utils/auditLedger', () => ({
  AuditLedger: {
    signAndLog: vi.fn().mockResolvedValue(undefined),
  },
}))

import { useDailyLogOffline } from '../useDailyLogOffline'

describe('useDailyLogOffline', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    toArrayMock.mockResolvedValue([])
    getLatestDailyLogDraft.mockResolvedValue(null)
    listDailyLogDrafts.mockResolvedValue([])
  })

  it('persists log_date inside daily-log drafts', async () => {
    const { result } = renderHook(() => useDailyLogOffline())

    await act(async () => {
      await result.current.saveDraft(
        {
          farm: '3',
          date: '2026-04-14',
        },
        {
          draftUuid: 'draft-1',
          farmId: '3',
          logDate: '2026-04-14',
        },
      )
    })

    expect(upsertDailyLogDraft).toHaveBeenCalled()
    expect(upsertDailyLogDraft.mock.calls[0][0]).toMatchObject({
      draft_uuid: 'draft-1',
      farm_id: '3',
      log_date: '2026-04-14',
    })
  })

  it('queries the latest draft using log_date instead of created_at', async () => {
    const { result } = renderHook(() => useDailyLogOffline())

    await act(async () => {
      await result.current.loadDraft({ farmId: '8', logDate: '2026-04-20' })
    })

    expect(getLatestDailyLogDraft).toHaveBeenCalledWith({
      status: 'draft',
      farm_id: '8',
      log_date: '2026-04-20',
    })
  })

  it('maps camelCase draft filters to the Dexie draft schema', async () => {
    const { result } = renderHook(() => useDailyLogOffline())

    await act(async () => {
      await result.current.loadDrafts({ farmId: '9', logDate: '2026-04-30' })
    })

    expect(listDailyLogDrafts).toHaveBeenCalledWith({
      farm_id: '9',
      log_date: '2026-04-30',
    })
  })
})
