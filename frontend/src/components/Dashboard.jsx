import { USE_MOCK } from '../api/client.js';
import { useDashboardData } from '../hooks/useDashboardData.js';
import { useTransactionFilters } from '../hooks/useTransactionFilters.js';
import AlertsPanel from './AlertsPanel.jsx';
import FilterTabs from './FilterTabs.jsx';
import RiskDistribution from './RiskDistribution.jsx';
import RiskMetricsBar from './RiskMetricsBar.jsx';
import TransactionTable from './TransactionTable.jsx';

export default function Dashboard() {
  const { transactions, stats, loading, error, updatedAt, refresh } = useDashboardData();
  const { filters, visible, counts, setView, setQuery } = useTransactionFilters(transactions);

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Fraud Monitor</h1>
          <p className="text-sm text-slate-500">
            {updatedAt ? `Updated ${updatedAt.toLocaleTimeString()}` : 'Loading…'}
            {USE_MOCK && (
              <span className="ml-2 rounded bg-slate-200 px-1.5 py-0.5 text-xs font-medium text-slate-700">Mock data</span>
            )}
          </p>
        </div>
        <button
          onClick={refresh}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
        >
          Refresh
        </button>
      </header>

      {error && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          Couldn’t reach the API: {error}.{' '}
          {transactions.length > 0 ? 'Showing the last data received.' : 'Is the backend running on the configured URL?'}
        </div>
      )}

      {loading ? (
        <p className="py-20 text-center text-slate-500" role="status">Loading dashboard…</p>
      ) : (
        <>
          <RiskMetricsBar stats={stats} />

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2"><AlertsPanel transactions={transactions} /></div>
            <RiskDistribution live={stats?.live} />
          </div>

          <section aria-label="Transactions" className="space-y-3">
            <FilterTabs
              view={filters.view}
              counts={counts}
              onViewChange={setView}
              query={filters.query}
              onQueryChange={setQuery}
            />
            <TransactionTable transactions={visible} />
          </section>
        </>
      )}
    </div>
  );
}
