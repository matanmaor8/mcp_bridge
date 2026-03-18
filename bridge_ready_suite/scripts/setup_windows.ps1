$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Write-Host "Root: $root"

Push-Location (Join-Path $root 'python_orchestrator')
if (-not (Test-Path '.venv')) {
  py -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path '.env')) {
  Copy-Item .env.example .env
  Write-Host 'Created python_orchestrator\.env from template'
}
Pop-Location

Push-Location (Join-Path $root 'chatgpt_bridge_app')
if (-not (Test-Path '.env')) {
  Copy-Item .env.example .env
  Write-Host 'Created chatgpt_bridge_app\.env from template'
}
npm install
Pop-Location

Write-Host ''
Write-Host 'Setup completed.'
Write-Host 'Next steps:'
Write-Host '1. Put OPENAI_API_KEY into python_orchestrator\.env'
Write-Host '2. Run scripts\preflight_check.ps1'
