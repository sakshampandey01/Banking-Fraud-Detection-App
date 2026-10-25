// Mirrors the backend's decision rules (README "Decision rules").
// The API returns riskLevel already decided; these are only used for display
// (e.g. drawing threshold lines on a chart) and for validating mock data.
export const RISK_LEVELS = /** @type {const} */ (['LOW', 'MEDIUM', 'HIGH']);
export const HIGH_RISK_THRESHOLD = 0.908351;   // models/best_fraud_model_tuned.pkl
export const MEDIUM_RISK_THRESHOLD = 0.5;      // MEDIUM_RISK_THRESHOLD in .env

export const VIEWS = /** @type {const} */ ({
  ALL: 'all',
  FLAGGED: 'flagged',
  HIGH_RISK: 'highRisk',
});
