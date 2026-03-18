$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$pyRoot = Join-Path $root 'python_orchestrator'
$bridgeRoot = Join-Path $root 'chatgpt_bridge_app'

Write-Host '=== Runtime checks ==='
py --version
node --version
npm --version

Write-Host ''
Write-Host '=== Python environment ==='
if (Test-Path (Join-Path $pyRoot '.venv\Scripts\python.exe')) {
  & (Join-Path $pyRoot '.venv\Scripts\python.exe') --version
} else {
  Write-Warning 'Missing python_orchestrator virtual environment'
}

Write-Host ''
Write-Host '=== Environment files ==='
$pyEnv = Join-Path $pyRoot '.env'
$bridgeEnv = Join-Path $bridgeRoot '.env'
if (Test-Path $pyEnv) {
  $content = Get-Content $pyEnv -Raw
  if ($content -match 'OPENAI_API_KEY=' -and $content -notmatch 'OPENAI_API_KEY=your_') {
    Write-Host 'python_orchestrator/.env looks configured'
  } else {
    Write-Warning 'python_orchestrator/.env exists but OPENAI_API_KEY still looks empty'
  }
} else {
  Write-Warning 'python_orchestrator/.env is missing'
}
if (Test-Path $bridgeEnv) {
  Write-Host 'chatgpt_bridge_app/.env exists'
} else {
  Write-Warning 'chatgpt_bridge_app/.env is missing'
}

Write-Host ''
Write-Host '=== Backend tests ==='
Push-Location $pyRoot
if (Test-Path '.venv\Scripts\python.exe') {
  & .\.venv\Scripts\python.exe -m pytest -q
} else {
  Write-Warning 'Skipping pytest because .venv is missing'
}
Pop-Location

Write-Host ''
Write-Host '=== Optional tools ==='
$codexCmd = Get-Command codex -ErrorAction SilentlyContinue
if ($codexCmd) { Write-Host "Codex CLI found: $($codexCmd.Source)" } else { Write-Warning 'Codex CLI not found (only needed for --mode codex)' }
$ngrokCmd = Get-Command ngrok -ErrorAction SilentlyContinue
if ($ngrokCmd) { Write-Host "ngrok found: $($ngrokCmd.Source)" } else { Write-Warning 'ngrok not found (only needed for ChatGPT connector test)' }

Write-Host ''
Write-Host '=== Next suggested commands ==='
Write-Host 'Backend local test:'
Write-Host '  cd python_orchestrator'
Write-Host '  .\.venv\Scripts\python.exe app.py --task "Improve logging in the sample repo and add tests" --mode repo --repo .\sample_repo_template'
Write-Host ''
Write-Host 'Bridge local test:'
Write-Host '  cd chatgpt_bridge_app'
Write-Host '  node server.js'
