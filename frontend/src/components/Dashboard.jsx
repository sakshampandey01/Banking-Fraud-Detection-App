import { useDashboardData } from '../hooks/useDashboardData.js';
import { useTransactionFilters } from '../hooks/useTransactionFilters.js';
import AlertsPanel from './AlertsPanel.jsx';
import FilterTabs from './FilterTabs.jsx';
import HealthBanner from './HealthBanner.jsx';
import PredictionForm from './PredictionForm.jsx';
import RiskDistribution from './RiskDistribution.jsx';
import RiskMetricsBar from './RiskMetricsBar.jsx';
import TransactionTable from './TransactionTable.jsx';

export default function Dashboard() {
  const { transactions, stats, health, loading, error, updatedAt, refresh } = useDashboardData();
  const { filters, visible, counts, setView, setQuery } = useTransactionFilters(transactions);
  const notReady = health && !health.ready_for_scoring ? 'Scoring is currently unavailable (see the notice above).' : null;

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Fraud Monitor</h1>
          <p className="text-sm text-slate-500">
            {updatedAt ? `Updated ${updatedAt.toLocaleTimeString()}` : 'Loading…'}
            {health?.model?.loaded && <span className="ml-2 text-xs">Model: {health.model.name}</span>}
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
          Couldn’t load data: {error}.{' '}
          {transactions.length > 0 ? 'Showing the last data received.' : 'Check that the backend is running and VITE_API_URL is correct.'}
        </div>
      )}

      <HealthBanner health={health} />

      {loading ? (
        <p className="py-20 text-center text-slate-500" role="status">Loading dashboard…</p>
      ) : stats ? (
        <>
          <RiskMetricsBar stats={stats} />

          <PredictionForm onSaved={refresh} disabledReason={notReady} />

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2"><AlertsPanel transactions={transactions} /></div>
            <RiskDistribution live={stats.live} />
          </div>

          <section aria-label="Transactions" className="space-y-3">
            <FilterTabs
              view={filters.view}
              counts={counts}
              onViewChange={setView}
              query={filters.query}
              onQueryChange={setQuery}
            />
            <TransactionTable transactions={visible} hasAny={transactions.length > 0} />
          </section>
        </>
      ) : null}
    </div>
  );
}
