import { BarChart3, Filter, LineChart, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import MandiBoard from '../components/MandiBoard'
import { ErrorState, LoadingBlock } from '../components/feedback'
import { ButtonLink } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useApi } from '../hooks/useApi'
import { endpoints } from '../services/api'
import { formatNumber } from '../utils/format'

const features = [
  {
    icon: Filter,
    title: 'Find the price at your mandi',
    text: 'Search by crop, state, district or market and see minimum, modal and maximum prices with the date they were recorded.',
  },
  {
    icon: BarChart3,
    title: 'See how prices have moved',
    text: 'Weekly price charts show the seasonal rise and fall for each crop, for one market or averaged across markets.',
  },
  {
    icon: LineChart,
    title: 'Estimate the next few weeks',
    text: 'A machine-learning model trained on past prices gives an estimate 1, 2 or 4 weeks ahead, with a typical error range.',
  },
  {
    icon: ShieldCheck,
    title: 'Know where every number comes from',
    text: 'Each record shows its source and date. Demo data is always marked, and estimates are never presented as guarantees.',
  },
]

const steps = [
  ['Pick a crop and market', 'Choose what you grow or trade and the mandi you sell in.'],
  ['Check recent prices', 'Compare the latest modal price with the last few months.'],
  ['Get an estimate', 'Ask for a 1, 2 or 4 week estimate and see how far it typically misses.'],
]

export default function Landing() {
  const { isAuthenticated } = useAuth()
  const board = useApi(({ signal }) => endpoints.prices({ latest: true, sort: 'crop', per_page: 40 }, { signal }), [])
  const summary = useApi(({ signal }) => endpoints.summary({ signal }), [])

  // One row per crop for the board (its first market alphabetically by crop sort).
  const boardRows = []
  const seen = new Set()
  for (const p of board.data?.items || []) {
    if (!seen.has(p.crop.id)) {
      seen.add(p.crop.id)
      boardRows.push(p)
    }
  }

  return (
    <>
      <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 pb-16 pt-10 sm:px-6 md:pt-16 lg:grid-cols-[1.05fr_1fr]">
        <div>
          <h1 className="text-[2.6rem] leading-[1.04] font-extrabold sm:text-6xl">
            Know the mandi rate before you load the truck.
          </h1>
          <p className="mt-5 max-w-xl text-lg text-ink-soft">
            AgriConnect brings crop prices from markets across India into one place, shows how they have moved,
            and estimates where they are heading in the next few weeks.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            {isAuthenticated ? (
              <ButtonLink to="/dashboard" variant="dark" className="px-6">Open your dashboard</ButtonLink>
            ) : (
              <ButtonLink to="/register" className="px-6">Create a free account</ButtonLink>
            )}
            <ButtonLink to="/markets" variant="secondary" className="px-6">Browse market prices</ButtonLink>
          </div>
          {summary.data && (
            <p className="mt-8 text-sm text-ink-soft">
              {formatNumber(summary.data.price_records)} price records for {summary.data.crops} crops from{' '}
              {summary.data.markets} markets in {summary.data.states} states.
            </p>
          )}
        </div>
        <div>
          {board.loading && <div className="mandi-board p-6"><LoadingBlock label="Loading prices" rows={6} /></div>}
          {board.error && <ErrorState error={board.error} onRetry={board.reload} title="Prices could not load" />}
          {board.data && boardRows.length > 0 && <MandiBoard prices={boardRows} />}
        </div>
      </section>

      <section className="border-y border-line bg-white">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <h2 className="max-w-xl text-3xl font-extrabold">Built for the questions farmers and traders ask every week</h2>
          <ul className="mt-10 grid gap-x-12 gap-y-9 md:grid-cols-2">
            {features.map(({ icon: Icon, title, text }) => (
              <li key={title} className="flex gap-4">
                <Icon className="mt-1 size-6 shrink-0 text-leaf" aria-hidden="true" />
                <div>
                  <h3 className="text-xl font-bold">{title}</h3>
                  <p className="mt-1.5 text-ink-soft">{text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <h2 className="text-3xl font-extrabold">How it works</h2>
        <ol className="mt-8 grid gap-6 md:grid-cols-3">
          {steps.map(([title, text], i) => (
            <li key={title} className="border-l-4 border-leaf pl-5">
              <span className="font-display text-4xl font-extrabold text-sprout [-webkit-text-stroke:1.5px_var(--color-forest)]">
                {i + 1}
              </span>
              <h3 className="mt-2 text-xl font-bold">{title}</h3>
              <p className="mt-1 text-ink-soft">{text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mx-auto mb-16 max-w-6xl px-4 sm:px-6">
        <div className="flex flex-col items-start gap-5 rounded-xl bg-sprout px-6 py-8 md:flex-row md:items-center md:justify-between md:px-10">
          <div>
            <h2 className="text-2xl font-extrabold">Start with the crop you grow</h2>
            <p className="mt-1 text-ink-soft">Browsing prices is open to everyone. Estimates need a free account.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <ButtonLink to={isAuthenticated ? '/predict' : '/register'} variant="dark">
              {isAuthenticated ? 'Get a price estimate' : 'Create a free account'}
            </ButtonLink>
            <Link to="/about" className="inline-flex min-h-11 items-center font-bold text-forest underline underline-offset-4">
              About the data
            </Link>
          </div>
        </div>
      </section>
    </>
  )
}
