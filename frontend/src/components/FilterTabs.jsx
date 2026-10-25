import { VIEWS } from '../lib/constants.js';

const TABS = [
  { view: VIEWS.ALL,       label: 'All' },
  { view: VIEWS.FLAGGED,   label: 'Flagged' },
  { view: VIEWS.HIGH_RISK, label: 'High Risk' },
];

export default function FilterTabs({ view, counts, onViewChange, query, onQueryChange }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div role="tablist" aria-label="Transaction filter" className="inline-flex rounded-lg bg-slate-100 p-1">
        {TABS.map(({ view: v, label }) => {
          const active = v === view;
          return (
            <button
              key={v}
              role="tab"
              aria-selected={active}
              onClick={() => onViewChange(v)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 ${
                active ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {label} <span className="tabular-nums text-slate-500">({counts[v]})</span>
            </button>
          );
        })}
      </div>

      <label className="relative block sm:w-64">
        <span className="sr-only">Search transactions</span>
        <input
          type="search"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Search ID, account, type…"
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
        />
      </label>
    </div>
  );
}
