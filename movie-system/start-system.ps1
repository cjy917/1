# FYWZ Movies 一键启动
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Get-NetTCPConnection -LocalPort 5000,5173 -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location '$root\backend'; Write-Host 'Backend: http://127.0.0.1:5000' -ForegroundColor Cyan; python app.py"
)

Start-Sleep -Seconds 3

Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location '$root\frontend'; Write-Host 'Frontend: http://localhost:5173' -ForegroundColor Cyan; npm run dev"
)

Write-Host "已启动！请访问 http://localhost:5173" -ForegroundColor Green
