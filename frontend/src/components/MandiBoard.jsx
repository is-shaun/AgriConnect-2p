import { Link } from 'react-router-dom'
import { formatDate, formatPrice } from '../utils/format'

/**
 * The "mandi board": latest modal price per crop, styled like the chalk price boards
 * at Indian market yards. Rows come straight from GET /api/prices?latest=true.
 */
export default function MandiBoard({ prices, title = 'Latest mandi prices', compact = false }) {
  const isDemo = prices.some((p) => p.is_demo)
  const newest = prices.reduce((d, p) => (p.observation_date > d ? p.observation_date : d), '')
  return (
    <figure className="mandi-board p-5 sm:p-6">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-2 pb-3 mb-1 border-b-2 border-chalk/25">
        <span className="font-display text-xl font-bold text-white">{title}</span>
        <span className="text-xs text-chalk/75">₹ per quintal, as of {formatDate(newest)}</span>
      </figcaption>
      <table className="w-full text-[0.95rem]">
        <thead className="sr-only">
          <tr>
            <th>Crop</th>
            <th>Market</th>
            <th>Modal price</th>
          </tr>
        </thead>
        <tbody>
          {prices.map((p) => (
            <tr key={p.id} className="board-row">
              <td className="py-2.5 pr-2">
                <Link to={`/crops/${p.crop.id}`} className="font-bold text-white hover:underline underline-offset-4">
                  {p.crop.name}
                </Link>
              </td>
              {!compact && <td className="py-2.5 pr-2 text-chalk/70 text-sm">{p.location.market_name}</td>}
              <td className="py-2.5 text-right tabular font-display text-lg font-semibold text-[#f6e7b0]">
                {formatPrice(p.modal_price)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {isDemo && (
        <p className="mt-3 rounded bg-mustard/20 px-2.5 py-1.5 text-xs text-[#f6e7b0]">
          Demo board: these are synthetic prices for demonstration, not real mandi rates.
        </p>
      )}
    </figure>
  )
}
