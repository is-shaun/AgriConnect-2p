import { describe, expect, it } from 'vitest'
import { formatDate, formatPercent, formatPrice, formatUnit, locationLabel, percentChange } from '../utils/format'

describe('format helpers', () => {
  it('formats rupees with Indian digit grouping and no paise', () => {
    expect(formatPrice(245000.4)).toBe('₹2,45,000')
    expect(formatPrice(null)).toBe('—')
  })
  it('turns API units into readable text', () => {
    expect(formatUnit('Rs/quintal')).toBe('per quintal')
    expect(formatUnit('kg')).toBe('kg')
  })
  it('formats ISO calendar dates without timezone drift', () => {
    expect(formatDate('2026-10-16')).toMatch(/16 Oct 2026/)
    expect(formatDate('not a date')).toBe('—')
  })
  it('computes and formats percentage change', () => {
    expect(percentChange(100, 110)).toBeCloseTo(10)
    expect(formatPercent(-2.345)).toBe('−2.3%')
    expect(formatPercent(null)).toBe('—')
  })
  it('builds location labels', () => {
    expect(locationLabel({ market_name: 'Patna', district: 'Patna', state: 'Bihar' })).toBe('Patna, Bihar')
    expect(locationLabel({ market_name: 'Lasalgaon', district: 'Nashik', state: 'Maharashtra' })).toBe('Lasalgaon, Nashik, Maharashtra')
  })
})
