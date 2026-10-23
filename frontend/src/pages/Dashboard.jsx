import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { History, LineChart, Store } from 'lucide-react'
import PriceChart from '../components/PriceChart'
import PriceTable from '../components/PriceTable'
import { Alert, DataBadge, EmptyState, ErrorState, LoadingBlock } from '../components/feedback'
import { ButtonLink, PageHeader, Panel, SelectField } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useApi, useRecentCrops } from '../hooks/useApi'
import { endpoints } from '../services/api'
import { formatDate, formatNumber, formatPercent, formatPrice, formatUnit, percentChange } from '../utils/format'

function Metric({ label, value, note }) {
  return (
    <div className="rounded-xl border border-line bg-white px-5 py-4">
      <p className="text-sm text-ink-soft">{label}</p>
      <p className="mt-1 font-display text-3xl font-extrabold tabular text-forest">{value}</p>
      {note && <p className="mt-1 text-xs text-ink-soft">{note}</p>}
    </div>
  )
}

function oneYearBefore(iso) {
  const d = new Date(`${iso}T00:00:00`)
  d.setFullYear(d.getFullYear() - 1)
  return d.toISOString().slice(0, 10)
}

export default function Dashboard() {
  const { user } = useAuth()
  const { recent } = useRecentCrops()
  const summary = useApi(({ signal }) => endpoints.summary({ signal }), [])
  const crops = useApi(({ signal }) => endpoints.crops({ per_page: 100 }, { signal }), [])
  const latest = useApi(({ signal }) => endpoints.prices({ latest: true, per_page: 8, sort: '-observation_date' }, { signal }), [])
  const mine = useApi(({ signal }) => endpoints.predictions({ per_page: 5 }, { signal }), [])
  const [cropId, setCropId] = useState('')

  useEffect(() => {
    if (!cropId && crops.data?.items?.length) setCropId(String(recent[0]?.id || crops.data.items[0].id))
  }, [crops.data, cropId, recent])

  const latestDate = summary.data?.latest_observation_date
  const history = useApi(
    ({ signal }) => endpoints.priceHistory({ crop_id: cropId, date_from: oneYearBefore(latestDate) }, { signal }),
    [cropId, latestDate],
    { enabled: Boolean(cropId && latestDate) },
  )
  const trend = useMemo(() => {
    const pts = history.data?.points || []
    if (pts.length < 5) return null
    return { last: pts[pts.length - 1], change: percentChange(pts[pts.length - 5].modal_price, pts[pts.length - 1].modal_price) }
  }, [history.data])

  const popular = [...(crops.data?.items || [])].sort((a, b) => b.record_count - a.record_count).slice(0, 6)
  const firstName = user?.name?.split(' ')[0]

  return (
    <>
      <PageHeader
        title={`Welcome back, ${firstName}`}
        description="Latest mandi prices, how they are moving, and your recent price estimates."
        actions={
          <>
            <ButtonLink to="/predict"><LineChart className="size-4" aria-hidden="true" />Get a price estimate</ButtonLink>
            <ButtonLink to="/markets" variant="secondary"><Store className="size-4" aria-hidden="true" />Explore markets</ButtonLink>
          </>
        }
      />

      {summary.error && <ErrorState error={summary.error} onRetry={summary.reload} />}
      {summary.data && summary.data.demo_price_records > 0 && (
        <div className="mb-6">
          <Alert tone="warning" title="You are looking at demo data">
            {summary.data.verified_price_records === 0
              ? 'All prices in this installation are synthetic and exist only to demonstrate the app. Import real market data to replace them.'
              : `${formatNumber(summary.data.demo_price_records)} of ${formatNumber(summary.data.price_records)} price records are synthetic demo data and are marked "Demo".`}
          </Alert>
        </div>
      )}

      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        {summary.loading ? (
          <div className="col-span-full"><LoadingBlock label="Loading summary" rows={1} /></div>
        ) : summary.data ? (
          <>
            <Metric label="Crops tracked" value={summary.data.crops} note={`${summary.data.markets} markets, ${summary.data.states} states`} />
            <Metric label="Price records" value={formatNumber(summary.data.price_records)} note={`${formatNumber(summary.data.verified_price_records)} imported, ${formatNumber(summary.data.demo_price_records)} demo`} />
            <Metric label="Your estimates" value={formatNumber(mine.data?.pagination.total ?? 0)} note={`${formatNumber(summary.data.predictions)} across all users`} />
            <Metric label="Latest data" value={formatDate(summary.data.latest_observation_date)} note="Most recent market observation" />
          </>
        ) : null}
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <Panel
          title="Price trend"
          action={
            crops.data && (
              <div className="w-60">
                <SelectField label={<span className="sr-only">Crop</span>} value={cropId} onChange={(e) => setCropId(e.target.value)}>
                  {crops.data.items.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </SelectField>
              </div>
            )
          }
        >
          {history.loading && <LoadingBlock label="Loading trend" />}
          {history.error && <ErrorState error={history.error} onRetry={history.reload} />}
          {history.data && history.data.points.length === 0 && <EmptyState title="No price history for this crop yet" />}
          {history.data && history.data.points.length > 0 && (
            <>
              {trend && (
                <p className="mb-3 text-sm text-ink-soft">
                  Average modal price across markets, last 12 months.{' '}
                  <span className="font-bold text-ink tabular">{formatPrice(trend.last.modal_price)} {formatUnit(history.data.crop.unit)}</span>
                  {' '}in the latest week, {formatPercent(trend.change)} over 4 weeks.
                </p>
              )}
              <PriceChart points={history.data.points} label={`${history.data.crop.name} weekly price trend`} />
              <div className="mt-3 flex items-center justify-between text-sm">
                {history.data.points.some((p) => p.is_demo) ? <DataBadge isDemo /> : <span />}
                <Link to={`/crops/${cropId}`} className="font-bold text-forest underline underline-offset-4">Crop details</Link>
              </div>
            </>
          )}
        </Panel>

        <div className="space-y-6">
          <Panel title={recent.length ? 'Recently viewed crops' : 'Popular crops'}>
            {crops.loading && <LoadingBlock rows={3} />}
            {crops.error && <ErrorState error={crops.error} onRetry={crops.reload} />}
            {(recent.length ? recent : popular).length === 0 && !crops.loading && !crops.error && (
              <EmptyState title="No crops yet">Load the demo data or import a price file to get started.</EmptyState>
            )}
            <ul className="flex flex-wrap gap-2">
              {(recent.length ? recent : popular).map((c) => (
                <li key={c.id}>
                  <Link to={`/crops/${c.id}`} className="inline-flex min-h-10 items-center rounded-full border border-line bg-field px-4 font-bold text-forest hover:border-forest">
                    {c.name}
                  </Link>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Your recent estimates" action={<Link to="/predict" className="text-sm font-bold text-forest underline underline-offset-4">New estimate</Link>}>
            {mine.loading && <LoadingBlock rows={3} />}
            {mine.error && <ErrorState error={mine.error} onRetry={mine.reload} />}
            {mine.data?.items.length === 0 && (
              <EmptyState icon={History} title="No estimates yet" action={<ButtonLink to="/predict">Get your first estimate</ButtonLink>}>
                Pick a crop and market to see where its price may go in the next few weeks.
              </EmptyState>
            )}
            <ul className="divide-y divide-line/70">
              {mine.data?.items.map((p) => (
                <li key={p.id} className="flex items-center justify-between gap-3 py-2.5">
                  <div className="min-w-0">
                    <p className="truncate font-bold">{p.crop.name}, {p.location.market_name}</p>
                    <p className="text-xs text-ink-soft">{p.horizon_weeks} week{p.horizon_weeks > 1 ? 's' : ''} ahead, week ending {formatDate(p.prediction_date)}</p>
                  </div>
                  <p className="text-right font-bold tabular">{formatPrice(p.predicted_price)}</p>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      </div>

      <Panel className="mt-6" title="Latest market prices" action={<Link to="/markets" className="text-sm font-bold text-forest underline underline-offset-4">All prices</Link>}>
        {latest.loading && <LoadingBlock />}
        {latest.error && <ErrorState error={latest.error} onRetry={latest.reload} />}
        {latest.data?.items.length === 0 && <EmptyState title="No prices yet">Seed the demo data or import a CSV file.</EmptyState>}
        {latest.data?.items.length > 0 && <PriceTable items={latest.data.items} caption="Latest price per crop and market" />}
      </Panel>
    </>
  )
}
