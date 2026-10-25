import { formatAmount, formatTimestamp } from '../lib/format.js';
import { isHighRisk } from '../lib/transactionFilters.js';
import RiskScoreBar from './RiskScoreBar.jsx';

/** Most recent HIGH-risk transactions. `transactions` is already newest-first-agnostic; we sort here. */
export default function AlertsPanel({ transactions, limit = 5 }) {
  const alerts = transactions
    .filter(isHighRisk)
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, limit);

  return (
    <section aria-label="Fraud alerts" className="rounded-xl border border-red-200 bg-white shadow-sm">
      <header className="flex items-center justify-between border-b border-red-100 bg-red-50 px-4 py-3 rounded-t-xl">
        <h2 className="text-sm font-semibold text-red-900">Fraud alerts</h2>
        <span className="rounded-full bg-red-600 px-2 py-0.5 text-xs font-semibold text-white">{alerts.length}</span>
      </header>

      {alerts.length === 0 ? (
        <p className="p-6 text-center text-sm text-slate-500">No high-risk activity. All clear.</p>
      ) : (
        <ul className="divide-y divide-slate-100" aria-live="polite">
          {alerts.map((t) => (
            <li key={t.transactionID} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-900">
                  {t.type.replace('_', ' ')} · <span className="tabular-nums">{formatAmount(t.amount)}</span>
                </p>
                <p className="truncate text-xs text-slate-500">
                  {t.origAccount} → {t.destAccount} · {formatTimestamp(t.timestamp)}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <RiskScoreBar score={t.riskScore} level={t.riskLevel} />
                <span className="rounded bg-slate-900 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                  {t.status}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
