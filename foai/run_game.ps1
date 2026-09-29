Set-Location -Path $PSScriptRoot
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " Launching 22AIE201 Pygame Serious Game + Mesa Multi-Agent Loop " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "Controls: Left Click to flip cards | SPACE to advance | ESC to quit" -ForegroundColor Yellow
if (Test-Path ".\.venv\Scripts\python.exe") {
    & ".\.venv\Scripts\python.exe" main.py --mode game
} else {
    python main.py --mode game
}
