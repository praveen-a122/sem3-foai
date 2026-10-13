# MindSpring Agent Lab

This guide explains the live Electron-to-Mesa path, the two new task families, and the experiment for comparing adaptive difficulty with fixed difficulty.

## Live round flow

1. The Electron renderer runs a game and creates task telemetry.
2. `electron_backend/server.py` validates the task, keeps a bounded list of whitelisted trial fields, and passes the telemetry to `CognitiveHealthModel.process_task_result()`.
3. `ScreenerAgent` calculates task-specific gameplay metrics, records score components, evidence count, an exploratory uncertainty interval, quality notes, and a plain-language explanation. Its Electron scoring path does not load a diagnostic probability.
4. `MemoryAnalysisAgent` summarizes pair, sequence, and delayed-recall evidence. `AttentionAnalysisAgent` summarizes Stroop and Reflex Lab evidence. Each agent marks itself idle for tasks outside its domain rather than pretending it analysed every task.
5. `AdaptiveDifficultyAgent` reads the task score, accuracy/error rate, median response time, response-time variability, evidence size, same-difficulty history, practice adjustment, and applicable domain-agent indicators. It selects the next level and records the metrics and settings before and after its decision.
6. The UI displays the explanation after each round. The **Agent lab** button opens the live state and recent decision history from `GET /api/agents/state`.

## Agents in the Electron session

- **ScreenerAgent:** a transparent task-specific performance rubric. The weighted scores and thresholds are engineering choices, not validated clinical norms.
- **MemoryAnalysisAgent:** explains recall, sequence span, pair matching, and immediate-to-delayed retention/recognition. For delayed recall, its retention signal also contributes to adaptive decisions.
- **AttentionAnalysisAgent:** explains reaction-time spread, false starts, omissions, commission errors, and Stroop word-reading slips. For Go/No-Go, repeated commission errors contribute to adaptive decisions.
- **AdaptiveDifficultyAgent:** holds an independent level and settings for each task, checks evidence before promoting, discounts observed improvement that may reflect practice, and avoids changing difficulty solely on one low-confidence result when the participant is above the lowest level.
- **PatientAgent:** a synthetic participant for the original Mesa simulation/evaluation path. It does not model the real person playing Electron.
- **TileAgent:** a legacy spatial-board representation. Electron draws its boards in JavaScript.

The first four agents form the live task-aware feedback loop. `PatientAgent` and `TileAgent` remain for compatibility with the original simulation.

## Game tasks and core measurements

| Task | Main measurements | Difficulty parameters |
|---|---|---|
| Find the pairs | Matches, unsuccessful attempts, response latency and hesitations | Pair-board size and the existing round progression |
| Color sequence | Recalled sequence, retries, response latency | Flash duration and gap between flashes |
| Spatial sequence | Correct spatial order, retries, response latency | Flash duration and gap; grid remains 3×3 |
| Color & word (Stroop) | Ink-colour accuracy, retries, word-reading slips and latency | Incongruent-trial rate and response window |
| Reflex Lab: simple | Trial-level reaction times, median, variability, false starts and omissions | Random wait interval and response window |
| Reflex Lab: choice | Trial-level latency, choice accuracy and errors | Number of choice options and response window |
| Reflex Lab: Go/No-Go | Trial-level latency, false starts, omissions and commission errors | No-Go frequency and response window |
| Delayed recall | Immediate free recall, delayed free recall, recognition hits/misses, false alarms and retention ratio | Number of learned items, study duration and delay interval |

Reflex Lab keeps one record per trial. An early click is a false start and does not consume a valid trial; the app caps repeated false starts so a session cannot get stuck forever. A no-response on a Go trial is an omission. A response to a No-Go stimulus is a commission error. These terms describe actions in the task, not a diagnosis.

Delayed recall stores counts and recognition trial summaries, not the participant's typed recall text. The distraction interval is a simple moving-target task and is not itself treated as a separate cognitive test.

## Evidence, practice and adaptation

Each task has its own level 1–3 setting. The adaptive decision is deliberately conservative:

- Low accuracy, repeated errors, a low task-specific score, or very slow responses can lower difficulty when the evidence is sufficient.
- A very small or uncertain sample normally leads to another observation instead of a level change. A stronger pattern, multiple errors, or unusually slow responses can still justify easing the task.
- Raising difficulty requires repeated strong performance at the current level, few errors, a reasonable response-time profile, adequate evidence confidence, a manageable Wilson-style accuracy uncertainty interval, and a practice-adjusted score in the target band.
- Practice gain is compared only between exposures at the same difficulty, so scores from different board/sequence levels are not treated as like-for-like observations.

The confidence and uncertainty values are engineering summaries of the current round's sample size and accuracy. They are not calibrated probability estimates about a person or disease.

## Inspecting agents during a session

1. Start MindSpring and begin a session.
2. Select **Agent lab** in the top bar.
3. Inspect the current state for each agent, including task history, metrics used, explanations, current level, settings, and recent actions.
4. After any scored round, use **Refresh** if you want an immediate snapshot. The panel also refreshes when a round is submitted while it is open.

The decision history is bounded in memory for this running session. The full task results, including sanitized trial evidence, are saved in the session JSON under `electron_sessions/`.

## Comparing adaptive and fixed testing

Run from the project root:

```powershell
python evaluation/compare_adaptive_fixed.py
```

This produces `evaluation/adaptive_vs_fixed_results.json`. It runs a deterministic, synthetic experiment with artificial response curves and a simple adaptive policy. It compares estimated three-level ability, posterior uncertainty, and trials needed to reach a posterior threshold against a fixed level-2 policy. It does **not** use real participants or the full runtime agent code, and the output is not clinical evidence. Treat it as a quick engineering probe: if adaptation does not reduce trials or uncertainty in this toy setup, improve the policy and rerun the experiment rather than claiming an adaptive advantage.

## Limitations and responsible interpretation

MindSpring is an academic software prototype. Its scores describe performance in these games and cannot confirm or rule out dementia, ADHD, or any other medical condition. Response times depend on the computer, display, input device, familiarity, fatigue, accessibility needs and many other factors. Clinical claims would require a research protocol, independent labels from qualified assessment, suitable reference data, participant-level and external validation, calibration, fairness evaluation, privacy controls and ethics approval.
