export function logRuntimeError(event, error, context = {}) {
  const requestId = error?.response?.data?.request_id || null
  const code = error?.response?.data?.code || null
  // Keep console for local diagnostics, but enforce structured output.
  console.error('[runtime-error]', {
    event,
    code,
    request_id: requestId,
    message: error?.message || error?.response?.data?.detail || 'unknown error',
    ...context,
  })
}
