const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })
const plain = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })

/** ₹2,450 – prices are shown without paise; mandi prices are quoted in whole rupees. */
export function formatPrice(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return inr.format(Number(value))
}

export function formatNumber(value) {
  if (value === null || value === undefined) return '—'
  return plain.format(Number(value))
}

/** "Rs/quintal" -> "per quintal" */
export function formatUnit(unit) {
  if (!unit) return ''
  const m = /^Rs\.?\s*\/\s*(.+)$/i.exec(unit)
  return m ? `per ${m[1]}` : unit
}

const dateFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
const shortFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' })

function parseDate(value) {
  if (!value) return null
  // Treat plain YYYY-MM-DD as a calendar date (no timezone shift).
  const d = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

export function formatDate(value) {
  const d = parseDate(value)
  return d ? dateFmt.format(d) : '—'
}

export function formatShortDate(value) {
  const d = parseDate(value)
  return d ? shortFmt.format(d) : ''
}

export function percentChange(from, to) {
  if (!from || to === null || to === undefined) return null
  return ((Number(to) - Number(from)) / Number(from)) * 100
}

export function formatPercent(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  const sign = value > 0 ? '+' : value < 0 ? '−' : ''
  return `${sign}${Math.abs(value).toFixed(digits)}%`
}

export function locationLabel(loc) {
  if (!loc) return ''
  return `${loc.market_name}, ${loc.district === loc.market_name ? loc.state : `${loc.district}, ${loc.state}`}`
}
