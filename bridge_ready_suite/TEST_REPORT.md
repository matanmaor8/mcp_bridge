# Test report

## Python tests
Command run:

```text
cd python_orchestrator
python -m pytest -q --durations=0
```

Result:

- Status: PASS
- Total tests: 6 passed

Measured slowest durations reported by pytest:

- `tests/test_repo_idempotent.py::test_repo_mode_is_idempotent` → 6.27s
- `tests/test_codex_long_prompt.py::test_codex_long_prompt_uses_task_file` → 4.48s
- `tests/test_codex_detection.py::test_detect_codex_command_returns_reason` setup → 0.07s
- `tests/test_repo_blocks_unknown.py::test_unknown_repo_task_is_blocked` → 0.02s
- Remaining durations were under 0.005s each.

## Node bridge tests
Command run:

```text
cd chatgpt_bridge_app
node tests/test_server.mjs
```

Result:

- Status: PASS

Measured durations:

- `GET /health` → 5ms
- `GET /mcp returns SSE` → 6ms
- `POST /mcp initialize` → 16ms
- `POST /mcp tools/list` → 3ms
- `POST /run_async mock` → 17ms
- `GET /jobs/:id completes` → 1733ms
- `GET /jobs/:id/result returns parsed text` → 3ms
- `MCP tools/call start + status + result` → 1502ms

## What was validated

- no `404` on `/mcp`
- no `404` on `/.well-known/mcp`
- `/mcp` now returns `text/event-stream`
- async job creation returns a job ID
- async status polling works
- async result retrieval works
- MCP-style `initialize`, `tools/list`, and `tools/call` work locally
- long task input is written via task file and can create a repo file without command-line length issues
