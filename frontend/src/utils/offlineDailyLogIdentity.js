export const IDEMPOTENCY_MISMATCH_CODE = 'IDEMPOTENCY_MISMATCH'

export const isIdempotencyMismatch409 = (error) => {
  const response = error?.response
  if (response?.status !== 409) return false
  const data = response?.data || {}
  if (data.code === IDEMPOTENCY_MISMATCH_CODE) return true
  const detail = String(data.detail || data.error || error?.message || '').toLowerCase()
  return (
    detail.includes('idempotency') ||
    detail.includes('different payload') ||
    detail.includes('بيانات مختلفة') ||
    detail.includes('مسبق')
  )
}

export const resolveDailyLogPayloadUuid = (entry = {}) =>
  entry.payload_uuid ||
  entry.payloadUuid ||
  entry.queue_id ||
  entry.queueId ||
  entry.uuid ||
  entry.idempotency_key ||
  entry.idempotencyKey ||
  entry.id ||
  null

export const resolveDailyLogReplayIdentity = (entry = {}, makeKey) => ({
  payloadUuid: resolveDailyLogPayloadUuid(entry),
  idempotencyKey: entry.idempotency_key || entry.idempotencyKey || makeKey(),
})

export const buildDailyLogIdempotencyRotationPatch = (
  entry = {},
  { newKey, nowIsoValue, lastError = null } = {},
) => {
  const previousKey = entry.idempotency_key || entry.idempotencyKey || null
  const rotatedAt = nowIsoValue || new Date().toISOString()
  return {
    status: 'pending',
    dead_letter: false,
    idempotency_key: newKey,
    previous_idempotency_key: previousKey,
    retry_count: 0,
    next_attempt_at: rotatedAt,
    last_error: lastError,
    dead_letter_reason: null,
    meta: {
      ...(entry.meta || {}),
      ...(previousKey ? { previous_idempotency_key: previousKey } : {}),
      idempotency_key_rotated_at: rotatedAt,
    },
    updated_at: rotatedAt,
  }
}
