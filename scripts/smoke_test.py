"""
End-to-end smoke test of the whole stack (DB procedure + trigger + ML + API).
WARNING: writes to the database (creates transactions, blocks one account). Use a dev DB.

    python -m scripts.smoke_test
"""
import json
import warnings

from fastapi.testclient import TestClient
from sqlalchemy import text

warnings.filterwarnings("ignore")
from app.database import get_engine  # noqa: E402
from app.main import app  # noqa: E402


def pick(conn, where, n=1):
    q = f"""SELECT a.account_number FROM accounts a JOIN users u USING (user_id)
            WHERE a.status='ACTIVE' AND {where} ORDER BY random() LIMIT {n}"""
    return [r[0] for r in conn.execute(text(q))]


def show(label, r):
    print(f"\n### {label}\nHTTP {r.status_code}\n{json.dumps(r.json(), indent=2)[:900]}")


def main():
    with get_engine().connect() as c:
        a, b, c2 = pick(c, "u.user_type='CUSTOMER' AND a.balance > 1000000", 3)
        merchant = pick(c, "u.user_type='MERCHANT'")[0]
        broke = pick(c, "u.user_type='CUSTOMER' AND a.balance BETWEEN 100 AND 1000")[0]

    with TestClient(app) as api:
        before = api.get(f"/api/accounts/{a}").json()["balance"]
        r = api.post("/api/transactions/evaluate",
                     json={"type": "PAYMENT", "amount": 250.50, "orig_account": a, "dest_account": merchant, "step": 14})
        show("1. low-risk PAYMENT -> expect 201, COMPLETED", r)
        print("   balance before/after:", before, "->", api.get(f"/api/accounts/{a}").json()["balance"])

        r = api.post("/api/transactions/evaluate",
                     json={"type": "TRANSFER", "amount": 181, "orig_account": b, "dest_account": c2, "step": 3})
        show("2. suspicious night TRANSFER -> expect HIGH, BLOCKED, account BLOCKED (trigger)", r)

        r = api.post("/api/transactions/evaluate",
                     json={"type": "PAYMENT", "amount": 10, "orig_account": b, "dest_account": merchant})
        show("3. blocked account tries again -> expect 423", r)

        r = api.post("/api/transactions/evaluate",
                     json={"type": "PAYMENT", "amount": 5000, "orig_account": broke, "dest_account": merchant, "step": 14})
        show("4. amount > balance, low risk -> expect 422 INSUFFICIENT_FUNDS (nothing is saved)", r)

        r = api.post("/api/transactions/evaluate",
                     json={"type": "PAYMENT", "amount": 5, "orig_account": "C0000000000", "dest_account": merchant})
        show("5. unknown account -> expect 404", r)

        r = api.post("/api/transactions/evaluate",
                     json={"type": "WIRE", "amount": 5, "orig_account": a, "dest_account": merchant})
        show("6. invalid type -> expect 422 (validation)", r)

        show("7. audit trail written by trigger", api.get(f"/api/accounts/{b}/audit"))
        show("8. analyst unblocks false positive",
             api.patch(f"/api/accounts/{b}/status", json={"status": "ACTIVE", "reason": "verified with customer"}))
        show("9. audit now has 2 rows", api.get(f"/api/accounts/{b}/audit"))
        show("10. latest API transactions", api.get("/api/transactions?source=API&limit=3"))
        show("11. stats", api.get("/api/stats/summary"))

    with get_engine().connect() as c:
        try:
            c.execute(text("UPDATE fraud_logs SET risk_level='LOW'"))
        except Exception as e:  # append-only trigger
            print("\n### 12. UPDATE on fraud_logs rejected by trigger ->", str(e.orig).splitlines()[0])


if __name__ == "__main__":
    main()
