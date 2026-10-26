"""Runs the SQL behaviour tests (tests/sql/test_database.sql) through the `psql` command-line client.

Needs `psql` on PATH and TEST_DATABASE_URL pointing at an EMPTY throw-away database, e.g.
    createdb fraud_test
    TEST_DATABASE_URL=postgresql://localhost:5432/fraud_test python -m pytest tests/test_sql.py -v
(a plain postgresql:// URL, or postgresql+psycopg://, both work).
The SQL test itself runs inside a transaction that is rolled back.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
URL = (os.environ.get("TEST_DATABASE_URL") or "").replace("postgresql+psycopg://", "postgresql://")
pytestmark = [
    pytest.mark.skipif(not shutil.which("psql"), reason="psql not found on PATH"),
    pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set"),
]


def psql(*args):
    return subprocess.run(["psql", URL, "-X", "-v", "ON_ERROR_STOP=1", *args], capture_output=True, text=True, timeout=120)


@pytest.fixture(scope="module", autouse=True)
def schema():
    for f in ("00_drop_all.sql", "01_schema.sql", "02_seed_reference.sql", "03_routines.sql", "04_views.sql"):
        r = psql("-q", "-f", str(ROOT / "sql" / f))
        assert r.returncode == 0, f"{f}: {r.stderr}"


def test_schema_scripts_are_idempotent():
    for f in ("01_schema.sql", "02_seed_reference.sql", "03_routines.sql", "04_views.sql", "05_seed_demo_accounts.sql"):
        r = psql("-q", "-f", str(ROOT / "sql" / f))
        assert r.returncode == 0, f"{f} failed on re-run: {r.stderr}"


def test_database_behaviour():
    r = psql("-q", "-f", str(ROOT / "tests" / "sql" / "test_database.sql"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ALL DATABASE TESTS PASSED" in r.stdout
    assert "FAILED" not in r.stdout


def test_concurrent_transfers_cannot_overdraw():
    r = subprocess.run(["bash", str(ROOT / "tests" / "sql" / "test_concurrency.sh")], capture_output=True, text=True,
                       timeout=120, env={**os.environ, "PSQL_URL": URL})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS: concurrent transfers cannot overdraw an account" in r.stdout
