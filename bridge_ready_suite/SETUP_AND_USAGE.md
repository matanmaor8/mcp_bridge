# Bridge + MCP + Web App setup

## What changed

This package includes:

- a stream-aware MCP endpoint at `/mcp`
- async bridge REST endpoints:
  - `POST /run_async`
  - `GET /jobs/:jobId`
  - `GET /jobs/:jobId/result`
- a mobile-friendly web app at `/` and `/public/index.html`
- a long-prompt-safe Codex runner that writes the full task into `.bridge_codex_task.txt`

## Known defaults already filled in

The web app is prefilled with:

- Mode: `codex`
- Repo path: `C:\Users\matan\Downloads\floor_plan_ai_windows_friendly\floor_plan_ai_windows_friendly`

## Laptop usage

### 1. Start the Python orchestrator dependencies
Open PowerShell:

```powershell
cd C:\Users\matan\Downloads\bridge_ready_suite\bridge_ready_suite\python_orchestrator
.\.venv\Scripts\activate
python -m pytest -q
```

### 2. Start the bridge server
Open another PowerShell:

```powershell
cd C:\Users\matan\Downloads\bridge_ready_suite\bridge_ready_suite\chatgpt_bridge_app
node server.js
```

Expected output includes:

```text
Bridge listening on http://localhost:8787
Using orchestrator root: ...\python_orchestrator
```

### 3. Start ngrok
Open another PowerShell:

```powershell
ngrok http 8787
```

Take the public HTTPS URL, for example:

```text
https://YOUR-SUBDOMAIN.ngrok-free.dev
```

### 4. Use the web app from your laptop browser
Open:

```text
http://localhost:8787/
```

Or through ngrok:

```text
https://YOUR-SUBDOMAIN.ngrok-free.dev/
```

## Mobile usage

1. Keep `node server.js` running on your laptop.
2. Keep `ngrok http 8787` running on your laptop.
3. On your phone browser, open:

```text
https://YOUR-SUBDOMAIN.ngrok-free.dev/
```

4. The base URL field can stay as the same ngrok URL.
5. Tap `Start job`, then `Refresh status`, then `Fetch result`.

## ChatGPT connector usage

Connector URL:

```text
https://YOUR-SUBDOMAIN.ngrok-free.dev/mcp
```

After code changes:

1. restart `node server.js`
2. keep ngrok running
3. refresh the connector in ChatGPT settings

## Quick health checks

```powershell
Invoke-RestMethod http://localhost:8787/health
Invoke-RestMethod http://localhost:8787/.well-known/mcp
Invoke-RestMethod http://localhost:8787/mcp
Invoke-RestMethod -Method Post -Uri http://localhost:8787/mcp -ContentType "application/json" -Body '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Important note for long prompts

Long content is no longer passed through the command line.
The runner writes the task into:

```text
.bridge_codex_task.txt
```

inside the target repository, then asks Codex to read that file.
That avoids Windows command-line length failures.
