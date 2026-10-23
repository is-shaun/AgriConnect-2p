import { useId } from 'react'
import { Link } from 'react-router-dom'
import { Loader2 } from 'lucide-react'

const base =
  'inline-flex items-center justify-center gap-2 font-bold rounded-lg transition-colors disabled:opacity-55 disabled:cursor-not-allowed min-h-11 px-4 text-[0.95rem]'
const variants = {
  primary: 'bg-leaf text-white hover:bg-leaf-dark',
  dark: 'bg-forest text-white hover:bg-forest-deep',
  secondary: 'bg-white text-forest border border-line hover:border-forest',
  ghost: 'text-forest hover:bg-sprout/60',
  danger: 'bg-white text-danger border border-danger/40 hover:bg-danger-soft',
}

export function Button({ variant = 'primary', loading = false, className = '', children, ...props }) {
  return (
    <button className={`${base} ${variants[variant]} ${className}`} disabled={loading || props.disabled} {...props}>
      {loading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  )
}

export function ButtonLink({ variant = 'primary', className = '', ...props }) {
  return <Link className={`${base} ${variants[variant]} ${className}`} {...props} />
}

const control =
  'w-full rounded-lg border bg-white px-3 min-h-11 text-ink placeholder:text-ink-soft/60 focus:outline-none focus:ring-3 focus:ring-leaf/25 focus:border-leaf'

function FieldShell({ id, label, hint, error, required, children }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-bold text-ink">
        {label}
        {required && <span className="text-ink-soft font-normal"> (required)</span>}
      </label>
      {children}
      {hint && !error && (
        <p id={`${id}-hint`} className="text-sm text-ink-soft">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  )
}

function describedBy(id, hint, error) {
  return error ? `${id}-error` : hint ? `${id}-hint` : undefined
}

export function Field({ label, hint, error, required, className = '', ...props }) {
  const id = useId()
  return (
    <FieldShell id={id} label={label} hint={hint} error={error} required={required}>
      <input
        id={id}
        className={`${control} ${error ? 'border-danger' : 'border-line'} ${className}`}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy(id, hint, error)}
        required={required}
        {...props}
      />
    </FieldShell>
  )
}

export function TextArea({ label, hint, error, required, ...props }) {
  const id = useId()
  return (
    <FieldShell id={id} label={label} hint={hint} error={error} required={required}>
      <textarea
        id={id}
        className={`${control} py-2.5 min-h-32 ${error ? 'border-danger' : 'border-line'}`}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy(id, hint, error)}
        required={required}
        {...props}
      />
    </FieldShell>
  )
}

export function SelectField({ label, hint, error, required, children, ...props }) {
  const id = useId()
  return (
    <FieldShell id={id} label={label} hint={hint} error={error} required={required}>
      <select
        id={id}
        className={`${control} pr-8 ${error ? 'border-danger' : 'border-line'}`}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy(id, hint, error)}
        required={required}
        {...props}
      >
        {children}
      </select>
    </FieldShell>
  )
}

export function Panel({ title, action, children, className = '', bodyClassName = '' }) {
  return (
    <section className={`bg-white rounded-xl border border-line ${className}`}>
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 px-5 pt-4 pb-3 border-b border-line/70">
          {title && <h2 className="text-lg font-bold">{title}</h2>}
          {action}
        </header>
      )}
      <div className={bodyClassName || 'p-5'}>{children}</div>
    </section>
  )
}

export function PageHeader({ title, description, actions }) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between mb-6">
      <div className="max-w-2xl">
        <h1 className="text-3xl md:text-[2.15rem] font-extrabold">{title}</h1>
        {description && <p className="mt-2 text-ink-soft">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}
