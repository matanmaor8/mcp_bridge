$ErrorActionPreference = 'Stop'
$ngrok = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrok) {
  throw 'ngrok is not installed or not in PATH.'
}
ngrok http 8787
