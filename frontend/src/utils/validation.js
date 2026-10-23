// Client-side checks mirror the server rules so people get instant feedback.
// The server re-validates everything; these are a convenience, not a security control.

const EMAIL_RE = /^[^@\s]{1,64}@[^@\s]+\.[A-Za-z]{2,}$/

export function validateEmail(v) {
  if (!v?.trim()) return 'Enter your email address.'
  if (!EMAIL_RE.test(v.trim())) return 'Enter a valid email address, like name@example.com.'
  return null
}

export function validatePassword(v) {
  if (!v) return 'Enter a password.'
  if (v.length < 8) return 'Use at least 8 characters.'
  if (v.length > 128) return 'Use at most 128 characters.'
  if (!/[A-Za-z]/.test(v) || !/\d/.test(v)) return 'Include at least one letter and one number.'
  return null
}

export function validateName(v) {
  if (!v?.trim()) return 'Enter your name.'
  if (v.trim().length < 2) return 'Use at least 2 characters.'
  if (v.trim().length > 100) return 'Use at most 100 characters.'
  return null
}

export function validateLength(v, { label, min = 1, max = 255 }) {
  const t = (v || '').trim()
  if (!t) return `Enter ${label}.`
  if (t.length < min) return `Use at least ${min} characters.`
  if (t.length > max) return `Use at most ${max} characters.`
  return null
}

/** Run a map of validators; returns an object containing only the failing fields. */
export function collectErrors(checks) {
  return Object.fromEntries(Object.entries(checks).filter(([, msg]) => Boolean(msg)))
}
