$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $root 'python_orchestrator')
.\.venv\Scripts\python.exe app.py --task "Improve logging in the sample repo and add tests" --mode repo --repo .\sample_repo_template
Pop-Location
