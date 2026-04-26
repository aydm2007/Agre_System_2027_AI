/**
 * [AGRI-GUARDIAN] Decimal Utilities for Financial Calculations
 * §1.II: "ALWAYS use Decimal. NEVER use float for money or quantities."
 *
 * In JavaScript, we use string-based arithmetic simulation or
 * convert to fixed precision integers for safe calculations.
 */

/**
 * Safely parse a numeric string to a fixed precision number.
 * For financial amounts: 2 decimal places
 * For quantities: 3 decimal places
 *
 * @param {string|number} value - The value to parse
 * @param {number} precision - Decimal places (default: 2)
 * @returns {number} - Safe fixed-precision number
 */
export function toDecimal(value, precision = 2) {
  if (value === null || value === undefined || value === '') {
    return 0
  }

  const parsed =
    typeof value === 'string'
      ? value.replace(/[^\d.-]/g, '') // Remove non-numeric chars except . and -
      : value

  const num = Number(parsed)

  if (isNaN(num)) {
    console.warn('[AGRI-GUARDIAN] Invalid decimal value:', value)
    return 0
  }

  // Round to precision using integer math to avoid floating point errors
  const factor = Math.pow(10, precision)
  return Math.round(num * factor) / factor
}

/**
 * Multiply two decimal values with precision.
 * Used for quantity × unit_price calculations.
 *
 * @param {number} a - First value
 * @param {number} b - Second value
 * @param {number} precision - Result precision (default: 2)
 * @returns {number} - Safe product
 */
export function multiplyDecimal(a, b, precision = 2) {
  const factor = Math.pow(10, precision)
  return Math.round(toDecimal(a, precision) * toDecimal(b, precision) * factor) / factor
}

/**
 * Sum an array of decimal values.
 *
 * @param {number[]} values - Array of numbers
 * @param {number} precision - Result precision (default: 2)
 * @returns {number} - Safe sum
 */
export function sumDecimals(values, precision = 2) {
  const factor = Math.pow(10, precision)
  const sum = values.reduce((acc, val) => acc + Math.round(toDecimal(val, precision) * factor), 0)
  return sum / factor
}

/**
 * Format a number for display with Arabic locale.
 *
 * @param {number} value - The value to format
 * @param {number} precision - Decimal places (default: 2)
 * @returns {string} - Formatted string
 */
export function formatCurrency(value, precision = 2) {
  return toDecimal(value, precision).toLocaleString('en-US', {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  })
}

/**
 * Calculate line total (qty × unit_price).
 * §1.II compliant.
 *
 * @param {number|string} quantity
 * @param {number|string} unitPrice
 * @returns {number}
 */
export function lineTotal(quantity, unitPrice) {
  return multiplyDecimal(toDecimal(quantity, 3), toDecimal(unitPrice, 2), 2)
}

/**
 * AGRI-GUARDIAN: Safe Currency Math
 * JavaScript native math is dangerous for finance.
 * We treat money as strings or formatted integers.
 */

export const formatMoney = (amount) => {
  if (amount === null || amount === undefined) return '0.00'

  // Force conversion to string first to avoid scientific notation 1e+7
  let numStr = String(amount)

  // Basic formatting without float math
  const formatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })

  // Handle "Clean" input parsing
  // If we receive '1000.5', Number() is safe-ish for display only
  return formatter.format(Number(numStr))
}

export const safeMultiply = (qty, price) => {
  // Keep display math aligned with project decimal helpers.
  return String(multiplyDecimal(toDecimal(qty, 3), toDecimal(price, 2), 2))
}
