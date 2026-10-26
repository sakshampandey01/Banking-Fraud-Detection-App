import { formatRiskScore } from '../lib/format.js';
import RiskBadge from './RiskBadge.jsx';
import RiskScoreBar from './RiskScoreBar.jsx';

/** Shows exactly what the API returned for one transaction. */
export default function ResultCard({ result }) {
  if (!result) return null;
  const tone = result.riskLevel === 'HIGH' ? 'border-red-300 bg-red-50' : result.riskLevel === 'MEDIUM' ? 'border-amber-300 bg-amber-50' : 'border-emerald-300 bg-emerald-50';
  return (
    <section aria-label="Prediction result" aria-live="polite" className={`rounded-xl border p-4 ${tone}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <RiskBadge level={result.riskLevel} />
          <span className="text-sm font-medium text-slate-900">
            {result.isFraud ? 'Suspected fraud' : 'Not flagged as fraud'}
          </span>
        </div>
        <RiskScoreBar score={result.probability} level={result.riskLevel} />
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-700 sm:grid-cols-4">
        <div><dt className="text-slate-500">Fraud probability</dt><dd className="tabular-nums">{formatRiskScore(result.probability)}</dd></div>
        <div><dt className="text-slate-500">Decision threshold</dt><dd className="tabular-nums">{formatRiskScore(result.threshold)}</dd></div>
        <div><dt className="text-slate-500">Model</dt><dd className="truncate">{result.modelName}</dd></div>
        <div><dt className="text-slate-500">Saved</dt><dd>{result.stored ? `Yes · ${result.transactionId} · ${result.status}` : 'No (check only)'}</dd></div>
      </dl>
      {result.message && <p className="mt-2 text-sm text-slate-800">{result.message}</p>}
    </section>
  );
}
