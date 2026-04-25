# IncidentIQ Autopilot

IncidentIQ Autopilot is a terminal-native, enterprise CloudOps/SRE agent for the vLLM / LLM-D Hackathon (Track 5: Agentic Edge powered by NemoClaw).

## What Track 5 means
Track 5 requires an agentic workflow, not a chatbot:
- autonomous monitoring
- tool calling and multi-step reasoning
- policy-steered action control
- safe/unsafe action separation
- approval gates for risky operations
- measurable inference/decision latency

## Why this is not a chatbot
This system runs as a control-plane service. It continuously monitors containers, detects incidents, reasons about remediation, applies governance, executes or suppresses actions, and emits notifications/reports. No conversational UI is required.

## NemoClaw-style governance
`governance.py` implements NemoClaw-style steerability:
- policy check
- action tier classification
- allowed vs blocked decision
- decision reason
- human approval gate

Runtime message behavior:
- `NemoClaw runtime detected` when NemoClaw/guardrails package is importable.
- `NemoClaw-style governance policy applied` otherwise.

## vLLM integration
`llm_client.py` supports OpenAI-compatible vLLM endpoints:
- `VLLM_BASE_URL` (default `http://localhost:8000/v1`)
- `VLLM_MODEL` (required for live vLLM completions)

Behavior:
- If endpoint/model work: `vLLM endpoint detected: using vLLM reasoning`
- If unavailable: `vLLM unavailable: using local fallback reasoning`

No model training is performed. This is inference-time orchestration only.

## Architecture
- `payment-service` (nginx demo service)
- `order-service` (nginx demo service)
- `incidentiq-agent` (Python autonomous control-plane)

Agent modules:
- `main.py` CLI entrypoint
- `agent.py` monitor loop + workflow orchestration
- `tools.py` container inspection/restart/log analysis tools
- `governance.py` tier/policy/risk engine
- `simulation.py` shadow simulation for blocked actions
- `llm_client.py` vLLM OpenAI-compatible reasoning client + fallback
- `notifier.py` terminal Slack-style notifications
- `control.py` operator commands for mode and approval control
- `state.json` per-service mode and approval status

## Tiered action governance
Tier 1 (auto-executable):
- restart service/container
- retry failed job
- fetch logs
- inspect container
- describe service

Tier 2 (approval-gated only):
- scaling production cluster
- changing CPU/memory limits
- modifying deployment YAML
- restarting database
- changing security/network config

Tier 2 behavior:
- risk scoring
- shadow simulation
- no autonomous production execution
- approval required

## Run
```bash
cd incidentiq-autopilot
docker compose up --build
```

Services started:
- `payment-service`
- `order-service`
- `incidentiq-agent`

## Demo commands
### 1) Unexpected crash (auto-remediation)
```bash
docker stop order-service
```
Expected:
- agent detects container down
- classifies Tier 1
- restarts automatically
- prints workflow report:
  `Reasoning -> Tool Selection -> NemoClaw Governance Check -> vLLM Reasoning -> Action Execution -> Notification -> Final Report`

### 2) Chaos test (do not fight engineer)
```bash
python control.py chaos payment-service
docker stop payment-service
```
Expected:
- no auto-restart
- marks pending approval
- prints: `Chaos test detected. Human approval required.`

Approve:
```bash
python control.py approve payment-service
```
Expected:
- restarts service
- resets mode to `normal`

### 3) Maintenance mode suppression
```bash
python control.py maintenance payment-service
docker stop payment-service
```
Expected:
- no restart
- prints: `Maintenance mode active. Remediation suppressed.`

### 4) Tier 2 risky action scenario
```bash
python main.py --scenario oom
```
Expected:
- OOM/memory pressure detected
- memory limit change recommended
- classified Tier 2
- no execution, shadow simulation only
- risk score + approval required shown

Additional scenarios:
```bash
python main.py --scenario crashloop
python main.py --scenario db_timeout
python main.py --scenario instance_stopped
```

## Inference efficiency logging
Each workflow prints step latency for:
- log analysis
- governance check
- vLLM/local reasoning
- action execution/simulation
- total decision latency

Comparison lines included:
- `Local rule-based draft latency`
- `vLLM verification latency`

## Expected terminal outputs
- governance decision with tier/approval status
- explicit chaos/maintenance suppression messages
- shadow simulation logs for blocked actions
- Slack-style notification panel
- final incident action report with latency metrics

## Hackathon pitch
IncidentIQ Autopilot demonstrates a production-minded agentic SRE control plane that combines deterministic operations logic with optional vLLM reasoning and NemoClaw-style policy steering. It can autonomously remediate low-risk failures while respecting operator intent (chaos/maintenance) and enforcing strict approval gates for high-risk actions.

## Limitations
- Uses local Docker container signals as the incident source.
- vLLM fallback is deterministic when endpoint/model are not available.
- Current state store is file-based (`state.json`) for demo simplicity.

## Future cloud integrations
- AWS: ECS/EKS health checks, CloudWatch and EventBridge inputs
- GCP: GKE + Cloud Logging incident streams
- Azure: AKS + Monitor alert automation
- OpenShift: project-aware policy packs and rollout controls
- External ITSM/ChatOps approvals (ServiceNow, Jira, Slack workflows)
