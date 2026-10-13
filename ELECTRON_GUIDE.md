# MindSpring Electron UI

The original Pygame app remains in place. MindSpring is an additional fullscreen Electron UI with eight task types. It sends task-specific telemetry and a bounded set of trial records to the Mesa model.

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

The Electron experience now includes eight tasks:

- **Find the pairs:** card-pair attempts, matches, errors, response latency, and hesitation intervals.
- **Color sequence:** sequence submissions, wrong sequences/retries, input latency, and sequence length.
- **Spatial sequence:** sequence submissions, wrong locations/order, input latency, and sequence length. The game grid remains 3×3.
- **Color & word (Stroop):** ink-colour responses, retries, word-reading slips, and response latency.
- **Reflex Lab: simple reaction:** randomized cue timing, trial-by-trial reaction times, false starts, omissions, median response time and variability.
- **Reflex Lab: choice reaction:** symbol discrimination with 2–4 choice options, trial-by-trial timing, and choice errors.
- **Reflex Lab: Go/No-Go:** trial-by-trial timing, false starts, missed Go targets and commission errors for responding to No-Go cues.
- **Delayed recall:** a study phase, immediate free recall, a distraction interval, delayed free recall, and recognition trials that record hits, misses, false alarms and correct rejections. The user's typed recall text is not saved; only counts are retained.

### Mesa agents

The app's **Agent lab** button opens a developer panel showing each agent's current state, role, metrics, explanations, and recent history. The API endpoint `GET /api/agents/state` returns this same snapshot. The panel automatically refreshes after a round when it is open.

- **`ScreenerAgent`** computes a task-specific play score and shows its component scores, weights, metrics used, evidence sample count, uncertainty estimate, quality flags, and possible practice adjustment. It does not produce diagnostic probabilities in the Electron path.
- **`MemoryAnalysisAgent`** summarizes pair/sequence results and the difference between immediate recall, delayed recall, and recognition. Its delayed-retention signal can inform adaptive difficulty.
- **`AttentionAnalysisAgent`** summarizes response variability, false starts, omissions, commission errors and Stroop word-reading slips. Its Go/No-Go commission-error signal can inform adaptive difficulty.
- **`AdaptiveDifficultyAgent`** owns a separate level and settings for each game, records before/after parameters and the reason for each decision, discounts score gains that may be due to practice at the same level, and holds a level if one small sample is too uncertain to justify changing it.
- **`PatientAgent`** remains a simulated participant for the legacy Mesa simulation. It is not a model of the actual Electron player. **`TileAgent`** remains part of the legacy board model; Electron renders its boards in JavaScript.

Each score is a readable engineering heuristic, not a calibrated clinical norm. The confidence and uncertainty summaries describe how much task evidence was available; they are not probabilities that somebody has a disease. See [MINDSPRING_AGENT_LAB_GUIDE.md](MINDSPRING_AGENT_LAB_GUIDE.md) for the agent flow and decisions in more detail.

### Difficulty logic and experiment

The task-specific parameters differ by game: pair-board size, sequence flash/gap timing, Stroop conflict frequency, Reflex Lab response windows/options/No-Go frequency, and delayed-recall list size/study/delay duration. Difficulty changes are recorded with the metrics used and a plain-language explanation. Promotion requires repeated good performance at one level and sufficiently precise evidence; a low-confidence result normally triggers another observation instead of a fast adjustment.

To compare a simple synthetic adaptive policy with fixed-level testing, run from the project root:

```powershell
python evaluation/compare_adaptive_fixed.py
```

The script writes `evaluation/adaptive_vs_fixed_results.json`. It uses synthetic participants and toy response curves only; it is an engineering experiment and must not be interpreted as a clinical validation result. Its results should guide further tuning rather than being presented as proof that adaptive testing is always more efficient.

MindSpring's overall profile and individual scores describe gameplay performance only. They cannot confirm or rule out cognitive impairment or any medical condition. Proper screening research would require appropriate reference groups, participant-level and external validation, calibration, fairness checks, consent, privacy review and ethics approval.

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
