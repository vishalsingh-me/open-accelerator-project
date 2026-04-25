from __future__ import annotations

from importlib.util import find_spec
from typing import Literal

from pydantic import BaseModel, Field

Tier = Literal["Tier 1", "Tier 2"]


class PolicyDecision(BaseModel):
    service: str
    action: str
    mode: str
    tier: Tier
    allowed: bool
    blocked: bool
    approval_required: bool
    policy_reason: str
    risk_score: int = Field(ge=0, le=100)


def detect_nemoclaw_runtime() -> bool:
    return find_spec("nemoclaw") is not None or find_spec("nemoguardrails") is not None


def classify_action_tier(action: str) -> Tier:
    value = action.lower()
    tier2 = [
        "scale production cluster",
        "change cpu",
        "change memory",
        "set resources",
        "modify deployment yaml",
        "kubectl apply",
        "restart database",
        "security",
        "network",
    ]
    if any(token in value for token in tier2):
        return "Tier 2"
    return "Tier 1"


def risk_score(action: str, root_cause: str) -> int:
    score = 25
    value = action.lower()

    if "restart" in value:
        score += 15
    if "inspect" in value or "logs" in value or "describe" in value:
        score += 5
    if "retry" in value:
        score += 10

    if "scale" in value:
        score += 45
    if "set resources" in value or "change memory" in value or "change cpu" in value:
        score += 50
    if "restart database" in value:
        score += 55
    if "deployment yaml" in value or "kubectl apply" in value:
        score += 45
    if "network" in value or "security" in value:
        score += 55

    if root_cause in {"database connection timeout", "CrashLoopBackOff"}:
        score += 5

    return min(score, 100)


def requires_approval(action: str) -> bool:
    return classify_action_tier(action) == "Tier 2"


def evaluate_policy(service: str, action: str, mode: str, root_cause: str) -> PolicyDecision:
    tier = classify_action_tier(action)
    score = risk_score(action, root_cause)

    if mode == "maintenance":
        return PolicyDecision(
            service=service,
            action=action,
            mode=mode,
            tier=tier,
            allowed=False,
            blocked=True,
            approval_required=False,
            policy_reason="Maintenance mode active. Remediation suppressed.",
            risk_score=score,
        )

    if mode == "chaos":
        return PolicyDecision(
            service=service,
            action=action,
            mode=mode,
            tier=tier,
            allowed=False,
            blocked=True,
            approval_required=True,
            policy_reason="Chaos test detected. Human approval required.",
            risk_score=score,
        )

    if tier == "Tier 2":
        return PolicyDecision(
            service=service,
            action=action,
            mode=mode,
            tier=tier,
            allowed=False,
            blocked=True,
            approval_required=True,
            policy_reason="Tier 2 risky action requires approval; execute shadow simulation only.",
            risk_score=score,
        )

    return PolicyDecision(
        service=service,
        action=action,
        mode=mode,
        tier=tier,
        allowed=True,
        blocked=False,
        approval_required=False,
        policy_reason="Tier 1 action allowed for autonomous remediation.",
        risk_score=score,
    )
