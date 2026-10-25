import { formatRiskScore, riskPercent } from '../lib/format.js';

const BAR = { HIGH: 'bg-red-500', MEDIUM: 'bg-amber-500', LOW: 'bg-emerald-500' };

/** riskScore is a 0..1 decimal; all conversion to % happens in lib/format.js. */
export default function RiskScoreBar({ score, level }) {
  return (
    <div className="flex items-center gap-2" title={`Fraud probability ${score}`}>
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-200" role="presentation">
        <div className={`h-full rounded-full ${BAR[level] ?? BAR.LOW}`} style={{ width: `${riskPercent(score)}%` }} />
      </div>
      <span className="w-12 text-right text-xs tabular-nums text-slate-700">{formatRiskScore(score)}</span>
    </div>
  );
}
