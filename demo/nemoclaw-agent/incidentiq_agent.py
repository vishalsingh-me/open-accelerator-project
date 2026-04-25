"""
IncidentIQ+ — NemoClaw + vLLM Enterprise Incident Response Agent
================================================================

Builder-tier Track 5 project with Deep Tech governance elements.

The deterministic pipeline is the source of truth:
logs -> analysis -> root cause -> severity -> commands -> risk -> shadow simulation -> report

vLLM is optional and used only to polish the final report. If vLLM is unavailable,
the local deterministic report is still produced.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:  # pragma: no cover - deterministic mode does not require httpx.
    httpx = None  # type: ignore

from tools import (
    command_generator,
    incident_report,
    log_analyzer,
    remediation_simulator,
    risk_scoring,
    root_cause_detector,
    severity_classifier,
)


VLLM_ENDPOINT = os.getenv("VLLM_ENDPOINT", "http://localhost:8000/v1")
MODEL = os.getenv("MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
LLM_POLISH_TIMEOUT = float(os.getenv("LLM_POLISH_TIMEOUT", "3"))
BASE_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = BASE_DIR / "sample_incidents"


TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "analyze_logs",
            "description": "Analyze infrastructure logs and extract structured incident signals.",
            "parameters": {
                "type": "object",
                "properties": {"logs": {"type": "string"}},
                "required": ["logs"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_root_cause",
            "description": "Detect the most likely root cause from log analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis": {"type": "object"},
                    "logs": {"type": "string"},
                },
                "required": ["analysis", "logs"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "classify_severity",
            "description": "Classify incident severity from analysis and root cause.",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis": {"type": "object"},
                    "root_cause": {"type": "object"},
                },
                "required": ["analysis", "root_cause"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_commands",
            "description": "Generate diagnostic and approval-gated remediation commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis": {"type": "object"},
                    "root_cause": {"type": "object"},
                    "severity": {"type": "object"},
                },
                "required": ["analysis", "root_cause", "severity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_risk",
            "description": "Apply governance policy and risk-score generated commands.",
            "parameters": {
                "type": "object",
                "properties": {"commands": {"type": "object"}},
                "required": ["commands"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_remediation",
            "description": "Simulate the remediation plan in shadow mode without executing commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis": {"type": "object"},
                    "root_cause": {"type": "object"},
                    "commands": {"type": "object"},
                    "risk": {"type": "object"},
                },
                "required": ["analysis", "root_cause", "commands", "risk"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_incident_report",
            "description": "Generate the final structured and markdown incident report.",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis": {"type": "object"},
                    "root_cause": {"type": "object"},
                    "severity": {"type": "object"},
                    "commands": {"type": "object"},
                    "risk": {"type": "object"},
                    "simulation": {"type": "object"},
                },
                "required": ["analysis", "root_cause", "severity", "commands", "risk", "simulation"],
            },
        },
    },
]


def execute_tool(name: str, args: Dict[str, Any]) -> str:
    """Execute an IncidentIQ+ deterministic tool and return JSON."""
    try:
        if name == "analyze_logs":
            result = log_analyzer.analyze(args["logs"])
        elif name == "detect_root_cause":
            result = root_cause_detector.detect(args["analysis"], args["logs"])
        elif name == "classify_severity":
            result = severity_classifier.classify(args["analysis"], args["root_cause"])
        elif name == "generate_commands":
            result = command_generator.generate(args["analysis"], args["root_cause"], args["severity"])
        elif name == "score_risk":
            result = risk_scoring.score(args["commands"])
        elif name == "simulate_remediation":
            result = remediation_simulator.simulate(args["analysis"], args["root_cause"], args["commands"], args["risk"])
        elif name == "generate_incident_report":
            result = incident_report.generate_report(
                args["analysis"],
                args["root_cause"],
                args["severity"],
                args["commands"],
                args["risk"],
                args["simulation"],
            )
        else:
            result = {"error": f"Unknown tool: {name}"}
    except Exception as exc:  # Keep CLI graceful for demos.
        result = {"error": f"Tool execution failed: {exc}"}
    return json.dumps(result, indent=2)


def _print_step(name: str, result: Dict[str, Any], quiet: bool = False) -> None:
    if quiet:
        return
    print(f"[IncidentIQ+] calling {name}")
    if name == "analyze_logs":
        print(f"  summary: {result['short_summary']}")
    elif name == "detect_root_cause":
        print(f"  root cause: {result['root_cause']} ({result['confidence']} confidence)")
    elif name == "classify_severity":
        print(f"  severity: {result['severity']} ({result['score']}/10)")
    elif name == "generate_commands":
        total = len(result.get("diagnostic_commands", [])) + len(result.get("remediation_commands", []))
        print(f"  command plan: {total} generated, none executed")
    elif name == "score_risk":
        print(f"  policy: {result['policy_decision']} | overall risk: {result['overall_risk']}")
    elif name == "simulate_remediation":
        print(f"  simulation: {result['simulation_mode']} -> {result['status']}")
    elif name == "generate_incident_report":
        print(f"  final status: {result['final_status']}")


def run_incident_pipeline(logs: str, quiet: bool = False) -> Dict[str, Any]:
    """Run the deterministic IncidentIQ+ pipeline."""
    analysis = log_analyzer.analyze(logs)
    _print_step("analyze_logs", analysis, quiet)

    root = root_cause_detector.detect(analysis, logs)
    _print_step("detect_root_cause", root, quiet)

    severity = severity_classifier.classify(analysis, root)
    _print_step("classify_severity", severity, quiet)

    commands = command_generator.generate(analysis, root, severity)
    _print_step("generate_commands", commands, quiet)

    risk = risk_scoring.score(commands)
    _print_step("score_risk", risk, quiet)

    simulation = remediation_simulator.simulate(analysis, root, commands, risk)
    _print_step("simulate_remediation", simulation, quiet)

    report = incident_report.generate_report(analysis, root, severity, commands, risk, simulation)
    _print_step("generate_incident_report", report, quiet)

    return {
        "analysis": analysis,
        "root_cause": root,
        "severity": severity,
        "commands": commands,
        "risk": risk,
        "simulation": simulation,
        "report": report,
    }


def polish_report_with_llm(pipeline_output: Dict[str, Any]) -> Optional[str]:
    """Ask vLLM to lightly polish the deterministic report. Failure is non-fatal."""
    if httpx is None:
        return None

    report = pipeline_output["report"]["markdown_report"]
    prompt = (
        "Polish this incident report for an SRE demo. Preserve all facts, commands, "
        "risk decisions, and the warning that no remediation commands were executed.\n\n"
        f"{report}"
    )

    try:
        response = httpx.post(
            f"{VLLM_ENDPOINT}/chat/completions",
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": "You polish incident reports without changing technical facts."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 1400,
            },
            timeout=LLM_POLISH_TIMEOUT,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"].get("content")
        if content and "IncidentIQ+" in content:
            return content
    except Exception as exc:
        print(f"[IncidentIQ+] vLLM polish unavailable, using deterministic report: {exc}", file=sys.stderr)
    return None


def run_agent(logs: str, use_llm: bool = False, quiet: bool = False) -> Dict[str, Any]:
    """Run the IncidentIQ+ agent. Deterministic pipeline is always primary."""
    output = run_incident_pipeline(logs, quiet=quiet)
    if use_llm:
        polished = polish_report_with_llm(output)
        if polished:
            output["report"]["markdown_report"] = polished
            output["llm_polish"] = {"used": True, "endpoint": VLLM_ENDPOINT, "model": MODEL, "timeout_seconds": LLM_POLISH_TIMEOUT}
        else:
            output["llm_polish"] = {"used": False, "endpoint": VLLM_ENDPOINT, "model": MODEL, "timeout_seconds": LLM_POLISH_TIMEOUT}
    else:
        output["llm_polish"] = {"used": False, "reason": "disabled"}
    return output


def load_sample(name: str) -> str:
    aliases = {
        "oom": "oomkilled",
        "oomkilled": "oomkilled",
        "image": "imagepullbackoff",
        "imagepullbackoff": "imagepullbackoff",
        "crash": "crashloopbackoff",
        "crashloopbackoff": "crashloopbackoff",
        "503": "service_503",
        "service_503": "service_503",
        "node": "node_pressure",
        "node_pressure": "node_pressure",
    }
    sample = aliases.get(name.lower())
    if not sample:
        available = ", ".join(sorted(aliases))
        raise ValueError(f"Unknown sample '{name}'. Available samples: {available}")
    path = SAMPLE_DIR / f"{sample}.txt"
    return path.read_text(encoding="utf-8")


def load_logs(args: argparse.Namespace) -> str:
    if args.sample:
        return load_sample(args.sample)
    if args.file:
        path = Path(args.file)
        if not path.exists():
            raise FileNotFoundError(f"Incident log file not found: {path}")
        return path.read_text(encoding="utf-8")
    if args.interactive:
        print("Paste incident logs, then press Ctrl-D:")
        return sys.stdin.read()
    raise ValueError("Provide --sample, --file, or --interactive.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="IncidentIQ+ enterprise incident response agent")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--sample", help="Run a bundled sample: oomkilled, imagepullbackoff, crashloopbackoff, service_503, node_pressure")
    source.add_argument("--file", help="Path to an incident log file")
    source.add_argument("--interactive", action="store_true", help="Read incident logs from stdin")
    parser.add_argument("--json", action="store_true", help="Print full JSON result instead of markdown report")
    parser.add_argument("--use-llm", action="store_true", help="Enable optional vLLM report polishing with a short timeout")
    parser.add_argument("--no-llm", action="store_true", help="Compatibility flag; deterministic no-LLM mode is already the default")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start = time.time()
    try:
        logs = load_logs(args)
        result = run_agent(logs, use_llm=args.use_llm and not args.no_llm and not args.json, quiet=args.json)
    except Exception as exc:
        print(f"IncidentIQ+ error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("\n" + "=" * 78)
        print(result["report"]["markdown_report"])
        print("=" * 78)
        print(f"[IncidentIQ+] Completed in {time.time() - start:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
