# Python Orchestrator

This project is the local backend. It supports:
- `mock` mode
- `openai` mode
- `repo` mode
- `codex` mode

## What is already completed
- idempotent safe repo edits for the bundled sample repo
- rollback if repo validation fails
- file-path allowlist
- run logs under `runs/`
- ready adapter for Codex CLI

## What you need before testing
- Python 3.11+
- optional: Node.js if you want Codex CLI or the ChatGPT bridge app
- OpenAI API key in `.env`
- optional: install Codex CLI with `npm i -g @openai/codex`

## Windows PowerShell setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set `OPENAI_API_KEY`.

## Validate the backend

```powershell
python -m pytest
```

## Run sample repo in safe repo mode

```powershell
python app.py --task "Improve logging in the sample repo and add tests" --mode repo --repo .\sample_repo_template
```

## Verify the bundled sample repo tests
Run from inside the sample repo so `app/` resolves correctly.

```powershell
Push-Location .\sample_repo_template
python -m pytest
Pop-Location
```

## Run Codex mode
This keeps the local orchestrator and tries to hand execution to Codex CLI.

```powershell
python app.py --task "Improve logging in the sample repo and add tests" --mode codex --repo .\sample_repo_template
```

## Important note
For `codex` mode, this package can prepare everything except your local Codex CLI login/install. If Codex CLI is missing, the app will tell you.
