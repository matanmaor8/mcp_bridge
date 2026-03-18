$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $root 'chatgpt_bridge_app')
node server.js
Pop-Location
