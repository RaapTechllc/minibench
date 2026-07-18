# Issue #34 primitive private-probe transport

**Boundary:** `codex/issue-34-generated-repository-repair` in its existing isolated worktree.

## Defect

`multiprocessing.Connection.recv()` unpickled candidate-controlled return values in the trusted verifier process. A hostile `__reduce__` could therefore execute outside the child timeout boundary and inspect trusted parent frames.

## Correction

- Candidate outputs are JSON-encoded inside the killable spawned child.
- The child sends bytes rather than pickled Python objects.
- The parent bounds the payload at 4096 bytes, decodes JSON, and accepts only the exact `completed`/`outputs` primitive envelope.
- Encoding, size, decode, child, and protocol failures fail closed as verification failures.
- A regression returns an object with a malicious `__reduce__` and proves its marker is never created.

## Deterministic checks

```bash
agentbench/.venv/bin/python -m pytest agentbench/tests/test_generated_repairs.py -q
agentbench/.venv/bin/python -m pytest agentbench/tests -q
git diff --check
```

No merge, deployment, release, live model call, credential use, or trading action is authorized.
