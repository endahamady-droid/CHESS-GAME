$ErrorActionPreference = "Stop"

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonCandidates = @(
  "python",
  "py",
  "C:\Users\endah\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)

foreach ($Python in $PythonCandidates) {
  try {
    & $Python --version *> $null
    Set-Location $Here
    & $Python "$Here\server.py"
    exit $LASTEXITCODE
  } catch {
  }
}

Write-Error "Python was not found. Install Python, then run this script again."
