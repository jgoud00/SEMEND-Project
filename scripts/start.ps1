param([switch]$Production)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Install dependencies first; see README.md.' }
$frontendRoot = Join-Path $projectRoot 'frontend'
foreach ($port in @(8000, 5173)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Port $port is already in use. Stop that server before launching." }
}
if ($Production) {
    Push-Location $frontendRoot
    try { & npm.cmd run build; if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' } }
    finally { Pop-Location }
}
$backendProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--app-dir', 'backend', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRoot 'backend.log') -RedirectStandardError (Join-Path $projectRoot 'backend-error.log')
$mode = if ($Production) { 'preview' } else { 'dev' }
# Start Node directly; stopping its PID also stops the server on Windows.
try {
    $frontendProcess = Start-Process -FilePath (Get-Command node.exe).Source -ArgumentList @('node_modules/vite/bin/vite.js', $mode, '--host', '127.0.0.1') -WorkingDirectory $frontendRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRoot 'frontend.log') -RedirectStandardError (Join-Path $projectRoot 'frontend-error.log')
    Write-Host 'ForearmSense AI: http://127.0.0.1:5173 | API: http://127.0.0.1:8000/docs'
    Write-Host 'Press Ctrl+C to stop both servers.'
    while (-not $backendProcess.HasExited -and -not $frontendProcess.HasExited) { Start-Sleep -Seconds 1; $backendProcess.Refresh(); $frontendProcess.Refresh() }
} finally {
    if ($frontendProcess -and -not $frontendProcess.HasExited) { Stop-Process -Id $frontendProcess.Id -ErrorAction SilentlyContinue }
    if (-not $backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue }
}
