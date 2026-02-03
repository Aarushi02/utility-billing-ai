import json
import logging
from datetime import datetime, date
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple, Optional, Union

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Safe eval helpers
# ---------------------------------------------------------------------

SAFE_GLOBALS = {
    "__builtins__": None,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
}

def _safe_eval(expr: str, context: Dict[str, Any], *, desc: str = "") -> Any:
    if not expr:
        return None
    try:
        return eval(expr, SAFE_GLOBALS, context)
    except Exception as e:
        logger.warning(f"Eval error in {desc}: {e} (expr={expr!r})")
        return None


# ---------------------------------------------------------------------
# Voltage tier helpers
# ---------------------------------------------------------------------

def _parse_voltage_tier_key(key: str) -> Tuple[float, float]:
    import re

    text = key.replace("kV", "").strip()

    if text.lower().startswith("over"):
        nums = re.findall(r"(\d+(\.\d+)?)", text)
        low = float(nums[0][0]) if nums else 0.0
        return low, float("inf")

    nums = re.findall(r"(\d+(\.\d+)?)", text)
    if len(nums) >= 2:
        return float(nums[0][0]), float(nums[1][0])

    if nums:
        v = float(nums[0][0])
        return v, v

    return 0.0, float("inf")


def _select_rate_by_voltage(value_obj, delivery_voltage, *, step_name: str) -> float:
    if not isinstance(value_obj, dict):
        try:
            return float(value_obj or 0.0)
        except Exception:
            logger.warning(f"Bad rate in {step_name}")
            return 0.0

    if delivery_voltage is None:
        logger.warning(f"No voltage for tiered rate in {step_name}")
        return 0.0

    for key, rate in value_obj.items():
        low, high = _parse_voltage_tier_key(key)
        if low <= delivery_voltage <= high:
            return float(rate or 0.0)

    logger.warning(f"No voltage tier match in {step_name}")
    return 0.0


# ---------------------------------------------------------------------
# Service class helpers
# ---------------------------------------------------------------------

def _normalize_sc_code(sc: Optional[str]) -> str:
    if sc is None:
        return ""
    return str(sc).upper().replace(" ", "").replace("-", "")


def _parse_effective_date(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    try:
        return pd.to_datetime(raw).date()
    except Exception:
        return None


def _extract_effective_date(item: dict) -> Optional[date]:
    eff = item.get("effective_date") or (item.get("metadata") or {}).get("effective_date")
    return _parse_effective_date(eff)


# ---------------------------------------------------------------------
# Audit Engine
# ---------------------------------------------------------------------

class AuditEngine:
    """
    Tariff audit engine with TRA + RDM override support.
    """

    def __init__(self, tariff_definitions_path: str):
        self.tariff_map = self._load_logic(tariff_definitions_path)

    # -----------------------------------------------------------------
    # Load tariff logic
    # -----------------------------------------------------------------

    def _load_logic(self, path: str) -> Dict[str, List[dict]]:
        with open(path, "r") as f:
            data = json.load(f)

        if isinstance(data, dict) and "tariffs" in data:
            data = data["tariffs"]

        mapping: Dict[str, List[dict]] = {}

        for item in data:
            sc = _normalize_sc_code(item["sc_code"])
            item["_effective_date"] = _extract_effective_date(item)
            mapping.setdefault(sc, []).append(item)

        for sc, items in mapping.items():
            items.sort(
                key=lambda x: (
                    x["_effective_date"] is None,
                    x["_effective_date"] or date.min,
                )
            )

        return mapping

    # -----------------------------------------------------------------
    # Pick tariff version
    # -----------------------------------------------------------------

    def _pick_logic_for_bill(self, sc_code: str, bill_dt) -> Optional[dict]:
        versions = self.tariff_map.get(sc_code)
        if not versions:
            return None

        if not bill_dt:
            return versions[-1]

        if isinstance(bill_dt, datetime):
            bill_dt = bill_dt.date()

        candidates = [
            v for v in versions
            if v["_effective_date"] and v["_effective_date"] <= bill_dt
        ]

        return max(candidates, key=lambda v: v["_effective_date"]) if candidates else versions[0]

    # -----------------------------------------------------------------
    # Core calculation
    # -----------------------------------------------------------------

    def calculate_expected_bill(self, row: pd.Series) -> dict:
        sc_code = _normalize_sc_code(row.get("service_class", "SC1"))

        bill_date = row.get("read_date") or row.get("bill_date")
        try:
            bill_date = pd.to_datetime(bill_date)
        except Exception:
            pass

        logic = self._pick_logic_for_bill(sc_code, bill_date)
        if not logic:
            return {
                "status": "SKIPPED",
                "expected_bill": 0.0,
                "variance": 0.0,
                "trace": ["No tariff logic"],
            }

        logic_steps = logic.get("logic_steps", [])

        user = SimpleNamespace(
            billed_kwh=float(row.get("billed_kwh", 0) or 0),
            billed_demand=float(row.get("billed_demand", 0) or 0),
            billed_rkva=float(row.get("billed_rkva", 0) or 0),
            days_used=int(row.get("days_used", 30) or 30),
            bill_date=bill_date,
        )

        delivery_voltage = row.get("delivery_voltage_kv") or row.get("delivery_voltage")
        try:
            delivery_voltage = float(delivery_voltage)
        except Exception:
            delivery_voltage = None

        ctx = {
            "user": user,
            "delivery_voltage": delivery_voltage,
            "pd": pd,
        }

        total_expected = 0.0
        trace: List[str] = []
        min_candidates: List[float] = []

        # -------------------------------------------------------------
        # Tariff steps
        # -------------------------------------------------------------

        for step in logic_steps:
            name = step.get("step_name", "Step")
            ctype = (step.get("charge_type") or "").strip()
            condition = step.get("condition", "Always")

            if condition != "Always":
                if not _safe_eval(condition.replace(" kV", ""), ctx, desc=name):
                    continue

            if ctype in {"minimum_charge", "minimum_bill"}:
                min_candidates.append(float(step.get("value", 0) or 0))
                continue

            cost = 0.0

            if ctype == "fixed_fee":
                cost = _select_rate_by_voltage(step.get("value"), delivery_voltage, step_name=name)

            elif ctype in {"per_kwh", "energy_charge"}:
                rate = _select_rate_by_voltage(step.get("value"), delivery_voltage, step_name=name)
                cost = rate * user.billed_kwh

            elif ctype in {"per_kw", "demand_charge"}:
                rate = _select_rate_by_voltage(step.get("value"), delivery_voltage, step_name=name)
                cost = rate * user.billed_demand

            elif ctype in {"per_rkva", "reactive_demand_fee"}:
                rate = _select_rate_by_voltage(step.get("value"), delivery_voltage, step_name=name)
                cost = rate * user.billed_rkva

            else:
                continue

            total_expected += cost
            trace.append(f"{name}: ${cost:.2f}")

        # -------------------------------------------------------------
        # TRA override
        # -------------------------------------------------------------

        try:
            override_tra = float(row.get("override_tra") or 0.0)
        except Exception:
            override_tra = 0.0

        if override_tra:
            tra_charge = override_tra * user.billed_kwh
            total_expected += tra_charge
            trace.append(
                f"TRA Override: {override_tra:.5f} × {user.billed_kwh:.2f} kWh = ${tra_charge:.2f}"
            )

        # -------------------------------------------------------------
        # RDM override
        # -------------------------------------------------------------

        try:
            override_rdm = float(row.get("override_rdm") or 0.0)
        except Exception:
            override_rdm = 0.0

        ENERGY_RDM_SC = {"SC1", "SC1C", "SC2"}
        DEMAND_RDM_SC = {"SC2D", "SC3", "SC3A"}

        if override_rdm:
            rdm_charge = 0.0

            if sc_code in ENERGY_RDM_SC:
                rdm_charge = override_rdm * user.billed_kwh
                trace.append(
                    f"RDM Override (Energy): {override_rdm:.5f} × {user.billed_kwh:.2f} kWh = ${rdm_charge:.2f}"
                )

            elif sc_code in DEMAND_RDM_SC:
                rdm_charge = override_rdm * user.billed_demand
                trace.append(
                    f"RDM Override (Demand): {override_rdm:.5f} × {user.billed_demand:.2f} kW = ${rdm_charge:.2f}"
                )

            total_expected += rdm_charge

        # -------------------------------------------------------------
        # Minimum bill enforcement
        # -------------------------------------------------------------

        if min_candidates:
            min_required = max(min_candidates)
            if total_expected < min_required:
                total_expected = min_required
                trace.append(f"Minimum bill enforced: ${min_required:.2f}")

        actual = float(row.get("bill_amount", 0) or 0)
        variance = actual - total_expected

        return {
            "status": "SUCCESS",
            "sc_code": sc_code,
            "actual_bill": round(actual, 2),
            "expected_bill": round(total_expected, 2),
            "variance": round(variance, 2),
            "trace": trace,
        }
