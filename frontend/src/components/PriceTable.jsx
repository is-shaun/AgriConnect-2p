import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import { Link } from 'react-router-dom'
import { formatDate, formatPrice, formatUnit } from '../utils/format'
import { DataBadge } from './feedback'

function SortHeader({ label, field, sort, onSort, align = 'left' }) {
  const alignCls = align === 'right' ? 'text-right' : 'text-left'
  if (!onSort) return <th scope="col" className={`px-4 py-3 ${alignCls}`}>{label}</th>
  const active = sort?.replace('-', '') === field
  const desc = sort?.startsWith('-')
  const Icon = !active ? ArrowUpDown : desc ? ArrowDown : ArrowUp
  return (
    <th scope="col" className={`px-4 py-3 ${alignCls}`} aria-sort={active ? (desc ? 'descending' : 'ascending') : 'none'}>
      <button
        className={`inline-flex items-center gap-1 font-bold hover:text-forest ${align === 'right' ? 'flex-row-reverse' : ''}`}
        onClick={() => onSort(active && !desc ? `-${field}` : field)}
      >
        {label}
        <Icon className={`size-3.5 ${active ? 'text-forest' : 'text-ink-soft/50'}`} aria-hidden="true" />
      </button>
    </th>
  )
}

/** Market price records. Shows min / modal / max separately; modal is the most common traded price. */
export default function PriceTable({ items, sort, onSort, showCrop = true, caption }) {
  return (
    <div className="overflow-x-auto -mx-5 md:mx-0">
      <table className="w-full min-w-[720px] text-sm">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead className="text-left text-ink-soft border-b border-line">
          <tr>
            {showCrop && <SortHeader label="Crop" field="crop" sort={sort} onSort={onSort} />}
            <SortHeader label="Market" field="market" sort={sort} onSort={onSort} />
            <SortHeader label="Date" field="observation_date" sort={sort} onSort={onSort} />
            <SortHeader label="Min" field="min_price" sort={sort} onSort={onSort} align="right" />
            <SortHeader label="Modal" field="modal_price" sort={sort} onSort={onSort} align="right" />
            <SortHeader label="Max" field="max_price" sort={sort} onSort={onSort} align="right" />
            <th scope="col" className="px-4 py-3">Source</th>
          </tr>
        </thead>
        <tbody>
          {items.map((p) => (
            <tr key={p.id} className="border-b border-line/60 last:border-0 hover:bg-field/70">
              {showCrop && (
                <td className="px-4 py-3 font-bold">
                  <Link to={`/crops/${p.crop.id}`} className="text-forest hover:underline underline-offset-4">
                    {p.crop.name}
                  </Link>
                </td>
              )}
              <td className="px-4 py-3">
                <span className="block">{p.location.market_name}</span>
                <span className="block text-xs text-ink-soft">
                  {p.location.district}, {p.location.state}
                </span>
              </td>
              <td className="px-4 py-3 whitespace-nowrap">{formatDate(p.observation_date)}</td>
              <td className="px-4 py-3 text-right tabular text-ink-soft">{formatPrice(p.min_price)}</td>
              <td className="px-4 py-3 text-right tabular font-bold">
                {formatPrice(p.modal_price)}
                <span className="block text-xs font-normal text-ink-soft">{formatUnit(p.unit)}</span>
              </td>
              <td className="px-4 py-3 text-right tabular text-ink-soft">{formatPrice(p.max_price)}</td>
              <td className="px-4 py-3">
                <DataBadge isDemo={p.is_demo} compact />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
