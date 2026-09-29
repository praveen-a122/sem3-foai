@echo off
title Cognitive Assessment Serious Game (22AIE201)
cd /d "%~dp0"
echo =================================================================
echo  Launching 22AIE201 Pygame Serious Game + Mesa Multi-Agent Loop
echo =================================================================
echo Controls:
echo  - Left Click : Flip / inspect card
echo  - Space / Click : Advance after round completion
echo  - Escape     : Exit game cleanly
echo =================================================================
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py --mode game
) else (
    python main.py --mode game
)
pause
