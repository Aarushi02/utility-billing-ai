import json
import logging
from datetime import datetime, date
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple, Optional, Union

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---- helpers for safe eval -------------------------------------------------

SAFE_GLOBALS = {
    "__builtins__": None,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
}


def _safe_eval(expr: str, context: Dict[str, Any], *, desc: str = "") -> Any:
    """
    Evaluate a small arithmetic expression safely with a limited global namespace.
    """
    if not expr:
        return None
    try:
        return eval(expr, SAFE_GLOBALS, context)
    except Exception as e:
        logger.warning(f"Eval error in {desc or 'expression'}: {e} (expr={expr!r})")
        return None


def _parse_voltage_tier_key(key: str) -> Tuple[float, float]:
    """
    Parse keys like:
        '0-2.2 kV', '2.2-15 kV', '22-50 kV', 'Over 60 kV'
    into (low_kv, high_kv) ranges. high_kv may be float('inf').
    """
    import re

    text = key.replace("kV", "").strip()
    # Over 60 kV
    if text.lower().startswith("over"):
        nums = re.findall(r"(\d+(\.\d+)?)", text)
        if nums:
            low = float(nums[0][0])
        else:
            low = 0.0
        return low, float("inf")

    # 0-2.2, 2.2-15, 22-50
    nums = re.findall(r"(\d+(\.\d+)?)", text)
    if len(nums) >= 2:
        low = float(nums[0][0])
        high = float(nums[1][0])
        return low, high

    # Fallback: treat as a single point
    if nums:
        val = float(nums[0][0])
        return val, val

    # Last resort
    return 0.0, float("inf")


def _select_rate_by_voltage(
    value_obj: Any,
    delivery_voltage: Optional[float],
    *,
    step_name: str,
) -> float:
    """
    For SC3 / SC3A style structures where 'value' is a dict keyed by voltage band,
    pick the appropriate rate based on delivery_voltage (in kV).

    If delivery_voltage is None or no band matches, return 0 and log a warning.
    """
    if not isinstance(value_obj, dict):
        # Already a scalar
        try:
            return float(value_obj or 0.0)
        except Exception:
            logger.warning(f"Could not parse numeric rate in {step_name}: {value_obj!r}")
            return 0.0

    if delivery_voltage is None:
        logger.warning(
            f"delivery_voltage not provided but value is tiered in {step_name}. Returning 0."
        )
        return 0.0

    for key, rate in value_obj.items():
        low, high = _parse_voltage_tier_key(key)
        if low <= delivery_voltage <= high:
            try:
                return float(rate or 0.0)
            except Exception:
                logger.warning(f"Could not parse tiered rate {rate!r} in {step_name}.")
                return 0.0

    logger.warning(
        f"No voltage tier match for delivery_voltage={delivery_voltage} kV in {step_name}. Returning 0."
    )
    return 0.0


# ---- service-class normalization ------------------------------------------


def _normalize_sc_code(sc: Optional[str]) -> str:
    """
    Normalize service class codes so DB values and JSON sc_code align.

    Examples:
      'SC-1'   -> 'SC1'
      'sc1 '   -> 'SC1'
      'SC 2ND' -> 'SC2ND'
      'SC2-ND' -> 'SC2ND'
    """
    if sc is None:
        return ""
    return str(sc).upper().replace(" ", "").replace("-", "")


def _parse_effective_date(raw: Optional[str]) -> Optional[date]:
    """
    Parse an effective_date string from JSON into a date object.
    Accepts formats like '2009-04-27' or '2009-04-27T00:00:00'.
    """
    if not raw:
        return None
    try:
        # pandas is tolerant of many ISO-ish formats
        return pd.to_datetime(raw).date()
    except Exception:
        logger.warning(f"Could not parse effective_date: {raw!r}")
        return None

def _extract_effective_date(item: dict) -> Optional[date]:
        eff_raw = item.get("effective_date") or item.get("effective_from")
        if not eff_raw:
            md = item.get("metadata") or {}
            eff_raw = md.get("effective_date") or md.get("effective_from")
        return _parse_effective_date(eff_raw)


class AuditEngine:
    """
    Tariff calculation / audit engine.

    Now supports multiple versions per sc_code with different effective_date.
    For a given bill, we pick the tariff where:

        effective_date <= read_date (or bill_date)
        and effective_date is the closest one before that date.
    """

    def __init__(self, tariff_definitions_path: str):
        # tariff_map: sc_code -> List[dict] (each dict is a tariff version)
        self.tariff_map: Dict[str, List[dict]] = self._load_logic(tariff_definitions_path)

    # --------------------------------------------------------------------- #
    # Loading / mapping tariff JSON
    # --------------------------------------------------------------------- #
    
    def _load_logic(self, path: str) -> Dict[str, List[dict]]:
        """
        Load tariff JSON. Supports:

        - Old style: one entry per sc_code (no effective_date)
        - New style: multiple entries per sc_code, each with an 'effective_date'

        Stored as: { 'SC1': [item_v1, item_v2, ...], ... }
        where each item has an extra field '_effective_date' (date or None).
        """
        try:
            with open(path, "r") as f:
                data = json.load(f)

            # Support both list format and {"tariffs": [...]} format
            if isinstance(data, dict) and "tariffs" in data:
                data = data["tariffs"]

            mapping: Dict[str, List[dict]] = {}

            for item in data:
                raw_sc = item["sc_code"]
                key = _normalize_sc_code(raw_sc)
                
                # NEW: also look inside metadata for effective_date
                eff_date = _extract_effective_date(item)
                item["_effective_date"] = eff_date

                mapping.setdefault(key, []).append(item)


            # Sort each list by effective_date ascending (None last)
            for key, items in mapping.items():
                items.sort(
                    key=lambda it: (
                        it["_effective_date"] is None,  # items with date first
                        it["_effective_date"] or date.min,
                    )
                )

            logger.info(
                "Engine loaded logic for SCs: %s",
                list(mapping.keys()),
            )
            return mapping

        except FileNotFoundError:
            logger.error(f"Logic file {path} not found.")
            return {}
        except Exception as e:
            logger.error(f"Failed to load logic file {path}: {e}")
            return {}
        

    # --------------------------------------------------------------------- #
    # Tariff selection per bill
    # --------------------------------------------------------------------- #

    def _pick_logic_for_bill(
        self,
        sc_code: str,
        bill_dt: Optional[Union[datetime, date]],
    ) -> Optional[dict]:
        """
        For a given SC and bill/read date, choose the correct tariff version.

        Rule:
          - consider all versions for this sc_code
          - among those with effective_date <= bill_dt, pick the one
            with the MAX effective_date (closest before the bill)
          - if none match, fall back to the latest available version
        """
        versions = self.tariff_map.get(sc_code)
        if not versions:
            return None

        if bill_dt is None or pd.isna(bill_dt):
            # No date -> use latest version
            return versions[-1]

        if isinstance(bill_dt, datetime):
            bill_d = bill_dt.date()
        else:
            bill_d = bill_dt

        # Filter by effective_date <= bill_d
        candidates = [
            v for v in versions
            if v["_effective_date"] is not None and v["_effective_date"] <= bill_d
        ]

        if candidates:
            # Choose the one with the largest effective_date
            selected = max(candidates, key=lambda v: v["_effective_date"])
            return selected

        # If no effective_date <= bill date, fall back to the earliest defined
        return versions[0]

    # --------------------------------------------------------------------- #
    # Core billing logic
    # --------------------------------------------------------------------- #

    def calculate_expected_bill(self, row: pd.Series) -> dict:
        """
        Given a user_bills row, compute expected bill based on tariff logic.
        Tariff version is chosen by SC + read_date/bill_date.
        """
        raw_sc = row.get("service_class", "SC1")
        sc_code = _normalize_sc_code(raw_sc)

        # Prefer read_date, then bill_date
        bill_date = row.get("read_date") or row.get("bill_date")
        if isinstance(bill_date, str):
            try:
                bill_date = pd.to_datetime(bill_date)
            except Exception:
                pass

        logic = self._pick_logic_for_bill(sc_code, bill_date)
        if not logic:
            reason = f"No logic for {raw_sc} (normalized={sc_code})"
            return {
                "status": "SKIPPED",
                "reason": reason,
                "sc_code": sc_code,
                "expected_amount": 0.0,
                "expected_bill": 0.0,
                "variance": 0.0,
                "trace": [reason],
            }

        logic_steps: List[dict] = logic.get("logic_steps") or []

        # Some SCs are effectively reference-only / canceled and have no rate logic
        if not logic_steps:
            note = logic.get("note") or logic.get("notes") or "No active rate logic."
            reason = f"{raw_sc}: {note}"
            return {
                "status": "SKIPPED",
                "reason": reason,
                "sc_code": sc_code,
                "expected_amount": 0.0,
                "expected_bill": 0.0,
                "variance": 0.0,
                "trace": [reason],
            }

        # Additional fields used in some tariffs (SC1-TOU, SC3A, etc.)
        time_of_use = row.get("time_of_use")  # e.g. 'On Peak', 'Off Peak'
        delivery_voltage = row.get("delivery_voltage_kv") or row.get("delivery_voltage")
        try:
            delivery_voltage = float(delivery_voltage) if delivery_voltage is not None else None
        except Exception:
            delivery_voltage = None

        # Use SimpleNamespace so formulas can do user.billed_kwh, user.billed_demand, etc.
        user_context = SimpleNamespace(
            billed_kwh=float(row.get("billed_kwh", 0) or 0),
            billed_demand=float(row.get("billed_demand", 0) or 0),
            billed_rkva=float(row.get("billed_rkva", 0) or 0),
            days_used=int(row.get("days_used", 30) or 30),
            bill_date=bill_date,
        )

        eval_context: Dict[str, Any] = {
            "user": user_context,
            "pd": pd,
            "time_of_use": time_of_use,
            "delivery_voltage": delivery_voltage,
        }

        total_expected = 0.0
        trace_log: List[str] = []
        min_candidates: List[float] = []  # store minimum_charge / minimum_bill values

        # Normalize conditions like "delivery_voltage <= 15 kV" -> "delivery_voltage <= 15"
        def _normalize_condition(cond: str) -> str:
            if not isinstance(cond, str):
                return "Always"
            return cond.replace(" kV", "")

        # ---- iterate tariff steps ---------------------------------------

        for step in logic_steps:
            step_name = step.get("step_name", "Unknown")
            charge_type = (step.get("charge_type") or "").strip()
            condition = _normalize_condition(step.get("condition", "Always"))

            # Skip purely descriptive/note steps
            if not charge_type and "note" in step:
                trace_log.append(f"{step_name}: informational only, no charge applied.")
                continue

            # Handle reference-only classifications (SC4, SC6, SC12, etc.)
            if charge_type in {
                "reference",
                "energy_rate",
                "demand_rate",
                "energy_rate_minimum",
                "demand_determination",
            }:
                ref_note = step.get("reference") or step.get("note") or "Reference-only step."
                trace_log.append(f"{step_name}: {ref_note} (no direct charge computed).")
                continue

            # Evaluate condition (if not "Always")
            if condition != "Always":
                cond_result = _safe_eval(condition, eval_context, desc=f"condition in {step_name}")
                if not cond_result:
                    trace_log.append(f"{step_name}: condition '{condition}' false; skipped.")
                    continue

            # Minimum charge / minimum bill are processed AFTER main charges
            if charge_type in {"minimum_charge", "minimum_bill"}:
                try:
                    min_val = float(step.get("value", 0) or 0.0)
                    min_candidates.append(min_val)
                    trace_log.append(f"{step_name}: minimum candidate recorded (${min_val:.2f}).")
                except Exception:
                    logger.warning(f"Could not parse minimum value in {step_name}.")
                continue

            # Now calculate actual monetary cost for normal charge types
            cost = 0.0

            try:
                # 1) Fixed monthly fees (may or may not be tiered by voltage)
                if charge_type == "fixed_fee":
                    rate = _select_rate_by_voltage(
                        step.get("value", 0.0),
                        delivery_voltage,
                        step_name=step_name,
                    )
                    cost = float(rate)

                # 2) kWh-based charges
                elif charge_type in {"per_kwh", "energy_charge"}:
                    rate = _select_rate_by_voltage(
                        step.get("value", 0.0),
                        delivery_voltage,
                        step_name=step_name,
                    )
                    quantity_expr = (
                        step.get("unit") or step.get("applies_to") or "user.billed_kwh"
                    )
                    # Avoid nonsense like "per kWh" as an expression
                    if "user." not in str(quantity_expr):
                        quantity_expr = "user.billed_kwh"
                    quantity = _safe_eval(
                        str(quantity_expr),
                        eval_context,
                        desc=f"kWh quantity in {step_name}",
                    )
                    quantity = float(quantity or 0.0)
                    cost = rate * quantity

                # 3) kW demand-based charges
                elif charge_type in {"per_kw", "demand_charge", "demand_fee"}:
                    rate = _select_rate_by_voltage(
                        step.get("value", 0.0),
                        delivery_voltage,
                        step_name=step_name,
                    )

                    # SC3 style: 'demand_kw': "min(40, user.billed_demand)" etc.
                    if "demand_kw" in step:
                        demand_expr = step["demand_kw"]
                    else:
                        # SC2-D / SC3A style: unit or formula
                        demand_expr = (
                            step.get("formula") or step.get("unit") or "user.billed_demand"
                        )

                    if "user." not in str(demand_expr):
                        demand_expr = "user.billed_demand"

                    demand_kw = _safe_eval(
                        str(demand_expr),
                        eval_context,
                        desc=f"demand_kW in {step_name}",
                    )
                    demand_kw = float(demand_kw or 0.0)
                    cost = rate * demand_kw

                # 4) reactive demand-based charges
                elif charge_type in {"per_rkva", "reactive_demand_fee"}:
                    rate = _select_rate_by_voltage(
                        step.get("value", 0.0),
                        delivery_voltage,
                        step_name=step_name,
                    )

                    rkva_expr = (
                        step.get("demand_rkva")
                        or step.get("formula")
                        or step.get("unit")
                        or "user.billed_rkva"
                    )
                    if "user." not in str(rkva_expr):
                        rkva_expr = "user.billed_rkva"

                    rkva = _safe_eval(
                        str(rkva_expr),
                        eval_context,
                        desc=f"demand_rkva in {step_name}",
                    )
                    rkva = float(rkva or 0.0)
                    cost = rate * rkva

                else:
                    # Unknown / unsupported charge type
                    trace_log.append(
                        f"{step_name}: charge_type '{charge_type}' unsupported; skipped."
                    )
                    continue

                total_expected += cost
                trace_log.append(f"{step_name}: ${cost:.2f}")

            except Exception as e:
                logger.error(f" Math Error in {step_name}: {e}")

        # ---- apply minimum charge logic (if any) -------------------------

        if min_candidates:
            # Use the strictest (highest) minimum as a first-pass approximation.
            min_required = max(min_candidates)
            if total_expected < min_required:
                adjustment = min_required - total_expected
                total_expected = min_required
                trace_log.append(
                    f"Minimum Charge Adjustment: Increased bill to minimum ${min_required:.2f} "
                    f"(+${adjustment:.2f})."
                )

        # ---- final variance ----------------------------------------------

        actual_bill = float(row.get("bill_amount", 0.0) or 0.0)
        variance = actual_bill - total_expected

        return {
            "status": "SUCCESS",
            "sc_code": sc_code,
            "actual_bill": round(actual_bill, 2),
            "expected_bill": round(total_expected, 2),
            "variance": round(variance, 2),
            "trace": trace_log,
        }
