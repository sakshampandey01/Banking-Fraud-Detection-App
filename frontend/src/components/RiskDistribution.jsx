import { formatCount } from '../lib/format.js';

const SEGMENTS = [
  { key: 'high',   label: 'High',   bar: 'bg-red-500',     dot: 'bg-red-500' },
  { key: 'medium', label: 'Medium', bar: 'bg-amber-500',   dot: 'bg-amber-500' },
  { key: 'low',    label: 'Low',    bar: 'bg-emerald-500', dot: 'bg-emerald-500' },
];

/** Stacked bar of live model decisions by risk level (stats.live). */
export default function RiskDistribution({ live }) {
  if (!live) return null;
  const total = live.high + live.medium + live.low;

  return (
    <section aria-label="Risk distribution" className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">Risk distribution</h2>
      <p className="text-xs text-slate-500">{formatCount(total)} transactions scored live</p>

      <div className="mt-4 flex h-3 overflow-hidden rounded-full bg-slate-200" role="presentation">
        {total > 0 && SEGMENTS.map(({ key, bar }) => (
          <div key={key} className={bar} style={{ width: `${(live[key] / total) * 100}%` }} />
        ))}
      </div>

      <ul className="mt-4 space-y-2 text-sm">
        {SEGMENTS.map(({ key, label, dot }) => (
          <li key={key} className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-slate-600">
              <span className={`h-2.5 w-2.5 rounded-full ${dot}`} aria-hidden="true" />
              {label}
            </span>
            <span className="tabular-nums font-medium text-slate-900">
              {formatCount(live[key])}
              <span className="ml-1 text-xs font-normal text-slate-500">
                ({total ? Math.round((live[key] / total) * 100) : 0}%)
              </span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
