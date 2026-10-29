"""Tenant policy: how a bank, fund or platform tunes Substrate without touching its law.

Policy can tighten thresholds, restrict temperaments and cap firmness. It cannot switch off the
Honesty Floor or the Safety Protocol.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Policy(BaseModel):
    # wealth
    concentration_stop_pct: float = 25.0
    concentration_caution_pct: float = 10.0
    # venture
    check_stop_pct_of_fund: float = 10.0
    check_caution_pct_of_fund: float = 5.0
    arr_multiple_caution: float = 40.0
    arr_multiple_stop: float = 100.0
    # founder
    runway_stop_months: float = 6.0
    runway_caution_months: float = 12.0
    # delivery
    allowed_temperaments: list[str] = Field(default_factory=lambda: [
        "mentor", "father", "boss", "partner", "comfort", "kid", "surgeon", "grandmother"])
    max_firmness: int = Field(5, ge=1, le=5)
    domains: list[str] = Field(default_factory=lambda: ["wealth", "venture", "founder", "wellbeing"])
    crisis_region: str = "AE"


DEFAULT = Policy()
