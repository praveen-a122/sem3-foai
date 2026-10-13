Set-Location -Path $PSScriptRoot

if (-not (Test-Path ".\electron\node_modules\electron\package.json")) {
    Write-Host "Electron dependencies are not installed yet. Installing them now..." -ForegroundColor Yellow
    Push-Location ".\electron"
    npm install
    $installExit = $LASTEXITCODE
    Pop-Location
    if ($installExit -ne 0) {
        Write-Host "npm install failed. Check the network/npm error above and try again." -ForegroundColor Red
        exit $installExit
    }
}

if (Test-Path ".\.venv\Scripts\python.exe") {
    $env:PYTHON = (Resolve-Path ".\.venv\Scripts\python.exe").Path
} else {
    $env:PYTHON = "python"
}

Push-Location (Join-Path $PSScriptRoot "electron")
npm start
$appExit = $LASTEXITCODE
Pop-Location
exit $appExit
