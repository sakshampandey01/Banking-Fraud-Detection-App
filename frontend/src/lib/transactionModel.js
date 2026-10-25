/**
 * @typedef {'LOW'|'MEDIUM'|'HIGH'} RiskLevel
 *
 * @typedef {Object} Transaction            // the shape every component consumes
 * @property {string}  transactionID        // "TXN-1000003"
 * @property {number}  amount
 * @property {string}  type                 // CASH_IN | CASH_OUT | DEBIT | PAYMENT | TRANSFER
 * @property {string}  origAccount
 * @property {string}  destAccount
 * @property {number}  riskScore            // 0..1 decimal (backend: fraud_probability). Use lib/format.js to display it
 * @property {RiskLevel} riskLevel          // backend decides; never recompute in the UI
 * @property {boolean} isFlagged            // riskLevel is MEDIUM or HIGH
 * @property {'COMPLETED'|'BLOCKED'} status
 * @property {string}  timestamp            // ISO 8601 (backend: created_at)
 */

/**
 * Adapter: backend TransactionOut  ->  frontend Transaction.
 * This is the ONLY place that knows backend field names. Rename a column
 * server-side and you change this one function.
 * @param {Object} row  one item of GET /api/transactions
 * @returns {Transaction}
 */
export function fromApi(row) {
  const riskLevel = row.risk_level ?? 'LOW';     // DATASET rows have no ML verdict
  return {
    transactionID: `TXN-${row.txn_id}`,
    amount: Number(row.amount),                  // API sends Decimal as string/number
    type: row.type_code,
    origAccount: row.orig_account,
    destAccount: row.dest_account,
    riskScore: row.fraud_probability ?? 0,
    riskLevel,
    isFlagged: riskLevel === 'MEDIUM' || riskLevel === 'HIGH',
    status: row.status,
    timestamp: new Date(row.created_at).toISOString(),
  };
}
