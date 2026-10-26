import { useCallback, useEffect, useState } from 'react';
import { fetchHealth, fetchStats } from '../api/statsApi.js';
import { fetchTransactions } from '../api/transactionsApi.js';

const POLL_MS = 30_000;

/**
 * Loads transactions + stats + health together and re-polls. Components never call fetch directly.
 * `loading` is true only for the first load; background refreshes keep the old data visible.
 * Health is best-effort: if only /api/health fails, the dashboard still shows the rest.
 */
export function useDashboardData() {
  const [state, setState] = useState({ transactions: [], stats: null, health: null, loading: true, error: null, updatedAt: null });

  const load = useCallback(async () => {
    try {
      const [transactions, stats, health] = await Promise.all([
        fetchTransactions(), fetchStats(), fetchHealth().catch(() => null),
      ]);
      setState({ transactions, stats, health, loading: false, error: null, updatedAt: new Date() });
    } catch (err) {
      setState((s) => ({ ...s, loading: false, error: err.message }));   // keep stale data on screen
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, [load]);

  return { ...state, refresh: load };
}
