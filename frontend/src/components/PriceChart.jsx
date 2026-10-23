import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatDate, formatPrice, formatShortDate } from '../utils/format'

const C = { modal: '#1f4d2b', band: '#ddedcf', predicted: '#d9a521', grid: '#e3e8de', axis: '#4b5a4f' }

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  return (
    <div className="rounded-lg border border-line bg-white px-3 py-2 text-sm shadow-[var(--shadow-soft)]">
      <p className="font-bold">Week ending {formatDate(label)}</p>
      {row.modal_price != null && <p className="tabular">Modal: {formatPrice(row.modal_price)}</p>}
      {row.min_price != null && (
        <p className="tabular text-ink-soft">
          Range: {formatPrice(row.min_price)} – {formatPrice(row.max_price)}
        </p>
      )}
      {row.predicted != null && <p className="tabular font-bold text-[#7a5a06]">Estimate: {formatPrice(row.predicted)}</p>}
      {row.range?.[0] != null && (
        <p className="tabular text-ink-soft">
          Typical range: {formatPrice(row.range[0])} – {formatPrice(row.range[1])}
        </p>
      )}
    </div>
  )
}

/**
 * Weekly price trend. `points`: [{date, modal_price, min_price?, max_price?}].
 * Optional `prediction`: {date, value, low, high, baseDate, basePrice} drawn as a dashed
 * segment from the last observed week to the estimate.
 */
export default function PriceChart({ points, prediction, height = 300, showBand = true, label = 'Price trend chart' }) {
  const data = points.map((p) => ({
    ...p,
    band: showBand && p.min_price != null ? [p.min_price, p.max_price] : undefined,
  }))
  if (prediction) {
    const last = data[data.length - 1]
    if (last) {
      last.predicted = last.modal_price
      // Anchor the error band at the latest observed price so it fans out to the estimate.
      if (prediction.low != null) last.range = [last.modal_price, last.modal_price]
    }
    data.push({
      date: prediction.date,
      predicted: prediction.value,
      range: prediction.low != null ? [prediction.low, prediction.high] : undefined,
    })
  }
  return (
    <div role="img" aria-label={label} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 4 }}>
          <CartesianGrid stroke={C.grid} vertical={false} />
          <XAxis dataKey="date" tickFormatter={formatShortDate} tick={{ fill: C.axis, fontSize: 12 }} minTickGap={28} tickLine={false} axisLine={{ stroke: C.grid }} />
          <YAxis
            tickFormatter={(v) => `₹${Math.round(v).toLocaleString('en-IN')}`}
            tick={{ fill: C.axis, fontSize: 12 }}
            width={72}
            domain={['auto', 'auto']}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<ChartTooltip />} />
          <Legend wrapperStyle={{ fontSize: 13 }} />
          {showBand && <Area dataKey="band" name="Min–max range" stroke="none" fill={C.band} fillOpacity={0.8} isAnimationActive={false} />}
          {prediction?.low != null && (
            <Area dataKey="range" name="Typical error range" stroke="none" fill={C.predicted} fillOpacity={0.18} isAnimationActive={false} />
          )}
          <Line dataKey="modal_price" name="Modal price" stroke={C.modal} strokeWidth={2.25} dot={false} isAnimationActive={false} connectNulls />
          {prediction && (
            <>
              <ReferenceLine x={prediction.baseDate} stroke={C.axis} strokeDasharray="2 4" />
              <Line dataKey="predicted" name="Estimate" stroke={C.predicted} strokeWidth={2.5} strokeDasharray="6 4" dot={{ r: 4, fill: C.predicted }} isAnimationActive={false} connectNulls />
            </>
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
