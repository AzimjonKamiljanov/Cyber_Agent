"""Policy evaluation engine enforcing 3-tier action permissions and audit logging."""

import logging
from typing import Any

from cyber_agent.audit.logger import get_audit_logger
from cyber_agent.policy.confirmations import ConfirmationStore, get_confirmation_store
from cyber_agent.policy.permissions import PolicyDecision, PolicyTier, PolicyVerdict
from cyber_agent.policy.taint import SessionTaintTracker, get_taint_tracker

logger = logging.getLogger(__name__)

# Explicit static mapping of forbidden tools (must NEVER be allowed)
FORBIDDEN_TOOLS = {
    "delete_file",
    "sudo_command",
    "arbitrary_shell",
    "get_secret",
    "payment",
    "git_force_push",
    "change_policy",
}


class PolicyEngine:
    """Evaluates proposed tool execution against permission tiers, confirmations, and taint."""

    def __init__(
        self,
        confirmation_store: ConfirmationStore | None = None,
        taint_tracker: SessionTaintTracker | None = None,
    ) -> None:
        self.confirmation_store = confirmation_store or get_confirmation_store()
        self.taint_tracker = taint_tracker or get_taint_tracker()
        self.audit_logger = get_audit_logger()
        self._tool_tiers: dict[str, PolicyTier] = {}

    def register_tool_tier(self, tool_name: str, tier: PolicyTier) -> None:
        """Register the permission tier for a given tool name."""
        if tool_name in FORBIDDEN_TOOLS or tier == PolicyTier.RED:
            # Forbidden tools are registered as RED or refused
            self._tool_tiers[tool_name] = PolicyTier.RED
        else:
            self._tool_tiers[tool_name] = tier

    def evaluate(
        self,
        tool_name: str,
        args: dict[str, Any],
        action_id: str | None = None,
        confirmation_token: str | None = None,
    ) -> PolicyDecision:
        """Evaluate a proposed tool execution."""
        is_tainted = self.taint_tracker.is_tainted()

        # 1. Reject forbidden RED tools unconditionally
        if tool_name in FORBIDDEN_TOOLS or self._tool_tiers.get(tool_name) == PolicyTier.RED:
            decision = PolicyDecision(
                verdict=PolicyVerdict.DENY,
                tier=PolicyTier.RED,
                reason=f"Action '{tool_name}' is forbidden by system security policy (RED tier)",
                tainted=is_tainted,
            )
            self._log_decision(tool_name, args, decision)
            return decision

        # 2. Unknown tools are denied
        if tool_name not in self._tool_tiers:
            decision = PolicyDecision(
                verdict=PolicyVerdict.DENY,
                tier=PolicyTier.RED,
                reason=f"Unknown tool '{tool_name}' is not registered in policy registry",
                tainted=is_tainted,
            )
            self._log_decision(tool_name, args, decision)
            return decision

        tier = self._tool_tiers[tool_name]

        # 3. GREEN tier evaluation
        if tier == PolicyTier.GREEN:
            decision = PolicyDecision(
                verdict=PolicyVerdict.ALLOW,
                tier=PolicyTier.GREEN,
                reason=f"Tool '{tool_name}' is authorized under GREEN tier",
                tainted=is_tainted,
            )
            self._log_decision(tool_name, args, decision)
            return decision

        # 4. YELLOW tier evaluation
        if tier == PolicyTier.YELLOW:
            # If token and action_id are provided, validate consumption
            if action_id and confirmation_token:
                valid, msg = self.confirmation_store.validate_and_consume(action_id, confirmation_token, args)
                if valid:
                    decision = PolicyDecision(
                        verdict=PolicyVerdict.ALLOW,
                        tier=PolicyTier.YELLOW,
                        reason=f"Action '{tool_name}' confirmed with valid single-use token",
                        action_id=action_id,
                        tainted=is_tainted,
                    )
                else:
                    decision = PolicyDecision(
                        verdict=PolicyVerdict.DENY,
                        tier=PolicyTier.YELLOW,
                        reason=f"Confirmation failed: {msg}",
                        action_id=action_id,
                        tainted=is_tainted,
                    )
                self._log_decision(tool_name, args, decision)
                return decision

            # Token not provided yet -> Generate pending confirmation
            act_id, raw_token = self.confirmation_store.create_confirmation(tool_name, args)
            reason = f"Action '{tool_name}' requires on-screen confirmation card"
            if is_tainted:
                reason += " [TAINT WARNING: session contains untrusted external content]"

            decision = PolicyDecision(
                verdict=PolicyVerdict.CONFIRM,
                tier=PolicyTier.YELLOW,
                reason=reason,
                action_id=act_id,
                confirmation_token=raw_token,
                tainted=is_tainted,
            )
            self._log_decision(tool_name, args, decision)
            return decision

        # Default fallback: fail-closed to DENY
        decision = PolicyDecision(
            verdict=PolicyVerdict.DENY,
            tier=PolicyTier.RED,
            reason="Unrecognized policy condition",
            tainted=is_tainted,
        )
        self._log_decision(tool_name, args, decision)
        return decision

    def _log_decision(self, tool_name: str, args: dict[str, Any], decision: PolicyDecision) -> None:
        self.audit_logger.log_event(
            "POLICY_EVAL",
            {
                "tool_name": tool_name,
                "args": args,
                "verdict": decision.verdict.value,
                "tier": decision.tier.value,
                "reason": decision.reason,
                "action_id": decision.action_id,
                "tainted": decision.tainted,
            },
        )


_global_policy_engine: PolicyEngine | None = None


def get_policy_engine() -> PolicyEngine:
    global _global_policy_engine
    if _global_policy_engine is None:
        _global_policy_engine = PolicyEngine()
    return _global_policy_engine
