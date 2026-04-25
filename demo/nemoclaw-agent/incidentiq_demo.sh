#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "IncidentIQ+ demo: OOMKilled critical incident"
echo "============================================================"
python3 incidentiq_agent.py --sample oomkilled --no-llm

echo
echo "IncidentIQ+ JSON summary"
echo "============================================================"
python3 incidentiq_agent.py --sample oomkilled --json
