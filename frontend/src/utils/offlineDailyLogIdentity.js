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

export const isUuidLike = (value) =>
  typeof value === 'string' &&
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)

export const resolveDailyLogReplayIdentity = (entry = {}, makeKey) => {
  const fallback = typeof makeKey === 'function' ? makeKey : () => null
  const payloadCandidate = resolveDailyLogPayloadUuid(entry)
  const idempotencyCandidate = entry.idempotency_key || entry.idempotencyKey
  return {
    payloadUuid: isUuidLike(payloadCandidate) ? payloadCandidate : fallback(),
    idempotencyKey: isUuidLike(idempotencyCandidate) ? idempotencyCandidate : fallback(),
  }
}

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
