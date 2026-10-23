import { ChevronLeft, ChevronRight } from 'lucide-react'
import { formatNumber } from '../utils/format'

export default function Pagination({ pagination, onPage }) {
  if (!pagination) return null
  const { page, pages, total, per_page: perPage } = pagination
  const from = total === 0 ? 0 : (page - 1) * perPage + 1
  const to = Math.min(page * perPage, total)
  const btn =
    'inline-flex items-center gap-1 rounded-lg border border-line bg-white px-3 min-h-10 font-bold text-forest disabled:opacity-40 disabled:cursor-not-allowed hover:border-forest'
  return (
    <nav aria-label="Pagination" className="flex flex-wrap items-center justify-between gap-3 pt-4 text-sm">
      <p className="text-ink-soft tabular">
        Showing {formatNumber(from)}–{formatNumber(to)} of {formatNumber(total)}
      </p>
      <div className="flex items-center gap-2">
        <button className={btn} onClick={() => onPage(page - 1)} disabled={page <= 1}>
          <ChevronLeft className="size-4" aria-hidden="true" /> Previous
        </button>
        <span className="px-2 tabular" aria-current="page">
          Page {page} of {pages}
        </span>
        <button className={btn} onClick={() => onPage(page + 1)} disabled={page >= pages}>
          Next <ChevronRight className="size-4" aria-hidden="true" />
        </button>
      </div>
    </nav>
  )
}
