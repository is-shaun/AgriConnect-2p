import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import Logo from '../components/Logo'
import { Alert } from '../components/feedback'
import { Button, Field } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { collectErrors, validateEmail, validateName, validatePassword } from '../utils/validation'

function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="min-h-screen grid lg:grid-cols-[1fr_minmax(0,560px)]">
      <div className="hidden lg:flex flex-col justify-between bg-forest p-10 text-chalk">
        <Logo light />
        <blockquote className="max-w-md">
          <p className="font-display text-3xl font-bold leading-snug text-white">
            “Selling two weeks later can mean a very different price. Seeing the trend first helps.”
          </p>
          <footer className="mt-4 text-chalk/75">Why we built AgriConnect</footer>
        </blockquote>
        <p className="text-sm text-chalk/60">Prices and estimates for crops across Indian mandis.</p>
      </div>
      <main id="main" className="flex items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-8"><Logo /></div>
          <h1 className="text-3xl font-extrabold">{title}</h1>
          <p className="mt-2 text-ink-soft">{subtitle}</p>
          <div className="mt-8">{children}</div>
          <p className="mt-6 text-ink-soft">{footer}</p>
        </div>
      </main>
    </div>
  )
}

function applyServerError(err, setErrors, setFormError) {
  if (err.code === 'validation_error') {
    setErrors(err.details || {})
    setFormError(err.details?._ || null)
  } else {
    setFormError(err.message)
  }
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const notice = location.state?.message
  const warning = location.state?.notice

  const submit = async (e) => {
    e.preventDefault()
    const errs = collectErrors({ email: validateEmail(form.email), password: form.password ? null : 'Enter your password.' })
    setErrors(errs)
    setFormError(null)
    if (Object.keys(errs).length) return
    setSubmitting(true)
    try {
      await login({ email: form.email.trim(), password: form.password })
      navigate(location.state?.from || '/dashboard', { replace: true })
    } catch (err) {
      applyServerError(err, setErrors, setFormError)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Log in"
      subtitle="Welcome back. Log in to see your dashboard and price estimates."
      footer={<>New to AgriConnect? <Link to="/register" className="font-bold text-forest underline underline-offset-4">Create an account</Link></>}
    >
      <form onSubmit={submit} noValidate className="space-y-5">
        {notice && !formError && <Alert tone="success">{notice}</Alert>}
        {warning && !formError && <Alert tone="warning">{warning}</Alert>}
        {formError && <Alert tone="error">{formError}</Alert>}
        <Field label="Email" type="email" autoComplete="email" value={form.email} error={errors.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <Field label="Password" type="password" autoComplete="current-password" value={form.password} error={errors.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <Button type="submit" loading={submitting} className="w-full">Log in</Button>
      </form>
    </AuthShell>
  )
}

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    const errs = collectErrors({
      name: validateName(form.name),
      email: validateEmail(form.email),
      password: validatePassword(form.password),
      confirm: form.confirm !== form.password ? 'The passwords do not match.' : null,
    })
    setErrors(errs)
    setFormError(null)
    if (Object.keys(errs).length) return
    setSubmitting(true)
    try {
      await register({ name: form.name.trim(), email: form.email.trim(), password: form.password })
      navigate('/dashboard', { replace: true })
    } catch (err) {
      applyServerError(err, setErrors, setFormError)
    } finally {
      setSubmitting(false)
    }
  }

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  return (
    <AuthShell
      title="Create your account"
      subtitle="Free to use. Your account keeps a history of the price estimates you request."
      footer={<>Already have an account? <Link to="/login" className="font-bold text-forest underline underline-offset-4">Log in</Link></>}
    >
      <form onSubmit={submit} noValidate className="space-y-5">
        {formError && <Alert tone="error">{formError}</Alert>}
        <Field label="Full name" autoComplete="name" value={form.name} error={errors.name} onChange={set('name')} />
        <Field label="Email" type="email" autoComplete="email" value={form.email} error={errors.email} onChange={set('email')} />
        <Field label="Password" type="password" autoComplete="new-password" value={form.password} error={errors.password}
          hint="At least 8 characters, with a letter and a number." onChange={set('password')} />
        <Field label="Confirm password" type="password" autoComplete="new-password" value={form.confirm} error={errors.confirm}
          onChange={set('confirm')} />
        <Button type="submit" loading={submitting} className="w-full">Create account</Button>
        <p className="text-xs text-ink-soft">
          By creating an account you agree to the <Link to="/terms" className="underline">terms</Link> and{' '}
          <Link to="/privacy" className="underline">privacy notice</Link>.
        </p>
      </form>
    </AuthShell>
  )
}
