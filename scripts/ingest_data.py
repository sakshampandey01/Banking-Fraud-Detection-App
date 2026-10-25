"""
Bulk-load Fraud.csv (PaySim, 6.36M rows) into the normalized schema.

Strategy (fast, set-based, constant memory):
  1. COPY the CSV, streamed, into an UNLOGGED staging table   (no per-row INSERTs)
  2. INSERT ... SELECT DISTINCT   -> users, accounts          (set-based SQL)
  3. INSERT ... SELECT + JOINs    -> transactions
  4. ANALYZE, drop staging, print a summary

Usage (run 01_schema.sql, 02_procedures.sql, 03_triggers.sql first):
    python -m scripts.ingest_data --csv data/Fraud.csv --max-rows 1000000   # dev sample
    python -m scripts.ingest_data --csv data/Fraud.csv                      # everything
    python -m scripts.ingest_data --csv data/Fraud.csv --truncate           # reload from scratch
Afterwards run sql/04_indexes_views.sql.
"""
import argparse
import itertools
import time

import psycopg

from app.config import get_settings

STAGING_DDL = """
DROP TABLE IF EXISTS stg_fraud_raw;
CREATE UNLOGGED TABLE stg_fraud_raw (
    row_id            BIGSERIAL,            -- keeps CSV order
    step              INTEGER,
    type              VARCHAR(10),
    amount            NUMERIC(18,2),
    name_orig         VARCHAR(20),
    old_balance_orig  NUMERIC(18,2),
    new_balance_orig  NUMERIC(18,2),
    name_dest         VARCHAR(20),
    old_balance_dest  NUMERIC(18,2),
    new_balance_dest  NUMERIC(18,2),
    is_fraud          SMALLINT,
    is_flagged_fraud  SMALLINT
);
"""

COPY_SQL = """
COPY stg_fraud_raw (step, type, amount, name_orig, old_balance_orig, new_balance_orig,
                    name_dest, old_balance_dest, new_balance_dest, is_fraud, is_flagged_fraud)
FROM STDIN WITH (FORMAT csv, HEADER true)
"""

INSERT_USERS = """
INSERT INTO users (external_ref, user_type)
SELECT n, CASE WHEN left(n, 1) = 'M' THEN 'MERCHANT' ELSE 'CUSTOMER' END
FROM (SELECT name_orig AS n FROM stg_fraud_raw
      UNION
      SELECT name_dest FROM stg_fraud_raw) names
ORDER BY n
"""

# Account balance = the latest balance we ever saw for that account in the CSV.
INSERT_ACCOUNTS = """
INSERT INTO accounts (user_id, account_number, balance, status)
SELECT u.user_id, u.external_ref, GREATEST(b.bal, 0), 'ACTIVE'
FROM users u
JOIN (
    SELECT DISTINCT ON (nm) nm, bal
    FROM (SELECT name_orig AS nm, step, row_id, new_balance_orig AS bal FROM stg_fraud_raw
          UNION ALL
          SELECT name_dest,       step, row_id, new_balance_dest        FROM stg_fraud_raw) x
    ORDER BY nm, step DESC, row_id DESC
) b ON b.nm = u.external_ref
"""

INSERT_TXNS = """
INSERT INTO transactions (step, type_code, amount, orig_account_id, dest_account_id,
                          old_balance_orig, new_balance_orig, old_balance_dest, new_balance_dest,
                          status, source, is_fraud_label, is_flagged_fraud_rule)
SELECT s.step, s.type, s.amount, ao.account_id, ad.account_id,
       s.old_balance_orig, s.new_balance_orig, s.old_balance_dest, s.new_balance_dest,
       'COMPLETED', 'DATASET', s.is_fraud = 1, s.is_flagged_fraud = 1
FROM stg_fraud_raw s
JOIN accounts ao ON ao.account_number = s.name_orig
JOIN accounts ad ON ad.account_number = s.name_dest
ORDER BY s.row_id
"""


def csv_chunks(path: str, max_rows: int, chunk_lines: int = 200_000):
    """Yield the CSV (header + at most max_rows data rows) as byte chunks."""
    with open(path, "rb") as f:
        lines = itertools.islice(f, max_rows + 1) if max_rows else f
        while True:
            block = list(itertools.islice(lines, chunk_lines))
            if not block:
                return
            yield b"".join(block)


def step(msg: str, t0: float) -> float:
    now = time.time()
    print(f"   {msg}  ({now - t0:,.1f}s)")
    return now


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, help="path to Fraud.csv")
    ap.add_argument("--max-rows", type=int, default=0, help="load only the first N rows (0 = all)")
    ap.add_argument("--truncate", action="store_true", help="empty the tables first")
    args = ap.parse_args()

    with psycopg.connect(get_settings().psycopg_dsn) as conn:
        cur = conn.cursor()
        cur.execute("SET work_mem = '256MB'")

        if args.truncate:
            print("[0/5] truncating tables")
            cur.execute("TRUNCATE account_audit, fraud_logs, transactions, accounts, users RESTART IDENTITY CASCADE")
        else:
            cur.execute("SELECT (SELECT count(*) FROM users)")
            if cur.fetchone()[0] > 0:
                raise SystemExit("Tables are not empty. Re-run with --truncate to reload.")

        t = time.time()
        print("[1/5] COPY csv -> staging")
        cur.execute(STAGING_DDL)
        with cur.copy(COPY_SQL) as copy:
            for chunk in csv_chunks(args.csv, args.max_rows):
                copy.write(chunk)
        t = step("staging loaded", t)

        print("[2/5] users");        cur.execute(INSERT_USERS);    t = step(f"{cur.rowcount:,} users", t)
        print("[3/5] accounts");     cur.execute(INSERT_ACCOUNTS); t = step(f"{cur.rowcount:,} accounts", t)
        print("[4/5] transactions"); cur.execute(INSERT_TXNS);     t = step(f"{cur.rowcount:,} transactions", t)

        print("[5/5] cleanup + ANALYZE")
        cur.execute("DROP TABLE stg_fraud_raw")
        conn.commit()

    # ANALYZE must run outside the failed/open transaction -> own autocommit connection
    with psycopg.connect(get_settings().psycopg_dsn, autocommit=True) as conn:
        for tbl in ("users", "accounts", "transactions"):
            conn.execute(f"ANALYZE {tbl}")
        row = conn.execute(
            "SELECT count(*), count(*) FILTER (WHERE is_fraud_label) FROM transactions"
        ).fetchone()
    print(f"\nDone: {row[0]:,} transactions loaded, {row[1]:,} labelled fraud.")
    print("Next: python -m scripts.run_sql sql/04_indexes_views.sql")


if __name__ == "__main__":
    main()
