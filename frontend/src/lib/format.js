/**
 * riskScore is a 0..1 probability (backend: fraud_probability).
 * These helpers are the ONLY place it is turned into a percentage.
 * Never do `score * 100` or `score + '%'` inline in a component.
 */
const clamp01 = (n) => (Number.isFinite(n) ? Math.min(1, Math.max(0, n)) : 0);

/** 0.9944 -> 99.44 (a number, for bar widths) */
export const riskPercent = (score) => clamp01(score) * 100;

/** 0.9944 -> "99.4%" ; 0.5 -> "50.0%" ; null/NaN -> "0.0%" */
export const formatRiskScore = (score) => `${riskPercent(score).toFixed(1)}%`;

const amountFmt = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
/** The dataset has no currency, so no symbol is shown. */
export const formatAmount = (n) => amountFmt.format(n);

export const formatCount = (n) => new Intl.NumberFormat('en-US').format(n ?? 0);

export const formatTimestamp = (iso) =>
  new Date(iso).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
