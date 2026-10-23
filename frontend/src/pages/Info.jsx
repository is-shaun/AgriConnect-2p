import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert } from '../components/feedback'
import { Button, ButtonLink, Field, TextArea } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { endpoints } from '../services/api'
import { formatDate, formatPrice } from '../utils/format'
import { collectErrors, validateEmail, validateLength, validateName } from '../utils/validation'

function Prose({ title, intro, children }) {
  return (
    <article className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-4xl font-extrabold">{title}</h1>
      {intro && <p className="mt-4 text-lg text-ink-soft">{intro}</p>}
      <div className="mt-8 space-y-5 text-[1.05rem] leading-relaxed [&_h2]:mt-10 [&_h2]:text-2xl [&_h2]:font-bold [&_a]:font-bold [&_a]:text-forest [&_a]:underline [&_ul]:list-disc [&_ul]:pl-6 [&_li]:mt-1.5">
        {children}
      </div>
    </article>
  )
}

export function About() {
  const model = useApi(({ signal }) => endpoints.modelInfo({ signal }), [])
  const m = model.data
  return (
    <Prose
      title="About AgriConnect"
      intro="AgriConnect helps farmers, traders and agricultural workers check crop prices across Indian markets, follow how they change, and get a statistical estimate of where they may go next."
    >
      <h2>Where the prices come from</h2>
      <p>
        Every price record stores the crop, market, date, minimum, maximum and modal price, and its source. Records
        are added by importing data files in a documented format, for example a properly licensed export from Agmarknet
        or data.gov.in. Imported records are labelled <strong>Imported</strong>.
      </p>
      <p>
        This installation ships with a <strong>synthetic demo dataset</strong> so the app can be tried without real
        data. Demo records are always labelled <strong>Demo</strong> and must not be used as real market rates.
      </p>
      <h2>How price estimates work</h2>
      <p>
        Prices are grouped into weekly averages for each crop and market. A machine-learning model looks at the latest
        weeks (recent changes, short and long averages, volatility and time of year) and estimates the price 1, 2 or 4 weeks
        later. Several models were compared on weeks they had never seen, including the simple rule “next price equals
        today’s price”, and the most accurate one was kept.
      </p>
      {m?.available && (
        <ul>
          <li>Current model: {m.model_name.replaceAll('_', ' ')}, trained {formatDate(m.trained_at)}.</li>
          <li>Average miss on held-out weeks: {formatPrice(m.test_metrics.mae)} per quintal ({m.test_metrics.mape_pct.toFixed(1)}%).</li>
          <li>Same test for “price stays the same”: {formatPrice(m.test_metrics.baseline_mae)} per quintal.</li>
          {m.is_demo && <li><strong>This model was trained on synthetic data.</strong> Its accuracy says nothing about real markets.</li>}
        </ul>
      )}
      <p>
        Estimates are not guarantees. Weather, government procurement, export rules and transport can move prices in
        ways no model built on past prices can foresee.
      </p>
      <div className="flex flex-wrap gap-3 pt-4">
        <ButtonLink to="/markets">Browse market prices</ButtonLink>
        <ButtonLink to="/contact" variant="secondary">Contact us</ButtonLink>
      </div>
    </Prose>
  )
}

export function Contact() {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' })
  const [errors, setErrors] = useState({})
  const [status, setStatus] = useState(null)
  const [sending, setSending] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    const errs = collectErrors({
      name: validateName(form.name),
      email: validateEmail(form.email),
      subject: validateLength(form.subject, { label: 'a subject', min: 3, max: 150 }),
      message: validateLength(form.message, { label: 'a message', min: 10, max: 5000 }),
    })
    setErrors(errs)
    setStatus(null)
    if (Object.keys(errs).length) return
    setSending(true)
    try {
      const res = await endpoints.contact({
        name: form.name.trim(), email: form.email.trim(), subject: form.subject.trim(), message: form.message.trim(),
      })
      setForm({ name: '', email: '', subject: '', message: '' })
      setStatus({ tone: 'success', text: res.message })
    } catch (err) {
      if (err.code === 'validation_error') setErrors(err.details)
      else setStatus({ tone: 'error', text: err.message })
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1fr_1.3fr]">
      <div>
        <h1 className="text-4xl font-extrabold">Contact us</h1>
        <p className="mt-4 text-lg text-ink-soft">
          Ask a question, report a wrong price, or tell us which markets and crops you would like to see.
        </p>
        <p className="mt-4 text-ink-soft">We read every message. Please do not include passwords or bank details.</p>
      </div>
      <form onSubmit={submit} noValidate className="space-y-5 rounded-xl border border-line bg-white p-6">
        {status && <Alert tone={status.tone}>{status.text}</Alert>}
        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="Your name" autoComplete="name" value={form.name} error={errors.name} onChange={set('name')} />
          <Field label="Email" type="email" autoComplete="email" value={form.email} error={errors.email} onChange={set('email')} />
        </div>
        <Field label="Subject" value={form.subject} error={errors.subject} onChange={set('subject')} maxLength={150} />
        <TextArea label="Message" value={form.message} error={errors.message} onChange={set('message')} maxLength={5000}
          hint={`${form.message.length} / 5000 characters`} />
        <Button type="submit" loading={sending}>Send message</Button>
      </form>
    </div>
  )
}

function ReviewNotice() {
  return (
    <Alert tone="warning" title="Placeholder text: needs legal review">
      This page is a template and has not been reviewed by a lawyer. Replace it before running AgriConnect for real users.
    </Alert>
  )
}

export function Privacy() {
  return (
    <Prose title="Privacy notice">
      <ReviewNotice />
      <h2>What we store</h2>
      <ul>
        <li>Your name, email address and a one-way hash of your password (never the password itself).</li>
        <li>The price estimates you request, linked to your account.</li>
        <li>Messages you send through the contact form.</li>
      </ul>
      <h2>Cookies</h2>
      <p>
        We use a session cookie to keep you logged in and a security cookie that protects forms from cross-site requests.
        The browser also stores your recently viewed crops locally on your device. We use no advertising or tracking cookies.
      </p>
      <h2>Your choices</h2>
      <p>You can update your details on your profile page. To delete your account, <Link to="/contact">contact us</Link>.</p>
    </Prose>
  )
}

export function Terms() {
  return (
    <Prose title="Terms of use">
      <ReviewNotice />
      <h2>Information only</h2>
      <p>
        Prices and estimates on AgriConnect are provided for information. Estimates are statistical and may be wrong.
        Do not rely on them alone for selling, buying or financial decisions.
      </p>
      <h2>Demo data</h2>
      <p>Records and estimates marked “Demo” are synthetic and do not describe any real market.</p>
      <h2>Your account</h2>
      <p>Keep your password private. Do not misuse the service or try to access other people’s data.</p>
    </Prose>
  )
}

export function NotFound() {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center px-4 py-24 text-center">
      <p className="font-display text-7xl font-extrabold text-sprout [-webkit-text-stroke:2px_var(--color-forest)]">404</p>
      <h1 className="mt-4 text-3xl font-extrabold">This page does not exist</h1>
      <p className="mt-2 text-ink-soft">The link may be broken or the page may have moved.</p>
      <div className="mt-6 flex gap-3">
        <ButtonLink to="/">Go to the home page</ButtonLink>
        <ButtonLink to="/markets" variant="secondary">Browse prices</ButtonLink>
      </div>
    </div>
  )
}
