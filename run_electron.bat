@echo off
setlocal
cd /d "%~dp0"

echo =============================================================
echo  MindSpring - Electron Cognitive Games + Mesa Agents
echo =============================================================

where node >nul 2>nul
if errorlevel 1 (
    echo Node.js is not installed or is not on PATH.
    echo Install a current Node.js LTS release, then reopen this terminal.
    pause
    exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
    echo npm is not installed or is not on PATH.
    pause
    exit /b 1
)

if not exist "electron\node_modules\electron\package.json" (
    echo Electron dependencies are not installed yet.
    echo Installing project dependencies now...
    cd electron
    call npm install
    if errorlevel 1 (
        echo npm install failed. Check the network/npm error above and try again.
        pause
        exit /b 1
    )
    cd /d "%~dp0"
)

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=%CD%\.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

cd electron
call npm start
set "APP_EXIT=%ERRORLEVEL%"
cd /d "%~dp0"
if not "%APP_EXIT%"=="0" (
    echo MindSpring exited with code %APP_EXIT%.
    pause
)
exit /b %APP_EXIT%
