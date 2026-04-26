/**
 * [AGRI-GUARDIAN] Unified API Error Parser
 * Extracts structured error codes and messages from the backend's
 * unified error response format.
 *
 * Backend error format:
 *   { error: { code: "VALIDATION_ERROR", message: "...", details: {...} } }
 *
 * Usage:
 *   import { parseApiError } from '../utils/apiErrors'
 *   try { await api.post(...) } catch (err) { const { code, message } = parseApiError(err) }
 */
import ar from '../i18n/ar'

const errorStrings = ar.errors || {}

/**
 * Parse a backend API error response into a structured { code, message, details } object.
 * Falls back gracefully for non-standard error shapes.
 *
 * @param {Error|Object} error - Axios error or raw error object
 * @returns {{ code: string, message: string, details: Object }}
 */
export function parseApiError(error) {
  // Case 1: Structured backend error
  const data = error?.response?.data
  if (data?.error?.code) {
    return {
      code: data.error.code,
      message: data.error.message || errorStrings[data.error.code] || 'خطأ غير محدد',
      details: data.error.details || {},
    }
  }

  // Case 2: DRF legacy format { detail: "..." }
  if (data?.detail) {
    return {
      code: _classifyFromStatus(error?.response?.status),
      message: String(data.detail),
      details: {},
    }
  }

  // Case 3: Network error (no response)
  if (!error?.response) {
    return {
      code: 'NETWORK_ERROR',
      message: errorStrings.networkError || 'تعذر الاتصال بالخادم',
      details: {},
    }
  }

  // Case 4: Unknown error shape
  return {
    code: 'UNKNOWN_ERROR',
    message: error?.message || 'حدث خطأ غير متوقع',
    details: {},
  }
}

/**
 * Get a user-friendly Arabic error message from an API error.
 * @param {Error|Object} error
 * @returns {string}
 */
export function getErrorMessage(error) {
  return parseApiError(error).message
}

/**
 * Check whether an error is a specific domain error code.
 * @param {Error|Object} error
 * @param {string} code - e.g. 'FISCAL_PERIOD_CLOSED'
 * @returns {boolean}
 */
export function isErrorCode(error, code) {
  return parseApiError(error).code === code
}

/**
 * Check if the error indicates the session has expired (401).
 * @param {Error|Object} error
 * @returns {boolean}
 */
export function isSessionExpired(error) {
  return error?.response?.status === 401
}

/**
 * Check if the error is a network connectivity issue.
 * @param {Error|Object} error
 * @returns {boolean}
 */
export function isNetworkError(error) {
  return !error?.response && error?.code !== 'ECONNABORTED'
}

// ──────────────────────────────────────────────────────────────────
// Internal helpers
// ──────────────────────────────────────────────────────────────────

function _classifyFromStatus(status) {
  const map = {
    400: 'VALIDATION_ERROR',
    401: 'AUTHENTICATION_FAILED',
    403: 'PERMISSION_DENIED',
    404: 'NOT_FOUND',
    429: 'THROTTLED',
    500: 'INTERNAL_ERROR',
  }
  return map[status] || 'UNKNOWN_ERROR'
}
