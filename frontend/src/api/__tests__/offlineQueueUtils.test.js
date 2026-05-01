import { describe, expect, it } from 'vitest'

import { normalizeDailyLogQueueEntry } from '../offlineQueueUtils'
import {
  buildDailyLogIdempotencyRotationPatch,
  isIdempotencyMismatch409,
  resolveDailyLogReplayIdentity,
} from '../../utils/offlineDailyLogIdentity'
import { normalizeActivityForeignKeys } from '../../utils/dailyLogPayload'
import { isStaleSyncingQueueItem } from '../../offline/dexie_db'

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
      queue_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      payload_uuid: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      uuid: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
      idempotency_key: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
      status: 'dead_letter',
      dead_letter: true,
      farm_id: '21',
      meta: { taskName: 'all' },
    }

    const patch = buildDailyLogIdempotencyRotationPatch(entry, {
      newKey: 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
      nowIsoValue: '2026-04-27T18:00:00.000Z',
      lastError: 'HTTP 409',
    })
    const replayIdentity = resolveDailyLogReplayIdentity(
      { ...entry, ...patch },
      () => 'ffffffff-ffff-4fff-8fff-ffffffffffff',
    )

    expect(patch).toMatchObject({
      status: 'pending',
      dead_letter: false,
      idempotency_key: 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
      previous_idempotency_key: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
      retry_count: 0,
    })
    expect(patch).not.toHaveProperty('uuid')
    expect(patch).not.toHaveProperty('payload_uuid')
    expect(replayIdentity.payloadUuid).toBe('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb')
    expect(replayIdentity.idempotencyKey).toBe('eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee')
  })

  it('repairs legacy non-UUID replay idempotency keys before HTTP replay', () => {
    const replayIdentity = resolveDailyLogReplayIdentity(
      {
        payload_uuid: '6ef6e28e-3d06-4821-b831-174a54c2e4ea',
        idempotency_key: '1777468364956-edpi3fv0vxe',
      },
      () => '12345678-1234-4234-8234-123456789abc',
    )

    expect(replayIdentity.payloadUuid).toBe('6ef6e28e-3d06-4821-b831-174a54c2e4ea')
    expect(replayIdentity.idempotencyKey).toBe('12345678-1234-4234-8234-123456789abc')
  })

  it('drops blank FK aliases and preserves valid legacy FK ids for replay payloads', () => {
    const normalized = normalizeActivityForeignKeys({
      well_id: '32',
      asset: '31',
      asset_id: '31',
      task: '222',
      crop: '259',
      tree_loss_reason: '',
      tree_loss_reason_id: '',
      variety: '',
      product: '32',
      crop_plan: '',
    })

    expect(normalized).toMatchObject({
      well_asset_id: 32,
      asset_id: 31,
      task_id: 222,
      crop_id: 259,
      product_id: 32,
    })
    expect(normalized).not.toHaveProperty('well_id')
    expect(normalized).not.toHaveProperty('asset')
    expect(normalized).not.toHaveProperty('task')
    expect(normalized).not.toHaveProperty('crop')
    expect(normalized).not.toHaveProperty('tree_loss_reason')
    expect(normalized).not.toHaveProperty('tree_loss_reason_id')
    expect(normalized).not.toHaveProperty('variety')
    expect(normalized).not.toHaveProperty('crop_plan')
    expect(normalized).not.toHaveProperty('crop_plan_id')
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

  it('detects stale syncing daily-log queue items without changing replay identity', () => {
    const now = new Date('2026-04-28T08:00:00.000Z').getTime()
    expect(
      isStaleSyncingQueueItem(
        {
          status: 'syncing',
          updated_at: '2026-04-28T07:58:30.000Z',
          payload_uuid: 'payload-23',
          idempotency_key: 'attempt-key',
        },
        now,
      ),
    ).toBe(true)
    expect(
      isStaleSyncingQueueItem(
        {
          status: 'syncing',
          updated_at: '2026-04-28T07:59:30.000Z',
          payload_uuid: 'payload-23',
          idempotency_key: 'attempt-key',
        },
        now,
      ),
    ).toBe(false)
  })
})
