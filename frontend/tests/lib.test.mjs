// Plain-Node tests (no browser, no build): `npm test`. They run the real src/ modules with a fake fetch.
import assert from 'node:assert/strict';
import { afterEach, describe, test } from 'node:test';

import { ApiError, parseErrorBody } from '../src/api/client.js';
import { fetchHealth, fetchStats, statsFromApi } from '../src/api/statsApi.js';
import { evaluateTransaction, fetchTransactions, predictTransaction, resultFromApi } from '../src/api/transactionsApi.js';
import { filterReducer, initialFilterState } from '../src/lib/filterReducer.js';
import { formatAmount, formatRiskScore, riskPercent } from '../src/lib/format.js';
import { parseMoney, toPayload, validateForm } from '../src/lib/formValidation.js';
import { computeMetrics, countByView, filterTransactions } from '../src/lib/transactionFilters.js';
import { fromApi } from '../src/lib/transactionModel.js';

const realFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = realFetch; });

/** Install a fake fetch that records calls and returns the queued JSON bodies. */
function fakeFetch(...responses) {
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options, body: options.body ? JSON.parse(options.body) : undefined });
    const r = responses.shift();
    if (r instanceof Error) throw r;
    return { ok: r.status < 400, status: r.status, statusText: r.statusText ?? '', json: async () => { if (r.notJson) throw new Error('x'); return r.body; } };
  };
  return calls;
}

const ROW = { txn_id: 12, step: 5, type_code: 'TRANSFER', amount: '1000.00', status: 'COMPLETED', source: 'API', created_at: '2026-10-25T02:14:09Z',
  orig_account: 'C1', dest_account: 'C2', fraud_probability: 0.97, risk_level: 'HIGH' };

describe('API paths and shapes (what the backend really exposes)', () => {
  test('transactions come from /api/transactions?source=API and are adapted', async () => {
    const calls = fakeFetch({ status: 200, body: [ROW] });
    const [t] = await fetchTransactions({ limit: 50 });
    assert.equal(calls[0].url, 'http://localhost:8000/api/transactions?source=API&limit=50');
    assert.deepEqual([t.transactionID, t.amount, t.riskScore, t.riskLevel, t.isFlagged], ['TXN-12', 1000, 0.97, 'HIGH', true]);
  });

  test('stats come from /api/stats and are mapped to camelCase', async () => {
    const body = { total_transactions: 7, transactions_today: 3, fraud_flagged: 1, blocked_accounts: 2,
      live: { evaluated: 7, today: 3, high: 1, medium: 2, low: 4 }, dataset: { transactions: 0, fraud: 0 } };
    const calls = fakeFetch({ status: 200, body });
    const s = await fetchStats();
    assert.equal(calls[0].url, 'http://localhost:8000/api/stats');
    assert.equal(s.totalTransactions, 7); assert.equal(s.highRiskDetections, 1); assert.equal(s.blockedAccounts, 2);
    assert.deepEqual(statsFromApi(body).live, body.live);
  });

  test('health comes from /api/health', async () => {
    const calls = fakeFetch({ status: 200, body: { status: 'ok', ready_for_scoring: true, issues: [] } });
    assert.equal((await fetchHealth()).ready_for_scoring, true);
    assert.equal(calls[0].url, 'http://localhost:8000/api/health');
  });

  test('evaluate POSTs snake_case JSON to /api/transactions/evaluate', async () => {
    const calls = fakeFetch({ status: 201, body: { txn_id: 5, status: 'BLOCKED', risk_level: 'HIGH', action_taken: 'BLOCKED', is_fraud: true,
      fraud_probability: 0.95, decision_threshold: 0.908351, model_name: 'XGBoost', origin_account_status: 'BLOCKED', message: 'blocked' } });
    const r = await evaluateTransaction({ type: 'TRANSFER', amount: 950000, origAccount: 'C1', destAccount: 'C2', step: '27' });
    assert.equal(calls[0].url, 'http://localhost:8000/api/transactions/evaluate');
    assert.equal(calls[0].options.method, 'POST');
    assert.deepEqual(calls[0].body, { type: 'TRANSFER', amount: 950000, orig_account: 'C1', dest_account: 'C2', step: 27 });
    assert.deepEqual([r.stored, r.transactionId, r.riskLevel, r.probability, r.isFraud, r.originAccountStatus], [true, 'TXN-5', 'HIGH', 0.95, true, 'BLOCKED']);
  });

  test('evaluate omits step when it is blank', async () => {
    const calls = fakeFetch({ status: 201, body: { txn_id: 1, risk_level: 'LOW', fraud_probability: 0.01, is_fraud: false, decision_threshold: 0.9, model_name: 'm' } });
    await evaluateTransaction({ type: 'PAYMENT', amount: 5, origAccount: 'C1', destAccount: 'M2', step: undefined });
    assert.equal('step' in calls[0].body, false);
  });

  test('predict POSTs the four balances to /api/predict and reports "not stored"', async () => {
    const calls = fakeFetch({ status: 200, body: { fraud_probability: 0.3, is_fraud: false, risk_level: 'LOW', decision_threshold: 0.908351, medium_threshold: 0.5, model_name: 'XGBoost', step: 3 } });
    const r = await predictTransaction({ type: 'TRANSFER', amount: 181, step: undefined, oldBalanceOrig: 181, newBalanceOrig: 0, oldBalanceDest: 0, newBalanceDest: 181 });
    assert.equal(calls[0].url, 'http://localhost:8000/api/predict');
    assert.deepEqual(calls[0].body, { type: 'TRANSFER', amount: 181, old_balance_orig: 181, new_balance_orig: 0, old_balance_dest: 0, new_balance_dest: 181 });
    assert.equal(r.stored, false); assert.equal(r.transactionId, null);
  });
});

describe('errors', () => {
  test('backend error envelope becomes ApiError with code and message', async () => {
    fakeFetch({ status: 422, body: { error: { code: 'INSUFFICIENT_FUNDS', message: 'Insufficient funds: balance 5, requested 10' } } });
    await assert.rejects(fetchStats(), (e) => e instanceof ApiError && e.status === 422 && e.code === 'INSUFFICIENT_FUNDS' && /Insufficient funds/.test(e.message));
  });

  test('503 with instructions keeps the message', async () => {
    fakeFetch({ status: 503, body: { error: { code: 'MODEL_UNAVAILABLE', message: 'Model file not found: ...' } } });
    await assert.rejects(fetchStats(), (e) => e.code === 'MODEL_UNAVAILABLE' && e.status === 503);
  });

  test('FastAPI {detail} and non-JSON bodies are handled', async () => {
    fakeFetch({ status: 404, body: { detail: 'Account not found' } }, { status: 500, statusText: 'Internal Server Error', notJson: true });
    await assert.rejects(fetchStats(), /Account not found/);
    await assert.rejects(fetchStats(), /Internal Server Error/);
  });

  test('network failure explains the backend is unreachable', async () => {
    fakeFetch(new TypeError('Failed to fetch'));
    await assert.rejects(fetchStats(), (e) => e.code === 'NETWORK_ERROR' && /Cannot reach the API/.test(e.message));
  });

  test('parseErrorBody fallback', () => {
    assert.equal(parseErrorBody(null, 'fallback').message, 'fallback');
  });
});

describe('transaction adapter and filters', () => {
  const txns = [
    fromApi({ ...ROW, txn_id: 1, risk_level: 'LOW', fraud_probability: 0.01, created_at: '2026-10-25T01:00:00Z' }),
    fromApi({ ...ROW, txn_id: 2, risk_level: 'MEDIUM', fraud_probability: 0.6, created_at: '2026-10-25T02:00:00Z', amount: '50.50' }),
    fromApi({ ...ROW, txn_id: 3, risk_level: 'HIGH', fraud_probability: 0.95, status: 'BLOCKED', created_at: '2026-10-25T03:00:00Z' }),
  ];
  test('metrics are computed only from real rows', () => {
    const m = computeMetrics(txns);
    assert.deepEqual([m.total, m.flaggedCount, m.highRiskCount, m.blockedCount], [3, 2, 1, 1]);
    assert.ok(Math.abs(m.amountAtRisk - 1050.5) < 1e-9);
  });
  test('empty list gives zeros, not NaN', () => {
    const m = computeMetrics([]);
    assert.deepEqual([m.total, m.flaggedRate, m.avgRiskScore, m.amountAtRisk], [0, 0, 0, 0]);
  });
  test('filters, search and counts', () => {
    assert.deepEqual(filterTransactions(txns, { view: 'highRisk' }).map((t) => t.transactionID), ['TXN-3']);
    assert.deepEqual(filterTransactions(txns, { view: 'flagged' }).map((t) => t.transactionID), ['TXN-3', 'TXN-2']);
    assert.deepEqual(filterTransactions(txns, { query: 'txn-1' }).map((t) => t.transactionID), ['TXN-1']);
    assert.deepEqual(countByView(txns), { all: 3, flagged: 2, highRisk: 1 });
  });
  test('reducer', () => {
    assert.equal(filterReducer(initialFilterState, { type: 'SET_VIEW', view: 'flagged' }).view, 'flagged');
    assert.deepEqual(filterReducer({ view: 'x', query: 'y' }, { type: 'RESET' }), initialFilterState);
  });
  test('resultFromApi never invents a transaction id', () => {
    assert.equal(resultFromApi({ risk_level: 'LOW', fraud_probability: 0.1, is_fraud: false }).transactionId, null);
  });
});

describe('formatting', () => {
  test('probabilities', () => {
    assert.equal(formatRiskScore(0.9944), '99.4%'); assert.equal(formatRiskScore(null), '0.0%'); assert.equal(riskPercent(7), 100);
    assert.equal(formatAmount(1234.5), '1,234.50');
  });
});

describe('form validation mirrors the backend rules', () => {
  const ok = { type: 'TRANSFER', amount: '1,500.50', step: '', origAccount: 'C1', destAccount: 'M2',
    oldBalanceOrig: '10', newBalanceOrig: '0', oldBalanceDest: '0', newBalanceDest: '10' };
  test('valid input passes in both modes', () => {
    assert.deepEqual(validateForm(ok, 'evaluate'), {}); assert.deepEqual(validateForm(ok, 'check'), {});
  });
  test('amount rules', () => {
    for (const bad of ['', 'abc', '0', '-5', '1.234', '1e5', 'NaN']) assert.ok(validateForm({ ...ok, amount: bad }, 'evaluate').amount, `amount ${bad}`);
    assert.equal(parseMoney('1,500.50'), 1500.5);
  });
  test('account rules', () => {
    for (const bad of ['', 'X1', 'C', 'c12', 'C1234567890123456789']) assert.ok(validateForm({ ...ok, origAccount: bad }, 'evaluate').origAccount, bad);
    assert.ok(validateForm({ ...ok, origAccount: 'C1', destAccount: 'C1' }, 'evaluate').destAccount);
  });
  test('step rules', () => {
    for (const bad of ['0', '744', '1.5', 'x']) assert.ok(validateForm({ ...ok, step: bad }, 'check').step, bad);
    assert.equal(validateForm({ ...ok, step: '743' }, 'check').step, undefined);
  });
  test('balances must be present and non-negative in check mode', () => {
    assert.ok(validateForm({ ...ok, oldBalanceDest: '' }, 'check').oldBalanceDest);
    assert.ok(validateForm({ ...ok, newBalanceOrig: '-1' }, 'check').newBalanceOrig);
  });
  test('payload conversion', () => {
    assert.deepEqual(toPayload({ ...ok, step: '27' }, 'evaluate'), { type: 'TRANSFER', amount: 1500.5, step: 27, origAccount: 'C1', destAccount: 'M2' });
    assert.equal(toPayload(ok, 'check').oldBalanceOrig, 10);
  });
});
