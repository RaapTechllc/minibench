"""Container-backed terminal-operation tasks for the Real-Work Agent Cabinet."""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from agentbench.agent_tasks import (
    AgentBudget,
    AgentResult,
    AgentTaskManifest,
    AgentTrialResult,
    EnvironmentHandle,
    PreparedEnvironment,
    VerificationResult,
    build_agent_artifact,
    run_agent_trial,
)
from agentbench.terminal_worker import RPC_LIMIT, run_terminal_procedure


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
HARNESS = "agent-cabinet-terminal-operation"
_OUTPUT_LIMIT = 16_384
_PHASE1_IMAGE = "alpine@sha256:c64c687cbea9300178b30c95835354e34c4e4febc4badfe27102879de0483b5e"


def _run_command(argv: list[str], *, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@dataclass(frozen=True)
class ContainerPolicy:
    runtime: str
    image: str
    platform: str
    cpu_limit: float
    memory_mb: int
    pids_limit: int
    network: str

    @classmethod
    def from_dict(cls, raw: Any) -> "ContainerPolicy":
        if not isinstance(raw, dict):
            raise ValueError("container must be an object")
        runtime = raw.get("runtime")
        image = raw.get("image")
        platform = raw.get("platform")
        cpu_limit = raw.get("cpu_limit")
        memory_mb = raw.get("memory_mb")
        pids_limit = raw.get("pids_limit")
        network = raw.get("network")
        if runtime != "docker":
            raise ValueError("container.runtime must be docker")
        if not isinstance(image, str) or re.fullmatch(r"[^@\s]+@sha256:[0-9a-f]{64}", image) is None:
            raise ValueError("container.image must be pinned by sha256 digest")
        if image != _PHASE1_IMAGE:
            raise ValueError("container.image is not approved for phase 1")
        if platform != "linux/amd64":
            raise ValueError("container.platform must be linux/amd64")
        if not isinstance(cpu_limit, (int, float)) or isinstance(cpu_limit, bool) or cpu_limit <= 0:
            raise ValueError("container.cpu_limit must be positive")
        if not isinstance(memory_mb, int) or isinstance(memory_mb, bool) or memory_mb < 32:
            raise ValueError("container.memory_mb must be at least 32")
        if not isinstance(pids_limit, int) or isinstance(pids_limit, bool) or pids_limit < 8:
            raise ValueError("container.pids_limit must be at least 8")
        if network != "none":
            raise ValueError("container.network must be none")
        return cls(runtime, image, platform, float(cpu_limit), memory_mb, pids_limit, network)


@dataclass(frozen=True)
class TerminalTaskManifest:
    task: AgentTaskManifest
    scenario_id: str
    container: ContainerPolicy

    @classmethod
    def from_dict(cls, raw: Any) -> "TerminalTaskManifest":
        if not isinstance(raw, dict):
            raise ValueError("manifest must be an object")
        task = AgentTaskManifest.from_dict(raw)
        if task.scenario_type != "terminal-operation":
            raise ValueError("scenario_type must be terminal-operation")
        scenario_id = raw.get("scenario_id")
        if scenario_id not in SCENARIOS:
            raise ValueError(f"unsupported scenario_id: {scenario_id}")
        if task.preparation.strategy != "docker-terminal-v1" or task.verification.strategy != "docker-terminal-v1":
            raise ValueError("terminal tasks require docker-terminal-v1 lifecycle strategies")
        required = {"terminal", "filesystem", "local-process", "loopback-http"}
        if not required <= set(task.required_capabilities):
            raise ValueError("terminal task is missing required capabilities")
        return cls(task, scenario_id, ContainerPolicy.from_dict(raw.get("container")))


@dataclass(frozen=True)
class TerminalScenario:
    initial_files: dict[str, str]
    expected_files: dict[str, str]
    port: int
    response_file: str
    expected_response: str


SCENARIOS = {
    "http-banner": TerminalScenario(
        initial_files={
            "service.conf": "port=8080\nmessage=BROKEN\n",
            "www/index.html": "BROKEN\n",
        },
        expected_files={
            "service.conf": "port=8080\nmessage=READY\n",
            "www/index.html": "READY\n",
        },
        port=8080,
        response_file="www/index.html",
        expected_response="READY\n",
    ),
    "health-endpoint": TerminalScenario(
        initial_files={
            "app/settings.conf": "bind=127.0.0.1\nport=9090\nmode=maintenance\n",
            "site/health": "unhealthy\n",
        },
        expected_files={
            "app/settings.conf": "bind=127.0.0.1\nport=9090\nmode=active\n",
            "site/health": "healthy\n",
        },
        port=9090,
        response_file="site/health",
        expected_response="healthy\n",
    ),
}


def load_terminal_manifest(path: str | Path) -> TerminalTaskManifest:
    return TerminalTaskManifest.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _tree_digest(files: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative, content in sorted(files.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.encode("utf-8"))
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _failure_text(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stderr or result.stdout or "unknown error").strip().splitlines()[-1]


def runtime_skip_reason(
    command_runner: CommandRunner = _run_command,
    *,
    image: str | None = None,
) -> str | None:
    try:
        result = command_runner(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Docker runtime unavailable: {exc}"
    if result.returncode:
        return f"Docker runtime unavailable: {_failure_text(result)}"
    if image:
        try:
            present = command_runner(["docker", "image", "inspect", image], timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return f"Pinned Docker image unavailable: {exc}"
        if present.returncode:
            return f"Pinned Docker image unavailable: {image}"
    return None


@dataclass(frozen=True)
class DockerEnvironmentHandle(EnvironmentHandle):
    container_name: str


@dataclass(frozen=True)
class TerminalProcedureAgent:
    """Validated command data, never executable host-side candidate code."""

    commands: tuple[tuple[str, ...], ...]
    claimed_success: bool = True


class GoldTerminalAgent:
    """Deterministic offline reference procedure assembled verifier-side."""

    def __init__(self, scenario_id: str):
        if type(scenario_id) is not str or scenario_id not in SCENARIOS:
            raise ValueError("unsupported gold scenario")
        self.scenario_id = scenario_id

    def procedure(self) -> TerminalProcedureAgent:
        scenario = SCENARIOS[self.scenario_id]
        writes = []
        for relative, content in scenario.expected_files.items():
            writes.append(
                f"printf %s {shlex.quote(content)} > {shlex.quote('/workspace/' + relative)}"
            )
        service_root = "/workspace/" + str(Path(scenario.response_file).parent).replace("\\", "/")
        path = "/" if Path(scenario.response_file).name == "index.html" else f"/{Path(scenario.response_file).name}"
        return TerminalProcedureAgent(
            commands=(
                ("find", "/workspace", "-maxdepth", "3", "-type", "f", "-print"),
                ("sh", "-c", " && ".join(writes)),
                ("httpd", "-p", str(scenario.port), "-h", service_root),
                ("wget", "-qO-", f"http://127.0.0.1:{scenario.port}{path}"),
            )
        )


class DockerTerminalEnvironment:
    def __init__(
        self,
        manifest: TerminalTaskManifest,
        root: str | Path | None = None,
        *,
        command_runner: CommandRunner = _run_command,
    ):
        self.manifest = manifest
        self.scenario = SCENARIOS[manifest.scenario_id]
        self.root = Path(root) if root is not None else Path(tempfile.mkdtemp(prefix="mbt-root-"))
        self._owns_root = root is None
        self._runner = command_runner

    def _docker(self, *args: str, timeout: float = 15) -> subprocess.CompletedProcess[str]:
        return self._runner(["docker", *args], timeout=timeout)

    def _remove_container(self, name: str) -> None:
        try:
            self._docker("rm", "-f", name)
        except (OSError, subprocess.TimeoutExpired):
            pass

    def prepare(self, manifest: AgentTaskManifest, trial: int) -> PreparedEnvironment:
        if manifest.task_id != self.manifest.task.task_id:
            raise ValueError("environment and task manifests differ")
        reason = runtime_skip_reason(self._runner, image=self.manifest.container.image)
        if reason:
            raise RuntimeError(reason)
        workspace = self.root / f"{manifest.task_id}-trial-{trial}"
        name = f"minibench-{uuid.uuid4().hex[:12]}"
        try:
            workspace.mkdir(parents=True, exist_ok=False)
            for relative, content in self.scenario.initial_files.items():
                destination = workspace / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content, encoding="utf-8")
            if os.name != "nt":
                workspace.chmod(0o777)
                for directory in (path for path in workspace.rglob("*") if path.is_dir()):
                    directory.chmod(0o777)
                for file in (path for path in workspace.rglob("*") if path.is_file()):
                    file.chmod(0o666)
            digest = _tree_digest(self.scenario.initial_files)
            if digest != manifest.fixture.digest:
                raise RuntimeError("prepared fixture does not match its declared digest")
            policy = self.manifest.container
            result = self._docker(
                "run",
                "--detach",
                "--name",
                name,
                "--platform",
                policy.platform,
                "--network",
                policy.network,
                "--cpus",
                str(policy.cpu_limit),
                "--memory",
                f"{policy.memory_mb}m",
                "--pids-limit",
                str(policy.pids_limit),
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--read-only",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=8m",
                "--user",
                "65534:65534",
                "--workdir",
                "/workspace",
                "--mount",
                f"type=bind,src={workspace.resolve()},dst=/workspace",
                policy.image,
                "sleep",
                "600",
            )
            if result.returncode:
                raise RuntimeError(f"container preparation failed: {_failure_text(result)}")
            handle = DockerEnvironmentHandle(workspace, digest, name)
            return PreparedEnvironment(manifest.public_prompt, handle)
        except BaseException:
            self._remove_container(name)
            shutil.rmtree(workspace, ignore_errors=True)
            raise

    def execute(
        self,
        agent: TerminalProcedureAgent,
        handle: DockerEnvironmentHandle,
        prompt: str,
        budget: AgentBudget,
    ) -> AgentResult:
        if type(agent) is not TerminalProcedureAgent:
            raise TypeError("terminal agents must be declarative procedures")
        procedure = agent
        if (
            type(procedure.commands) is not tuple
            or len(procedure.commands) > budget.max_turns
            or type(procedure.claimed_success) is not bool
            or any(
                type(argv) is not tuple
                or not 1 <= len(argv) <= 32
                or any(
                    type(arg) is not str
                    or not arg
                    or len(arg) > 512
                    or "\0" in arg
                    for arg in argv
                )
                for argv in procedure.commands
            )
        ):
            raise ValueError("terminal procedure contains invalid or over-budget commands")
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe(duplex=True)
        process = context.Process(
            target=run_terminal_procedure,
            args=(child, procedure.commands, procedure.claimed_success),
            daemon=True,
        )
        deadline = time.monotonic() + budget.wall_time_seconds
        calls = 0
        started = False
        try:
            process.start()
            started = True
            child.close()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._remove_container(handle.container_name)
                    raise TimeoutError("terminal wall-time limit reached; container killed")
                if not parent.poll(min(remaining, 0.1)):
                    if not process.is_alive():
                        raise RuntimeError("terminal agent exited without a result")
                    continue
                try:
                    message = json.loads(parent.recv_bytes(RPC_LIMIT).decode("utf-8"))
                except (EOFError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise RuntimeError("invalid terminal agent protocol") from exc
                if not isinstance(message, dict) or not isinstance(message.get("kind"), str):
                    raise RuntimeError("invalid terminal agent protocol")
                if message["kind"] == "exec":
                    argv = message.get("argv")
                    calls += 1
                    if (
                        calls > budget.max_turns
                        or not isinstance(argv, list)
                        or not 1 <= len(argv) <= 32
                        or any(
                            not isinstance(arg, str)
                            or not arg
                            or len(arg) > 512
                            or "\0" in arg
                            for arg in argv
                        )
                    ):
                        raise RuntimeError("invalid or over-budget terminal request")
                    try:
                        result = self._runner(
                            ["docker", "exec", handle.container_name, *argv],
                            timeout=max(0.001, deadline - time.monotonic()),
                        )
                    except subprocess.TimeoutExpired as exc:
                        self._remove_container(handle.container_name)
                        raise TimeoutError("terminal command timed out; container killed") from exc
                    response = {
                        "kind": "exec_result",
                        "returncode": result.returncode,
                        "stdout": result.stdout[:_OUTPUT_LIMIT],
                        "stderr": result.stderr[:_OUTPUT_LIMIT],
                    }
                    parent.send_bytes(json.dumps(response, separators=(",", ":")).encode("utf-8"))
                    continue
                if message["kind"] == "timeout":
                    raise TimeoutError("terminal agent reported timeout")
                if message["kind"] == "error":
                    raise RuntimeError("terminal agent execution failed")
                if message["kind"] == "malformed":
                    return None
                if message["kind"] != "result" or not isinstance(message.get("result"), dict):
                    raise RuntimeError("invalid terminal agent protocol")
                return AgentResult(**message["result"])
        finally:
            parent.close()
            child.close()
            if started:
                process.join(timeout=0.2)
                if process.is_alive():
                    process.terminate()
                    process.join()

    def _is_running(self, handle: DockerEnvironmentHandle) -> bool:
        result = self._docker("inspect", "--format", "{{.State.Running}}", handle.container_name)
        return result.returncode == 0 and result.stdout.strip() == "true"

    def verify(self, handle: DockerEnvironmentHandle) -> VerificationResult:
        if not self._is_running(handle):
            return VerificationResult(False, "killed_process: service container is not running")

        top = self._docker("top", handle.container_name, "-eo", "comm,args")
        processes = []
        for line in top.stdout.splitlines():
            parts = line.strip().lower().split(maxsplit=1)
            if parts and parts[0] != "command":
                processes.append((parts[0], parts[1] if len(parts) == 2 else ""))
        service_root = "/workspace/" + str(Path(self.scenario.response_file).parent).replace("\\", "/")
        sleeper_count = sum(
            command == "sleep" and args in {"600", "sleep 600"}
            for command, args in processes
        )
        service_count = sum(
            command == "httpd"
            and f"-p {self.scenario.port}" in args
            and f"-h {service_root}" in args
            for command, args in processes
        )
        if (
            top.returncode
            or sleeper_count != 1
            or service_count not in {0, 1}
            or len(processes) != 1 + service_count
        ):
            return VerificationResult(False, "leaked_child_process: unexpected process remained after agent exit")

        current = {
            relative: (handle.workspace / relative).read_text(encoding="utf-8")
            for relative in self.scenario.initial_files
            if (handle.workspace / relative).is_file()
        }
        persistent_ok = current == self.scenario.expected_files
        unchanged = current == self.scenario.initial_files
        process = self._docker("exec", handle.container_name, "pidof", "httpd")
        response = self._docker(
            "exec",
            handle.container_name,
            "wget",
            "-qO-",
            f"http://127.0.0.1:{self.scenario.port}/"
            + ("" if Path(self.scenario.response_file).name == "index.html" else Path(self.scenario.response_file).name),
        )
        process_ok = process.returncode == 0
        response_ok = response.returncode == 0 and response.stdout == self.scenario.expected_response
        if persistent_ok and process_ok and response_ok:
            return VerificationResult(True, "success: durable files, process, and response verified after agent exit")
        if unchanged and not process_ok:
            return VerificationResult(False, "no_op: durable state and service were unchanged")
        if not persistent_ok and process_ok and response_ok:
            return VerificationResult(False, "transient_only: response changed without required durable configuration")
        return VerificationResult(False, "partial_configuration: durable files, process, or response is incomplete")

    def dispose(self, handle: DockerEnvironmentHandle | None) -> None:
        if handle is not None:
            self._remove_container(handle.container_name)
            shutil.rmtree(handle.workspace, ignore_errors=True)
        if self._owns_root:
            shutil.rmtree(self.root, ignore_errors=True)

    def is_disposed(self, handle: DockerEnvironmentHandle | None) -> bool:
        if handle is None:
            return not self._owns_root or not self.root.exists()
        try:
            absent = self._docker("inspect", handle.container_name).returncode != 0
        except (OSError, subprocess.TimeoutExpired):
            absent = False
        return absent and not handle.workspace.exists() and (
            not self._owns_root or not self.root.exists()
        )


def build_terminal_artifact(
    manifest: TerminalTaskManifest,
    trials: list[AgentTrialResult],
) -> dict[str, Any]:
    artifact = build_agent_artifact(manifest.task, trials)
    artifact["provenance"].update(
        {
            "harness": HARNESS,
            "scenario_id": manifest.scenario_id,
            "container": asdict(manifest.container),
        }
    )
    return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run offline terminal-operation smoke tasks")
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    manifests = [load_terminal_manifest(path) for path in args.manifest]
    for manifest in manifests:
        reason = runtime_skip_reason(image=manifest.container.image)
        if reason:
            print(f"SKIP: {reason}")
            return 0
    trials = []
    for number, manifest in enumerate(manifests, 1):
        trials.append(
            run_agent_trial(
                manifest.task,
                DockerTerminalEnvironment(manifest),
                GoldTerminalAgent(manifest.scenario_id).procedure(),
                trial=number,
            )
        )
    artifacts = [build_terminal_artifact(manifest, [trial]) for manifest, trial in zip(manifests, trials)]
    payload = {
        "harness": HARNESS,
        "artifacts": artifacts,
        "all_passed": all(trial.passed and trial.workspace_disposed for trial in trials),
    }
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "all_passed": payload["all_passed"],
                "tasks": [
                    {
                        "task_id": trial.task_id,
                        "outcome": trial.outcome,
                        "detail": trial.detail[:500],
                        "workspace_disposed": trial.workspace_disposed,
                    }
                    for trial in trials
                ],
            }
        )
    )
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
