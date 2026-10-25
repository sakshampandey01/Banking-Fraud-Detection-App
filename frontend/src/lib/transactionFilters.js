import { VIEWS } from './constants.js';

/** @typedef {import('./transactionModel.js').Transaction} Transaction */

// ---- predicates (single source of truth for what "High Risk"/"Flagged" mean) ----
/** HIGH = model said fraud; the backend blocked the transaction. */
export const isHighRisk = (t) => t.riskLevel === 'HIGH';
/** Flagged = MEDIUM or HIGH (so High Risk is a subset of Flagged). */
export const isFlagged = (t) => t.isFlagged === true;

/**
 * @param {Transaction[]} transactions
 * @param {{ view?: string, query?: string }} filters
 * @returns {Transaction[]}  new array, newest first; input is never mutated
 */
export function filterTransactions(transactions, { view = VIEWS.ALL, query = '' } = {}) {
  const q = query.trim().toLowerCase();

  return transactions
    .filter((t) => {
      if (view === VIEWS.HIGH_RISK && !isHighRisk(t)) return false;
      if (view === VIEWS.FLAGGED && !isFlagged(t)) return false;
      if (!q) return true;
      return [t.transactionID, t.origAccount, t.destAccount, t.type]
        .some((field) => field?.toLowerCase().includes(q));
    })
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
}

/** Headline numbers for the risk-metric cards. Always computed from ALL transactions, not the filtered view. */
export function computeMetrics(transactions) {
  const total = transactions.length;
  const flagged = transactions.filter(isFlagged);
  const high = transactions.filter(isHighRisk);
  const sum = (arr) => arr.reduce((s, t) => s + t.amount, 0);

  return {
    total,
    flaggedCount: flagged.length,
    highRiskCount: high.length,
    blockedCount: transactions.filter((t) => t.status === 'BLOCKED').length,
    flaggedRate: total ? flagged.length / total : 0,
    avgRiskScore: total ? transactions.reduce((s, t) => s + t.riskScore, 0) / total : 0,
    amountAtRisk: sum(flagged),
  };
}

/** Counts per tab, so buttons can show "High Risk (3)". */
export function countByView(transactions) {
  return {
    [VIEWS.ALL]: transactions.length,
    [VIEWS.FLAGGED]: transactions.filter(isFlagged).length,
    [VIEWS.HIGH_RISK]: transactions.filter(isHighRisk).length,
  };
}
