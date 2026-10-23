import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, LineChart, SearchX } from 'lucide-react'
import PriceChart from '../components/PriceChart'
import { DataBadge, EmptyState, ErrorState, LoadingBlock } from '../components/feedback'
import { ButtonLink, Field, PageHeader, Panel, SelectField } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useApi, useDebounced, useRecentCrops } from '../hooks/useApi'
import { endpoints } from '../services/api'
import { formatDate, formatNumber, formatPercent, formatPrice, formatUnit, percentChange } from '../utils/format'

export function CropsList() {
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const dq = useDebounced(q, 300)
  const crops = useApi(({ signal }) => endpoints.crops({ q: dq || undefined, category: category || undefined, per_page: 100 }, { signal }), [dq, category])

  const grouped = useMemo(() => {
    const g = {}
    for (const c of crops.data?.items || []) (g[c.category] ||= []).push(c)
    return Object.entries(g).sort(([a], [b]) => a.localeCompare(b))
  }, [crops.data])

  return (
    <>
      <PageHeader title="Crops" description="Every crop with price records, grouped by category, with its latest average modal price." />
      <div className="mb-6 grid gap-4 sm:grid-cols-[1fr_220px]">
        <Field label="Search crops" placeholder="e.g. wheat" value={q} onChange={(e) => setQ(e.target.value)} />
        <SelectField label="Category" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {crops.data?.categories.map((c) => <option key={c}>{c}</option>)}
        </SelectField>
      </div>
      {crops.loading && !crops.data && <LoadingBlock label="Loading crops" />}
      {crops.error && <ErrorState error={crops.error} onRetry={crops.reload} />}
      {crops.data?.items.length === 0 && (
        <EmptyState icon={SearchX} title="No crops found">Try another name, or clear the category filter.</EmptyState>
      )}
      <div className="space-y-8">
        {grouped.map(([cat, items]) => (
          <section key={cat}>
            <h2 className="mb-3 text-xl font-bold">{cat}</h2>
            <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-white">
              {items.map((c) => (
                <li key={c.id}>
                  <Link to={`/crops/${c.id}`} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 hover:bg-field/70">
                    <div className="min-w-0 max-w-xl">
                      <p className="font-bold text-forest">{c.name}</p>
                      <p className="text-sm text-ink-soft line-clamp-1">{c.description || 'No description yet.'}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold tabular">{formatPrice(c.latest_avg_modal_price)} <span className="text-xs font-normal text-ink-soft">{formatUnit(c.unit)}</span></p>
                      <p className="text-xs text-ink-soft">{c.market_count} market{c.market_count === 1 ? '' : 's'}, updated {formatDate(c.latest_date)}</p>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </>
  )
}

const PERIODS = [
  ['90', 'Last 3 months'],
  ['182', 'Last 6 months'],
  ['365', 'Last 12 months'],
  ['all', 'All history'],
]

function daysBefore(iso, days) {
  const d = new Date(`${iso}T00:00:00`)
  d.setDate(d.getDate() - Number(days))
  return d.toISOString().slice(0, 10)
}

export function CropDetail() {
  const { id } = useParams()
  const { isAuthenticated } = useAuth()
  const { remember } = useRecentCrops()
  const [locationId, setLocationId] = useState('')
  const [period, setPeriod] = useState('182')
  const crop = useApi(({ signal }) => endpoints.crop(id, { signal }), [id])

  useEffect(() => {
    if (crop.data) remember(crop.data.crop)
  }, [crop.data, remember])
  useEffect(() => setLocationId(''), [id])

  const latestDate = crop.data?.latest_by_market.reduce((d, p) => (p.observation_date > d ? p.observation_date : d), '')
  const history = useApi(
    ({ signal }) =>
      endpoints.priceHistory(
        { crop_id: id, location_id: locationId || undefined, date_from: period === 'all' ? undefined : daysBefore(latestDate, period) },
        { signal },
      ),
    [id, locationId, period, latestDate],
    { enabled: Boolean(latestDate) },
  )

  if (crop.loading) return <LoadingBlock label="Loading crop" rows={6} />
  if (crop.error)
    return crop.error.status === 404 ? (
      <EmptyState title="This crop does not exist" action={<ButtonLink to="/crops" variant="secondary">See all crops</ButtonLink>}>
        It may have been removed, or the link is wrong.
      </EmptyState>
    ) : (
      <ErrorState error={crop.error} onRetry={crop.reload} />
    )

  const { crop: c, latest_by_market: latest } = crop.data
  const pts = history.data?.points || []
  const change = pts.length > 1 ? percentChange(pts[0].modal_price, pts[pts.length - 1].modal_price) : null
  const predictLink = (locId) => (isAuthenticated ? `/predict?crop_id=${c.id}${locId ? `&location_id=${locId}` : ''}` : '/login')

  return (
    <>
      <Link to="/crops" className="mb-4 inline-flex items-center gap-1.5 text-sm font-bold text-forest">
        <ArrowLeft className="size-4" aria-hidden="true" /> All crops
      </Link>
      <PageHeader
        title={c.name}
        description={c.description}
        actions={<ButtonLink to={predictLink(locationId)}><LineChart className="size-4" aria-hidden="true" />{isAuthenticated ? 'Estimate future price' : 'Log in to estimate prices'}</ButtonLink>}
      />
      <p className="-mt-3 mb-6 text-sm text-ink-soft">
        {c.category}. Prices in {c.unit}. {formatNumber(c.record_count)} records from {latest.length} market{latest.length === 1 ? '' : 's'}.
      </p>

      {latest.length === 0 ? (
        <Panel><EmptyState title="No prices recorded for this crop yet">Import a price file that includes {c.name}.</EmptyState></Panel>
      ) : (
        <>
          <Panel
            title="Price history"
            action={
              <div className="flex flex-wrap gap-2">
                <div className="w-52">
                  <SelectField label={<span className="sr-only">Market</span>} value={locationId} onChange={(e) => setLocationId(e.target.value)}>
                    <option value="">All markets (average)</option>
                    {latest.map((p) => <option key={p.location.id} value={p.location.id}>{p.location.market_name}</option>)}
                  </SelectField>
                </div>
                <div className="w-44">
                  <SelectField label={<span className="sr-only">Period</span>} value={period} onChange={(e) => setPeriod(e.target.value)}>
                    {PERIODS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </SelectField>
                </div>
              </div>
            }
          >
            {history.loading && <LoadingBlock label="Loading history" />}
            {history.error && <ErrorState error={history.error} onRetry={history.reload} />}
            {history.data && pts.length === 0 && <EmptyState title="No prices in this period">Choose a longer period.</EmptyState>}
            {history.data && pts.length > 0 && (
              <>
                <p className="mb-3 text-sm text-ink-soft">
                  Weekly {locationId ? 'modal price with daily min–max range' : 'average modal price across markets with min–max range'}.
                  {change !== null && <> Change over the period: <span className="font-bold text-ink">{formatPercent(change)}</span>.</>}
                </p>
                <PriceChart points={pts} label={`${c.name} price history`} />
              </>
            )}
          </Panel>

          <Panel className="mt-6" title="Latest price by market" bodyClassName="p-0">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <caption className="sr-only">Latest {c.name} price in each market</caption>
                <thead className="border-b border-line text-left text-ink-soft">
                  <tr>
                    <th className="px-5 py-3">Market</th>
                    <th className="px-5 py-3">Date</th>
                    <th className="px-5 py-3 text-right">Min</th>
                    <th className="px-5 py-3 text-right">Modal</th>
                    <th className="px-5 py-3 text-right">Max</th>
                    <th className="px-5 py-3"><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {latest.map((p) => (
                    <tr key={p.id} className="border-b border-line/60 last:border-0">
                      <td className="px-5 py-3">
                        <span className="font-bold">{p.location.market_name}</span>
                        <span className="block text-xs text-ink-soft">{p.location.district}, {p.location.state}</span>
                      </td>
                      <td className="px-5 py-3 whitespace-nowrap">{formatDate(p.observation_date)} <DataBadge isDemo={p.is_demo} compact /></td>
                      <td className="px-5 py-3 text-right tabular text-ink-soft">{formatPrice(p.min_price)}</td>
                      <td className="px-5 py-3 text-right tabular font-bold">{formatPrice(p.modal_price)}</td>
                      <td className="px-5 py-3 text-right tabular text-ink-soft">{formatPrice(p.max_price)}</td>
                      <td className="px-5 py-3 text-right whitespace-nowrap">
                        <Link to={`/markets?crop_id=${c.id}&location_id=${p.location.id}`} className="font-bold text-forest underline underline-offset-4">Records</Link>
                        {isAuthenticated && (
                          <Link to={predictLink(p.location.id)} className="ml-4 font-bold text-forest underline underline-offset-4">Estimate</Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </>
  )
}
