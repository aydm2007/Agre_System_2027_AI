/**
 * Utility for robustly extracting human-readable Arabic error messages from API responses.
 * Handles DRF string arrays, objects, field-level errors, and Python stringified arrays.
 *
 * @param {Error} err The Axios error object
 * @param {string} fallbackMsg The default message if extraction fails
 * @returns {string} The extracted error message
 */
export function extractApiError(err, fallbackMsg = 'حدث خطأ غير معروف') {
  const errData = err?.response?.data
  if (!errData) {
    if (err?.message === 'Network Error') return 'خطأ في الاتصال بالخادم'
    return fallbackMsg
  }

  const extractMessage = (data) => {
    if (typeof data === 'string') {
      // Clean up python stringified arrays like "['لا يمكنك اعتماد...']"
      const match = data.match(/^\[['"](.*)['"]\]$/)
      return match ? match[1] : data
    }
    if (Array.isArray(data)) {
      return data.map(extractMessage).filter(Boolean).join(' | ')
    }
    if (typeof data === 'object' && data !== null) {
      const parts = []
      for (const [key, val] of Object.entries(data)) {
        const valStr = extractMessage(val)
        if (valStr) {
          parts.push(
            key === 'non_field_errors' || key === 'detail' || key === 'error'
              ? valStr
              : `${key}: ${valStr}`,
          )
        }
      }
      return parts.join(' | ')
    }
    return String(data)
  }

  const extracted = extractMessage(errData)
  return extracted || fallbackMsg
}
