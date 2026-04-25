"""Sandbox container simulation using Docker SDK."""

import json
import time
from typing import Any

import docker
from docker.errors import APIError, ImageNotFound

from vllm_client.client import VLLMClient

SIM_LABEL_KEY = "incidentiq.shadow.simulation"
SIM_LABEL_VALUE = "true"


def _parse_json_object(text: str) -> dict[str, Any]:
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


class ShadowSimulator:
    """Run remediation commands in an isolated sandbox container."""

    def __init__(self) -> None:
        self._docker = docker.from_env()
        self._vllm = VLLMClient()
        self._image_candidates = ("alpine:latest", "busybox:latest")
        self._container_ids: set[str] = set()

    def _ensure_image(self) -> str:
        """Ensure a simulation image exists locally, pulling if needed."""
        for image in self._image_candidates:
            try:
                self._docker.images.get(image)
                return image
            except ImageNotFound:
                try:
                    self._docker.images.pull(image)
                    return image
                except APIError:
                    continue
        raise RuntimeError("Unable to pull or find alpine:latest or busybox:latest")

    def simulate(self, command: dict) -> dict:
        """Run a command in an isolated container and evaluate safety."""
        image = self._ensure_image()
        command_text = str(command.get("command", "")).strip()
        if not command_text:
            return {
                "command": "",
                "exit_code": 1,
                "stdout": "",
                "stderr": "No command provided",
                "simulation_success": False,
                "safe": False,
                "warnings": ["No command provided for simulation."],
                "duration_ms": 0,
            }

        started = time.perf_counter()
        exit_code = 1
        stdout = ""
        stderr = ""

        container = self._docker.containers.create(
            image=image,
            command=["sh", "-lc", command_text],
            labels={SIM_LABEL_KEY: SIM_LABEL_VALUE},
            network_mode="none",
            read_only=True,
            tmpfs={"/tmp": "rw,size=64m"},
            mem_limit="128m",
            nano_cpus=500000000,  # 0.5 CPU
            working_dir="/tmp",
            detach=True,
            stdin_open=False,
            tty=False,
        )
        self._container_ids.add(container.id)

        try:
            container.start()
            wait_result = container.wait(timeout=30)
            exit_code = int(wait_result.get("StatusCode", 1))
        except Exception as exc:  # timeout/errors from wait
            try:
                container.kill()
            except Exception:
                pass
            stderr = f"Simulation execution error: {exc}"
            exit_code = 124
        finally:
            try:
                stdout = container.logs(stdout=True, stderr=False).decode(
                    "utf-8", errors="replace"
                )
            except Exception:
                stdout = ""
            try:
                stderr_logs = container.logs(stdout=False, stderr=True).decode(
                    "utf-8", errors="replace"
                )
                if stderr_logs:
                    stderr = f"{stderr}\n{stderr_logs}".strip() if stderr else stderr_logs
            except Exception:
                pass
            try:
                container.remove(force=True)
            except Exception:
                pass
            self._container_ids.discard(container.id)

        duration_ms = int((time.perf_counter() - started) * 1000)

        analysis_prompt = (
            "Did this command succeed safely? Return JSON: {success: bool, safe: bool, "
            "output_summary: str, warnings: [str]}\n\n"
            f"Command: {command_text}\n"
            f"Exit code: {exit_code}\n"
            f"STDOUT:\n{stdout}\n\n"
            f"STDERR:\n{stderr}"
        )
        assessment_raw = self._vllm.complete_draft(analysis_prompt)
        assessment = _parse_json_object(assessment_raw)

        success = bool(assessment.get("success", exit_code == 0))
        safe = bool(assessment.get("safe", False))
        warnings = assessment.get("warnings", [])
        if not isinstance(warnings, list):
            warnings = [str(warnings)]
        warnings = [str(w) for w in warnings]

        return {
            "command": command_text,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "simulation_success": success,
            "safe": safe,
            "warnings": warnings,
            "duration_ms": duration_ms,
        }

    def cleanup(self) -> None:
        """Remove all simulation containers created by this simulator."""
        for container_id in list(self._container_ids):
            try:
                container = self._docker.containers.get(container_id)
                container.remove(force=True)
            except Exception:
                pass
            finally:
                self._container_ids.discard(container_id)

        labeled = self._docker.containers.list(
            all=True, filters={"label": f"{SIM_LABEL_KEY}={SIM_LABEL_VALUE}"}
        )
        for container in labeled:
            try:
                container.remove(force=True)
            except Exception:
                pass
