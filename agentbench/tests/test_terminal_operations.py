import json
import subprocess
import time
from dataclasses import replace
from pathlib import Path

import pytest

from agentbench.agent_tasks import run_agent_trial
from agentbench.terminal_operations import (
    build_terminal_artifact,
    GoldTerminalAgent,
    DockerTerminalEnvironment,
    load_terminal_manifest,
    runtime_skip_reason,
    TerminalTaskManifest,
    TerminalProcedureAgent,
    _run_command,
)


TASKS = Path(__file__).resolve().parents[1] / "tasks"
MANIFESTS = sorted(TASKS.glob("minibench-terminal-*.json"))
HTTP_MANIFEST = next(path for path in MANIFESTS if "http-banner" in path.name)


class FakeDocker:
    def __init__(self):
        self.calls = []
        self.running = True
        self.service_running = False
        self.leaked = False
        self.httpd_args = ""
        self.workspace = None

    def __call__(self, argv, *, timeout=None):
        self.calls.append((tuple(argv), timeout))
        action = argv[1]
        if action == "info":
            return subprocess.CompletedProcess(argv, 0, "fake-docker\n", "")
        if action == "image":
            return subprocess.CompletedProcess(argv, 0, "present\n", "")
        if action == "run":
            mount = argv[argv.index("--mount") + 1]
            source = mount.split("src=", 1)[1].split(",dst=", 1)[0]
            self.workspace = Path(source)
            self.running = True
            return subprocess.CompletedProcess(argv, 0, "container-id\n", "")
        if action == "inspect":
            return subprocess.CompletedProcess(argv, 0 if self.running else 1, "true\n" if self.running else "", "")
        if action == "top":
            raise AssertionError("verify uses container ps, not docker top")
        if action == "exec":
            command = argv[3:]
            if command == ["ps", "-o", "comm,args"]:
                processes = "COMMAND COMMAND\nsleep sleep 600\n"
                if self.service_running:
                    processes += f"httpd {self.httpd_args}\n"
                if self.leaked:
                    processes += "sleep sleep 600\n"
                return subprocess.CompletedProcess(argv, 0, processes, "")
            if command[:2] == ["pidof", "httpd"]:
                return subprocess.CompletedProcess(argv, 0 if self.service_running else 1, "2\n" if self.service_running else "", "")
            if command and command[0] == "wget":
                port = command[-1].split(":")[-1].split("/")[0]
                target = self.workspace / ("www/index.html" if port == "8080" else "site/health")
                return subprocess.CompletedProcess(argv, 0 if self.service_running else 1, target.read_text() if self.service_running else "", "")
            if command and command[0] == "httpd":
                self.service_running = True
                self.httpd_args = " ".join(command)
            if command[:2] == ["sh", "-c"]:
                script = command[2]
                if "/workspace/service.conf" in script:
                    (self.workspace / "service.conf").write_text(
                        "port=8080\nmessage=READY\n", encoding="utf-8"
                    )
                if "/workspace/www/index.html" in script:
                    (self.workspace / "www/index.html").write_text("READY\n", encoding="utf-8")
                if "/workspace/app/settings.conf" in script:
                    (self.workspace / "app/settings.conf").write_text(
                        "bind=127.0.0.1\nport=9090\nmode=active\n", encoding="utf-8"
                    )
                if "/workspace/site/health" in script:
                    (self.workspace / "site/health").write_text("healthy\n", encoding="utf-8")
                if "sleep 600 &" in script:
                    self.leaked = True
                if "kill 1" in script:
                    self.running = False
            return subprocess.CompletedProcess(argv, 0, "", "")
        if action in {"kill", "rm"}:
            self.running = False
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(argv)


class TimingOutDocker(FakeDocker):
    def __call__(self, argv, *, timeout=None):
        if len(argv) > 3 and argv[1] == "exec" and argv[3] == "slow-command":
            raise subprocess.TimeoutExpired(argv, timeout)
        return super().__call__(argv, timeout=timeout)


class SlowDocker(FakeDocker):
    def __call__(self, argv, *, timeout=None):
        if len(argv) > 3 and argv[1] == "exec":
            time.sleep(0.6)
        return super().__call__(argv, timeout=timeout)


def state_agent(mode):
    commands = []
    if mode in {"gold", "partial"}:
        commands.append(
            (
                "sh",
                "-c",
                "printf READY > /workspace/www/index.html && printf READY > /workspace/service.conf",
            )
        )
    if mode in {"gold", "transient", "leak"}:
        commands.append(("httpd", "-p", "8080", "-h", "/workspace/www"))
    if mode == "transient":
        commands.append(("sh", "-c", "printf READY > /workspace/www/index.html"))
    if mode == "leak":
        commands.append(("sh", "-c", "sleep 600 &"))
    if mode == "killed":
        commands.append(("sh", "-c", "kill 1"))
    return TerminalProcedureAgent(tuple(commands))


class HostProbeAgent:
    def __init__(self, marker):
        self.marker = marker

    def execute(self, prompt, terminal, budget):
        self.marker.write_text("host code ran", encoding="utf-8")


def overridden_gold_agent(marker):
    agent = GoldTerminalAgent("http-banner")
    agent.procedure = lambda: marker.write_text("callback ran", encoding="utf-8")
    return agent


def test_terminal_manifests_declare_immutable_isolation_contracts():
    assert len(MANIFESTS) == 2

    loaded = [load_terminal_manifest(path) for path in MANIFESTS]

    assert len({item.task.task_id for item in loaded}) == 2
    for item in loaded:
        assert "@sha256:" in item.container.image
        assert item.container.platform == "linux/amd64"
        assert item.container.network == "none"
        assert item.container.cpu_limit > 0
        assert item.container.memory_mb >= 32
        assert item.container.pids_limit >= 8
        assert item.task.budget.wall_time_seconds > 0
        assert {"terminal", "filesystem", "local-process", "loopback-http"} <= set(item.task.required_capabilities)


@pytest.mark.parametrize(
    "image",
    [
        "busybox@sha256:abc",
        "busybox@sha256:" + "g" * 64,
        "busybox@sha256:" + "a" * 64 + "trailing",
    ],
)
def test_terminal_manifest_rejects_malformed_image_digest_before_runtime_probe(image):
    raw = json.loads(HTTP_MANIFEST.read_text(encoding="utf-8"))
    raw["container"]["image"] = image

    with pytest.raises(ValueError, match="pinned by sha256"):
        TerminalTaskManifest.from_dict(raw)


@pytest.mark.parametrize(
    "image",
    [
        "example.invalid/busybox@sha256:3c6ae8008e2c2eedd141725c30b20d9c36b026eb796688f88205845ef17aa213",
        "busybox@sha256:" + "b" * 64,
    ],
)
def test_terminal_manifest_rejects_unapproved_valid_image_reference(image):
    raw = json.loads(HTTP_MANIFEST.read_text(encoding="utf-8"))
    raw["container"]["image"] = image

    with pytest.raises(ValueError, match="not approved for phase 1"):
        TerminalTaskManifest.from_dict(raw)


def test_pinned_phase1_image_contains_required_busybox_binaries():
    """Regression: the approved image must natively supply httpd and wget under read-only/nonroot constraints."""
    from agentbench.terminal_operations import _PHASE1_IMAGE
    reason = runtime_skip_reason(image=_PHASE1_IMAGE)
    if reason:
        pytest.skip(reason)
    # httpd is the service binary the scenarios depend on
    httpd = _run_command(["docker", "run", "--rm", "--platform", "linux/amd64", _PHASE1_IMAGE, "httpd", "-v"])
    assert httpd.returncode == 0, "httpd binary missing from approved image"
    # wget fetches the loopback verification response
    wget = _run_command(["docker", "run", "--rm", "--platform", "linux/amd64", _PHASE1_IMAGE, "wget", "--help"])
    assert wget.returncode == 0, "wget binary missing from approved image"


@pytest.mark.parametrize(
    "mode, expected",
    [
        ("gold", "success"),
        ("noop", "no_op"),
        ("transient", "transient_only"),
        ("partial", "partial_configuration"),
        ("killed", "killed_process"),
        ("leak", "leaked_child_process"),
    ],
)
def test_hidden_verifier_classifies_durable_state_and_always_cleans(tmp_path, mode, expected):
    loaded = load_terminal_manifest(HTTP_MANIFEST)
    docker = FakeDocker()
    environment = DockerTerminalEnvironment(loaded, root=tmp_path, command_runner=docker)

    trial = run_agent_trial(loaded.task, environment, state_agent(mode), trial=1)

    assert trial.outcome == ("success" if mode == "gold" else "verification_failed")
    assert expected in trial.detail
    assert trial.agent_claimed_success is True
    assert trial.workspace_disposed is True
    assert list(tmp_path.iterdir()) == []


def test_timed_out_terminal_command_kills_container_and_reports_cleanup(tmp_path):
    loaded = load_terminal_manifest(HTTP_MANIFEST)
    docker = TimingOutDocker()

    trial = run_agent_trial(
        loaded.task,
        DockerTerminalEnvironment(loaded, root=tmp_path, command_runner=docker),
        TerminalProcedureAgent((("slow-command",),)),
        trial=1,
    )

    assert trial.outcome == "timeout"
    assert "resource budget" in trial.detail
    assert trial.workspace_disposed is True
    assert list(tmp_path.iterdir()) == []


def test_wall_time_covers_the_complete_multi_command_procedure(tmp_path):
    loaded = load_terminal_manifest(HTTP_MANIFEST)
    loaded = replace(loaded, task=replace(loaded.task, budget=replace(loaded.task.budget, wall_time_seconds=1)))
    started = time.monotonic()

    trial = run_agent_trial(
        loaded.task,
        DockerTerminalEnvironment(loaded, root=tmp_path, command_runner=SlowDocker()),
        TerminalProcedureAgent((("true",), ("true",))),
        trial=1,
    )

    assert trial.outcome == "timeout"
    assert time.monotonic() - started < 1.8
    assert trial.workspace_disposed is True


def test_arbitrary_host_python_adapter_is_rejected_without_execution(tmp_path):
    loaded = load_terminal_manifest(HTTP_MANIFEST)
    marker = tmp_path / "host-probe"

    trial = run_agent_trial(
        loaded.task,
        DockerTerminalEnvironment(loaded, root=tmp_path, command_runner=FakeDocker()),
        HostProbeAgent(marker),
        trial=1,
    )

    assert trial.outcome == "execution_failed"
    assert not marker.exists()
    assert trial.workspace_disposed is True


def test_gold_callback_override_is_rejected_without_execution(tmp_path):
    loaded = load_terminal_manifest(HTTP_MANIFEST)
    marker = tmp_path / "gold-callback"

    trial = run_agent_trial(
        loaded.task,
        DockerTerminalEnvironment(loaded, root=tmp_path, command_runner=FakeDocker()),
        overridden_gold_agent(marker),
        trial=1,
    )

    assert trial.outcome == "execution_failed"
    assert not marker.exists()
    assert trial.workspace_disposed is True


def test_container_launch_enforces_declared_limits_and_default_denied_network(tmp_path):
    loaded = load_terminal_manifest(HTTP_MANIFEST)
    docker = FakeDocker()

    trial = run_agent_trial(
        loaded.task,
        DockerTerminalEnvironment(loaded, root=tmp_path, command_runner=docker),
        state_agent("noop"),
        trial=1,
    )

    launch = next(argv for argv, _ in docker.calls if argv[1] == "run")
    assert launch[launch.index("--network") + 1] == "none"
    assert launch[launch.index("--cpus") + 1] == str(loaded.container.cpu_limit)
    assert launch[launch.index("--memory") + 1] == f"{loaded.container.memory_mb}m"
    assert launch[launch.index("--pids-limit") + 1] == str(loaded.container.pids_limit)
    assert "--read-only" in launch
    assert ("--cap-drop", "ALL") == (launch[launch.index("--cap-drop")], launch[launch.index("--cap-drop") + 1])
    assert trial.workspace_disposed is True


def test_terminal_artifact_uses_shared_shape_and_records_policy(tmp_path):
    loaded = load_terminal_manifest(MANIFESTS[1])
    trial = run_agent_trial(
        loaded.task,
        DockerTerminalEnvironment(loaded, root=tmp_path / "work", command_runner=FakeDocker()),
        GoldTerminalAgent(loaded.scenario_id).procedure(),
        trial=1,
    )

    artifact = build_terminal_artifact(loaded, [trial])

    assert artifact["summary"]["evaluation_type"] == "agent_harness"
    assert artifact["provenance"]["harness"] == "agent-cabinet-terminal-operation"
    assert artifact["provenance"]["container"]["network"] == "none"
    assert artifact["provenance"]["container"]["image"] == loaded.container.image


def test_runtime_skip_reason_is_explicit_when_docker_daemon_is_unavailable():
    def unavailable(argv, *, timeout=None):
        return subprocess.CompletedProcess(argv, 1, "", "daemon unavailable")

    reason = runtime_skip_reason(unavailable)

    assert reason == "Docker runtime unavailable: daemon unavailable"


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda path: path.stem)
def test_real_container_gold_smoke_or_explicit_skip(tmp_path, path):
    loaded = load_terminal_manifest(path)
    reason = runtime_skip_reason(image=loaded.container.image)
    if reason:
        pytest.skip(reason)
    environment = DockerTerminalEnvironment(loaded, root=tmp_path)
    trial = run_agent_trial(
        loaded.task,
        environment,
        GoldTerminalAgent(loaded.scenario_id).procedure(),
        trial=1,
    )

    assert trial.outcome == "success"
    assert trial.workspace_disposed is True
