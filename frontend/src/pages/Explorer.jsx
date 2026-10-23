import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, SearchX, X } from 'lucide-react'
import Pagination from '../components/Pagination'
import PriceTable from '../components/PriceTable'
import { EmptyState, ErrorState, LoadingBlock } from '../components/feedback'
import { Button, Field, PageHeader, Panel, SelectField } from '../components/ui'
import { useApi, useDebounced } from '../hooks/useApi'
import { endpoints } from '../services/api'

const FILTER_KEYS = ['q', 'crop_id', 'state', 'district', 'location_id', 'date_from', 'date_to', 'is_demo', 'latest']

export default function Explorer() {
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') || '')
  const debouncedQ = useDebounced(q, 350)

  const filters = Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) || '']))
  filters.q = debouncedQ
  const page = Number(params.get('page') || 1)
  const sort = params.get('sort') || '-observation_date'

  const update = (changes, keepPage = false) => {
    const next = new URLSearchParams(params)
    Object.entries(changes).forEach(([k, v]) => (v === '' || v == null ? next.delete(k) : next.set(k, v)))
    if (!keepPage) next.delete('page')
    setParams(next, { replace: true })
  }

  const crops = useApi(({ signal }) => endpoints.crops({ per_page: 100 }, { signal }), [])
  const markets = useApi(({ signal }) => endpoints.markets({ per_page: 100, crop_id: filters.crop_id || undefined }, { signal }), [filters.crop_id])

  const states = useMemo(() => [...new Set((markets.data?.items || []).map((m) => m.state))].sort(), [markets.data])
  const districts = useMemo(
    () => [...new Set((markets.data?.items || []).filter((m) => !filters.state || m.state === filters.state).map((m) => m.district))].sort(),
    [markets.data, filters.state],
  )
  const marketOptions = (markets.data?.items || []).filter(
    (m) => (!filters.state || m.state === filters.state) && (!filters.district || m.district === filters.district),
  )

  const query = useMemo(() => {
    const p = { page, per_page: 25, sort }
    Object.entries(filters).forEach(([k, v]) => v && (p[k] = v))
    return p
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.toString(), debouncedQ])
  const prices = useApi(({ signal }) => endpoints.prices(query, { signal }), [JSON.stringify(query)])

  const active = FILTER_KEYS.some((k) => params.get(k))
  const clear = () => {
    setQ('')
    setParams(new URLSearchParams(), { replace: true })
  }

  return (
    <>
      <PageHeader
        title="Market prices"
        description="Search price records by crop and market. Modal price is the price at which most of the produce was sold that day."
      />
      <Panel className="mb-6">
        <form className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" onSubmit={(e) => e.preventDefault()} role="search">
          <div className="relative md:col-span-2">
            <Field
              label="Search crop or market"
              placeholder="e.g. onion, Lasalgaon"
              value={q}
              onChange={(e) => {
                setQ(e.target.value)
                update({ q: e.target.value })
              }}
              className="pl-10"
            />
            <Search className="pointer-events-none absolute left-3 top-[2.55rem] size-4 text-ink-soft" aria-hidden="true" />
          </div>
          <SelectField label="Crop" value={filters.crop_id} onChange={(e) => update({ crop_id: e.target.value, location_id: '' })}>
            <option value="">All crops</option>
            {crops.data?.items.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </SelectField>
          <SelectField label="Data source" value={filters.is_demo} onChange={(e) => update({ is_demo: e.target.value })}>
            <option value="">Demo and imported</option>
            <option value="false">Imported only</option>
            <option value="true">Demo only</option>
          </SelectField>
          <SelectField label="State" value={filters.state} onChange={(e) => update({ state: e.target.value, district: '', location_id: '' })}>
            <option value="">All states</option>
            {states.map((s) => <option key={s}>{s}</option>)}
          </SelectField>
          <SelectField label="District" value={filters.district} onChange={(e) => update({ district: e.target.value, location_id: '' })}>
            <option value="">All districts</option>
            {districts.map((d) => <option key={d}>{d}</option>)}
          </SelectField>
          <SelectField label="Market" value={filters.location_id} onChange={(e) => update({ location_id: e.target.value })}>
            <option value="">All markets</option>
            {marketOptions.map((m) => <option key={m.id} value={m.id}>{m.market_name}</option>)}
          </SelectField>
          <SelectField label="Show" value={filters.latest} onChange={(e) => update({ latest: e.target.value })}>
            <option value="">Every record</option>
            <option value="true">Latest per crop and market</option>
          </SelectField>
          <Field label="From date" type="date" value={filters.date_from} max={filters.date_to || undefined} onChange={(e) => update({ date_from: e.target.value })} />
          <Field label="To date" type="date" value={filters.date_to} min={filters.date_from || undefined} onChange={(e) => update({ date_to: e.target.value })} />
          <div className="flex items-end md:col-span-2 xl:col-span-2">
            {active && (
              <Button type="button" variant="ghost" onClick={clear}>
                <X className="size-4" aria-hidden="true" /> Clear filters
              </Button>
            )}
          </div>
        </form>
      </Panel>

      <Panel>
        {prices.loading && !prices.data && <LoadingBlock label="Loading prices" rows={6} />}
        {prices.error && <ErrorState error={prices.error} onRetry={prices.reload} />}
        {prices.data && prices.data.items.length === 0 && (
          <EmptyState icon={SearchX} title="No prices match these filters" action={active && <Button variant="secondary" onClick={clear}>Clear filters</Button>}>
            Try a different crop or market, or widen the date range.
          </EmptyState>
        )}
        {prices.data && prices.data.items.length > 0 && (
          <div className={prices.loading ? 'opacity-60 transition-opacity' : ''} aria-busy={prices.loading}>
            <PriceTable items={prices.data.items} sort={sort} onSort={(s) => update({ sort: s })} caption="Market price records" />
            <Pagination pagination={prices.data.pagination} onPage={(p) => update({ page: p }, true)} />
          </div>
        )}
      </Panel>
    </>
  )
}
