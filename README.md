# incidentiq-plus

Starter scaffold for an IncidentIQ Plus Python project.

## Structure

- `agent/`: orchestration, analysis, governance, and speculative loop
- `tools/`: utility modules for analysis, risk, and reporting
- `simulation/`: shadow/sandbox simulation placeholders
- `vllm_client/`: vLLM client config scaffold
- `nemoclaw/`: policy package scaffold
- `cli/`: Typer-based command-line entrypoint
- `demo/`: sample logs and runnable demo script

## Quick start

1. Create a virtual environment and activate it.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy env file:
   - `cp .env.example .env` (or Windows equivalent)
4. Run demo:
   - `python demo/run_demo.py`
