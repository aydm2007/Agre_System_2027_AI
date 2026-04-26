import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const dexieHarness = vi.hoisted(() => {
  const tables = {
    generic_queue: [],
    sales_queue: [],
    harvest_queue: [],
    daily_log_queue: [],
    custody_queue: [],
    userData: [],
  }
  const clone = (value) => JSON.parse(JSON.stringify(value))
  const tableRef = (name) => tables[name]
  const replaceTable = (name, next) => {
    tables[name] = next
  }
  const buildTable = (name) => ({
  async put(record) {
    const rows = tableRef(name)
    const nextRecord = { ...record }
    if (nextRecord.id == null) {
      nextRecord.id = rows.length ? Math.max(...rows.map((row) => Number(row.id) || 0)) + 1 : 1
    }
    const existingIndex = rows.findIndex((row) => String(row.id) === String(nextRecord.id))
    if (existingIndex >= 0) {
      rows[existingIndex] = nextRecord
    } else {
      rows.push(nextRecord)
    }
    return nextRecord.id
  },
  async add(record) {
    return this.put(record)
  },
  async toArray() {
    return clone(tableRef(name))
  },
  async get(key) {
    const rows = tableRef(name)
    return clone(rows.find((row) => String(row.key ?? row.id) === String(key)) || null)
  },
  async update(id, changes) {
    const rows = tableRef(name)
    const index = rows.findIndex((row) => String(row.id) === String(id))
    if (index < 0) return 0
    rows[index] = { ...rows[index], ...changes }
    return 1
  },
  async delete(id) {
    replaceTable(
      name,
      tableRef(name).filter((row) => String(row.id) !== String(id)),
    )
  },
  async bulkDelete(ids) {
    const blocked = new Set(ids.map((value) => String(value)))
    replaceTable(
      name,
      tableRef(name).filter((row) => !blocked.has(String(row.id))),
    )
  },
  async clear() {
    replaceTable(name, [])
  },
  filter(fn) {
    return {
      toArray: async () => clone(tableRef(name).filter(fn)),
    }
  },
  where(field) {
    return {
      equals: (value) => ({
        delete: async () => {
          const before = tableRef(name).length
          replaceTable(
            name,
            tableRef(name).filter((row) => String(row[field]) !== String(value)),
          )
          return before - tableRef(name).length
        },
      }),
    }
  },
})
  const getQueueBuckets = (name, ownerKey = null) => {
    const rows = tableRef(name).filter((row) => !ownerKey || row.owner_key === ownerKey)
    const pendingStatuses = new Set(['pending', 'syncing', 'failed_retryable'])
    const failedStatuses = new Set(['dead_letter', 'quarantined'])
    return {
      pending: rows.filter((row) => pendingStatuses.has(row.status)),
      failed: rows.filter((row) => failedStatuses.has(row.status) || row.dead_letter),
    }
  }
  const clearQueueByType = async (name, type = 'all', ownerKey = null) => {
    const rows = tableRef(name)
    const pendingStatuses = new Set(['pending', 'syncing', 'failed_retryable'])
    const failedStatuses = new Set(['dead_letter', 'quarantined'])
    if (type === 'all') {
      replaceTable(
        name,
        ownerKey ? rows.filter((row) => row.owner_key !== ownerKey) : [],
      )
      return true
    }
    replaceTable(
      name,
      rows.filter((row) => {
        if (ownerKey && row.owner_key !== ownerKey) return true
        if (type === 'pending') return !pendingStatuses.has(row.status)
        if (type === 'failed') return !(failedStatuses.has(row.status) || row.dead_letter)
        return true
      }),
    )
    return true
  }
  const removeQueueItem = async (name, id, ownerKey = null) => {
    const rows = tableRef(name)
    const existing = rows.find((row) => String(row.id) === String(id))
    if (!existing) return false
    if (ownerKey && existing.owner_key !== ownerKey) return false
    replaceTable(
      name,
      rows.filter((row) => String(row.id) !== String(id)),
    )
    return true
  }
  const requeueFailures = async (name, ownerKey = null) => {
    const failedStatuses = new Set(['dead_letter', 'quarantined'])
    const rows = tableRef(name)
    let count = 0
    replaceTable(
      name,
      rows.map((row) => {
        if ((!ownerKey || row.owner_key === ownerKey) && (failedStatuses.has(row.status) || row.dead_letter)) {
          count += 1
          return {
            ...row,
            status: 'pending',
            dead_letter: false,
            retry_count: 0,
            last_error: null,
            dead_letter_reason: null,
            next_attempt_at: null,
          }
        }
        return row
      }),
    )
    return count
  }
  return { tables, clone, tableRef, replaceTable, buildTable, getQueueBuckets, clearQueueByType, removeQueueItem, requeueFailures }
})

const legacyStore = new Map()

vi.mock('idb-keyval', () => ({
  get: vi.fn(async (key) => legacyStore.get(key)),
  set: vi.fn(async (key, value) => {
    legacyStore.set(key, value)
  }),
  del: vi.fn(async (key) => {
    legacyStore.delete(key)
  }),
}))

vi.mock('../src/offline/dexie_db', () => {
  const { buildTable, getQueueBuckets, clearQueueByType, removeQueueItem, requeueFailures, tableRef } = dexieHarness
  const db = {
    generic_queue: buildTable('generic_queue'),
    sales_queue: buildTable('sales_queue'),
    harvest_queue: buildTable('harvest_queue'),
    daily_log_queue: buildTable('daily_log_queue'),
    custody_queue: buildTable('custody_queue'),
    userData: buildTable('userData'),
  }
  return {
    db,
    queueHarvest: vi.fn(async (record) => db.harvest_queue.add(record)),
    queueGenericRequest: vi.fn(async (record) => db.generic_queue.add(record)),
    getGenericQueueCounts: vi.fn(async (ownerKey = null) => {
      const buckets = getQueueBuckets('generic_queue', ownerKey)
      return { pending: buckets.pending.length, failed: buckets.failed.length }
    }),
    getGenericQueueDetails: vi.fn(async (ownerKey = null) => getQueueBuckets('generic_queue', ownerKey)),
    clearGenericQueue: vi.fn(async (type = 'all', ownerKey = null) => clearQueueByType('generic_queue', type, ownerKey)),
    removeGenericQueueItem: vi.fn(async (id, ownerKey = null) => removeQueueItem('generic_queue', id, ownerKey)),
    requeueGenericFailures: vi.fn(async (ownerKey = null) => requeueFailures('generic_queue', ownerKey)),
    getHarvestQueueCounts: vi.fn(async (ownerKey = null) => {
      const buckets = getQueueBuckets('harvest_queue', ownerKey)
      return { pending: buckets.pending.length, failed: buckets.failed.length }
    }),
    getHarvestQueueDetails: vi.fn(async (ownerKey = null) => getQueueBuckets('harvest_queue', ownerKey)),
    clearHarvestQueue: vi.fn(async (type = 'all', ownerKey = null) => clearQueueByType('harvest_queue', type, ownerKey)),
    removeHarvestQueueItem: vi.fn(async (id, ownerKey = null) => removeQueueItem('harvest_queue', id, ownerKey)),
    requeueHarvestFailures: vi.fn(async (ownerKey = null) => requeueFailures('harvest_queue', ownerKey)),
    getPendingSales: vi.fn(async () => []),
    getDailyLogQueueCounts: vi.fn(async (ownerKey = null) => {
      const buckets = getQueueBuckets('daily_log_queue', ownerKey)
      return { pending: buckets.pending.length, failed: buckets.failed.length }
    }),
    getDailyLogQueueDetails: vi.fn(async (ownerKey = null) => getQueueBuckets('daily_log_queue', ownerKey)),
    getCustodyQueueCounts: vi.fn(async (ownerKey = null) => {
      const buckets = getQueueBuckets('custody_queue', ownerKey)
      return { pending: buckets.pending.length, failed: buckets.failed.length }
    }),
    getCustodyQueueDetails: vi.fn(async (ownerKey = null) => getQueueBuckets('custody_queue', ownerKey)),
    clearDailyLogQueue: vi.fn(async (type = 'all', ownerKey = null) => clearQueueByType('daily_log_queue', type, ownerKey)),
    clearCustodyQueue: vi.fn(async (type = 'all', ownerKey = null) => clearQueueByType('custody_queue', type, ownerKey)),
    removeDailyLogQueueItem: vi.fn(async (id, ownerKey = null) => removeQueueItem('daily_log_queue', id, ownerKey)),
    removeCustodyQueueItem: vi.fn(async (id, ownerKey = null) => removeQueueItem('custody_queue', id, ownerKey)),
    requeueDailyLogFailures: vi.fn(async (ownerKey = null) => requeueFailures('daily_log_queue', ownerKey)),
    requeueCustodyFailures: vi.fn(async (ownerKey = null) => requeueFailures('custody_queue', ownerKey)),
    performOfflinePurge: vi.fn(async () => {}),
    nextOfflineClientSeq: vi.fn(async (ownerKey, category, scope = 'default') => {
      const key = `offline-seq:${ownerKey || 'anonymous'}:${category}:${scope}`
      const row = tableRef('userData').find((entry) => entry.key === key)
      const next = Number(row?.value || 0) + 1
      await db.userData.put({ key, value: next })
      return next
    }),
  }
})

import {
  api,
  clearOfflineQueue,
  CustodyTransfers,
  enqueueDailyLogSubmission,
  flushQueue,
  getOfflineQueueDetails,
  HarvestLogs,
  removeOfflineQueueItem,
  requeueFailedItems,
  safeRequest,
} from '../src/api/client'

const makeDataUrl = (text) => `data:text/plain;base64,${Buffer.from(text, 'utf8').toString('base64')}`
const defineGlobal = (key, value) => {
  Object.defineProperty(globalThis, key, {
    value,
    configurable: true,
    writable: true,
  })
}
const setNavigator = (value) => defineGlobal('navigator', value)
const originalNavigator = globalThis.navigator
const originalCrypto = globalThis.crypto
const originalAtob = globalThis.atob

describe('offline queue behaviour', () => {
  beforeEach(() => {
    legacyStore.clear()
    Object.keys(dexieHarness.tables).forEach((name) => {
      dexieHarness.tables[name] = []
    })
    globalThis.window = {
      dispatchEvent: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }
    setNavigator({ onLine: false })
    let counter = 0
    defineGlobal('crypto', {
      randomUUID: () => {
        counter += 1
        return `uuid-${counter}`
      },
    })
    defineGlobal('atob', (value) => Buffer.from(value, 'base64').toString('binary'))
    vi.spyOn(api, 'get').mockResolvedValue({ data: [] })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    setNavigator(originalNavigator)
    if (originalCrypto) {
      defineGlobal('crypto', originalCrypto)
    }
    if (originalAtob) {
      defineGlobal('atob', originalAtob)
    }
  })

  it('saves daily log entries with attachments when offline', async () => {
    await enqueueDailyLogSubmission({
      logPayload: { farm: 1, date: '2025-09-23' },
      activityPayload: { task: 5 },
      attachments: [
        { name: 'note.txt', type: 'text/plain', size: 4, data: makeDataUrl('test') },
      ],
    })

    const details = await getOfflineQueueDetails()
    expect(details.dailyLogs).toHaveLength(1)
    expect(details.dailyLogs[0].attachments).toHaveLength(1)
    expect(details.dailyLogs[0].attachments[0].name).toBe('note.txt')
  })

  it('stores daily log queue envelopes without backend-owned cost fields', async () => {
    await enqueueDailyLogSubmission({
      logPayload: { farm: 21, date: '2026-04-25' },
      activityPayload: {
        task: 5,
        crop: 4,
        locations: [9],
        cost_materials: '12.123456',
        cost_total: '13.999999',
        smart_card_stack: [{ card_key: 'materials' }],
      },
      attachments: [],
    })

    const details = await getOfflineQueueDetails()
    expect(details.dailyLogs).toHaveLength(1)
    expect(details.dailyLogs[0].activityPayload.cost_materials).toBeUndefined()
    expect(details.dailyLogs[0].activityPayload.cost_total).toBeUndefined()
    expect(details.dailyLogs[0].activityPayload.smart_card_stack).toBeUndefined()
    expect(details.dailyLogs[0].activityPayload.task).toBe(5)
  })

  it('flushes daily logs without cost fields and records local sync history', async () => {
    await enqueueDailyLogSubmission({
      logPayload: { farm: 21, log_date: '2026-04-25' },
      activityPayload: {
        task: 5,
        locations: [9],
        cost_materials: '12.123456',
        cost_total: '13.999999',
      },
      attachments: [],
    })
    vi.spyOn(api, 'post').mockResolvedValue({
      data: { log_id: 101, activity_id: 202 },
    })

    const result = await flushQueue()

    expect(result.processedDailyLogs).toBe(1)
    expect(api.post).toHaveBeenCalledWith(
      '/offline/daily-log-replay/atomic/',
      expect.objectContaining({
        activity: expect.not.objectContaining({
          cost_materials: expect.anything(),
          cost_total: expect.anything(),
        }),
      }),
      expect.any(Object),
    )

    const details = await getOfflineQueueDetails()
    expect(details.dailyLogs).toHaveLength(0)
    expect(details.syncRecords[0]).toMatchObject({
      category: 'daily_log',
      status: 'success',
      local: true,
    })
  })

  it('clears queues via clearOfflineQueue helper', async () => {
    await enqueueDailyLogSubmission({
      logPayload: { farm: 2, date: '2025-09-23' },
      activityPayload: { task: 9 },
      attachments: [],
    })

    await clearOfflineQueue('daily-log')
    const details = await getOfflineQueueDetails()
    expect(details.dailyLogs).toHaveLength(0)
  })

  it('requeues failed daily log items and resets counters', async () => {
    legacyStore.set('offline-failures::user:anonymous', {
      requests: [],
      dailyLogs: [
        {
          id: 'failed-1',
          queuedAt: '2025-01-01T00:00:00.000Z',
          attempts: 3,
          nextAttemptAt: '2025-01-02T00:00:00.000Z',
          lastError: 'HTTP 500',
          logPayload: { farm: 7, date: '2025-09-24' },
          activityPayload: { task: 11 },
          attachments: [],
        },
      ],
    })

    const requeued = await requeueFailedItems('daily-log')
    expect(requeued).toBe(1)

    const details = await getOfflineQueueDetails()
    expect(details.dailyLogs).toHaveLength(1)
    expect(details.failedDailyLogs).toHaveLength(0)
  })

  it('removes queued and failed items via removeOfflineQueueItem', async () => {
    await enqueueDailyLogSubmission({
      logPayload: { farm: 5, date: '2025-09-25' },
      activityPayload: { task: 12 },
      attachments: [],
    })
    const detailsBefore = await getOfflineQueueDetails()
    const queuedId = detailsBefore.dailyLogs[0].id

    legacyStore.set('offline-failures::user:anonymous', {
      requests: [],
      dailyLogs: [
        {
          id: 'failed-remove',
          queuedAt: '2025-01-04T00:00:00.000Z',
          attempts: 2,
          nextAttemptAt: '2025-01-05T00:00:00.000Z',
          lastError: 'HTTP 500',
        },
      ],
    })
    await requeueFailedItems('daily-log')

    const removedQueued = await removeOfflineQueueItem('daily-log', queuedId)
    expect(removedQueued).toBe(true)

    const migratedDetails = await getOfflineQueueDetails()
    const failedId = migratedDetails.dailyLogs[0]?.id
    const removedFailed = await removeOfflineQueueItem('daily-log', failedId)
    expect(removedFailed).toBe(true)
  })

  it('normalizes service scopes when queuing new daily logs', async () => {
    await enqueueDailyLogSubmission({
      logPayload: { farm: 3, date: '2025-10-01' },
      activityPayload: {
        service_counts_payload: [
          { variety_id: 77, service_count: 4, service_type: '', service_scope: '' },
        ],
      },
      attachments: [],
      meta: {
        farmId: 3,
        date: '2025-10-01',
        serviceCounts: [
          { variety_id: 77, service_count: 4, service_scope: null, service_type: '' },
        ],
      },
    })

    const details = await getOfflineQueueDetails()
    expect(details.dailyLogs).toHaveLength(1)
    const [entry] = details.dailyLogs
    expect(entry.meta).toBeTruthy()
    expect(entry.meta.serviceCounts).toHaveLength(1)
    expect(entry.meta.serviceCounts[0].service_scope).toBe('general')
    expect(entry.meta.serviceCounts[0].service_type).toBe('general')
    expect(entry.activityPayload.service_counts_payload[0].service_scope).toBe('general')
    expect(entry.activityPayload.service_counts_payload[0].service_type).toBe('general')
  })

  it('repairs legacy daily log entries without service scopes', async () => {
    legacyStore.set('offline-daily-logs::user:anonymous', [
      {
        id: 'legacy-1',
        type: 'daily-log',
        queuedAt: '2025-01-05T00:00:00.000Z',
        attempts: 0,
        nextAttemptAt: '2025-01-05T00:00:00.000Z',
        logPayload: { farm: 9, date: '2025-10-02' },
        activityPayload: {
          service_counts_payload: [{ variety_id: 88, service_count: 6, service_type: '' }],
        },
        meta: {
          farmId: 9,
          date: '2025-10-02',
          serviceCounts: [{ variety_id: 88, service_count: 6, service_type: '' }],
        },
        attachments: [],
      },
    ])

    const details = await getOfflineQueueDetails()
    expect(details.dailyLogs).toHaveLength(1)
  })

  it('limits returned queue details and reports meta stats', async () => {
    for (let index = 0; index < 5; index += 1) {
      await enqueueDailyLogSubmission({
        logPayload: { farm: 1, date: `2025-10-0${index + 1}` },
        activityPayload: { task: index + 1 },
        attachments: [],
      })
    }

    const details = await getOfflineQueueDetails({ limit: 2 })
    expect(details.dailyLogs).toHaveLength(2)
    expect(details.meta.dailyLogs).toMatchObject({ total: 5, returned: 2, truncated: true })
  })

  it('queues harvest replay entries in harvest_queue when offline', async () => {
    await HarvestLogs.create({
      farm_id: 4,
      crop_plan: 91,
      date: '2025-10-08',
      qty: '7.500',
    })

    const details = await getOfflineQueueDetails()
    expect(details.harvests).toHaveLength(1)
    expect(details.harvests[0].category).toBe('harvest')
  })

  it('queues custody replay entries in custody_queue when offline', async () => {
    await CustodyTransfers.issue({
      farm_id: 8,
      supervisor_id: 13,
      item_id: 21,
      from_location_id: 4,
      qty: '2.000',
    })

    const details = await getOfflineQueueDetails()
    expect(details.custody).toHaveLength(1)
    expect(details.custody[0].category).toBe('custody')
  })

  it('blocks strict finance routes from generic offline replay', async () => {
    await expect(
      safeRequest('post', '/finance/supplier-settlements/', { farm_id: 1, amount: '10.00' }),
    ).rejects.toThrow(/posture-only offline/i)
  })

  it('sends numeric log values when coming back online', async () => {
    const requestSpy = vi.spyOn(api, 'request').mockResolvedValue({ data: {} })
    const originalStatus = navigator.onLine

    try {
      navigator.onLine = true

      await safeRequest('post', '/activities/', { log: '123' })

      expect(requestSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          method: 'post',
          url: '/activities/',
          data: { log: 123 },
        }),
      )
    } finally {
      navigator.onLine = originalStatus
      requestSpy.mockRestore()
    }
  })
})
