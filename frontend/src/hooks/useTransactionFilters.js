import { useMemo, useReducer } from 'react';
import { filterReducer, initialFilterState } from '../lib/filterReducer.js';
import { computeMetrics, countByView, filterTransactions } from '../lib/transactionFilters.js';

/**
 * Owns ALL filter state for the dashboard.
 * Components get data + setters; they never filter or count anything themselves.
 * @param {import('../lib/transactionModel.js').Transaction[]} transactions
 */
export function useTransactionFilters(transactions) {
  const [filters, dispatch] = useReducer(filterReducer, initialFilterState);

  const visible = useMemo(() => filterTransactions(transactions, filters), [transactions, filters]);
  const metrics = useMemo(() => computeMetrics(transactions), [transactions]);
  const counts  = useMemo(() => countByView(transactions), [transactions]);

  return {
    filters,
    visible,      // -> <TransactionTable />
    metrics,      // -> <RiskMetricsBar />
    counts,       // -> <FilterTabs />
    setView:  (view)  => dispatch({ type: 'SET_VIEW', view }),
    setQuery: (query) => dispatch({ type: 'SET_QUERY', query }),
    reset:    ()      => dispatch({ type: 'RESET' }),
  };
}
