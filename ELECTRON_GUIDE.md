# MindSpring Electron UI

The original Pygame app remains in place. MindSpring is an additional fullscreen Electron UI that plays the same four task types and sends each round's raw gameplay telemetry to the existing Mesa model.

## First-time setup (Windows)

1. Install Python 3.10+ and Node.js (npm is included with Node).
2. From the project root, create/activate the project's virtual environment and install Python packages:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. Install Electron:

   ```powershell
   cd electron
   npm install
   cd ..
   ```

4. Launch fullscreen:

   ```powershell
   .\run_electron.bat
   ```

   Or run `npm start` from the `electron` directory. The Electron main process starts `electron_backend/server.py` using the project's `.venv` when present. If `.venv` is absent, it falls back to `python`.

   The `npm start` command now runs an Electron-binary preflight first. Recent Electron releases can install the JavaScript package without the desktop executable and download that executable on demand, so the preflight checks for `electron.exe` and attempts the download before the UI starts. If the primary download host is unreachable, it retries with the alternate Electron mirror.

### Fixing `TypeError: fetch failed` during Electron startup

This message means Electron could not fetch its desktop binary; the app's game code has not started yet. The Node.js version in the reported example (`v24.14.1`) is new enough for Electron 44, so do not downgrade Node as the first fix. The likely issue is network access to the Electron release host, DNS, or a required proxy.

Run the launcher again after switching to a network that can reach the download host. You can also try the official install command from the `electron/` directory:

```powershell
npx install-electron --no
```

If GitHub's release downloads are blocked, try the alternate mirror in PowerShell and then start the app:

```powershell
$env:ELECTRON_MIRROR = "https://npmmirror.com/mirrors/electron/"
npx install-electron --no
npm start
```

If your network requires an HTTP proxy, configure the proxy in your terminal and follow Electron's proxy installation guidance. Do not delete the entire project or change the game code to fix this download error.

## Linux / macOS

Install the requirements into a virtual environment, run `npm install` in `electron/`, then run `npm start` from that directory. Set `PYTHON` if your Python executable is not on the default path.

## How the analysis works

- **Find the pairs:** card-pair attempts, matches, errors, response latency, and hesitation intervals.
- **Color sequence:** sequence submissions, wrong sequences/retries, input latency, and sequence length.
- **Spatial sequence:** sequence submissions, wrong locations/order, input latency, board size, and sequence length.
- **Color & word:** ink-color responses, retries, word-reading slips, and response latency.

`ScreenerAgent` uses a task-aware, transparent heuristic for these Electron tasks. It deliberately does **not** apply the Pairs-trained clinical classifier to sequence or Stroop data. Pair matching is evaluated with match efficiency, retries, and timing; both sequence games retain sequence length and wrong-submission counts; Stroop also counts errors made by choosing the printed word instead of its ink color.

For pair/sequence tasks, the project play score combines 75% accuracy and 25% baseline-adjusted response speed, with a small hesitation penalty. Stroop allocates 65% to response accuracy, 25% to speed, and 10% to the separate word-reading/inhibition measure. These weights are an engineering rubric, not published clinical norms.

`AdaptiveDifficultyAgent` keeps a separate level (1–3) and recent accuracy history for each game. It eases a task when accuracy drops below 60%, the error rate reaches 40%, or responses are very slow. It raises difficulty only after at least two recent samples show high accuracy (88% or better), few errors (15% or less), and timely responses. Especially difficult rounds can trigger a gentle break suggestion. The thresholds are easy-to-read project settings, not calibrated medical cutoffs. `CognitiveHealthModel.process_task_result()` coordinates the Mesa assessment, adaptation, spatial representation, history, and data collection.

The app reports a **game performance score**, not MMSE, a diagnosis, or a validated clinical risk classification. These scores cannot confirm or rule out cognitive impairment and need independent validation before any real-world screening use. Session JSON is saved locally under `electron_sessions/`; the existing Pygame logs and session files are left alone.

## Controls

- **Esc:** pause / resume. Paused time is excluded from response latency.
- **F11:** toggle fullscreen.
- The close button returns to the welcome screen. Results already saved by the local service remain on disk.

## Original app

The original Pygame application and its launch scripts remain available:

```powershell
python main.py --mode game
python main.py --mode test
```

Use the **project root** as the working directory for either app. The ZIP contains an older `foai/` snapshot from the source repository; the root-level files are the canonical project used by the included launchers.
