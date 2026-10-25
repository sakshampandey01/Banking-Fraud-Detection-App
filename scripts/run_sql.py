"""
Run one or more .sql files against the database (psql replacement for Windows users).

    python -m scripts.run_sql sql/01_schema.sql sql/02_procedures.sql sql/03_triggers.sql
"""
import sys
import psycopg
from app.config import get_settings


def main(paths: list[str]) -> None:
    dsn = get_settings().psycopg_dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        for path in paths:
            with open(path, encoding="utf-8") as f:
                sql = f.read()
            print(f"-> running {path}")
            conn.execute(sql)          # no parameters => multi-statement scripts are fine
    print("done.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
