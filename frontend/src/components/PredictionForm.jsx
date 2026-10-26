import { useState } from 'react';
import { createAccount, evaluateTransaction, fetchAccounts, predictTransaction } from '../api/transactionsApi.js';
import { TRANSACTION_TYPES } from '../lib/constants.js';
import { toPayload, validateForm } from '../lib/formValidation.js';
import ResultCard from './ResultCard.jsx';

const EMPTY = {
  type: 'TRANSFER', amount: '', step: '', origAccount: '', destAccount: '',
  oldBalanceOrig: '', newBalanceOrig: '', oldBalanceDest: '', newBalanceDest: '',
};

const input = 'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900';

function Field({ label, error, hint, children }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      {children}
      {hint && !error && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
      {error && <span role="alert" className="mt-1 block text-xs text-red-700">{error}</span>}
    </label>
  );
}

/**
 * mode 'evaluate' -> POST /api/transactions/evaluate (accounts must exist; the transaction is scored AND saved)
 * mode 'check'    -> POST /api/predict               (you type the balances; nothing is saved)
 * `onSaved` lets the dashboard refresh after a transaction was stored.
 */
export default function PredictionForm({ onSaved, disabledReason }) {
  const [mode, setMode] = useState('evaluate');
  const [values, setValues] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [result, setResult] = useState(null);
  const [accounts, setAccounts] = useState(null);

  const set = (key) => (e) => setValues((v) => ({ ...v, [key]: e.target.value }));

  async function loadAccounts() {
    try { setAccounts(await fetchAccounts()); } catch { setAccounts([]); }
  }
  // load the account suggestions the first time the user focuses an account field
  const ensureAccounts = () => { if (accounts === null) loadAccounts(); };

  async function submit(e) {
    e.preventDefault();
    const found = validateForm(values, mode);
    setErrors(found);
    setApiError(null);
    if (Object.keys(found).length) return;
    setSubmitting(true);
    try {
      const payload = toPayload(values, mode);
      const res = mode === 'evaluate' ? await evaluateTransaction(payload) : await predictTransaction(payload);
      setResult(res);
      if (res.stored) onSaved?.();
    } catch (err) {
      setResult(null);
      setApiError(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section aria-label="Check a transaction" className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-slate-900">Check a transaction</h2>
        <div role="tablist" aria-label="Mode" className="inline-flex rounded-lg bg-slate-100 p-1 text-sm">
          {[['evaluate', 'Score & save'], ['check', 'Check only']].map(([m, label]) => (
            <button key={m} type="button" role="tab" aria-selected={mode === m}
              onClick={() => { setMode(m); setErrors({}); setApiError(null); setResult(null); }}
              className={`rounded-md px-3 py-1 font-medium ${mode === m ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>
              {label}
            </button>
          ))}
        </div>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        {mode === 'evaluate'
          ? 'The model scores the transaction using the accounts’ real balances, then it is stored. High-risk transactions are blocked.'
          : 'Type the four balances yourself. The model returns a probability; nothing is stored.'}
      </p>

      {disabledReason && <p role="status" className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-900">{disabledReason}</p>}

      <form onSubmit={submit} noValidate className="mt-4 space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Type" error={errors.type}>
            <select className={input} value={values.type} onChange={set('type')}>
              {TRANSACTION_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
            </select>
          </Field>
          <Field label="Amount" error={errors.amount}>
            <input className={input} inputMode="decimal" placeholder="1500.00" value={values.amount} onChange={set('amount')} />
          </Field>
          <Field label="Step (optional)" error={errors.step} hint="Hour 1–743; blank = now">
            <input className={input} inputMode="numeric" placeholder="e.g. 27" value={values.step} onChange={set('step')} />
          </Field>
        </div>

        {mode === 'evaluate' ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="From account" error={errors.origAccount}>
              <input className={input} list="accounts-list" placeholder="C1305486145" value={values.origAccount}
                onFocus={ensureAccounts} onChange={set('origAccount')} autoComplete="off" />
            </Field>
            <Field label="To account" error={errors.destAccount}>
              <input className={input} list="accounts-list" placeholder="C553264065" value={values.destAccount}
                onFocus={ensureAccounts} onChange={set('destAccount')} autoComplete="off" />
            </Field>
            <datalist id="accounts-list">
              {(accounts ?? []).map((a) => <option key={a.account_number} value={a.account_number}>{a.status === 'BLOCKED' ? 'blocked' : `balance ${a.balance}`}</option>)}
            </datalist>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-4">
            <Field label="Sender balance before" error={errors.oldBalanceOrig}><input className={input} inputMode="decimal" value={values.oldBalanceOrig} onChange={set('oldBalanceOrig')} /></Field>
            <Field label="Sender balance after" error={errors.newBalanceOrig}><input className={input} inputMode="decimal" value={values.newBalanceOrig} onChange={set('newBalanceOrig')} /></Field>
            <Field label="Receiver balance before" error={errors.oldBalanceDest}><input className={input} inputMode="decimal" value={values.oldBalanceDest} onChange={set('oldBalanceDest')} /></Field>
            <Field label="Receiver balance after" error={errors.newBalanceDest}><input className={input} inputMode="decimal" value={values.newBalanceDest} onChange={set('newBalanceDest')} /></Field>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <button type="submit" disabled={submitting}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2">
            {submitting ? 'Scoring…' : mode === 'evaluate' ? 'Score and save' : 'Check'}
          </button>
          <button type="button" onClick={() => { setValues(EMPTY); setErrors({}); setApiError(null); setResult(null); }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">Clear</button>
        </div>
      </form>

      {apiError && (
        <div role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <p><span className="font-semibold">{apiError.code.replace(/_/g, ' ').toLowerCase()}:</span> {apiError.message}</p>
        </div>
      )}
      <div className="mt-4"><ResultCard result={result} /></div>

      {mode === 'evaluate' && <NewAccount onCreated={() => { setAccounts(null); }} />}
    </section>
  );
}

function NewAccount({ onCreated }) {
  const [open, setOpen] = useState(false);
  const [number, setNumber] = useState('');
  const [balance, setBalance] = useState('0');
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  async function create(e) {
    e.preventDefault();
    setMsg(null);
    if (!/^[CM][0-9]{1,18}$/.test(number.trim())) return setMsg({ ok: false, text: 'Use C or M followed by digits, e.g. C900000010.' });
    const amount = Number(balance);
    if (!Number.isFinite(amount) || amount < 0) return setMsg({ ok: false, text: 'Opening balance must be 0 or more.' });
    setBusy(true);
    try {
      await createAccount({ accountNumber: number.trim(), balance: amount });
      setMsg({ ok: true, text: `Account ${number.trim()} opened.` });
      setNumber('');
      onCreated?.();
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <details open={open} onToggle={(e) => setOpen(e.currentTarget.open)} className="mt-4 border-t border-slate-100 pt-3 text-sm">
      <summary className="cursor-pointer font-medium text-slate-700">Need an account? Open one</summary>
      <form onSubmit={create} className="mt-3 flex flex-wrap items-end gap-3">
        <label className="block text-xs text-slate-600">Account number
          <input className={`${input} mt-1`} placeholder="C900000010" value={number} onChange={(e) => setNumber(e.target.value)} />
        </label>
        <label className="block text-xs text-slate-600">Opening balance
          <input className={`${input} mt-1`} inputMode="decimal" value={balance} onChange={(e) => setBalance(e.target.value)} />
        </label>
        <button disabled={busy} className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-60">{busy ? 'Opening…' : 'Open account'}</button>
      </form>
      {msg && <p role="status" className={`mt-2 text-xs ${msg.ok ? 'text-emerald-700' : 'text-red-700'}`}>{msg.text}</p>}
    </details>
  );
}
