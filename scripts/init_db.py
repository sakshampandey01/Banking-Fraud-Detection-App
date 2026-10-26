#!/usr/bin/env python3
"""
Create (if needed) and initialise the PostgreSQL database from the scripts in sql/.

    python scripts/init_db.py                 # create DB if missing, apply schema + reference data (safe to repeat)
    python scripts/init_db.py --demo          # also add six made-up demo accounts for trying the form
    python scripts/init_db.py --refresh-summary
    python scripts/init_db.py --reset --yes   # DANGER: drop everything first (deletes all stored data)

The connection comes from DATABASE_URL in .env (see .env.example).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SQL_DIR = ROOT / "sql"
CORE_FILES = ["01_schema.sql", "02_seed_reference.sql", "03_routines.sql", "04_views.sql"]


def _say(msg: str) -> None:
    print(msg, flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", action="store_true", help="add demo accounts (sql/05_seed_demo_accounts.sql)")
    ap.add_argument("--reset", action="store_true", help="DROP all project tables first (needs --yes)")
    ap.add_argument("--yes", action="store_true", help="confirm --reset")
    ap.add_argument("--refresh-summary", action="store_true", help="REFRESH MATERIALIZED VIEW mv_fraud_summary")
    ap.add_argument("--database-url", default=None, help="override DATABASE_URL")
    args = ap.parse_args(argv)

    try:
        import psycopg
        from psycopg import sql as pgsql
        from sqlalchemy.engine import make_url
        from app.config import get_settings
    except ModuleNotFoundError as exc:
        print(f"ERROR: missing Python package '{exc.name}'. Activate the virtual environment and run "
              "`pip install -r requirements.txt`.", file=sys.stderr)
        return 2

    if args.reset and not args.yes:
        print("ERROR: --reset deletes ALL data. Add --yes to confirm.", file=sys.stderr)
        return 2

    url = make_url(args.database_url or get_settings().database_url)
    db_name = url.database
    if not db_name:
        print("ERROR: DATABASE_URL has no database name (…/fraud_db).", file=sys.stderr)
        return 2
    target_dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)
    admin_dsn = url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    shown = url.render_as_string(hide_password=True)

    # 1. create the database if it does not exist -------------------------------------------
    try:
        with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin:
            exists = admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,)).fetchone()
            if exists:
                _say(f"Database '{db_name}' already exists.")
            else:
                admin.execute(pgsql.SQL("CREATE DATABASE {}").format(pgsql.Identifier(db_name)))
                _say(f"Created database '{db_name}'.")
    except psycopg.OperationalError as exc:
        print(f"ERROR: cannot connect to PostgreSQL ({shown}).\n  {str(exc).strip()}\n"
              "  Is PostgreSQL running (brew services start postgresql@16) and is DATABASE_URL in .env correct?",
              file=sys.stderr)
        return 2
    except psycopg.Error as exc:
        print(f"ERROR: could not create the database: {exc}", file=sys.stderr)
        return 2

    # 2. apply the scripts -----------------------------------------------------------------
    files = (["00_drop_all.sql"] if args.reset else []) + CORE_FILES + (["05_seed_demo_accounts.sql"] if args.demo else [])
    try:
        with psycopg.connect(target_dsn, autocommit=True, connect_timeout=5) as conn:
            for name in files:
                path = SQL_DIR / name
                if not path.exists():
                    print(f"ERROR: {path} is missing.", file=sys.stderr)
                    return 2
                _say(f"Applying {name} ...")
                conn.execute(path.read_text())
            if args.refresh_summary:
                _say("Refreshing mv_fraud_summary ...")
                conn.execute("REFRESH MATERIALIZED VIEW mv_fraud_summary")

            # 3. verify the encoding against the model's preprocessing configuration ---------------
            from app.ml.features import DEFAULT_TYPE_ENCODING
            db_enc = dict(conn.execute("SELECT type_code, type_enc FROM transaction_types").fetchall())
            if db_enc != DEFAULT_TYPE_ENCODING:
                print(f"ERROR: transaction_types {db_enc} != expected encoding {DEFAULT_TYPE_ENCODING}", file=sys.stderr)
                return 1
            n_acc = conn.execute("SELECT count(*) FROM accounts").fetchone()[0]
    except psycopg.Error as exc:
        print(f"ERROR while applying SQL: {exc}", file=sys.stderr)
        return 1

    _say(f"\nDatabase ready: {shown}\n  transaction types seeded and matching the model encoding {db_enc}\n  accounts in database: {n_acc}")
    if n_acc == 0:
        _say("  Tip: run with --demo to add demo accounts, or create accounts via POST /api/accounts (see /docs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
