# MindSpring · Fundamentals of AI Project

An eight-task cognitive gameplay project for **22AIE201 Fundamentals of AI**. The repository includes the original Pygame interface, Mesa agent-based model, OASIS calibration and evaluation pipeline, plus a new fullscreen Electron UI.

## Run the Electron experience

1. Install the Python dependencies: `python -m pip install -r requirements.txt`
2. Install the UI dependency once: `cd electron && npm install`
3. Start the app from the project root with `run_electron.bat` (Windows), or run `npm start` inside `electron/`.

The Electron app starts a local Python service that routes trial-level gameplay telemetry through Mesa's `ScreenerAgent`, `MemoryAnalysisAgent`, `AttentionAnalysisAgent`, and `AdaptiveDifficultyAgent`. Use the **Agent lab** button inside the app to inspect agent state and decision history. Read [ELECTRON_GUIDE.md](ELECTRON_GUIDE.md) for setup and [MINDSPRING_AGENT_LAB_GUIDE.md](MINDSPRING_AGENT_LAB_GUIDE.md) for agent logic, task metrics, and the adaptive-versus-fixed experiment.

## Original Pygame / research pipeline

From the project root:

```bash
python main.py --mode game
python main.py --mode evaluate --patients 50 --days 30
python main.py --mode calibrate
python main.py --mode test
```

The existing Pygame frontend, session tooling, datasets, model bundle, evaluation scripts, and plots are retained. Use the project root as the working directory; `foai/` is an older duplicate snapshot shipped with the supplied project.

## Important limitation

This is an academic prototype. Its per-game score is a gameplay-performance heuristic, not a validated cognitive test, diagnosis, or medical recommendation. Real clinical screening would require expert-led validation, suitable normative data, privacy review, and ethics approval.
