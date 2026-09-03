import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional


# Tokenization
# Use an HMAC secret (not a bare hash) so tokens can't be reversed by brute
# forcing account number formats. Store this in an env var / secrets manager,
# never in source control.
TOKEN_SECRET = os.environ.get("BILL_TOKEN_SECRET", "").encode()

if not TOKEN_SECRET:
    raise RuntimeError(
        "BILL_TOKEN_SECRET is not set. Set it in your environment "
        "(e.g. EC2 instance env, not in code) before running the redactor."
    )


def tokenize(value: str, prefix: str = "TOK") -> str:
    """Deterministically hash an identifier into a stable, non-reversible token."""
    if not value:
        return f"{prefix}_UNKNOWN"
    digest = hmac.new(TOKEN_SECRET, value.strip().encode(), hashlib.sha256).hexdigest()
    return f"{prefix}_{digest[:12]}"


# Schema for a parsed bill 

@dataclass
class ChargeLineItem:
    description: str
    amount: float
    rate_code: Optional[str] = None


@dataclass
class ParsedBill:
    # --- Identifying / PII fields (NEVER forwarded to the LLM as-is) ---
    account_number: str
    customer_name: Optional[str] = None
    service_address: Optional[str] = None
    meter_number: Optional[str] = None

    # --- Non-PII operational fields (safe to forward) ---
    rate_schedule: Optional[str] = None
    billing_period_start: Optional[str] = None
    billing_period_end: Optional[str] = None
    usage_kwh: Optional[float] = None
    demand_kw: Optional[float] = None
    charge_line_items: list[ChargeLineItem] = field(default_factory=list)
    total_due: Optional[float] = None
    zip_code: Optional[str] = None  # optional: coarse location for rate-territory context



# Local (internal-only) token map, never sent externally

def store_token_mapping(token: str, account_number: str, db_write_fn) -> None:
    """
    Persist token -> real account number mapping in your own PostgreSQL DB
    (chatbot_leads-style table, e.g. `bill_account_tokens`), so anomaly
    results can be traced back internally. `db_write_fn` should be your
    existing DB write helper, e.g.:

        def db_write_fn(token, account_number):
            cursor.execute(
                "INSERT INTO bill_account_tokens (token, account_number) "
                "VALUES (%s, %s) ON CONFLICT (token) DO NOTHING",
                (token, account_number),
            )
    """
    db_write_fn(token, account_number)


# Build the LLM-safe payload

def build_llm_payload(bill: ParsedBill, include_zip: bool = True) -> dict:
    """
    Explicitly construct the payload sent to the LLM. Only fields listed here
    can ever reach the model — anything not mapped in is dropped by default,
    which is the safety property regex-redaction doesn't give you.
    """
    payload = {
        "account_token": tokenize(bill.account_number, prefix="ACCT"),
        "rate_schedule": bill.rate_schedule,
        "billing_period": {
            "start": bill.billing_period_start,
            "end": bill.billing_period_end,
        },
        "usage_kwh": bill.usage_kwh,
        "demand_kw": bill.demand_kw,
        "charges": [asdict(item) for item in bill.charge_line_items],
        "total_due": bill.total_due,
    }

    if include_zip and bill.zip_code:
        payload["zip_code"] = bill.zip_code  # coarse-grained, not street-level

    # Optional: tokenize meter number too, only if the anomaly model benefits
    # from tracking a specific meter's drift over time.
    if bill.meter_number:
        payload["meter_token"] = tokenize(bill.meter_number, prefix="METER")

    return payload


def validate_payload_has_no_pii(payload: dict) -> None:
    """
    Defensive check: fail loudly if a raw PII-looking field somehow ends up
    in the payload (e.g. someone edits build_llm_payload carelessly later).
    """
    forbidden_keys = {"customer_name", "service_address", "account_number", "meter_number"}
    found = forbidden_keys.intersection(payload.keys())
    if found:
        raise ValueError(f"PII fields leaked into LLM payload: {found}")


