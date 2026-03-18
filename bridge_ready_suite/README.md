# Bridge Ready Suite

This package gives you two connected layers:

- `python_orchestrator/` — the local multi-agent backend with `mock`, `openai`, `repo`, and `codex` modes
- `chatgpt_bridge_app/` — the ChatGPT-facing bridge app exposing `/run` and `/mcp`

## What is already done

- safe sample repo included
- idempotent repo edits
- rollback on failed tests
- allowlist for editable paths
- Codex adapter included
- ChatGPT bridge server included
- PowerShell setup and preflight scripts included

## What you still must do manually

1. Put your `OPENAI_API_KEY` in `python_orchestrator/.env`
2. Install runtimes you don't already have: Python, Node.js, and optionally Codex CLI and ngrok
3. If you want ChatGPT to call the bridge, expose the bridge over HTTPS and add `<public-url>/mcp` as a connector in ChatGPT

## Recommended order

1. Run `scripts\setup_windows.ps1`
2. Run `scripts\preflight_check.ps1`
3. Test backend locally in `repo` mode
4. Start the bridge locally and test `/run`
5. Start ngrok and connect ChatGPT to `/mcp`

## Fastest local test

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\preflight_check.ps1
```
