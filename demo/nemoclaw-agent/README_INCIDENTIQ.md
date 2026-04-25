# IncidentIQ+

IncidentIQ+ is a NemoClaw-powered enterprise incident response agent for large-scale infrastructure environments. It uses a deterministic tool pipeline for reliable incident diagnosis, vLLM-compatible inference for optional report polishing, and governance plus shadow simulation to make remediation safer.

Track: **Track 5 - Agentic Edge powered by NemoClaw**  
Skill lane: **Builder with Deep Tech elements**

## Problem

SRE and DevOps teams face massive log volumes, fragmented debugging context, slow manual triage, and high risk when applying production fixes. A normal chatbot can summarize logs, but it does not provide governed, tool-driven incident response.

## Solution

IncidentIQ+ turns raw infrastructure logs into a controlled incident workflow:

```text
User Input -> NemoClaw Agent -> Policy Check -> Tool Calling -> Speculative Verification -> Shadow Simulation -> Final Action Report
```

The MVP is intentionally reliable with small local models. The core analysis is deterministic, while vLLM can optionally polish the final report.

## Architecture

```text
incidentiq_agent.py
  run_incident_pipeline(logs)
    -> tools.log_analyzer.analyze
    -> tools.root_cause_detector.detect
    -> tools.severity_classifier.classify
    -> tools.command_generator.generate
    -> tools.risk_scoring.score
    -> tools.remediation_simulator.simulate
    -> tools.incident_report.generate_report
  run_agent(logs)
    -> deterministic pipeline
    -> optional vLLM report polish
```

Supported incident types:

- OOMKilled
- ImagePullBackOff
- CrashLoopBackOff
- HTTP 503 / readiness probe failure
- Node memory/disk pressure
- Unknown incident fallback

## Deep Tech Elements

### 1. Tiered Governance

- Tier 1 diagnostic read-only actions are auto-allowed.
- Tier 2 remediation changes require human approval.
- Dangerous actions are blocked.

Examples:

- `kubectl get`, `kubectl describe`, `kubectl logs`, `kubectl top` -> Safe
- `kubectl rollout restart`, `kubectl set resources`, `kubectl set image` -> Needs Approval
- `kubectl delete`, `rm -rf`, `chmod 777`, exposing secrets -> Dangerous

### 2. Speculative Agentic Loop

IncidentIQ+ drafts a remediation plan, verifies it against risk policy, then simulates the expected outcome before recommending any action.

### 3. Shadow Simulation

IncidentIQ+ never executes production remediation commands. It predicts likely outcomes, validation checks, and rollback plans in shadow mode.

### 4. Enterprise Alignment

IncidentIQ+ maps directly to Kubernetes, OpenShift, and SRE workflows. It reduces mean time to resolution while keeping production changes governed and reviewable.

## Local Setup

From this directory:

```bash
cd demo/nemoclaw-agent
```

Optional environment variables:

```bash
export VLLM_ENDPOINT=http://localhost:8000/v1
export MODEL=Qwen/Qwen2.5-0.5B-Instruct
```

For NemoClaw/OpenShell sandbox usage:

```bash
export VLLM_ENDPOINT=http://host.openshell.internal:8000/v1
export MODEL=Qwen/Qwen2.5-0.5B-Instruct
```

The deterministic pipeline works even if vLLM is not running.

## vLLM Setup

Start a local OpenAI-compatible vLLM server with your model, then point IncidentIQ+ to it:

```bash
export VLLM_ENDPOINT=http://localhost:8000/v1
export MODEL=Qwen/Qwen2.5-0.5B-Instruct
```

IncidentIQ+ does not call vLLM by default. To enable optional report polishing, pass `--use-llm`. If the endpoint is unavailable, the CLI falls back to the deterministic markdown report after a short timeout.

## NemoClaw Setup

Use the existing Track 5 setup:

```bash
bash setup.sh
nemoclaw agentic-edge connect
```

Inside the sandbox, run:

```bash
python3 /workspace/incidentiq_agent.py --sample oomkilled --no-llm
```

## Usage

Run bundled samples:

```bash
python3 incidentiq_agent.py --sample oomkilled --no-llm
python3 incidentiq_agent.py --sample imagepullbackoff --no-llm
python3 incidentiq_agent.py --sample crashloopbackoff --no-llm
python3 incidentiq_agent.py --sample service_503 --no-llm
python3 incidentiq_agent.py --sample node_pressure --no-llm
```

Run with a file:

```bash
python3 incidentiq_agent.py --file sample_incidents/oomkilled.txt --no-llm
```

Read logs interactively:

```bash
python3 incidentiq_agent.py --interactive --no-llm
```

Print JSON:

```bash
python3 incidentiq_agent.py --sample oomkilled --json
```

Deterministic mode is the default. This explicit form is recommended for demos:

```bash
python3 incidentiq_agent.py --sample oomkilled --no-llm
```

Enable optional vLLM polishing:

```bash
python3 incidentiq_agent.py --sample oomkilled --use-llm
```

## Demo Script

Run:

```bash
bash incidentiq_demo.sh
```

2-minute pitch:

1. Problem: SREs are flooded with logs and production fixes are risky.
2. Solution: IncidentIQ+ diagnoses, governs, simulates, and reports safe action plans.
3. Live demo: `python3 incidentiq_agent.py --sample oomkilled --no-llm`
4. Output: Critical severity, Memory Limit Exceeded, safe diagnostics, approval-gated remediation, shadow simulation.
5. Track 5 alignment: NemoClaw-style agent loop, vLLM-compatible inference, tool calling, steerable governance.
6. Impact: faster MTTR, safer production operations, enterprise-ready incident automation.

## Expected OOMKilled Output

- Severity: Critical
- Root cause: Memory Limit Exceeded
- Evidence: OOMKilled, Exit Code 137, restart count, memory limit
- Diagnostic commands:
  - `kubectl describe pod api-service`
  - `kubectl logs api-service --previous`
  - `kubectl top pod api-service`
- Remediation command:
  - `kubectl set resources deployment/api-service --limits=memory=1Gi --requests=memory=512Mi`
- Risk:
  - diagnostic commands Safe
  - resource update Needs Approval
  - overall Medium
  - policy decision Human approval required
- Simulation:
  - Shadow mode Passed
  - Expected pod restart loop stops if usage remains below new limit
- Final status:
  - Safe to execute after approval

## Known Limitations

- The MVP uses regex and keyword heuristics, not a live Kubernetes API.
- Commands are generated for review only and are never executed.
- Unknown incidents intentionally remain conservative.
- The optional vLLM step is report polishing only; correctness comes from deterministic tools.
- ImagePullBackOff remediation requires verifying the correct image tag outside this MVP.

## Future Work

- Add live Kubernetes/OpenShift read-only API connectors.
- Add approval workflow integration with Slack, Jira, or PagerDuty.
- Add benchmark set for tool accuracy, latency, and policy enforcement.
- Add speculative small-model draft plus larger-model verification profiles.
- Add report export and incident timeline persistence.
