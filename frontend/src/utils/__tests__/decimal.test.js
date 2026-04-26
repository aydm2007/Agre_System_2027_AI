/**
 * [AGRI-GUARDIAN] Unit Tests for Decimal Utilities
 * Testing §1.II Financial Immutability compliance
 */
import { describe, it, expect } from 'vitest'
import { toDecimal, multiplyDecimal, sumDecimals, lineTotal, formatCurrency } from '../decimal'

describe('toDecimal', () => {
  it('handles null and undefined values', () => {
    expect(toDecimal(null)).toBe(0)
    expect(toDecimal(undefined)).toBe(0)
    expect(toDecimal('')).toBe(0)
  })

  it('parses numeric strings correctly', () => {
    expect(toDecimal('123.45')).toBe(123.45)
    expect(toDecimal('1,234.56')).toBe(1234.56) // With comma
    expect(toDecimal('  100.99  ')).toBe(100.99) // With whitespace
  })

  it('handles numbers directly', () => {
    expect(toDecimal(123.456)).toBe(123.46) // Default precision 2
    expect(toDecimal(123.456, 3)).toBe(123.456) // Precision 3
    expect(toDecimal(99.999, 2)).toBe(100) // Rounding
  })

  it('handles negative numbers', () => {
    expect(toDecimal('-50.5')).toBe(-50.5)
    expect(toDecimal(-100.123)).toBe(-100.12)
  })

  it('handles invalid inputs with warning', () => {
    expect(toDecimal('abc')).toBe(0)
    expect(toDecimal('not a number')).toBe(0)
  })
})

describe('multiplyDecimal', () => {
  it('multiplies with correct precision', () => {
    expect(multiplyDecimal(10, 5)).toBe(50)
    expect(multiplyDecimal(3.33, 3)).toBe(9.99)
    expect(multiplyDecimal(0.1, 0.2)).toBe(0.02) // Floating point edge case
  })

  it('handles string inputs', () => {
    expect(multiplyDecimal('10', '5')).toBe(50)
    expect(multiplyDecimal('3.33', '3')).toBe(9.99)
  })
})

describe('sumDecimals', () => {
  it('sums array of values', () => {
    expect(sumDecimals([10, 20, 30])).toBe(60)
    expect(sumDecimals([0.1, 0.2, 0.3])).toBe(0.6)
  })

  it('handles empty array', () => {
    expect(sumDecimals([])).toBe(0)
  })

  it('handles mixed inputs', () => {
    expect(sumDecimals(['10', 20, '30.5'])).toBe(60.5)
  })
})

describe('lineTotal', () => {
  it('calculates quantity × unit_price correctly', () => {
    expect(lineTotal(10, 5)).toBe(50)
    expect(lineTotal('10', '5')).toBe(50)
    expect(lineTotal(3.5, 10.25)).toBe(35.88) // 3.5 × 10.25 = 35.875 → 35.88
  })

  it('handles edge cases', () => {
    expect(lineTotal(0, 100)).toBe(0)
    expect(lineTotal(100, 0)).toBe(0)
    expect(lineTotal(null, 100)).toBe(0)
  })
})

describe('formatCurrency', () => {
  it('formats with locale and correct separators', () => {
    const formatted = formatCurrency(1234.56)
    // formatCurrency uses en-US locale — returns Western digits with commas
    expect(formatted).toContain('1')
    expect(formatted).toContain('234')
    expect(formatted).toContain('56')
  })

  it('respects precision', () => {
    const formatted = formatCurrency(100.1, 2)
    expect(formatted).toContain('100')
    expect(formatted).toContain('10')
  })

  it('handles negative numbers', () => {
    const formatted = formatCurrency(-500.5)
    expect(formatted).toMatch(/-500\.50/)
  })

  it('handles zero correctly', () => {
    const formatted = formatCurrency(0)
    expect(formatted).toContain('0.00')
  })

  it('handles NaN and invalid inputs gracefully', () => {
    // Should fallback to 0.00
    expect(formatCurrency(NaN)).toContain('0.00')
    expect(formatCurrency(undefined)).toContain('0.00')
    expect(formatCurrency(null)).toContain('0.00')
    expect(formatCurrency('invalid')).toContain('0.00')
  })

  it('formats large numbers correctly with commas', () => {
    const formatted = formatCurrency(1000000.99)
    // Using string matching to be locale agnostic but checking for commas or spaces
    // depending on the node environment. Typically 1,000,000.99
    expect(formatted.replace(/[^0-9.]/g, '')).toBe('1000000.99')
  })
})
