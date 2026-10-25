from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import Engine, text

from app.dependencies import engine_dep
from app.schemas.transaction import ACCOUNT_PATTERN, AccountOut, AccountStatusUpdate, AuditOut

router = APIRouter(prefix="/accounts", tags=["accounts"])

AccountNumber = Path(pattern=ACCOUNT_PATTERN)

_ACCOUNT_SQL = """SELECT a.account_number, u.user_type, a.balance, a.status, a.opened_at
                    FROM accounts a JOIN users u USING (user_id)
                   WHERE a.account_number = :n"""


@router.get("/{account_number}", response_model=AccountOut)
def get_account(account_number: str = AccountNumber, engine: Engine = Depends(engine_dep)):
    with engine.connect() as conn:
        row = conn.execute(text(_ACCOUNT_SQL), {"n": account_number}).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "Account not found")
    return row


@router.patch("/{account_number}/status", response_model=AccountOut)
def set_account_status(body: AccountStatusUpdate, account_number: str = AccountNumber,
                       engine: Engine = Depends(engine_dep)):
    """Analyst review: unblock a false positive (or block manually). The audit trigger records it."""
    with engine.begin() as conn:
        # the audit trigger reads this transaction-local setting as the 'reason'
        conn.execute(text("SELECT set_config('app.change_reason', :r, true)"),
                     {"r": f"MANUAL: {body.reason}"})
        updated = conn.execute(text("UPDATE accounts SET status = :s WHERE account_number = :n"),
                               {"s": body.status, "n": account_number}).rowcount
        if updated == 0:
            raise HTTPException(404, "Account not found")
        row = conn.execute(text(_ACCOUNT_SQL), {"n": account_number}).mappings().one()
    return row


@router.get("/{account_number}/audit", response_model=list[AuditOut])
def account_audit(account_number: str = AccountNumber, engine: Engine = Depends(engine_dep)):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""SELECT au.old_status, au.new_status, au.reason, au.changed_by, au.changed_at
                      FROM account_audit au JOIN accounts a USING (account_id)
                     WHERE a.account_number = :n ORDER BY au.changed_at DESC"""),
            {"n": account_number},
        ).mappings().all()
    return rows
