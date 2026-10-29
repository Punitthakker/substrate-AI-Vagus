"""Substrate data model: the genome (Person), the base pair (Ledger events), and the wire types."""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from .limbic import Limbic


class State(str, Enum):
    calm = "calm"
    stressed = "stressed"
    euphoric = "euphoric"
    defensive = "defensive"
    decision_ready = "decision-ready"


class Polarity(str, Enum):
    """How hard the truth is. Ordered: proceed < caution < stop."""
    proceed = "proceed"
    caution = "caution"
    stop = "stop"

    @property
    def severity(self) -> int:
        return {"proceed": 0, "caution": 1, "stop": 2}[self.value]


# ---------------------------------------------------------------- genome

class Inheritance(BaseModel):
    heirs: list[str] = Field(default_factory=list)
    scope: Literal["values", "values+ledger", "full"] = "values"
    revocable: Literal[True] = True  # a will you cannot revoke is rejected


class Consent(BaseModel):
    candor_level: int = Field(3, ge=1, le=5, description="1 gentle ... 5 brutal. Set by the human.")
    allow_training: bool = Field(False, description="Opt-in: may this genome's ledger train the Vagus model?")
    inheritance: Inheritance = Field(default_factory=Inheritance)


class Position(BaseModel):
    asset: str
    value: float
    kind: str = "other"


class Bias(BaseModel):
    type: str
    evidence: list[str] = Field(default_factory=list)
    last_seen: Optional[str] = None


class RiskProfile(BaseModel):
    stated: Literal["conservative", "moderate", "aggressive"] = "moderate"
    observed: Optional[Literal["conservative", "moderate", "aggressive"]] = None


class Goal(BaseModel):
    name: str
    priority: int = 1


class Ancestor(BaseModel):
    """What an heir received: the elder's values and the lessons they paid for. Never their money or messages."""
    from_user: str
    name: str                          # first name only
    relation: str = "family"
    vintage: str = ""
    scope: str = "values"
    values: list[str] = Field(default_factory=list)
    lessons: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    checksum: str = ""
    received: str = ""


class Person(BaseModel):
    """The genome: who this human is across months, not messages. User-owned, exportable, deletable."""
    user_id: str = ""
    name: str = "Client"
    domain: Literal["wealth", "venture", "founder", "wellbeing", "markets"] = "wealth"
    vintage: str = ""
    consent: Consent = Field(default_factory=Consent)
    temperament: str = "mentor"
    values: list[str] = Field(default_factory=list)
    risk_profile: RiskProfile = Field(default_factory=RiskProfile)
    liquid_net_worth: Optional[float] = None
    currency: str = "USD"
    positions: list[Position] = Field(default_factory=list)
    biases: list[Bias] = Field(default_factory=list)
    goals: list[Goal] = Field(default_factory=list)
    decision_style: Optional[str] = None
    profile: dict[str, Any] = Field(default_factory=dict, description="Domain-specific facts: fund size, burn, support contacts...")
    # learned by the outcome loop
    adherence: dict[str, dict[str, int]] = Field(default_factory=dict)
    lessons: list[str] = Field(default_factory=list)
    # inherited: genomes passed down, revocable by the elder
    ancestry: list[Ancestor] = Field(default_factory=list)
    # voluntary precommitments ("no bets until 9am"), see substrate/pacts.py
    pacts: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------- engine wire types

class Signals(BaseModel):
    exclamations: int = 0
    caps_ratio: float = 0.0
    euphoric: list[str] = Field(default_factory=list)
    stressed: list[str] = Field(default_factory=list)
    defensive: list[str] = Field(default_factory=list)
    urgency: list[str] = Field(default_factory=list)


class Facts(BaseModel):
    """Hard numbers computed before any model is consulted. The basis of the Honesty Floor."""
    domain: str = "wealth"
    amount: Optional[float] = None
    asset: Optional[str] = None
    existing_exposure: Optional[float] = None
    concentration_pct: Optional[float] = None
    leverage: bool = False
    loss_chasing: bool = False
    fomo: bool = False
    profile_breach: bool = False
    prior_ignored: list[dict] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    safety: bool = False
    floor: Polarity = Polarity.proceed
    flags: list[str] = Field(default_factory=list)


class CouncilVote(BaseModel):
    model: str
    polarity: Optional[Polarity] = None
    ok: bool = True
    error: Optional[str] = None


class Verdict(BaseModel):
    polarity: Polarity
    headline: str
    reasons: list[str] = Field(default_factory=list)
    model: str = "rule-core"
    floor_applied: bool = False
    council: list[CouncilVote] = Field(default_factory=list)


class Forecast(BaseModel):
    label: str
    value: str
    note: str = ""


class Prediction(BaseModel):
    p_follow: float
    drivers: list[str] = Field(default_factory=list)
    forecasts: list[Forecast] = Field(default_factory=list)
    escalate: Optional[str] = None


class Turn(BaseModel):
    role: Literal["user", "substrate"]
    content: str


class AdviseRequest(BaseModel):
    user_id: str
    message: str
    thread: list[Turn] = Field(default_factory=list)
    stakes: Optional[Literal["low", "medium", "high"]] = None
    temperament: Optional[str] = None


class AdviseResponse(BaseModel):
    ledger_id: str
    domain: str
    label: str
    safety: bool = False
    state: State
    signals: Signals
    stakes: Literal["low", "medium", "high"]
    firmness: int
    tone_notes: list[str] = Field(default_factory=list)
    temperament: str
    facts: Facts
    verdict: Verdict
    prediction: Optional[Prediction] = None
    limbic: Optional[Limbic] = None
    ancestry: Optional[str] = None     # the elder's lesson cited, if the heir is repeating their pattern
    pact_offer: Optional[dict] = None  # "hold me to it until 9am", offered on a hard stop
    pact_active: Optional[dict] = None # the human's own promise, in force right now
    message: str
    hash: str
    prev_hash: str


class OutcomeRequest(BaseModel):
    ledger_id: str
    action: Optional[Literal["followed", "ignored", "partial"]] = None
    outcome_type: Optional[Literal["pnl", "avoided-loss", "qualitative"]] = None
    value_delta: Optional[float] = None
    horizon: str = "30d"
    note: Optional[str] = None
