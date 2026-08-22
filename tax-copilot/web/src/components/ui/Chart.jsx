import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

import { seriesColor } from './chartTokens.js';

/**
 * Chart shell for the two forms this app needs: grouped bars and single-series
 * bars, both comparing magnitudes across named settings.
 *
 * Colours are slots 1-3 of the validated categorical order (blue, orange, aqua),
 * read from CSS custom properties so dark mode uses steps chosen for the dark
 * surface rather than an automatic flip. On light, aqua sits at 2.74:1 against
 * the surface -- below the 3:1 line -- so every chart here is accompanied by its
 * data table, which is the relief that permits it.
 */

function ChartTooltip({ active, payload, label, formatter }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-title">{label}</div>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="chart-tooltip-row">
          <span className="chart-swatch" style={{ backgroundColor: entry.color }} />
          <span>{entry.name}</span>
          <strong style={{ marginInlineStart: 'auto' }}>
            {formatter ? formatter(entry.value) : entry.value}
          </strong>
        </div>
      ))}
    </div>
  );
}

export function Legend({ series }) {
  // Always rendered for two or more series: identity must never be carried by
  // colour alone.
  if (series.length < 2) return null;
  return (
    <div className="chart-legend">
      {series.map((item, index) => (
        <span key={item.key} className="chart-legend-item">
          <span className="chart-swatch" style={{ backgroundColor: seriesColor(index) }} />
          {item.label}
        </span>
      ))}
    </div>
  );
}

export function GroupedBarChart({
  data,
  series,
  xKey = 'name',
  height = 260,
  domain = [0, 1],
  formatter = (v) => (v == null ? '—' : Number(v).toFixed(3)),
}) {
  return (
    <div className="chart-frame">
      <Legend series={series} />
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }} barGap={2}>
          <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
          <XAxis
            dataKey={xKey}
            tick={{ fill: 'var(--chart-axis)', fontSize: 11 }}
            axisLine={{ stroke: 'var(--chart-grid)' }}
            tickLine={false}
            interval={0}
          />
          <YAxis
            domain={domain}
            tick={{ fill: 'var(--chart-axis)', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={40}
            orientation="right"
          />
          <Tooltip
            cursor={{ fill: 'var(--surface-hover)' }}
            content={<ChartTooltip formatter={formatter} />}
          />
          {series.map((item, index) => (
            <Bar
              key={item.key}
              dataKey={item.key}
              name={item.label}
              fill={seriesColor(index)}
              radius={[4, 4, 0, 0]}
              maxBarSize={38}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Single series, coloured per bar only to mark the baseline row. */
export function HighlightBarChart({
  data,
  dataKey,
  xKey = 'name',
  height = 240,
  domain = [0, 1],
  highlightKey = 'isBaseline',
  formatter = (v) => (v == null ? '—' : Number(v).toFixed(3)),
}) {
  return (
    <div className="chart-frame">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
          <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
          <XAxis
            dataKey={xKey}
            tick={{ fill: 'var(--chart-axis)', fontSize: 11 }}
            axisLine={{ stroke: 'var(--chart-grid)' }}
            tickLine={false}
            interval={0}
          />
          <YAxis
            domain={domain}
            tick={{ fill: 'var(--chart-axis)', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={40}
            orientation="right"
          />
          <Tooltip
            cursor={{ fill: 'var(--surface-hover)' }}
            content={<ChartTooltip formatter={formatter} />}
          />
          <Bar dataKey={dataKey} radius={[4, 4, 0, 0]} maxBarSize={44}>
            {data.map((row, index) => (
              <Cell
                key={index}
                // Colour follows the entity, not the rank: the highlighted bar is
                // the baseline config, wherever it happens to sort.
                fill={row[highlightKey] ? seriesColor(1) : seriesColor(0)}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
