$ErrorActionPreference = "Stop"

$Project = "C:\INFO7VERSION CLAUDE"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

g++ `
  -std=c++17 `
  -Wall `
  -Wextra `
  -I $Project `
  "$Here\engine.cpp" `
  "$Project\board.cpp" `
  "$Project\game.cpp" `
  "$Project\mask.cpp" `
  -o "$Here\engine.exe"

Write-Host "Built $Here\engine.exe"
