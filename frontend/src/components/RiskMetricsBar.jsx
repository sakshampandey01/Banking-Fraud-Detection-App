import { formatCount } from '../lib/format.js';

const ACCENT = {
  neutral: 'text-slate-900',
  danger: 'text-red-700',
  warn: 'text-amber-700',
};

function MetricCard({ label, value, hint, accent = 'neutral' }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className={`mt-1 text-3xl font-semibold tabular-nums ${ACCENT[accent]}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

/** Headline numbers straight from GET /api/stats (server-side counts, not the loaded page). */
export default function RiskMetricsBar({ stats }) {
  if (!stats) return null;
  return (
    <section aria-label="Risk metrics" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        label="Total transactions"
        value={formatCount(stats.totalTransactions)}
        hint={stats.dataset.transactions > 0 ? `${formatCount(stats.dataset.fraud)} labelled fraud in the historical dataset` : 'Transactions scored by this application'}
      />
      <MetricCard label="Processed today" value={formatCount(stats.transactionsToday)} hint="Scored live by the model" />
      <MetricCard
        label="High-risk detections"
        value={formatCount(stats.highRiskDetections)}
        hint="Blocked by the model"
        accent="danger"
      />
      <MetricCard label="Blocked accounts" value={formatCount(stats.blockedAccounts)} hint="Awaiting analyst review" accent="warn" />
    </section>
  );
}
