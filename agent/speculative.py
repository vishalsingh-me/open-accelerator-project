"""Speculative draft-and-verify loop."""

import json
import time

from vllm_client.client import VLLMClient


def _parse_json_object(text: str) -> dict:
    """Parse a JSON object from model output text."""
    if not text:
        return {}

    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = stripped[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


class SpeculativeLoop:
    """Draft with a small model, verify with a large model."""

    def __init__(self):
        self.vllm_client = VLLMClient()
        self.total_verifications = 0
        self.correct_draft_count = 0

    def verify(self, command: dict, context: dict) -> dict:
        """Run draft + verify and return a structured verification decision."""
        started = time.perf_counter()
        command_text = str(command.get("command", ""))
        context_json = json.dumps(context, ensure_ascii=True)

        draft_prompt = (
            "System: Assess this remediation command for safety in incident response. "
            "Is this command safe? What could go wrong? Any better alternative? "
            "Return concise plain text.\n\n"
            f"Command: {command_text}\n"
            f"Command metadata: {json.dumps(command, ensure_ascii=True)}\n"
            f"Incident context: {context_json}"
        )
        draft_assessment = self.vllm_client.complete_draft(draft_prompt)

        verify_prompt = (
            "System: Review this command and the draft assessment. Override if draft "
            "is wrong. Return JSON: {verified: bool, final_command: str, "
            "draft_was_correct: bool, override_reason: str, confidence: 0-1}\n\n"
            f"Original command: {command_text}\n"
            f"Command metadata: {json.dumps(command, ensure_ascii=True)}\n"
            f"Incident context: {context_json}\n"
            f"Draft assessment: {draft_assessment}"
        )
        verify_response = self.vllm_client.complete_large(verify_prompt)
        parsed = _parse_json_object(verify_response)

        verified = bool(parsed.get("verified", False))
        final_command = str(parsed.get("final_command", command_text))
        draft_was_correct = bool(parsed.get("draft_was_correct", False))
        override_reason = str(parsed.get("override_reason", ""))

        confidence = parsed.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        self.total_verifications += 1
        if draft_was_correct:
            self.correct_draft_count += 1

        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "command": final_command,
            "draft_assessment": draft_assessment,
            "verified": verified,
            "draft_was_correct": draft_was_correct,
            "override_reason": override_reason,
            "confidence": confidence,
            "latency_ms": latency_ms,
        }

    def draft_accuracy(self) -> float:
        """Return running draft correctness rate for demo metrics."""
        if self.total_verifications == 0:
            return 0.0
        return self.correct_draft_count / self.total_verifications

    def metrics(self) -> dict:
        """Return counters for speculative verification demo stats."""
        return {
            "total_verifications": self.total_verifications,
            "correct_draft_count": self.correct_draft_count,
            "draft_accuracy": self.draft_accuracy(),
        }


class SpeculativeExecutor(SpeculativeLoop):
    """Backward-compatible class name used by existing orchestrator."""

    def run(self, context: dict) -> dict:
        """Compatibility wrapper for older callsites."""
        plan = context.get("plan", {}) if isinstance(context, dict) else {}
        command = {"command": str(plan.get("action", "noop")), **(plan if isinstance(plan, dict) else {})}
        return self.verify(command, context if isinstance(context, dict) else {})
