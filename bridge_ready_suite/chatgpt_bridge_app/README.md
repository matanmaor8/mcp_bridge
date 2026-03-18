# ChatGPT Bridge App

This server exposes two useful layers:

- `/run` for direct local testing
- `/mcp` for ChatGPT connector integration

## Setup

```powershell
npm install
Copy-Item .env.example .env
```

Edit `.env` if needed:
- `ORCHESTRATOR_ROOT` — path to the Python orchestrator folder
- `PYTHON_COMMAND` — defaults to `python`
- `DEFAULT_MODE` — defaults to `repo`
- `DEFAULT_REPO` — defaults to `sample_repo_template`
- optional `MCP_BEARER_TOKEN`

## Start

```powershell
node server.js
```

## Health check

```powershell
Invoke-RestMethod http://localhost:8787/health
```

## Direct local test

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8787/run -ContentType 'application/json' -Body '{"task":"Improve logging in the sample repo and add tests","mode":"repo","repo":"sample_repo_template"}'
```

## ChatGPT connector

Expose the local server over HTTPS, then add:

```text
https://YOUR-TUNNEL-URL/mcp
```

as a connector in ChatGPT.

If you set `MCP_BEARER_TOKEN`, use the same bearer token in the connector.
