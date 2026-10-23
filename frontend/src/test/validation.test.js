import { describe, expect, it } from 'vitest'
import { collectErrors, validateEmail, validateLength, validateName, validatePassword } from '../utils/validation'

describe('client validation mirrors server rules', () => {
  it('validates email', () => {
    expect(validateEmail('')).toMatch(/Enter/)
    expect(validateEmail('farmer@')).toMatch(/valid/)
    expect(validateEmail('farmer@example.com')).toBeNull()
  })
  it('validates password strength', () => {
    expect(validatePassword('short1')).toMatch(/8/)
    expect(validatePassword('allletters')).toMatch(/letter and one number/)
    expect(validatePassword('harvest2026')).toBeNull()
  })
  it('validates names and lengths', () => {
    expect(validateName('A')).toMatch(/2/)
    expect(validateName('Asha')).toBeNull()
    expect(validateLength('hi', { label: 'a subject', min: 3 })).toMatch(/3/)
  })
  it('collects only failing fields', () => {
    expect(collectErrors({ a: null, b: 'bad', c: undefined })).toEqual({ b: 'bad' })
  })
})
