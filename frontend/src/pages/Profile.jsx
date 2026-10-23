import { useState } from 'react'
import { Alert, ErrorState, LoadingBlock } from '../components/feedback'
import { Button, Field, PageHeader, Panel } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useApi } from '../hooks/useApi'
import { endpoints } from '../services/api'
import { formatDate } from '../utils/format'
import { collectErrors, validateEmail, validateName, validatePassword } from '../utils/validation'

function useFormState(initial) {
  const [values, setValues] = useState(initial)
  const [errors, setErrors] = useState({})
  const [status, setStatus] = useState(null) // {tone, text}
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setValues((v) => ({ ...v, [k]: e.target.value }))
  return { values, setValues, errors, setErrors, status, setStatus, saving, setSaving, set }
}

export default function Profile() {
  const { setUser } = useAuth()
  const profile = useApi(({ signal }) => endpoints.profile({ signal }), [])
  // Keep showing the forms during a background reload so their status messages survive.
  if (profile.loading && !profile.data) return <LoadingBlock label="Loading profile" />
  if (profile.error && !profile.data) return <ErrorState error={profile.error} onRetry={profile.reload} />
  const { user, stats } = profile.data
  return (
    <>
      <PageHeader title="Your profile" description="Update your name, email address or password." />
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <DetailsForm user={user} onSaved={(u) => { setUser(u); profile.reload() }} />
          <PasswordForm />
        </div>
        <Panel title="Account">
          <dl className="space-y-3 text-sm">
            <div><dt className="text-ink-soft">Member since</dt><dd className="font-bold">{formatDate(user.created_at)}</dd></div>
            <div><dt className="text-ink-soft">Account type</dt><dd className="font-bold capitalize">{user.role}</dd></div>
            <div><dt className="text-ink-soft">Price estimates requested</dt><dd className="font-bold">{stats.predictions}</dd></div>
          </dl>
        </Panel>
      </div>
    </>
  )
}

function DetailsForm({ user, onSaved }) {
  const f = useFormState({ name: user.name, email: user.email, current_password: '' })
  const emailChanged = f.values.email.trim().toLowerCase() !== user.email

  const submit = async (e) => {
    e.preventDefault()
    const errs = collectErrors({
      name: validateName(f.values.name),
      email: validateEmail(f.values.email),
      current_password: emailChanged && !f.values.current_password ? 'Enter your current password to change your email.' : null,
    })
    f.setErrors(errs)
    f.setStatus(null)
    if (Object.keys(errs).length) return
    const payload = {}
    if (f.values.name.trim() !== user.name) payload.name = f.values.name.trim()
    if (emailChanged) {
      payload.email = f.values.email.trim()
      payload.current_password = f.values.current_password
    }
    if (!Object.keys(payload).length) return f.setStatus({ tone: 'info', text: 'Nothing has changed.' })
    f.setSaving(true)
    try {
      const { user: updated } = await endpoints.updateProfile(payload)
      f.setValues({ name: updated.name, email: updated.email, current_password: '' })
      f.setStatus({ tone: 'success', text: 'Profile saved.' })
      onSaved(updated)
    } catch (err) {
      if (err.code === 'validation_error') f.setErrors(err.details)
      else f.setStatus({ tone: 'error', text: err.message })
    } finally {
      f.setSaving(false)
    }
  }

  return (
    <Panel title="Details">
      <form onSubmit={submit} noValidate className="space-y-5 max-w-lg">
        {f.status && <Alert tone={f.status.tone}>{f.status.text}</Alert>}
        <Field label="Full name" autoComplete="name" value={f.values.name} error={f.errors.name} onChange={f.set('name')} />
        <Field label="Email" type="email" autoComplete="email" value={f.values.email} error={f.errors.email} onChange={f.set('email')} />
        {emailChanged && (
          <Field label="Current password" type="password" autoComplete="current-password" value={f.values.current_password}
            error={f.errors.current_password} hint="Needed to confirm an email change." onChange={f.set('current_password')} />
        )}
        <Button type="submit" loading={f.saving}>Save profile</Button>
      </form>
    </Panel>
  )
}

function PasswordForm() {
  const f = useFormState({ current_password: '', new_password: '', confirm: '' })
  const submit = async (e) => {
    e.preventDefault()
    const errs = collectErrors({
      current_password: f.values.current_password ? null : 'Enter your current password.',
      new_password: validatePassword(f.values.new_password),
      confirm: f.values.confirm !== f.values.new_password ? 'The passwords do not match.' : null,
    })
    f.setErrors(errs)
    f.setStatus(null)
    if (Object.keys(errs).length) return
    f.setSaving(true)
    try {
      await endpoints.updateProfile({ current_password: f.values.current_password, new_password: f.values.new_password })
      f.setValues({ current_password: '', new_password: '', confirm: '' })
      f.setStatus({ tone: 'success', text: 'Password changed.' })
    } catch (err) {
      if (err.code === 'validation_error') f.setErrors(err.details)
      else f.setStatus({ tone: 'error', text: err.message })
    } finally {
      f.setSaving(false)
    }
  }
  return (
    <Panel title="Password">
      <form onSubmit={submit} noValidate className="space-y-5 max-w-lg">
        {f.status && <Alert tone={f.status.tone}>{f.status.text}</Alert>}
        <Field label="Current password" type="password" autoComplete="current-password" value={f.values.current_password}
          error={f.errors.current_password} onChange={f.set('current_password')} />
        <Field label="New password" type="password" autoComplete="new-password" value={f.values.new_password}
          error={f.errors.new_password} hint="At least 8 characters, with a letter and a number." onChange={f.set('new_password')} />
        <Field label="Confirm new password" type="password" autoComplete="new-password" value={f.values.confirm}
          error={f.errors.confirm} onChange={f.set('confirm')} />
        <Button type="submit" variant="dark" loading={f.saving}>Change password</Button>
      </form>
    </Panel>
  )
}
