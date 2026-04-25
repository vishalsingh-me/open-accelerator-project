from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from governance import detect_nemoclaw_runtime, evaluate_policy
from llm_client import LLMReasoner
from notifier import notify_team
from simulation import shadow_simulate
from tools import (
    analyze_log_text,
    classify_severity,
    detect_root_cause,
    fetch_container_logs,
    is_container_running,
    restart_container,
)

SERVICES = ["payment-service", "order-service"]
STATE_PATH = Path(__file__).resolve().parent / "state.json"
SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"


class IncidentIQAgent:
    def __init__(self, monitor_interval: int = 3):
        self.console = Console()
        self.monitor_interval = monitor_interval
        self.reasoner = LLMReasoner()
        self.last_seen_running = {service: None for service in SERVICES}

    def _load_state(self) -> dict[str, Any]:
        if not STATE_PATH.exists():
            default = {
                service: {"mode": "normal", "pending_approval": False}
                for service in SERVICES
            }
            self._save_state(default)
            return default

        with STATE_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save_state(self, state: dict[str, Any]) -> None:
        with STATE_PATH.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2)

    def _update_pending_approval(self, service: str, pending: bool) -> None:
        state = self._load_state()
        entry = state.setdefault(service, {"mode": "normal", "pending_approval": False})
        entry["pending_approval"] = pending
        self._save_state(state)

    def _get_mode(self, service: str) -> str:
        state = self._load_state()
        return state.get(service, {}).get("mode", "normal")

    def monitor_loop(self) -> None:
        runtime_message = (
            "NemoClaw runtime detected"
            if detect_nemoclaw_runtime()
            else "NemoClaw-style governance policy applied"
        )

        self.console.print(
            Panel.fit(
                "IncidentIQ Autopilot Monitor Loop\n"
                f"Tracking services: {', '.join(SERVICES)}\n"
                f"Poll interval: {self.monitor_interval}s\n"
                f"{runtime_message}",
                border_style="cyan",
            )
        )

        while True:
            for service in SERVICES:
                running = is_container_running(service)
                prev = self.last_seen_running.get(service)

                if prev is None:
                    self.last_seen_running[service] = running
                    continue

                if prev and not running:
                    self.handle_service_down(service)
                elif not prev and running:
                    self.console.print(f"[green]{service} recovered and is running.[/green]")

                self.last_seen_running[service] = running

            time.sleep(self.monitor_interval)

    def handle_service_down(self, service: str) -> None:
        mode = self._get_mode(service)
        logs = fetch_container_logs(service)

        if mode in {"chaos", "maintenance"}:
            self.run_agentic_workflow(
                service=service,
                mode=mode,
                log_text=logs,
                forced_action=f"restart service/container {service}",
                trigger="service_down",
            )
            return

        self.run_agentic_workflow(
            service=service,
            mode=mode,
            log_text=logs,
            forced_action=f"restart service/container {service}",
            trigger="service_down",
        )

    def handle_scenario(self, scenario_name: str) -> None:
        scenario_file = SCENARIOS_DIR / f"{scenario_name}.txt"
        if not scenario_file.exists():
            raise FileNotFoundError(f"Scenario not found: {scenario_name}")

        log_text = scenario_file.read_text(encoding="utf-8")

        scenario_service = {
            "oom": "payment-service",
            "crashloop": "order-service",
            "db_timeout": "payment-service",
            "instance_stopped": "order-service",
        }.get(scenario_name, "payment-service")

        forced_action = {
            "oom": "change memory limits for payment-service deployment",
            "crashloop": "restart service/container order-service",
            "db_timeout": "restart database",
            "instance_stopped": "restart service/container order-service",
        }.get(scenario_name, "inspect container")

        mode = self._get_mode(scenario_service)
        self.run_agentic_workflow(
            service=scenario_service,
            mode=mode,
            log_text=log_text,
            forced_action=forced_action,
            trigger=f"scenario:{scenario_name}",
        )

    def run_agentic_workflow(
        self,
        service: str,
        mode: str,
        log_text: str,
        forced_action: str,
        trigger: str,
    ) -> dict[str, Any]:
        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"

        self.console.print(
            Panel.fit(
                "Reasoning -> Tool Selection -> NemoClaw Governance Check -> "
                "vLLM Verification -> Shadow Simulation -> Action Execution -> Notification -> Final Report",
                title=f"IncidentIQ Workflow ({incident_id})",
                border_style="bright_blue",
            )
        )

        timings: dict[str, float] = {}

        t0 = time.perf_counter()
        analysis = analyze_log_text(log_text)
        root_cause = detect_root_cause(log_text)
        severity = classify_severity(root_cause)
        timings["log_analysis"] = time.perf_counter() - t0

        self.console.print("[bold cyan]Reasoning[/bold cyan]")
        reasoning_table = Table(show_header=True)
        reasoning_table.add_column("Field", style="cyan")
        reasoning_table.add_column("Value", style="white")
        reasoning_table.add_row("Trigger", trigger)
        reasoning_table.add_row("Service", service)
        reasoning_table.add_row("Mode", mode)
        reasoning_table.add_row("Root Cause", root_cause)
        reasoning_table.add_row("Severity", severity)
        reasoning_table.add_row("Signals", ", ".join(analysis["signals"]))
        self.console.print(reasoning_table)

        self.console.print("[bold cyan]Tool Selection[/bold cyan]")
        tool_table = Table(show_header=True)
        tool_table.add_column("Tool", style="magenta")
        tool_table.add_column("Output", style="white")
        tool_table.add_row("fetch_container_logs", f"{len(log_text.splitlines())} lines")
        tool_table.add_row("analyze_log_text", analysis["analysis_note"])
        tool_table.add_row("detect_root_cause", root_cause)
        tool_table.add_row("classify_severity", severity)
        self.console.print(tool_table)

        t1 = time.perf_counter()
        policy = evaluate_policy(service=service, action=forced_action, mode=mode, root_cause=root_cause)
        timings["governance_check"] = time.perf_counter() - t1

        self.console.print("[bold cyan]NemoClaw Governance Check[/bold cyan]")
        governance_msg = "NemoClaw runtime detected" if detect_nemoclaw_runtime() else "NemoClaw-style governance policy applied"
        self.console.print(f"[yellow]{governance_msg}[/yellow]")
        gov_table = Table(show_header=True)
        gov_table.add_column("Policy Field", style="cyan")
        gov_table.add_column("Value", style="white")
        gov_table.add_row("Tier", policy.tier)
        gov_table.add_row("Allowed", str(policy.allowed))
        gov_table.add_row("Blocked", str(policy.blocked))
        gov_table.add_row("Approval Required", str(policy.approval_required))
        gov_table.add_row("Risk Score", f"{policy.risk_score}/100")
        gov_table.add_row("Reason", policy.policy_reason)
        self.console.print(gov_table)

        draft_start = time.perf_counter()
        local_draft = (
            f"Local draft: root cause={root_cause}; action={forced_action}; "
            f"mode={mode}; tier={policy.tier}."
        )
        local_draft_latency = time.perf_counter() - draft_start

        t2 = time.perf_counter()
        llm_result = self.reasoner.reason(
            prompt=(
                f"Service={service}\nMode={mode}\nRoot cause={root_cause}\n"
                f"Severity={severity}\nCandidate action={forced_action}\n"
                f"Policy reason={policy.policy_reason}\n"
                f"Logs:\n{log_text[:1200]}"
            )
        )
        timings["vllm_reasoning"] = time.perf_counter() - t2

        self.console.print("[bold cyan]vLLM Verification[/bold cyan]")
        self.console.print(Panel(llm_result["reasoning"], title=f"Reasoning Source: {llm_result['source']}", border_style="green"))

        comparison = Table(title="Inference Efficiency")
        comparison.add_column("Metric", style="cyan")
        comparison.add_column("Latency (ms)", style="white")
        comparison.add_row("Local rule-based draft latency", f"{local_draft_latency * 1000:.2f}")
        comparison.add_row("vLLM verification latency", f"{llm_result['latency'] * 1000:.2f}")
        self.console.print(comparison)

        action_outcome = "no_action"
        simulation_result: dict[str, Any] | None = None
        self.console.print("[bold cyan]Shadow Simulation[/bold cyan]")
        if policy.allowed:
            self.console.print("[dim]Shadow simulation skipped for allowed Tier 1 action.[/dim]")
        else:
            simulation_result = shadow_simulate(forced_action, service, root_cause)
            sim_panel = (
                f"status={simulation_result['status']}\n"
                f"expected={simulation_result['expected_result']}\n"
                f"safety={simulation_result['safety_note']}\n\n"
                f"{simulation_result['fake_logs']}"
            )
            self.console.print(Panel(sim_panel, border_style="yellow"))

        t3 = time.perf_counter()
        if policy.allowed:
            ok, detail = restart_container(service) if "restart" in forced_action else (True, "non-restart tier1 action simulated")
            action_outcome = "executed" if ok else "failed"
            execution_note = detail
            self._update_pending_approval(service, False)
        else:
            action_outcome = "shadow_simulated"
            execution_note = simulation_result["safety_note"] if simulation_result else "simulation complete"
            if policy.approval_required:
                self._update_pending_approval(service, True)
        timings["action_execution_or_simulation"] = time.perf_counter() - t3

        self.console.print("[bold cyan]Action Execution[/bold cyan]")
        if mode == "chaos":
            self.console.print("[bold yellow]Chaos test detected. Human approval required.[/bold yellow]")
        if mode == "maintenance":
            self.console.print("[bold yellow]Maintenance mode active. Remediation suppressed.[/bold yellow]")
        if policy.approval_required and mode == "normal":
            self.console.print("[bold yellow]Approval required for Tier 2 action. No production execution.[/bold yellow]")

        action_table = Table(show_header=True)
        action_table.add_column("Field", style="cyan")
        action_table.add_column("Value", style="white")
        action_table.add_row("Candidate Action", forced_action)
        action_table.add_row("Outcome", action_outcome)
        action_table.add_row("Execution Note", execution_note)
        self.console.print(action_table)

        total_latency = sum(timings.values())

        summary_report = (
            f"Incident {incident_id} | service={service} | severity={severity}\n"
            f"root_cause={root_cause} | action={forced_action}\n"
            f"tier={policy.tier} | policy={policy.policy_reason}\n"
            f"result={action_outcome} | total_decision_latency_ms={total_latency * 1000:.2f}"
        )

        self.console.print("[bold cyan]Notification[/bold cyan]")
        notify_team(summary_report)

        self.console.print("[bold cyan]Final Report[/bold cyan]")
        final_table = Table(title="IncidentIQ Final Action Report")
        final_table.add_column("Field", style="cyan")
        final_table.add_column("Value", style="white")
        final_table.add_row("Incident ID", incident_id)
        final_table.add_row("Service", service)
        final_table.add_row("Mode", mode)
        final_table.add_row("Root Cause", root_cause)
        final_table.add_row("Severity", severity)
        final_table.add_row("Tier", policy.tier)
        final_table.add_row("Policy Decision", "Allowed" if policy.allowed else "Blocked")
        final_table.add_row("Approval Required", str(policy.approval_required))
        final_table.add_row("Action Outcome", action_outcome)
        final_table.add_row("Log analysis latency (ms)", f"{timings['log_analysis'] * 1000:.2f}")
        final_table.add_row("Governance latency (ms)", f"{timings['governance_check'] * 1000:.2f}")
        final_table.add_row("vLLM/local latency (ms)", f"{timings['vllm_reasoning'] * 1000:.2f}")
        final_table.add_row("Action/sim latency (ms)", f"{timings['action_execution_or_simulation'] * 1000:.2f}")
        final_table.add_row("Total decision latency (ms)", f"{total_latency * 1000:.2f}")
        self.console.print(final_table)

        return {
            "incident_id": incident_id,
            "service": service,
            "root_cause": root_cause,
            "severity": severity,
            "action": forced_action,
            "policy": policy.model_dump(),
            "action_outcome": action_outcome,
            "timings": timings,
            "llm_source": llm_result["source"],
            "local_draft": local_draft,
        }
