"""Pydantic models = the JSON contract with the React frontend."""
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

TxnType = Literal["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]
ACCOUNT_PATTERN = r"^[CM][0-9]{1,18}$"          # e.g. C1231006815 / M1979787155


class EvaluateRequest(BaseModel):
    """The frontend sends ONLY who, how much and what kind. Balances are never client input."""
    model_config = ConfigDict(populate_by_name=True)

    type: TxnType
    amount: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    # `source_ref` / `destination_ref` are accepted as aliases of orig_account / dest_account
    orig_account: str = Field(pattern=ACCOUNT_PATTERN, examples=["C1305486145"],
                              validation_alias=AliasChoices("orig_account", "source_ref"))
    dest_account: str = Field(pattern=ACCOUNT_PATTERN, examples=["C553264065"],
                              validation_alias=AliasChoices("dest_account", "destination_ref"))
    # Optional simulated hour (1..743). If omitted the server derives it from the clock.
    step: Optional[int] = Field(default=None, ge=1, le=743)

    @field_validator("type", mode="before")
    @classmethod
    def _upper(cls, v):                       # accept "transfer" as well as "TRANSFER"
        return v.upper() if isinstance(v, str) else v


class EvaluateResponse(BaseModel):
    txn_id: int
    status: Literal["COMPLETED", "BLOCKED"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    action_taken: Literal["APPROVED", "APPROVED_FLAGGED", "BLOCKED"]
    is_fraud: bool                            # True when risk_level == HIGH
    fraud_probability: float
    decision_threshold: float
    model_name: str
    origin_account_status: Literal["ACTIVE", "BLOCKED"]
    message: str


class TransactionOut(BaseModel):
    txn_id: int
    step: int
    type_code: str
    amount: Decimal
    status: str
    source: str
    created_at: datetime
    orig_account: str
    dest_account: str
    orig_account_status: str
    old_balance_orig: Decimal
    new_balance_orig: Decimal
    old_balance_dest: Decimal
    new_balance_dest: Decimal
    is_fraud_label: Optional[bool] = None
    fraud_probability: Optional[float] = None
    risk_level: Optional[str] = None
    action_taken: Optional[str] = None
    model_name: Optional[str] = None


class AccountTransactionOut(TransactionOut):
    """A transaction seen from one account's point of view."""
    direction: Literal["SENT", "RECEIVED"]


class AccountOut(BaseModel):
    account_number: str
    user_type: str
    balance: Decimal
    status: Literal["ACTIVE", "BLOCKED"]
    opened_at: datetime


class AccountStatusUpdate(BaseModel):
    status: Literal["ACTIVE", "BLOCKED"]
    reason: str = Field(min_length=3, max_length=200)


class AuditOut(BaseModel):
    old_status: str
    new_status: str
    reason: str
    changed_by: str
    changed_at: datetime


class LiveStats(BaseModel):
    evaluated: int            # transactions scored by the model through the API
    today: int                # ... of which since midnight (DB time zone)
    high: int
    medium: int
    low: int


class DatasetStats(BaseModel):
    transactions: int         # historical PaySim rows
    fraud: int                # rows labelled fraud in the dataset


class StatsOut(BaseModel):
    total_transactions: int           # dataset + live
    transactions_today: int           # live transactions processed today
    fraud_flagged: int                # live: HIGH-risk (model) decisions
    blocked_accounts: int             # accounts currently BLOCKED
    live: LiveStats
    dataset: DatasetStats
