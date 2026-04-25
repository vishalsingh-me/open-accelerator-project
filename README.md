# IncidentIQ+
> Enterprise agentic incident response — NemoClaw + vLLM + shadow simulation

**Tagline:** "IncidentIQ+ diagnoses infrastructure incidents, governs risky actions with policy enforcement, verifies commands speculatively, and safely simulates fixes before production."

## The Problem

Infrastructure incidents still rely on slow, manual response loops:

- **30-120 minute MTTR** due to fragmented triage workflows
- **Manual log analysis** across Kubernetes, app, DB, and alert streams
- **Limited safety guardrails** when teams automate remediation commands

IncidentIQ+ addresses this gap with an agentic, policy-aware response pipeline designed for real operations pressure.

## Architecture

IncidentIQ+ follows a safety-first execution path:

```text
                +----------------------+
                |   Incident Logs      |
                | (K8s / app / infra)  |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |  Perception Layer    |
                | analyze + severity + |
                | root-cause detection |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Governance Engine    |
                | NemoClaw tier policy |
                | + risk scoring       |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Speculative Loop     |
                | draft (3B) -> verify |
                | (70B) + accuracy KPI |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Shadow Simulation    |
                | Docker sandbox       |
                | no-net + resource    |
                | limits + safe eval   |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Safe Action Decision |
                | auto / review / block|
                +----------------------+
```

## Core Innovations

1. **Tiered governance (NemoClaw policy enforcement)**  
   Commands are classified into `tier1`, `tier2`, or `blocked`, with severity/risk-aware approval gates.

2. **Speculative loop (draft accuracy metric)**  
   A small draft model proposes quick safety assessment, then a large verifier overrides when needed.  
   The system tracks `draft_was_correct` as a live demo metric.

3. **Shadow simulation (Docker sandbox)**  
   Verified commands run in an isolated container with no network, read-only root FS, CPU/memory limits, and timeout controls.

4. **Rich CLI for real DevOps workflows**  
   Live progress streaming, safety badges, governed command tables, and final incident report output in terminal-first UX.

## Demo Metrics

During live runs, IncidentIQ+ highlights:

- **Speculative accuracy %** (headline stat)
- **MTTR reduction** versus manual triage/decision loops
- **Commands blocked by policy** before production impact

## Stack

- NemoClaw
- vLLM (Llama 70B + 3B draft)
- Docker simulation sandbox
- Rich CLI
- Python

## Setup

1. Install dependencies:
   - `pip install -r requirements.txt`
2. Configure environment:
   - copy `.env.example` to `.env`
3. Start vLLM server (OpenAI-compatible endpoint), for example:
   - `python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-3.1-70B-Instruct --served-model-name meta-llama/Llama-3.1-70B-Instruct --port 8000`
4. Run demo scenarios:
   - `python demo/run_demo.py`
5. Run Rich CLI:
   - `python -m cli.interface --log-file demo/sample_logs/pod_crash_oom.log`

## Track

**Track 5 — Agentic Edge powered by NemoClaw, Builder lane**

## Built At

**vLLM Hackathon 2025**
