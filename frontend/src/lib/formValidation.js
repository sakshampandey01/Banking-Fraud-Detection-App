import { TRANSACTION_TYPES } from './constants.js';

const ACCOUNT = /^[CM][0-9]{1,18}$/;

/** Parse a user-typed money amount. Returns a number or null. Accepts at most 2 decimals. */
export function parseMoney(text) {
  const t = String(text ?? '').trim().replace(/,/g, '');
  if (!/^\d+(\.\d{1,2})?$/.test(t)) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

/** Client-side checks that mirror the backend rules, so mistakes are caught before a request is sent.
 *  The backend remains the authority and re-validates everything. */
export function validateForm(values, mode) {
  const errors = {};
  if (!TRANSACTION_TYPES.includes(values.type)) errors.type = 'Choose a transaction type.';

  const amount = parseMoney(values.amount);
  if (amount === null) errors.amount = 'Enter an amount with at most 2 decimals, e.g. 1500.50.';
  else if (amount <= 0) errors.amount = 'Amount must be greater than zero.';

  if (values.step !== '' && values.step != null) {
    const s = Number(values.step);
    if (!Number.isInteger(s) || s < 1 || s > 743) errors.step = 'Step must be a whole number from 1 to 743.';
  }

  if (mode === 'evaluate') {
    for (const key of ['origAccount', 'destAccount']) {
      if (!ACCOUNT.test(String(values[key] ?? '').trim())) errors[key] = 'Use C or M followed by digits, e.g. C1305486145.';
    }
    if (!errors.origAccount && !errors.destAccount && values.origAccount.trim() === values.destAccount.trim()) {
      errors.destAccount = 'Origin and destination must be different accounts.';
    }
  } else {
    for (const key of ['oldBalanceOrig', 'newBalanceOrig', 'oldBalanceDest', 'newBalanceDest']) {
      const n = parseMoney(values[key]);
      if (n === null) errors[key] = 'Enter a balance (0 or more, at most 2 decimals).';
    }
  }
  return errors;
}

/** Convert validated form strings into the numbers the API client sends. */
export function toPayload(values, mode) {
  const base = { type: values.type, amount: parseMoney(values.amount), step: values.step === '' ? undefined : Number(values.step) };
  if (mode === 'evaluate') {
    return { ...base, origAccount: values.origAccount.trim(), destAccount: values.destAccount.trim() };
  }
  return {
    ...base,
    oldBalanceOrig: parseMoney(values.oldBalanceOrig), newBalanceOrig: parseMoney(values.newBalanceOrig),
    oldBalanceDest: parseMoney(values.oldBalanceDest), newBalanceDest: parseMoney(values.newBalanceDest),
  };
}
