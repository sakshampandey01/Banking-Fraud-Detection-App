#!/usr/bin/env bash
# Concurrency test for sp_process_transaction (needs psql and a database with sql/01..04 applied).
#
#   PSQL_URL=postgresql://localhost:5432/fraud_db bash tests/sql/test_concurrency.sh
#   (or set PGHOST/PGDATABASE/... instead of PSQL_URL)
#
# Two sessions try to move 800 out of an account holding 1000 at the same moment, one of them
# deliberately holding its row locks for 2 seconds. The row lock inside the procedure must make
# exactly ONE succeed and the other fail with FD003 (insufficient funds): no overdraft, no deadlock.
# It COMMITS real rows for two throw-away accounts (C79000000x) and deletes them again at the end.
set -u
PSQL=(psql ${PSQL_URL:+"$PSQL_URL"} -X -q -A -t -v ON_ERROR_STOP=0)
SUFFIX=$$
A="C7900${SUFFIX: -5}1"; B="C7900${SUFFIX: -5}2"
cleanup() {
  "${PSQL[@]}" -c "
    DELETE FROM fraud_logs WHERE txn_id IN (SELECT t.txn_id FROM transactions t JOIN accounts a ON a.account_id IN (t.orig_account_id, t.dest_account_id) WHERE a.account_number IN ('$A','$B'));
    DELETE FROM transactions WHERE orig_account_id IN (SELECT account_id FROM accounts WHERE account_number IN ('$A','$B'))
                                OR dest_account_id IN (SELECT account_id FROM accounts WHERE account_number IN ('$A','$B'));
    DELETE FROM account_audit WHERE account_id IN (SELECT account_id FROM accounts WHERE account_number IN ('$A','$B'));
    WITH gone AS (DELETE FROM accounts WHERE account_number IN ('$A','$B') RETURNING user_id) DELETE FROM users WHERE user_id IN (SELECT user_id FROM gone);" >/dev/null 2>&1
}
trap cleanup EXIT

"${PSQL[@]}" -c "SELECT fn_open_account('$A', 1000.00); SELECT fn_open_account('$B', 0.00);" >/dev/null || { echo "FAILED: cannot reach the database / schema missing"; exit 2; }

call="CALL sp_process_transaction('$A','$B','TRANSFER',800.00,5,0.01,'CONCURRENCY-TEST',0.908351,0.5,NULL,NULL,NULL,NULL,NULL);"
out1=$(mktemp); out2=$(mktemp)
( "${PSQL[@]}" -c "BEGIN; $call SELECT pg_sleep(2); COMMIT;" >"$out1" 2>&1 ) &
sleep 0.5      # let session 1 take the locks first
( "${PSQL[@]}" -c "$call" >"$out2" 2>&1 ) &
wait

ok=$(cat "$out1" "$out2" | grep -c -E '^[0-9]+\|COMPLETED\|')
fd=$(cat "$out1" "$out2" | grep -c -E 'Insufficient funds')
bal=$("${PSQL[@]}" -c "SELECT balance FROM accounts WHERE account_number='$A'")
dst=$("${PSQL[@]}" -c "SELECT balance FROM accounts WHERE account_number='$B'")
echo "session results -> succeeded: $ok, rejected for insufficient funds: $fd, origin balance: $bal, destination balance: $dst"
if [ "$ok" = 1 ] && [ "$fd" = 1 ] && [ "$bal" = "200.00" ] && [ "$dst" = "800.00" ]; then
  echo "PASS: concurrent transfers cannot overdraw an account"; exit 0
fi
echo "FAILED: expected exactly one success + one FD003, origin 200.00, destination 800.00"; cat "$out1" "$out2"; exit 1
