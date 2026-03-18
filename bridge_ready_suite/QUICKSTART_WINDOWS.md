# Windows Quickstart

## 1. Setup once

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
```

## 2. Add your API key

Open `python_orchestrator\.env` and set `OPENAI_API_KEY`.

## 3. Validate everything locally

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\preflight_check.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start_backend_repo_test.ps1
```

## 4. Start bridge locally

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_bridge.ps1
```

Then in a second PowerShell window:

```powershell
Invoke-RestMethod http://localhost:8787/health
Invoke-RestMethod -Method Post -Uri http://localhost:8787/run -ContentType 'application/json' -Body '{"task":"Improve logging in the sample repo and add tests","mode":"repo","repo":"sample_repo_template"}'
```

## 5. Connect ChatGPT

Start a tunnel:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_ngrok_tunnel.ps1
```

Then use:

```text
https://YOUR-NGROK-URL/mcp
```

as the connector endpoint in ChatGPT.
