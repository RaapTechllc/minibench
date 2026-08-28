"""Offline, seeded feature-implementation tasks for the Agent Cabinet harness.

Each fixture is a small working repository. The public prompt asks for a
bounded cross-file behavior change; gold patches, hidden probes, and oracle
inputs stay in private fixture state. This family is separate from repository
repair, data/SQL repair, and terminal operations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import shutil
import subprocess
import sys
import tempfile
import threading
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from agentbench.agent_tasks import (
    AGENT_GRADER_VERSION,
    AgentAdapter,
    AgentBudget,
    AgentBudgetGuard,
    AgentResult,
    AgentTaskManifest,
    EnvironmentHandle,
    PreparedEnvironment,
    TaskEnvironment,
    VerificationResult,
    build_agent_artifact,
    execute_agent_with_budget,
    run_agent_trial,
)


FIXTURE_VERSION = "generated-feature-implementation@1"
HARNESS = "agent-cabinet-generated-feature"
SUITE = "minibench-agent-generated-feature-v1"
CATEGORY = "feature-implementation"
SCENARIO_TYPE = "generated-feature-implementation"
NETWORK_POLICY = "denied"
REQUIRED_CAPABILITIES = ("filesystem", "code-editing")
_BUDGET = AgentBudget(max_turns=3, wall_time_seconds=5, max_tokens=300, max_cost_usd=0.0)
_IGNORED_RUNTIME_PATH_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
_PRIVATE_PROBE_TIMEOUT_SECONDS = 1
_PRIVATE_PROBE_LIMIT = 4096
_PRIVATE_PROBE_WRAPPER_SECONDS = 4
_CANDIDATE_PROBE_PROGRAM = r"""
import json
import sys

def _run(payload):
    workspace = payload["workspace"]
    kind = payload["kind"]
    sys.path.insert(0, workspace)
    outputs = []
    if kind == "promo-receipt":
        from app.catalog import get_price
        from app.cart import Cart
        from app.checkout import checkout
        outputs.append(get_price(payload["sku_a"]))
        outputs.append(get_price(payload["sku_b"]))
        outputs.append(checkout(payload["items"]))
        cart = Cart()
        for sku, quantity in payload["items"]:
            cart.add(sku, quantity)
        outputs.append(cart.subtotal())
        outputs.append(cart.promotion_savings(payload["promo"]))
        outputs.append(checkout(payload["items"], payload["promo"]))
        alt = Cart()
        for sku, quantity in payload["alt_items"]:
            alt.add(sku, quantity)
        outputs.append(alt.promotion_savings(payload["alt_promo"]))
        outputs.append(checkout(payload["alt_items"], payload["alt_promo"]))
    elif kind == "tagged-search":
        from app.notes import Notebook
        from app.search import find
        from app.export import dump
        notebook = Notebook()
        ids = [notebook.add(title, body, tags) for title, body, tags in payload["notes"]]
        outputs.append(ids)
        outputs.append(find(notebook, payload["tag_query"]))
        outputs.append(find(notebook, payload["title_query"]))
        outputs.append(notebook.tags_for(ids[payload["tagged_index"]]))
        outputs.append(dump(notebook))
    elif kind == "quota-guard":
        from app.clients import count, remaining
        from app.handler import serve
        from app.status import health
        outputs.append(health())
        outputs.append(remaining(payload["fresh"]))
        outputs.append(count(payload["fresh"]))
        sequence = [serve(payload["client_a"]) for _ in range(payload["calls"])]
        outputs.append(sequence)
        outputs.append(remaining(payload["client_a"]))
        outputs.append(serve(payload["client_b"]))
        outputs.append(health())
    else:
        raise ValueError("unsupported probe")
    sys.stdout.buffer.write(json.dumps({"completed": True, "outputs": outputs}, separators=(",", ":")).encode())

if __name__ == "__main__":
    payload = json.loads(sys.stdin.buffer.read())
    sys.stdin.close()
    _run(payload)
"""


@dataclass(frozen=True)
class FeatureTemplate:
    name: str
    family: str
    network_policy: str
    capabilities: tuple[str, ...]
    build: Callable[[int], "GeneratedFeatureFixture"]


@dataclass(frozen=True)
class GeneratedFeatureFixture:
    seed: int
    template: FeatureTemplate
    baseline_files: dict[str, str]
    gold_files: dict[str, str]
    mutable_paths: tuple[str, ...]
    prompt: str
    oracle: dict[str, Any]

    @property
    def seed_hash(self) -> str:
        return hashlib.sha256(str(self.seed).encode()).hexdigest()

    @property
    def template_hash(self) -> str:
        return hashlib.sha256(self.template.name.encode()).hexdigest()

    def public_snapshot(self) -> bytes:
        payload = {
            "version": FIXTURE_VERSION,
            "files": self.baseline_files,
            "prompt": self.prompt,
            "network_policy": self.template.network_policy,
            "capabilities": list(self.template.capabilities),
            "budget": {
                "max_turns": _BUDGET.max_turns,
                "wall_time_seconds": _BUDGET.wall_time_seconds,
                "max_tokens": _BUDGET.max_tokens,
                "max_cost_usd": _BUDGET.max_cost_usd,
            },
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    def gold_snapshot(self) -> bytes:
        payload = {"version": FIXTURE_VERSION, "files": self.gold_files}
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _token(seed: int, label: str, size: int = 8) -> str:
    return hashlib.sha256(f"{seed}:{label}".encode()).hexdigest()[:size]


def _variant(seed: int, label: str) -> int:
    return int(_token(seed, label, 8), 16)


def _project_files(marker: str, extra: dict[str, str]) -> dict[str, str]:
    files = {
        "pyproject.toml": "[project]\nname = 'cabinet-shop'\n",
        "app/__init__.py": "",
        "app/build.py": f"BUILD = '{marker}'\n",
    }
    files.update(extra)
    return files


def _promo_receipt(seed: int) -> GeneratedFeatureFixture:
    marker = _token(seed, "promo-build")
    sku_a = f"item-{_token(seed, 'sku-a', 6)}"
    sku_b = f"part-{_token(seed, 'sku-b', 6)}"
    price_a = 320 + _variant(seed, "price-a") % 180
    price_b = 180 + _variant(seed, "price-b") % 120
    promo = 10 + _variant(seed, "promo") % 16
    alt_promo = 25
    prompt = (
        "When a promotion percent is provided, the printed bill must list the original "
        "subtotal, the promotion savings, and the reduced amount due. A purchase without "
        "a promotion must look and total the same as it does today, and catalog prices "
        "must stay the same."
    )
    catalog = (
        f"PRICES = {{\n    '{sku_a}': {price_a},\n    '{sku_b}': {price_b},\n}}\n\n"
        "def get_price(sku):\n    return PRICES[sku]\n"
    )
    cart = (
        "from app.catalog import get_price\n\n"
        "class Cart:\n"
        "    def __init__(self):\n"
        "        self._lines = []\n\n"
        "    def add(self, sku, quantity):\n"
        "        self._lines.append((sku, quantity, get_price(sku)))\n\n"
        "    def lines(self):\n"
        "        return list(self._lines)\n\n"
        "    def subtotal(self):\n"
        "        return sum(price * quantity for _, quantity, price in self._lines)\n\n"
        "    def promotion_savings(self, percent):\n"
        "        return 0\n"
    )
    gold_cart = cart.replace(
        "    def promotion_savings(self, percent):\n        return 0\n",
        "    def promotion_savings(self, percent):\n"
        "        if percent is None:\n"
        "            return 0\n"
        "        return self.subtotal() * percent // 100\n",
    )
    receipt = (
        "def render(cart, promotion=None):\n"
        "    rows = [f'{sku} x{quantity} @ {price}' for sku, quantity, price in cart.lines()]\n"
        "    rows.append(f'subtotal {cart.subtotal()}')\n"
        "    rows.append(f'due {cart.subtotal()}')\n"
        "    return '\\n'.join(rows) + '\\n'\n"
    )
    gold_receipt = (
        "def render(cart, promotion=None):\n"
        "    rows = [f'{sku} x{quantity} @ {price}' for sku, quantity, price in cart.lines()]\n"
        "    subtotal = cart.subtotal()\n"
        "    rows.append(f'subtotal {subtotal}')\n"
        "    if promotion is None:\n"
        "        rows.append(f'due {subtotal}')\n"
        "    else:\n"
        "        savings = cart.promotion_savings(promotion)\n"
        "        rows.append(f'savings {savings}')\n"
        "        rows.append(f'due {subtotal - savings}')\n"
        "    return '\\n'.join(rows) + '\\n'\n"
    )
    checkout = (
        "from app.cart import Cart\n"
        "from app.receipt import render\n\n"
        "def checkout(items, promotion=None):\n"
        "    cart = Cart()\n"
        "    for sku, quantity in items:\n"
        "        cart.add(sku, quantity)\n"
        "    return render(cart, promotion)\n"
    )
    baseline = _project_files(
        marker,
        {
            "app/catalog.py": catalog,
            "app/cart.py": cart,
            "app/receipt.py": receipt,
            "app/checkout.py": checkout,
        },
    )
    gold = {**baseline, "app/cart.py": gold_cart, "app/receipt.py": gold_receipt}
    items = ((sku_a, 2), (sku_b, 1))
    alt_items = ((sku_b, 3),)
    subtotal = price_a * 2 + price_b
    alt_subtotal = price_b * 3
    item_lines = [f"{sku} x{quantity} @ {price}" for sku, quantity, price in ((sku_a, 2, price_a), (sku_b, 1, price_b))]
    alt_lines = [f"{sku_b} x3 @ {price_b}"]
    plain = "\n".join([*item_lines, f"subtotal {subtotal}", f"due {subtotal}"]) + "\n"
    return GeneratedFeatureFixture(
        seed,
        TEMPLATES[0],
        baseline,
        gold,
        ("app/cart.py", "app/receipt.py"),
        prompt,
        {
            "kind": "promo-receipt",
            "sku_a": sku_a,
            "sku_b": sku_b,
            "items": [list(item) for item in items],
            "alt_items": [list(item) for item in alt_items],
            "promo": promo,
            "alt_promo": alt_promo,
            "price_a": price_a,
            "price_b": price_b,
            "subtotal": subtotal,
            "alt_subtotal": alt_subtotal,
            "plain_receipt": plain,
            "item_lines": item_lines,
            "alt_lines": alt_lines,
            "savings": subtotal * promo // 100,
            "alt_savings": alt_subtotal * alt_promo // 100,
        },
    )


def _tagged_search(seed: int) -> GeneratedFeatureFixture:
    marker = _token(seed, "search-build")
    label = f"mark-{_token(seed, 'label', 6)}"
    title_word = f"topic-{_token(seed, 'title', 6)}"
    other = f"other-{_token(seed, 'other', 6)}"
    skipped = f"skip-{_token(seed, 'skip', 6)}"
    prompt = (
        "Lookup should also return records that carry a requested label even when that "
        "label is absent from the title. Title matches and exported record contents must "
        "stay the same."
    )
    notes = (
        "class Notebook:\n"
        "    def __init__(self):\n"
        "        self._notes = []\n\n"
        "    def add(self, title, body, tags=None):\n"
        "        note = {\n"
        "            'id': len(self._notes) + 1,\n"
        "            'title': title,\n"
        "            'body': body,\n"
        "            'tags': list(tags or []),\n"
        "        }\n"
        "        self._notes.append(note)\n"
        "        return note['id']\n\n"
        "    def get(self, note_id):\n"
        "        note = self._notes[note_id - 1]\n"
        "        return {'id': note['id'], 'title': note['title'], 'body': note['body']}\n\n"
        "    def all(self):\n"
        "        return [self.get(note['id']) for note in self._notes]\n\n"
        "    def tags_for(self, note_id):\n"
        "        return []\n"
    )
    gold_notes = notes.replace(
        "    def tags_for(self, note_id):\n        return []\n",
        "    def tags_for(self, note_id):\n"
        "        if note_id < 1 or note_id > len(self._notes):\n"
        "            return []\n"
        "        return list(self._notes[note_id - 1]['tags'])\n",
    )
    search = (
        "def find(notebook, query):\n"
        "    return [note['id'] for note in notebook.all() if query in note['title']]\n"
    )
    gold_search = (
        "def find(notebook, query):\n"
        "    matches = []\n"
        "    for note in notebook.all():\n"
        "        if query in note['title'] or query in notebook.tags_for(note['id']):\n"
        "            matches.append(note['id'])\n"
        "    return matches\n"
    )
    export = "def dump(notebook):\n    return notebook.all()\n"
    baseline = _project_files(
        marker,
        {"app/notes.py": notes, "app/search.py": search, "app/export.py": export},
    )
    gold = {**baseline, "app/notes.py": gold_notes, "app/search.py": gold_search}
    sample_notes = (
        (other, "body-a", []),
        (f"quiet {marker[:4]}", "body-b", [label]),
        (skipped, "body-c", [f"alt-{_token(seed, 'alt', 6)}"]),
        (f"{title_word} memo", "body-d", []),
    )
    exported = [
        {"id": index, "title": title, "body": body}
        for index, (title, body, _) in enumerate(sample_notes, start=1)
    ]
    return GeneratedFeatureFixture(
        seed,
        TEMPLATES[1],
        baseline,
        gold,
        ("app/notes.py", "app/search.py"),
        prompt,
        {
            "kind": "tagged-search",
            "notes": [list(note[:2]) + [list(note[2])] for note in sample_notes],
            "tag_query": label,
            "title_query": title_word,
            "tagged_index": 1,
            "ids": [1, 2, 3, 4],
            "tag_hits": [2],
            "title_hits": [4],
            "tags": [label],
            "exported": exported,
        },
    )


def _quota_guard(seed: int) -> GeneratedFeatureFixture:
    marker = _token(seed, "quota-build")
    allowance = 2 + _variant(seed, "allowance") % 3
    client_a = f"user-{_token(seed, 'client-a', 6)}"
    client_b = f"peer-{_token(seed, 'client-b', 6)}"
    fresh = f"idle-{_token(seed, 'fresh', 6)}"
    prompt = (
        "Each client may make only the configured number of successful requests. Further "
        "requests from that client must be refused, successful replies must include how "
        "many allowed requests remain, and other clients plus the health check must stay "
        "unaffected."
    )
    limits = f"ALLOWANCE = {allowance}\n"
    clients = (
        "from app.limits import ALLOWANCE\n\n"
        "_counts = {}\n\n"
        "def count(client_id):\n"
        "    return _counts.get(client_id, 0)\n\n"
        "def tick(client_id):\n"
        "    _counts[client_id] = count(client_id) + 1\n"
        "    return _counts[client_id]\n\n"
        "def remaining(client_id):\n"
        "    return ALLOWANCE\n"
    )
    gold_clients = clients.replace(
        "def remaining(client_id):\n    return ALLOWANCE\n",
        "def remaining(client_id):\n"
        "    left = ALLOWANCE - count(client_id)\n"
        "    return left if left > 0 else 0\n",
    )
    handler = "def serve(client_id):\n    return {'ok': True, 'client': client_id}\n"
    gold_handler = (
        "from app.clients import remaining, tick\n\n"
        "def serve(client_id):\n"
        "    if remaining(client_id) <= 0:\n"
        "        return {'ok': False, 'client': client_id, 'remaining': 0}\n"
        "    tick(client_id)\n"
        "    return {'ok': True, 'client': client_id, 'remaining': remaining(client_id)}\n"
    )
    status = "def health():\n    return {'ok': True, 'service': 'ready'}\n"
    baseline = _project_files(
        marker,
        {
            "app/limits.py": limits,
            "app/clients.py": clients,
            "app/handler.py": handler,
            "app/status.py": status,
        },
    )
    gold = {**baseline, "app/clients.py": gold_clients, "app/handler.py": gold_handler}
    return GeneratedFeatureFixture(
        seed,
        TEMPLATES[2],
        baseline,
        gold,
        ("app/clients.py", "app/handler.py"),
        prompt,
        {
            "kind": "quota-guard",
            "allowance": allowance,
            "client_a": client_a,
            "client_b": client_b,
            "fresh": fresh,
            "calls": allowance + 1,
            "health": {"ok": True, "service": "ready"},
        },
    )


TEMPLATES = (
    FeatureTemplate("promo-receipt", "checkout-promotion", NETWORK_POLICY, REQUIRED_CAPABILITIES, _promo_receipt),
    FeatureTemplate("tagged-search", "label-lookup", NETWORK_POLICY, REQUIRED_CAPABILITIES, _tagged_search),
    FeatureTemplate("quota-guard", "client-allowance", NETWORK_POLICY, REQUIRED_CAPABILITIES, _quota_guard),
)


def generate_fixture(seed: int, *, fixture_version: str = FIXTURE_VERSION) -> GeneratedFeatureFixture:
    if fixture_version != FIXTURE_VERSION:
        raise ValueError(f"unsupported fixture version: {fixture_version}")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    return TEMPLATES[seed % len(TEMPLATES)].build(seed)


def manifest_for(fixture: GeneratedFeatureFixture) -> AgentTaskManifest:
    digest = "sha256:" + hashlib.sha256(fixture.public_snapshot()).hexdigest()
    return AgentTaskManifest.from_dict(
        {
            "manifest_version": "1",
            "suite": SUITE,
            "task_id": f"mba-feature-{fixture.seed_hash[:16]}",
            "category": CATEGORY,
            "scenario_type": SCENARIO_TYPE,
            "fixture": {"reference": FIXTURE_VERSION, "digest": digest},
            "public_prompt": fixture.prompt,
            "preparation": {"strategy": FIXTURE_VERSION},
            "verification": {"strategy": FIXTURE_VERSION},
            "required_capabilities": list(fixture.template.capabilities),
            "budget": {
                "max_turns": _BUDGET.max_turns,
                "wall_time_seconds": _BUDGET.wall_time_seconds,
                "max_tokens": _BUDGET.max_tokens,
                "max_cost_usd": _BUDGET.max_cost_usd,
            },
            "private": True,
        }
    )


def _is_runtime_artifact(path: Path) -> bool:
    return any(part in _IGNORED_RUNTIME_PATH_PARTS for part in path.parts)


def _promo_receipt_matches(text: Any, item_lines: list[str], subtotal: int, percent: int) -> bool:
    if not isinstance(text, str):
        return False
    savings = subtotal * percent // 100
    due = subtotal - savings
    lines = text.strip("\n").split("\n")
    if lines[: len(item_lines)] != item_lines:
        return False
    footer = lines[len(item_lines) :]
    if f"subtotal {subtotal}" not in footer or f"savings {savings}" not in footer or f"due {due}" not in footer:
        return False
    return due == subtotal or f"due {subtotal}" not in footer


def _outputs_match(kind: str, outputs: Any, spec: dict[str, Any]) -> bool:
    if not isinstance(outputs, list):
        return False
    if kind == "promo-receipt":
        if len(outputs) != 8:
            return False
        return (
            outputs[0] == spec["price_a"]
            and outputs[1] == spec["price_b"]
            and outputs[2] == spec["plain_receipt"]
            and outputs[3] == spec["subtotal"]
            and outputs[4] == spec["savings"]
            and _promo_receipt_matches(outputs[5], spec["item_lines"], spec["subtotal"], spec["promo"])
            and outputs[6] == spec["alt_savings"]
            and _promo_receipt_matches(outputs[7], spec["alt_lines"], spec["alt_subtotal"], spec["alt_promo"])
        )
    if kind == "tagged-search":
        return (
            len(outputs) == 5
            and outputs[0] == spec["ids"]
            and outputs[1] == spec["tag_hits"]
            and outputs[2] == spec["title_hits"]
            and outputs[3] == spec["tags"]
            and outputs[4] == spec["exported"]
        )
    if kind != "quota-guard" or len(outputs) != 7:
        return False
    allowance = spec["allowance"]
    client_a = spec["client_a"]
    expected_sequence = [
        {"ok": True, "client": client_a, "remaining": allowance - index - 1}
        for index in range(allowance)
    ]
    expected_sequence.append({"ok": False, "client": client_a, "remaining": 0})
    return (
        outputs[0] == spec["health"]
        and outputs[1] == allowance
        and outputs[2] == 0
        and outputs[3] == expected_sequence
        and outputs[4] == 0
        and outputs[5] == {"ok": True, "client": spec["client_b"], "remaining": allowance - 1}
        and outputs[6] == spec["health"]
    )


def _probe_request(fixture: GeneratedFeatureFixture, workspace: Path) -> dict[str, Any]:
    oracle = fixture.oracle
    if oracle["kind"] == "promo-receipt":
        return {
            "workspace": str(workspace),
            "kind": "promo-receipt",
            "sku_a": oracle["sku_a"],
            "sku_b": oracle["sku_b"],
            "items": oracle["items"],
            "alt_items": oracle["alt_items"],
            "promo": oracle["promo"],
            "alt_promo": oracle["alt_promo"],
        }
    if oracle["kind"] == "tagged-search":
        return {
            "workspace": str(workspace),
            "kind": "tagged-search",
            "notes": oracle["notes"],
            "tag_query": oracle["tag_query"],
            "title_query": oracle["title_query"],
            "tagged_index": oracle["tagged_index"],
        }
    return {
        "workspace": str(workspace),
        "kind": "quota-guard",
        "fresh": oracle["fresh"],
        "client_a": oracle["client_a"],
        "client_b": oracle["client_b"],
        "calls": oracle["calls"],
    }


def _probe_comparator_child(connection, request: bytes, kind: str, spec: dict[str, Any]) -> None:
    passed = False
    process = None
    timer = None
    try:
        process = subprocess.Popen(
            [sys.executable, "-I", "-c", _CANDIDATE_PROBE_PROGRAM],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        timed_out = threading.Event()

        def terminate() -> None:
            timed_out.set()
            try:
                process.kill()
            except OSError:
                pass

        timer = threading.Timer(_PRIVATE_PROBE_TIMEOUT_SECONDS, terminate)
        timer.start()
        process.stdin.write(request)
        process.stdin.close()
        raw = process.stdout.read(_PRIVATE_PROBE_LIMIT + 1)
        oversized = len(raw) > _PRIVATE_PROBE_LIMIT
        if oversized:
            process.kill()
        returncode = process.wait()
        if not timed_out.is_set() and not oversized and returncode == 0:
            payload = json.loads(raw.decode("utf-8"))
            if (
                isinstance(payload, dict)
                and payload.get("completed") is True
                and isinstance(payload.get("outputs"), list)
                and set(payload) == {"completed", "outputs"}
            ):
                passed = _outputs_match(kind, payload["outputs"], spec)
    except BaseException:
        pass
    finally:
        if timer is not None:
            timer.cancel()
        if process is not None:
            if process.poll() is None:
                with suppress(OSError):
                    process.kill()
            with suppress(OSError):
                process.wait()
            if process.stdin is not None:
                with suppress(OSError):
                    process.stdin.close()
            if process.stdout is not None:
                with suppress(OSError):
                    process.stdout.close()
    try:
        connection.send_bytes(b"1" if passed else b"0")
    finally:
        connection.close()


def _run_private_probe(fixture: GeneratedFeatureFixture, workspace: Path) -> bool:
    request = json.dumps(_probe_request(fixture, workspace), separators=(",", ":")).encode("utf-8")
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(
        target=_probe_comparator_child,
        args=(child, request, fixture.oracle["kind"], dict(fixture.oracle)),
        daemon=True,
    )
    try:
        process.start()
        child.close()
        if not parent.poll(_PRIVATE_PROBE_WRAPPER_SECONDS):
            process.terminate()
            process.join()
            return False
        return parent.recv_bytes(1) == b"1"
    except (EOFError, OSError):
        return False
    finally:
        parent.close()
        child.close()
        if process.pid is not None:
            process.join(timeout=1)
            if process.is_alive():
                process.terminate()
                process.join()


class GeneratedFeatureEnvironment(TaskEnvironment):
    def __init__(self, fixture: GeneratedFeatureFixture, root: str | Path | None = None):
        self.fixture = fixture
        self.root = Path(root) if root is not None else Path(tempfile.mkdtemp(prefix="mba-feature-"))
        self._owns_root = root is None

    def prepare(self, manifest: AgentTaskManifest, trial: int) -> PreparedEnvironment:
        if manifest.scenario_type != SCENARIO_TYPE:
            raise ValueError("unsupported scenario type")
        if manifest.fixture.reference != FIXTURE_VERSION:
            raise ValueError("unsupported fixture reference")
        if manifest.preparation.strategy != FIXTURE_VERSION:
            raise ValueError("unsupported preparation strategy")
        if manifest.verification.strategy != FIXTURE_VERSION:
            raise ValueError("unsupported verification strategy")
        if manifest.category != CATEGORY:
            raise ValueError("unsupported category")
        workspace = self.root / f"{manifest.task_id}-trial-{trial}"
        workspace.mkdir(parents=True, exist_ok=False)
        try:
            for relative, content in self.fixture.baseline_files.items():
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            digest = "sha256:" + hashlib.sha256(self.fixture.public_snapshot()).hexdigest()
            if digest != manifest.fixture.digest:
                raise RuntimeError("generated feature fixture digest mismatch")
            return PreparedEnvironment(manifest.public_prompt, EnvironmentHandle(workspace, digest))
        except BaseException:
            shutil.rmtree(workspace, ignore_errors=True)
            raise

    def execute(self, agent: AgentAdapter, handle: EnvironmentHandle, prompt: str, budget: AgentBudget) -> AgentResult:
        return execute_agent_with_budget(
            agent,
            prompt,
            handle.workspace,
            budget,
            start_method="spawn",
            network_policy=NETWORK_POLICY,
        )

    def verify(self, handle: EnvironmentHandle) -> VerificationResult:
        try:
            actual = {
                path.relative_to(handle.workspace).as_posix(): path.read_text(encoding="utf-8")
                for path in handle.workspace.rglob("*")
                if path.is_file() and not _is_runtime_artifact(path.relative_to(handle.workspace))
            }
        except BaseException:
            return VerificationResult(False, "hidden behavioral or collateral check failed")
        baseline = self.fixture.baseline_files
        if set(actual) != set(baseline):
            return VerificationResult(False, "hidden behavioral or collateral check failed")
        if any(actual[path] != content for path, content in baseline.items() if path not in self.fixture.mutable_paths):
            return VerificationResult(False, "hidden behavioral or collateral check failed")
        if all(actual[path] == baseline[path] for path in self.fixture.mutable_paths):
            return VerificationResult(False, "hidden behavioral or collateral check failed")
        if not _run_private_probe(self.fixture, handle.workspace):
            return VerificationResult(False, "hidden behavioral or collateral check failed")
        return VerificationResult(True, "hidden behavioral and regression checks passed")

    def dispose(self, handle: EnvironmentHandle | None) -> None:
        if handle is not None:
            shutil.rmtree(handle.workspace, ignore_errors=True)
        if self._owns_root:
            shutil.rmtree(self.root, ignore_errors=True)

    def is_disposed(self, handle: EnvironmentHandle | None) -> bool:
        return (handle is None or not handle.workspace.exists()) and (not self._owns_root or not self.root.exists())


class GeneratedFeatureGoldAgent:
    """Offline-only reference agent; it is never used to grade model output."""

    def __init__(self, fixture: GeneratedFeatureFixture):
        self.fixture = fixture

    def execute(self, prompt: str, workspace: Path, budget: AgentBudgetGuard) -> AgentResult:
        del prompt
        budget.consume(turns=1)
        for relative in self.fixture.mutable_paths:
            (workspace / relative).write_text(self.fixture.gold_files[relative], encoding="utf-8")
        return AgentResult("completed", claimed_success=True, turns=1, tokens_in=0, tokens_out=0, cost_usd=0.0)


def build_generated_feature_artifact(
    manifest: AgentTaskManifest,
    fixture: GeneratedFeatureFixture,
    trials: list[Any],
) -> dict[str, Any]:
    artifact = build_agent_artifact(manifest, trials)
    generator_identity = "|".join(f"{template.name}:{template.family}" for template in TEMPLATES)
    artifact["provenance"].update(
        {
            "fixture_version": FIXTURE_VERSION,
            "generator_sha256": hashlib.sha256(generator_identity.encode()).hexdigest(),
            "mutation_template_sha256": fixture.template_hash,
            "seed_sha256": fixture.seed_hash,
            "harness": HARNESS,
            "harness_version": AGENT_GRADER_VERSION,
            "network_policy": NETWORK_POLICY,
            "budgets": {
                "max_turns": manifest.budget.max_turns,
                "wall_time_seconds": manifest.budget.wall_time_seconds,
                "max_tokens": manifest.budget.max_tokens,
                "max_cost_usd": manifest.budget.max_cost_usd,
            },
            "terminal_outcome": "success" if all(trial.passed for trial in trials) else "verification_failed",
        }
    )
    for trial in artifact["trials"]:
        trial["detail"] = "pass" if trial["passed"] else "fail"
    return artifact


def run_offline(seed: int, trials: int, out: str | Path) -> int:
    fixture = generate_fixture(seed)
    manifest = manifest_for(fixture)
    environment = GeneratedFeatureEnvironment(fixture)
    results = [
        run_agent_trial(manifest, environment, GeneratedFeatureGoldAgent(fixture), trial=trial)
        for trial in range(1, trials + 1)
    ]
    artifact = build_generated_feature_artifact(manifest, fixture, results)
    destination = Path(out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact["summary"], indent=2))
    return 0 if all(result.passed and result.workspace_disposed for result in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a seeded generated feature-implementation task offline.")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.trials < 1:
        parser.error("--trials must be positive")
    return run_offline(args.seed, args.trials, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
