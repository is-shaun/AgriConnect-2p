import { AlertTriangle, CircleCheck, FlaskConical, Info, Loader2, RefreshCw, Sprout } from 'lucide-react'

export function Spinner({ label = 'Loading' }) {
  return (
    <span role="status" className="inline-flex items-center gap-2 text-ink-soft">
      <Loader2 className="size-5 animate-spin" aria-hidden="true" />
      <span>{label}…</span>
    </span>
  )
}

export function LoadingBlock({ label, rows = 4 }) {
  return (
    <div className="space-y-3" aria-busy="true">
      <Spinner label={label} />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-4 rounded bg-line/60 animate-pulse" style={{ width: `${90 - i * 12}%` }} />
      ))}
    </div>
  )
}

export function ErrorState({ error, onRetry, title = 'This section could not load' }) {
  return (
    <div role="alert" className="rounded-lg border border-danger/30 bg-danger-soft p-4 text-sm">
      <p className="flex items-center gap-2 font-bold text-danger">
        <AlertTriangle className="size-4" aria-hidden="true" />
        {title}
      </p>
      <p className="mt-1 text-ink">{error?.message || 'Something went wrong.'}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-3 inline-flex items-center gap-1.5 font-bold text-forest underline underline-offset-4">
          <RefreshCw className="size-4" aria-hidden="true" /> Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({ title, children, action, icon: Icon = Sprout }) {
  return (
    <div className="flex flex-col items-center text-center py-10 px-4">
      <span className="grid size-12 place-items-center rounded-full bg-sprout text-forest">
        <Icon className="size-6" aria-hidden="true" />
      </span>
      <h3 className="mt-4 text-lg font-bold">{title}</h3>
      {children && <p className="mt-1 max-w-md text-ink-soft">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

const alertStyles = {
  info: ['bg-sprout/60 border-leaf/30 text-ink', Info],
  success: ['bg-sprout border-leaf/40 text-ink', CircleCheck],
  warning: ['bg-mustard-soft border-mustard/50 text-ink', AlertTriangle],
  error: ['bg-danger-soft border-danger/30 text-ink', AlertTriangle],
}

export function Alert({ tone = 'info', title, children }) {
  const [cls, Icon] = alertStyles[tone]
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={`flex gap-3 rounded-lg border p-3.5 text-sm ${cls}`}>
      <Icon className="size-5 shrink-0 mt-0.5" aria-hidden="true" />
      <div>
        {title && <p className="font-bold">{title}</p>}
        {children}
      </div>
    </div>
  )
}

/** Marks where a price came from. Demo = synthetic, Imported = loaded from a real data file. */
export function DataBadge({ isDemo, compact = false }) {
  return isDemo ? (
    <span
      title="Synthetic demonstration data – not a real market price"
      className="inline-flex items-center gap-1 rounded-full bg-mustard-soft px-2 py-0.5 text-xs font-bold text-[#7a5a06] ring-1 ring-mustard/50"
    >
      <FlaskConical className="size-3" aria-hidden="true" />
      {compact ? 'Demo' : 'Demo data'}
    </span>
  ) : (
    <span
      title="Imported from a market data file"
      className="inline-flex items-center gap-1 rounded-full bg-sprout px-2 py-0.5 text-xs font-bold text-forest ring-1 ring-leaf/40"
    >
      <CircleCheck className="size-3" aria-hidden="true" />
      Imported
    </span>
  )
}
