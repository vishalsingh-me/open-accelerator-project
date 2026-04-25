"""Policy loading and evaluation logic for NemoClaw."""

import os
from typing import Any

import yaml


def policy_path() -> str:
    """Return policy file path from environment."""
    return os.getenv("NEMOCLAW_POLICY_PATH", "./nemoclaw/policies.yaml")


class PolicyEngine:
    """Evaluates actions against configured policy rules."""

    def __init__(self):
        self._policy_path = policy_path()
        self._policies = self._load_policies()

        self._tier1_actions = set(self._policies.get("tier1_actions", []))
        self._tier2_actions = set(self._policies.get("tier2_actions", []))
        self._blocked_actions = set(self._policies.get("blocked_actions", []))
        self._auto_approve_severity = set(
            self._policies.get("auto_approve_severity", [])
        )
        self._require_human_severity = set(
            self._policies.get("require_human_severity", [])
        )

    def _load_policies(self) -> dict[str, Any]:
        with open(self._policy_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            raise ValueError("Policy file must contain a YAML mapping/object.")
        return data

    def classify_action(self, action: str) -> str:
        """Return action tier: tier1, tier2, or blocked."""
        if action in self._blocked_actions:
            return "blocked"
        if action in self._tier1_actions:
            return "tier1"
        if action in self._tier2_actions:
            return "tier2"
        # Unknown actions are treated as blocked by default.
        return "blocked"

    def get_risk_threshold(self, tier: str) -> float:
        """Return max allowed risk score for the given tier."""
        thresholds = {
            "tier1": 0.4,
            "tier2": 0.75,
            "blocked": 0.0,
        }
        return thresholds.get(tier, 0.0)

    def check_policy(self, action: str, severity: str, risk_score: float) -> dict:
        """Evaluate if an action is allowed and whether human approval is required."""
        tier = self.classify_action(action)
        threshold = self.get_risk_threshold(tier)
        severity_normalized = severity.lower()

        if tier == "blocked":
            return {
                "allowed": False,
                "tier": tier,
                "requires_human": True,
                "reason": "Action is blocked by policy.",
            }

        if risk_score > threshold:
            return {
                "allowed": False,
                "tier": tier,
                "requires_human": True,
                "reason": (
                    f"Risk score {risk_score:.2f} exceeds {tier} threshold "
                    f"{threshold:.2f}."
                ),
            }

        requires_human = severity_normalized in self._require_human_severity
        if severity_normalized not in self._auto_approve_severity and not requires_human:
            requires_human = True

        if requires_human:
            reason = f"Severity '{severity}' requires human approval."
        else:
            reason = f"Action allowed under {tier} policy."

        return {
            "allowed": True,
            "tier": tier,
            "requires_human": requires_human,
            "reason": reason,
        }
