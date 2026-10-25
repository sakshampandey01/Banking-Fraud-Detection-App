import { fromApi } from '../lib/transactionModel.js';
import mock from '../data/mockTransactions.json' with { type: 'json' };
import { USE_MOCK, getJson } from './client.js';

/** @returns {Promise<import('../lib/transactionModel.js').Transaction[]>} */
export async function fetchTransactions({ limit = 200 } = {}) {
  if (USE_MOCK) return mock;
  return (await getJson(`/transactions?limit=${limit}`)).map(fromApi);
}
