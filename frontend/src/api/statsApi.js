import mock from '../data/mockStats.json' with { type: 'json' };
import { USE_MOCK, getJson } from './client.js';

/**
 * @typedef {Object} Stats
 * @property {number} totalTransactions   dataset + live
 * @property {number} transactionsToday   live, since midnight (DB time zone)
 * @property {number} highRiskDetections  live HIGH-risk decisions (backend: fraud_flagged)
 * @property {number} blockedAccounts
 * @property {{evaluated:number,today:number,high:number,medium:number,low:number}} live
 * @property {{transactions:number,fraud:number}} dataset
 */

/** Adapter: GET /api/stats (StatsOut) -> Stats. Only place that knows these snake_case names. */
export function statsFromApi(s) {
  return {
    totalTransactions: s.total_transactions,
    transactionsToday: s.transactions_today,
    highRiskDetections: s.fraud_flagged,
    blockedAccounts: s.blocked_accounts,
    live: s.live,
    dataset: s.dataset,
  };
}

/** @returns {Promise<Stats>} */
export async function fetchStats() {
  return statsFromApi(USE_MOCK ? mock : await getJson('/stats'));
}
