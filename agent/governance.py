"""Tiered policy enforcement for safe operations."""

from nemoclaw.policy import PolicyEngine
from tools import risk_scorer


class GovernanceEngine:
    """Evaluate generated remediation commands against policy and risk."""

    def __init__(self):
        self.policy_engine = PolicyEngine()

    def evaluate(self, commands: list[dict], severity: str) -> list[dict]:
        """Enrich each command with risk and policy decisions."""
        enriched: list[dict] = []
        for command in commands:
            command_text = str(command.get("command", ""))
            score = risk_scorer.score_risk(command_text, severity, command)
            policy = self.policy_engine.check_policy(command_text, severity, score)

            enriched_command = dict(command)
            enriched_command.update(
                {
                    "risk_score": score,
                    "tier": policy.get("tier", "blocked"),
                    "allowed": bool(policy.get("allowed", False)),
                    "requires_human": bool(policy.get("requires_human", True)),
                    "policy_reason": str(policy.get("reason", "")),
                }
            )
            enriched.append(enriched_command)
        return enriched

    def approve_tier1(self, commands: list[dict]) -> list[dict]:
        """Return safe, policy-allowed tier1 commands for auto-approval."""
        return [
            cmd
            for cmd in commands
            if cmd.get("tier") == "tier1"
            and bool(cmd.get("allowed", False))
            and float(cmd.get("risk_score", 1.0)) < 0.4
        ]

    def flag_tier2(self, commands: list[dict]) -> list[dict]:
        """Return tier2 commands needing human review, ready for CLI display."""
        flagged: list[dict] = []
        for cmd in commands:
            if cmd.get("tier") == "tier2" and bool(cmd.get("requires_human", False)):
                flagged.append(
                    {
                        "command": str(cmd.get("command", "")),
                        "risk_score": round(float(cmd.get("risk_score", 1.0)), 3),
                        "allowed": bool(cmd.get("allowed", False)),
                        "policy_reason": str(cmd.get("policy_reason", "")),
                    }
                )
        return flagged

    def block_dangerous(self, commands: list[dict]) -> list[dict]:
        """Return blocked commands with reasons for audit logging."""
        blocked: list[dict] = []
        for cmd in commands:
            if cmd.get("tier") == "blocked" or not bool(cmd.get("allowed", False)):
                blocked.append(
                    {
                        "command": str(cmd.get("command", "")),
                        "tier": str(cmd.get("tier", "blocked")),
                        "risk_score": float(cmd.get("risk_score", 1.0)),
                        "reason": str(cmd.get("policy_reason", "")),
                    }
                )
        return blocked


class Governance(GovernanceEngine):
    """Backward-compatible alias for previous Governance class name."""
