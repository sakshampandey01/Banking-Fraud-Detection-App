// Display-only mirrors of the backend's decision rules. The API returns riskLevel already decided;
// the UI never recomputes it. The real values come from GET /api/health (model.threshold) and each
// prediction response (decision_threshold) - these are only fallbacks for labels.
export const RISK_LEVELS = /** @type {const} */ (['LOW', 'MEDIUM', 'HIGH']);
export const TRANSACTION_TYPES = /** @type {const} */ (['PAYMENT', 'TRANSFER', 'CASH_OUT', 'CASH_IN', 'DEBIT']);

export const VIEWS = /** @type {const} */ ({
  ALL: 'all',
  FLAGGED: 'flagged',
  HIGH_RISK: 'highRisk',
});
