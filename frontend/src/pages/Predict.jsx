import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { History, Info } from 'lucide-react'
import Pagination from '../components/Pagination'
import PriceChart from '../components/PriceChart'
import { Alert, DataBadge, EmptyState, ErrorState, LoadingBlock } from '../components/feedback'
import { Button, PageHeader, Panel, SelectField } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { endpoints } from '../services/api'
import { formatDate, formatPercent, formatPrice, formatUnit, locationLabel, percentChange } from '../utils/format'

const MODEL_NAMES = {
  hist_gradient_boosting: 'Gradient boosting',
  random_forest: 'Random forest',
  ridge: 'Ridge regression',
  naive_last_value: 'Last value (baseline)',
  moving_average_4w: '4-week average (baseline)',
}

function Row({ label, children, className = '' }) {
  return (
    <div className="flex justify-between gap-4 border-b border-line/70 py-2 last:border-0">
      <dt className="text-ink-soft">{label}</dt>
      <dd className={`font-bold tabular text-right ${className}`}>{children}</dd>
    </div>
  )
}

function ResultCard({ result }) {
  const { prediction: p, details: d } = result
  const change = percentChange(d.base_price, d.predicted_price)
  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] md:items-end">
        <div>
          <p className="text-sm text-ink-soft">
            {p.crop.name} at {p.location.market_name}, estimated modal price for the week ending {formatDate(d.target_week_ending)}
          </p>
          <p className="mt-2 font-display text-5xl font-extrabold tabular text-forest">{formatPrice(p.predicted_price)}</p>
          <p className="text-ink-soft">{formatUnit(p.unit)}</p>
        </div>
        <dl className="text-sm">
          {d.typical_range && (
            <Row label="Typical range">{formatPrice(d.typical_range.low)} – {formatPrice(d.typical_range.high)}</Row>
          )}
          <Row label="Latest weekly price">{formatPrice(d.base_price)}</Row>
          <Row label="Expected change" className={change > 0 ? 'text-leaf-dark' : change < 0 ? 'text-danger' : ''}>
            {formatPercent(change)}
          </Row>
          <Row label="Latest data">{formatDate(d.last_observation_date)}</Row>
          <Row label="Model">
            <span title={p.model_version}>{MODEL_NAMES[d.model_name] || d.model_name}</span>
            {p.is_demo && <span className="ml-2 align-middle"><DataBadge isDemo compact /></span>}
          </Row>
        </dl>
      </div>
      <div>
        <PriceChart
          points={result.history}
          showBand={false}
          height={300}
          label={`Weekly prices and estimate for ${p.crop.name}`}
          prediction={{
            date: d.target_week_ending,
            value: d.predicted_price,
            low: d.typical_range?.low,
            high: d.typical_range?.high,
            baseDate: d.base_week_ending,
          }}
        />
        <p className="mt-2 text-xs text-ink-soft">
          Solid line: weekly average modal price. Dashed line: the estimate, starting from the latest week of data. The
          shaded band shows where 8 in 10 past estimates landed relative to the actual price.
        </p>
      </div>
    </div>
  )
}

export default function Predict() {
  const [params] = useSearchParams()
  const [form, setForm] = useState({
    crop_id: params.get('crop_id') || '',
    location_id: params.get('location_id') || '',
    horizon_weeks: params.get('horizon') || '',
  })
  const [errors, setErrors] = useState({})
  const [submitError, setSubmitError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [historyPage, setHistoryPage] = useState(1)

  const model = useApi(({ signal }) => endpoints.modelInfo({ signal }), [])
  const crops = useApi(({ signal }) => endpoints.crops({ per_page: 100 }, { signal }), [])
  const markets = useApi(
    ({ signal }) => endpoints.markets({ crop_id: form.crop_id, per_page: 100 }, { signal }),
    [form.crop_id],
    { enabled: Boolean(form.crop_id) },
  )
  const history = useApi(({ signal }) => endpoints.predictions({ page: historyPage, per_page: 8 }, { signal }), [historyPage])

  const horizons = model.data?.horizons || []
  const horizon = form.horizon_weeks || (horizons.length ? String(horizons[0]) : '')

  const submit = async (e) => {
    e.preventDefault()
    const errs = {}
    if (!form.crop_id) errs.crop_id = 'Choose a crop.'
    if (!form.location_id) errs.location_id = 'Choose a market.'
    if (!horizon) errs.horizon_weeks = 'Choose how far ahead to estimate.'
    setErrors(errs)
    setSubmitError(null)
    if (Object.keys(errs).length) return
    setSubmitting(true)
    try {
      const res = await endpoints.createPrediction({
        crop_id: Number(form.crop_id),
        location_id: Number(form.location_id),
        horizon_weeks: Number(horizon),
      })
      setResult(res)
      setHistoryPage(1)
      history.reload()
    } catch (err) {
      setResult(null)
      if (err.code === 'validation_error') setErrors(err.details)
      else setSubmitError(err)
    } finally {
      setSubmitting(false)
    }
  }

  const m = model.data
  return (
    <>
      <PageHeader
        title="Price estimate"
        description="Estimate the modal price of a crop at one market 1, 2 or 4 weeks ahead, based on its recent price history."
      />

      {model.error && <ErrorState error={model.error} onRetry={model.reload} />}
      {m && !m.available && (
        <Alert tone="error" title="Estimates are unavailable">
          No trained model is loaded on the server. An administrator needs to run the training script ({m.reason}).
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <Panel title="What to estimate">
          <form onSubmit={submit} noValidate className="space-y-5">
            <SelectField
              label="Crop"
              value={form.crop_id}
              error={errors.crop_id}
              onChange={(e) => setForm({ ...form, crop_id: e.target.value, location_id: '' })}
            >
              <option value="">Choose a crop</option>
              {crops.data?.items.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </SelectField>
            <SelectField
              label="Market"
              value={form.location_id}
              error={errors.location_id}
              disabled={!form.crop_id || markets.loading}
              hint={!form.crop_id ? 'Choose a crop first. Only markets with price history for it are listed.' : undefined}
              onChange={(e) => setForm({ ...form, location_id: e.target.value })}
            >
              <option value="">{markets.loading ? 'Loading markets…' : 'Choose a market'}</option>
              {markets.data?.items.map((loc) => <option key={loc.id} value={loc.id}>{locationLabel(loc)}</option>)}
            </SelectField>
            <SelectField
              label="How far ahead"
              value={horizon}
              error={errors.horizon_weeks}
              disabled={!horizons.length}
              onChange={(e) => setForm({ ...form, horizon_weeks: e.target.value })}
            >
              {horizons.map((h) => <option key={h} value={h}>{h} week{h > 1 ? 's' : ''} ahead</option>)}
            </SelectField>
            {submitError && (
              <Alert tone="error" title={submitError.code === 'insufficient_history' || submitError.code === 'unsupported_series' ? 'No estimate for this selection' : 'The estimate failed'}>
                {submitError.message}
              </Alert>
            )}
            <Button type="submit" loading={submitting} disabled={!m?.available} className="w-full">
              Estimate price
            </Button>
          </form>
          {m?.available && (
            <div className="mt-6 border-t border-line pt-4 text-sm text-ink-soft">
              <p className="flex items-center gap-1.5 font-bold text-ink"><Info className="size-4" aria-hidden="true" /> About this model</p>
              <p className="mt-1.5">
                On held-out weeks it missed the actual price by {formatPrice(m.test_metrics.mae)} on average
                ({m.test_metrics.mape_pct.toFixed(1)}%), compared with {formatPrice(m.test_metrics.baseline_mae)} for simply
                assuming the price stays the same.
              </p>
              {m.is_demo && <p className="mt-2"><DataBadge isDemo /> Trained on synthetic data, so these estimates say nothing about real markets.</p>}
            </div>
          )}
        </Panel>

        <Panel title="Result" bodyClassName="p-5 min-h-[300px]">
          {submitting && <LoadingBlock label="Running the model" />}
          {!submitting && !result && (
            <EmptyState title="Choose a crop, market and time frame">
              The estimate and a chart of recent weekly prices will appear here.
            </EmptyState>
          )}
          {!submitting && result && (
            <div className="space-y-5">
              {result.warnings.map((w) => <Alert key={w} tone="warning">{w}</Alert>)}
              <ResultCard result={result} />
              <p className="rounded-lg bg-field px-3 py-2 text-sm text-ink-soft">{result.disclaimer}</p>
            </div>
          )}
        </Panel>
      </div>

      <Panel className="mt-6" title="Your estimate history" bodyClassName="px-5 pb-5">
        {history.loading && !history.data && <div className="pt-5"><LoadingBlock rows={3} /></div>}
        {history.error && <div className="pt-5"><ErrorState error={history.error} onRetry={history.reload} /></div>}
        {history.data?.items.length === 0 && <EmptyState icon={History} title="No estimates yet">Your past estimates will be listed here.</EmptyState>}
        {history.data?.items.length > 0 && (
          <>
            <div className="overflow-x-auto -mx-5 md:mx-0">
              <table className="w-full min-w-[640px] text-sm">
                <caption className="sr-only">Your previous price estimates</caption>
                <thead className="text-left text-ink-soft border-b border-line">
                  <tr>
                    <th className="px-4 py-3">Requested</th>
                    <th className="px-4 py-3">Crop and market</th>
                    <th className="px-4 py-3">For week ending</th>
                    <th className="px-4 py-3 text-right">Latest price then</th>
                    <th className="px-4 py-3 text-right">Estimate</th>
                    <th className="px-4 py-3"><span className="sr-only">Data</span></th>
                  </tr>
                </thead>
                <tbody>
                  {history.data.items.map((p) => (
                    <tr key={p.id} className="border-b border-line/60 last:border-0">
                      <td className="px-4 py-3 whitespace-nowrap">{formatDate(p.created_at)}</td>
                      <td className="px-4 py-3"><span className="font-bold">{p.crop.name}</span>, {p.location.market_name}</td>
                      <td className="px-4 py-3 whitespace-nowrap">{formatDate(p.prediction_date)} ({p.horizon_weeks} wk)</td>
                      <td className="px-4 py-3 text-right tabular text-ink-soft">{formatPrice(p.base_price)}</td>
                      <td className="px-4 py-3 text-right tabular font-bold">{formatPrice(p.predicted_price)}</td>
                      <td className="px-4 py-3">{p.is_demo && <DataBadge isDemo compact />}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination pagination={history.data.pagination} onPage={setHistoryPage} />
          </>
        )}
      </Panel>
    </>
  )
}
