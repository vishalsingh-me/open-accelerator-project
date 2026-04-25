"""Main orchestrator for the IncidentIQ Plus workflow."""

from simulation.shadow import ShadowSimulator
from tools import command_gen, log_analyzer, report_gen, root_cause, severity
from .governance import Governance
from .speculative import SpeculativeExecutor


class IncidentLoop:
    """Coordinate analysis, planning, governance, and speculative checks."""

    def __init__(self) -> None:
        self.governance = Governance()
        self.speculative = SpeculativeExecutor()
        self.shadow = ShadowSimulator()

    @staticmethod
    def _emit(stream_callback, message: str) -> None:
        """Safely emit a progress update if callback is provided."""
        if callable(stream_callback):
            stream_callback(message)

    def run_incident(self, log_text: str, stream_callback=None) -> dict:
        """Execute full IncidentIQ+ pipeline for a single incident."""
        import time

        started = time.perf_counter()
        simulations: list[dict] = []
        spec_results: list[dict] = []

        self._emit(stream_callback, "Analyzing logs...")
        analysis = log_analyzer.analyze_logs(log_text)

        severity_result = severity.classify_severity(analysis)
        self._emit(stream_callback, f"Severity: {severity_result.get('severity', 'unknown')}")

        root_cause_result = root_cause.detect_root_cause(analysis, severity_result)
        self._emit(
            stream_callback,
            f"Root cause: {root_cause_result.get('root_cause', '')}",
        )

        commands = command_gen.generate_commands(
            root_cause_result, severity_result.get("severity", "medium")
        )
        self._emit(stream_callback, f"Generated {len(commands)} commands")

        governed = self.governance.evaluate(commands, severity_result.get("severity", "medium"))
        tier1 = self.governance.approve_tier1(governed)
        tier2 = self.governance.flag_tier2(governed)
        blocked = self.governance.block_dangerous(governed)

        verification_candidates = list(tier1) + list(tier2)
        verification_context = {
            "analysis": analysis,
            "severity": severity_result,
            "root_cause": root_cause_result,
            "governed_commands": governed,
        }

        for command in verification_candidates:
            command_text = str(command.get("command", ""))
            self._emit(stream_callback, f"Verifying: {command_text[:40]}...")

            spec = self.speculative.verify(command, verification_context)
            spec_results.append(spec)

            if spec.get("verified", False):
                command_for_sim = dict(command)
                command_for_sim["command"] = spec.get("command", command_text)
                sim = self.shadow.simulate(command_for_sim)
                simulations.append(sim)
                self._emit(
                    stream_callback,
                    f"Simulation: {'PASSED' if sim.get('safe', False) else 'FAILED'}",
                )

        metrics = self.speculative.metrics()
        speculative_accuracy_pct = round(metrics.get("draft_accuracy", 0.0) * 100.0, 2)

        result = {
            "severity": severity_result,
            "root_cause": root_cause_result,
            "commands": governed,
            "tier1_auto": tier1,
            "tier2_review": tier2,
            "blocked": blocked,
            "simulations": simulations,
            "speculative_accuracy": speculative_accuracy_pct,
            "speculative": spec_results,
        }

        if hasattr(report_gen, "generate"):
            report = report_gen.generate(result)
        else:
            report = report_gen.build_report(result)

        result["report"] = report
        result["total_latency_ms"] = int((time.perf_counter() - started) * 1000)
        return result

    def run(self, logs: str) -> dict:
        """Backward-compatible wrapper around the full incident pipeline."""
        return self.run_incident(logs, stream_callback=None)


def run_incident(log_text: str, stream_callback=None) -> dict:
    """Convenience function for one-shot incident execution."""
    loop = IncidentLoop()
    return loop.run_incident(log_text, stream_callback=stream_callback)
