import { fromApi } from '../lib/transactionModel.js';
import { getJson, postJson } from './client.js';

/** Transactions scored by this application (source=API), newest first. */
export async function fetchTransactions({ limit = 200 } = {}) {
  return (await getJson(`/api/transactions?source=API&limit=${limit}`)).map(fromApi);
}

/** POST /api/transactions/evaluate: score with the model AND store the transaction. */
export async function evaluateTransaction({ type, amount, origAccount, destAccount, step }) {
  const body = { type, amount, orig_account: origAccount, dest_account: destAccount };
  if (step) body.step = Number(step);
  return resultFromApi(await postJson('/api/transactions/evaluate', body));
}

/** POST /api/predict: score only, nothing is stored. */
export async function predictTransaction({ type, amount, step, oldBalanceOrig, newBalanceOrig, oldBalanceDest, newBalanceDest }) {
  const body = {
    type, amount,
    old_balance_orig: oldBalanceOrig, new_balance_orig: newBalanceOrig,
    old_balance_dest: oldBalanceDest, new_balance_dest: newBalanceDest,
  };
  if (step) body.step = Number(step);
  return resultFromApi(await postJson('/api/predict', body));
}

/** Account helpers used by the form's pickers. */
export const fetchAccounts = () => getJson('/api/accounts?limit=200');
export const createAccount = ({ accountNumber, balance }) =>
  postJson('/api/accounts', { account_number: accountNumber, balance });

/** Adapter: EvaluateResponse | PredictResponse -> what the result card shows. */
export function resultFromApi(r) {
  return {
    transactionId: r.txn_id != null ? `TXN-${r.txn_id}` : null,   // null => nothing was stored
    stored: r.txn_id != null,
    status: r.status ?? null,
    riskLevel: r.risk_level,
    probability: r.fraud_probability,
    isFraud: r.is_fraud,
    threshold: r.decision_threshold,
    modelName: r.model_name,
    message: r.message ?? null,
    originAccountStatus: r.origin_account_status ?? null,
  };
}
