import { describe, expect, it } from 'vitest'

import { normalizeDailyLogQueueEntry } from '../offlineQueueUtils'
import {
  buildDailyLogIdempotencyRotationPatch,
  isIdempotencyMismatch409,
  resolveDailyLogReplayIdentity,
} from '../../utils/offlineDailyLogIdentity'

describe('offlineQueueUtils', () => {
  it('normalizes legacy daily-log queue entries with farm data and equal distribution', () => {
    const normalized = normalizeDailyLogQueueEntry({
      uuid: 'legacy-1',
      category: 'daily_log',
      data: {
        farm: '21',
        date: '2026-04-27',
        task: '222',
        service_counts_payload: [
          {
            variety_id: 100,
            location_id: 123,
            service_count: '22',
            service_type: 'general',
            service_scope: 'location',
            distribution_mode: 'equal',
            distribution_factor: '',
          },
        ],
      },
    })

    expect(normalized.farm_id).toBe('21')
    expect(normalized.logPayload).toMatchObject({
      farm: '21',
      log_date: '2026-04-27',
    })
    expect(normalized.activityPayload.service_counts_payload[0]).toMatchObject({
      distribution_mode: 'uniform',
      service_scope: 'location',
    })
  })

  it('keeps payload uuid stable while rotating a failed daily-log idempotency key', () => {
    const entry = {
      id: 22,
      queue_id: 'queue-22',
      payload_uuid: 'payload-22',
      uuid: 'old-http-key',
      idempotency_key: 'old-http-key',
      status: 'dead_letter',
      dead_letter: true,
      farm_id: '21',
      meta: { taskName: 'all' },
    }

    const patch = buildDailyLogIdempotencyRotationPatch(entry, {
      newKey: 'new-http-key',
      nowIsoValue: '2026-04-27T18:00:00.000Z',
      lastError: 'HTTP 409',
    })
    const replayIdentity = resolveDailyLogReplayIdentity({ ...entry, ...patch }, () => 'fallback-key')

    expect(patch).toMatchObject({
      status: 'pending',
      dead_letter: false,
      idempotency_key: 'new-http-key',
      previous_idempotency_key: 'old-http-key',
      retry_count: 0,
    })
    expect(patch).not.toHaveProperty('uuid')
    expect(patch).not.toHaveProperty('payload_uuid')
    expect(replayIdentity.payloadUuid).toBe('payload-22')
    expect(replayIdentity.idempotencyKey).toBe('new-http-key')
  })

  it('detects 409 idempotency mismatch responses from backend and legacy detail text', () => {
    expect(
      isIdempotencyMismatch409({
        response: { status: 409, data: { code: 'IDEMPOTENCY_MISMATCH', detail: 'different' } },
      }),
    ).toBe(true)
    expect(
      isIdempotencyMismatch409({
        response: { status: 409, data: { detail: "تم استخدام المفتاح مسبقاً مع بيانات مختلفة." } },
      }),
    ).toBe(true)
    expect(isIdempotencyMismatch409({ response: { status: 400, data: {} } })).toBe(false)
  })
})
