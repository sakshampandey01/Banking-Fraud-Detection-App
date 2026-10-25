import { formatAmount, formatTimestamp } from '../lib/format.js';
import RiskBadge from './RiskBadge.jsx';
import RiskScoreBar from './RiskScoreBar.jsx';

const COLUMNS = ['Transaction', 'Time', 'Type', 'From → To', 'Amount', 'Risk score', 'Level', 'Status'];

const ROW_TINT = { HIGH: 'bg-red-50/60', MEDIUM: 'bg-amber-50/50', LOW: '' };

export default function TransactionTable({ transactions }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <caption className="sr-only">Transactions, newest first</caption>
        <thead className="bg-slate-50">
          <tr>
            {COLUMNS.map((c) => (
              <th
                key={c}
                scope="col"
                className={`whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 ${
                  c === 'Amount' ? 'text-right' : 'text-left'
                }`}
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {transactions.length === 0 ? (
            <tr>
              <td colSpan={COLUMNS.length} className="px-4 py-10 text-center text-slate-500">
                No transactions match this filter.
              </td>
            </tr>
          ) : (
            transactions.map((t) => (
              <tr key={t.transactionID} className={ROW_TINT[t.riskLevel]}>
                <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-700">{t.transactionID}</td>
                <td className="whitespace-nowrap px-4 py-3 text-slate-600">{formatTimestamp(t.timestamp)}</td>
                <td className="whitespace-nowrap px-4 py-3 text-slate-700">{t.type.replace('_', ' ')}</td>
                <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-600">
                  {t.origAccount} → {t.destAccount}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums font-medium text-slate-900">
                  {formatAmount(t.amount)}
                </td>
                <td className="px-4 py-3"><RiskScoreBar score={t.riskScore} level={t.riskLevel} /></td>
                <td className="px-4 py-3"><RiskBadge level={t.riskLevel} /></td>
                <td className="whitespace-nowrap px-4 py-3 text-xs font-medium text-slate-600">{t.status}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
