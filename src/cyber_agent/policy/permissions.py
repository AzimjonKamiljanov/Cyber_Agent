"""Permission tiers and policy verdicts for Cyber Agent."""

from dataclasses import dataclass
from enum import StrEnum


class PolicyTier(StrEnum):
    GREEN = "GREEN"    # Audited execution within scope
    YELLOW = "YELLOW"  # On-screen preview card + single-use confirm token
    RED = "RED"        # Forbidden / human-only (never executed)


class PolicyVerdict(StrEnum):
    ALLOW = "ALLOW"
    CONFIRM = "CONFIRM"
    DENY = "DENY"


@dataclass(frozen=True)
class PolicyDecision:
    verdict: PolicyVerdict
    tier: PolicyTier
    reason: str
    action_id: str | None = None
    confirmation_token: str | None = None
    tainted: bool = False
