const API = 'http://127.0.0.1:8765';

const TASKS = [
  { key: 'pairs', title: 'Find the pairs', subtitle: 'Find matching cards by remembering what you have seen.', domain: 'Associative visual memory', glyph: '▦', kicker: 'GAME 01 / 08' },
  { key: 'color_pattern', title: 'Color sequence', subtitle: 'Watch the colors light up, then repeat the pattern in order.', domain: 'Visual sequence memory', glyph: '✳', kicker: 'GAME 02 / 08' },
  { key: 'normal_pattern', title: 'Spatial sequence', subtitle: 'Remember where each tile lights up, then retrace its path.', domain: 'Spatial sequence memory', glyph: '⌗', kicker: 'GAME 03 / 08' },
  { key: 'stroop', title: 'Color & word', subtitle: 'Choose the ink color. Ignore what the word says and the color of each button.', domain: 'Selective attention and inhibition', glyph: 'Aa', kicker: 'GAME 04 / 08' },
  { key: 'reflex_simple', title: 'Simple reaction', subtitle: 'Wait for the glow, then respond as quickly as you comfortably can.', domain: 'Simple response speed and consistency', glyph: '◉', kicker: 'GAME 05 / 08' },
  { key: 'reflex_choice', title: 'Choice reaction', subtitle: 'Identify the symbol and select its matching label.', domain: 'Choice response and stimulus discrimination', glyph: '⌘', kicker: 'GAME 06 / 08' },
  { key: 'reflex_gonogo', title: 'Go / No-Go', subtitle: 'Respond to GO signals and hold your response for NO-GO signals.', domain: 'Response inhibition and sustained attention', glyph: '⏵', kicker: 'GAME 07 / 08' },
  { key: 'delayed_recall', title: 'Delayed recall', subtitle: 'Learn a small set of words, do a brief distractor task, then recall and recognize them.', domain: 'Immediate and delayed episodic recall', glyph: '◷', kicker: 'GAME 08 / 08' },
];

const PALETTE = [
  { name: 'RED', hex: '#eb2d2d', glow: 'rgba(235,45,45,.55)' },
  { name: 'ORANGE', hex: '#f57d23', glow: 'rgba(245,125,35,.55)' },
  { name: 'YELLOW', hex: '#f0d737', glow: 'rgba(240,215,55,.55)' },
  { name: 'GREEN', hex: '#2dbe4b', glow: 'rgba(45,190,75,.55)' },
  { name: 'BLUE', hex: '#2d78eb', glow: 'rgba(45,120,235,.55)' },
  { name: 'INDIGO', hex: '#5a41be', glow: 'rgba(90,65,190,.55)' },
  { name: 'VIOLET', hex: '#af41be', glow: 'rgba(175,65,190,.55)' },
];
const STROOP_COLORS = [
  { name: 'RED', hex: '#ff747b' },
  { name: 'BLUE', hex: '#6ea5ff' },
  { name: 'GREEN', hex: '#6cdaa5' },
  { name: 'YELLOW', hex: '#f4d46c' },
  { name: 'PURPLE', hex: '#bb9aff' },
  { name: 'ORANGE', hex: '#ffaa69' },
];
const CARD_SYMBOLS = ['🍎', '🪁', '🎧', '🌙', '🐳', '🍃', '🎲', '🌻', '🚲', '⭐', '🎈', '🍉', '🦋', '☕', '🪴', '🎹', '🧩', '🛸', '🐢', '🍓'];
const PAIR_BOARDS = [
  { rows: 3, cols: 4 }, { rows: 4, cols: 4 }, { rows: 4, cols: 5 },
  { rows: 4, cols: 6 }, { rows: 5, cols: 6 },
];
const PAIR_ROUNDS = 5;
const SEQUENCE_ROUNDS = 10;
const STROOP_ROUNDS = 10;
const REFLEX_TRIALS = 12;
const RECALL_ITEMS = [
  { word: 'APPLE', symbol: '🍎' }, { word: 'GUITAR', symbol: '🎸' }, { word: 'LADDER', symbol: '🪜' },
  { word: 'CANDLE', symbol: '🕯️' }, { word: 'TURTLE', symbol: '🐢' }, { word: 'PLANET', symbol: '🪐' },
  { word: 'FLOWER', symbol: '🌼' }, { word: 'CAMERA', symbol: '📷' }, { word: 'ANCHOR', symbol: '⚓' },
  { word: 'ORANGE', symbol: '🍊' }, { word: 'KEYBOARD', symbol: '⌨️' }, { word: 'CASTLE', symbol: '🏰' },
  { word: 'ROCKET', symbol: '🚀' }, { word: 'TEAPOT', symbol: '🫖' }, { word: 'BICYCLE', symbol: '🚲' },
  { word: 'SHELL', symbol: '🐚' }, { word: 'COMPASS', symbol: '🧭' }, { word: 'MUSHROOM', symbol: '🍄' },
  { word: 'BRIDGE', symbol: '🌉' }, { word: 'PENCIL', symbol: '✏️' },
];
const CHOICE_STIMULI = [
  { id: 'blue_circle', label: 'Blue circle', glyph: '●', color: '#4285f4' },
  { id: 'blue_square', label: 'Blue square', glyph: '■', color: '#4285f4' },
  { id: 'coral_circle', label: 'Coral circle', glyph: '●', color: '#ef806d' },
  { id: 'coral_square', label: 'Coral square', glyph: '■', color: '#ef806d' },
];
const CLIENT_TASK_SETTINGS = {
  stroop: [
    { incongruent_rate: 0.55 }, { incongruent_rate: 0.75 }, { incongruent_rate: 0.88 },
  ],
  reflex_simple: [
    { response_window_ms: 2200, wait_min_ms: 900, wait_max_ms: 2200 },
    { response_window_ms: 1800, wait_min_ms: 800, wait_max_ms: 1900 },
    { response_window_ms: 1500, wait_min_ms: 700, wait_max_ms: 1600 },
  ],
  reflex_choice: [
    { response_window_ms: 2600, choice_count: 2 },
    { response_window_ms: 2200, choice_count: 3 },
    { response_window_ms: 1800, choice_count: 4 },
  ],
  reflex_gonogo: [
    { response_window_ms: 1100, no_go_rate: 0.25 },
    { response_window_ms: 950, no_go_rate: 0.33 },
    { response_window_ms: 850, no_go_rate: 0.40 },
  ],
  delayed_recall: [
    { item_count: 6, study_seconds: 8, delay_seconds: 12 },
    { item_count: 8, study_seconds: 7, delay_seconds: 15 },
    { item_count: 10, study_seconds: 6, delay_seconds: 18 },
  ],
};
const TASK_ROUND_COUNTS = {
  pairs: PAIR_ROUNDS, color_pattern: SEQUENCE_ROUNDS, normal_pattern: SEQUENCE_ROUNDS,
  stroop: STROOP_ROUNDS, reflex_simple: 1, reflex_choice: 1, reflex_gonogo: 1, delayed_recall: 1,
};

const el = (id) => document.getElementById(id);
const state = {
  sessionId: null,
  participantCode: '',
  age: null,
  taskIndex: 0,
  difficulty: { pairs: 1, color_pattern: 1, normal_pattern: 1, stroop: 1, reflex_simple: 1, reflex_choice: 1, reflex_gonogo: 1, delayed_recall: 1 },
  results: [],
  currentRound: 1,
  renderToken: 0,
  isPaused: false,
  pauseStartedAt: 0,
  pausedTotalMs: 0,
  resultSummary: null,
  roundData: null,
  originalError: null,
  sequenceMemory: { color_pattern: [], normal_pattern: [] },
  stroopSchedule: [],
  developerOpen: false,
  developerSnapshot: null,
  taskSettings: {},
};

function activeNow() {
  const now = state.isPaused ? state.pauseStartedAt : performance.now();
  return now - state.pausedTotalMs;
}

function setScreen(name) {
  for (const [key, id] of [['welcome', 'welcomeScreen'], ['game', 'gameScreen'], ['results', 'resultsScreen']]) {
    el(id).classList.toggle('hidden', key !== name);
  }
  el('quitSession').classList.toggle('hidden', name !== 'game');
}

async function apiPost(path, payload) {
  const response = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  let result;
  try { result = await response.json(); } catch { throw new Error('The local analysis service returned an unreadable response.'); }
  if (!response.ok || !result.ok) throw new Error(result.error || 'The request could not be completed.');
  return result;
}

function showToast(message, duration = 3000) {
  const toast = el('toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timeout);
  showToast.timeout = setTimeout(() => toast.classList.remove('show'), duration);
}

function shuffle(items) {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

function getTaskSettings(game, level) {
  const current = state.taskSettings[game];
  if (current && (state.difficulty[game] || 1) === level) return current;
  const options = CLIENT_TASK_SETTINGS[game];
  return options ? options[level - 1] : {};
}

function average(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function sleepActive(milliseconds, token = state.renderToken) {
  return new Promise((resolve) => {
    let elapsed = 0;
    let previous = performance.now();
    const tick = () => {
      if (token !== state.renderToken) return resolve(false);
      const now = performance.now();
      if (!state.isPaused) elapsed += now - previous;
      previous = now;
      if (elapsed >= milliseconds) return resolve(true);
      setTimeout(tick, 24);
    };
    setTimeout(tick, 24);
  });
}

function updateProgress() {
  const currentTask = TASKS[state.taskIndex];
  const finishedGames = state.taskIndex;
  const taskRoundCount = TASK_ROUND_COUNTS[currentTask.key] || 1;
  const roundFraction = (state.currentRound - 1) / taskRoundCount;
  const totalFraction = clamp((finishedGames + Math.min(0.95, roundFraction) / 1.15) / TASKS.length, 0, .99);
  const percent = Math.round(totalFraction * 100);
  el('railProgressFill').style.width = `${percent}%`;
  el('railProgressText').textContent = `${finishedGames} of ${TASKS.length} games`;
  el('railPercent').textContent = `${percent}%`;
  document.querySelectorAll('.task-nav-item').forEach((item, index) => {
    item.classList.toggle('current', index === state.taskIndex);
    item.classList.toggle('done', index < state.taskIndex);
    const badge = item.querySelector('.nav-state');
    if (badge) badge.textContent = index < state.taskIndex ? '✓' : String(index + 1);
  });
}

function setGameHeader(task, round = 1) {
  el('gameKicker').textContent = `${task.kicker} · ROUND ${String(round).padStart(2, '0')}`;
  el('gameTitle').textContent = task.title;
  el('gameSubtitle').textContent = task.subtitle;
  const level = state.difficulty[task.key] || 1;
  el('difficultyLabel').textContent = ['Gentle level', 'Steady level', 'Challenge level'][level - 1] || 'Gentle level';
  updateProgress();
}

function stageHead(kicker, instruction, primaryValue, primaryLabel, secondaryValue, secondaryLabel) {
  return `<div class="task-stage-head">
    <div><div class="stage-kicker">${kicker}</div><p class="stage-instruction">${instruction}</p></div>
    <div class="stage-stats">
      <div class="stage-stat"><b>${primaryValue}</b><small>${primaryLabel}</small></div>
      <div class="stage-stat"><b>${secondaryValue}</b><small>${secondaryLabel}</small></div>
    </div>
  </div>`;
}

function setStageStatus(text, tone = '') {
  const status = el('stageStatus');
  if (!status) return;
  status.className = `stage-status ${tone}`.trim();
  status.innerHTML = `<span class="status-indicator"></span><span>${text}</span>`;
}

async function beginSession(event) {
  event.preventDefault();
  el('startError').textContent = '';
  const ageRaw = el('participantAge').value.trim();
  const age = ageRaw === '' ? null : Number(ageRaw);
  if (age !== null && (!Number.isInteger(age) || age < 18 || age > 110)) {
    el('startError').textContent = 'Enter an age between 18 and 110, or leave it blank.';
    return;
  }
  const startButton = el('startButton');
  startButton.disabled = true;
  startButton.querySelector('span:first-child').textContent = 'Connecting to Mesa…';
  try {
    const response = await apiPost('/api/session/start', {
      participant_code: el('participantCode').value,
      age,
    });
    state.sessionId = response.session_id;
    state.participantCode = el('participantCode').value.trim();
    state.age = age;
    state.difficulty = { ...state.difficulty, ...response.difficulty_levels };
    state.taskSettings = { ...(response.task_settings || {}) };
    state.taskIndex = 0;
    state.results = [];
    state.currentRound = 1;
    state.sequenceMemory = { color_pattern: [], normal_pattern: [] };
    state.stroopSchedule = [];
    state.developerSnapshot = null;
    state.pausedTotalMs = 0;
    state.isPaused = false;
    el('sessionShortId').textContent = response.session_id.slice(-8).toUpperCase();
    setScreen('game');
    launchTask(0);
  } catch (error) {
    el('startError').textContent = error.message;
  } finally {
    startButton.disabled = false;
    startButton.querySelector('span:first-child').textContent = 'Let’s play';
  }
}

function launchTask(index) {
  if (index >= TASKS.length) {
    finishSession();
    return;
  }
  state.taskIndex = index;
  state.currentRound = 1;
  state.renderToken += 1;
  state.roundData = null;
  const task = TASKS[index];
  setGameHeader(task, 1);
  if (task.key === 'pairs') startPairs(1);
  else if (task.key === 'color_pattern' || task.key === 'normal_pattern') {
    state.sequenceMemory[task.key] = [];
    const count = task.key === 'color_pattern' ? PALETTE.length : 9;
    while (state.sequenceMemory[task.key].length < 3) {
      state.sequenceMemory[task.key].push(nextPatternValue(state.sequenceMemory[task.key], count));
    }
    startSequenceRound(task.key, 1);
  } else if (task.key === 'stroop') {
    state.stroopSchedule = [];
    startStroopRound(1);
  } else if (task.key.startsWith('reflex_')) {
    startReflexRound(task.key);
  } else if (task.key === 'delayed_recall') {
    startDelayedRecall();
  }
}

function makeRoundMetrics(game, round, details) {
  const attempts = Math.max(1, details.attempts || 1);
  const correct = Math.max(0, details.correct_attempts || 0);
  const incorrect = Math.max(0, details.incorrect_attempts || 0);
  return {
    game,
    round,
    difficulty_level: state.difficulty[game] || 1,
    attempts,
    correct_attempts: correct,
    incorrect_attempts: incorrect,
    accuracy: correct / Math.max(1, correct + incorrect),
    error_rate: incorrect / attempts,
    mean_reaction_time_ms: Number(average(details.reaction_times || []).toFixed(2)),
    median_reaction_time_ms: Number(median(details.reaction_times || []).toFixed(2)),
    hesitation_count: details.hesitation_count || 0,
    completion_time_sec: Number((details.completion_time_sec || 0).toFixed(2)),
    sequence_length: details.sequence_length || undefined,
    matches_found: details.matches_found || undefined,
    total_pairs: details.total_pairs || undefined,
    word_reading_errors: details.word_reading_errors || undefined,
    trials: details.trials || undefined,
    trial_count: details.trial_count || undefined,
    valid_trial_count: details.valid_trial_count || undefined,
    median_reaction_time_ms: Number(median(details.reaction_times || []).toFixed(2)),
    reaction_time_variability_ms: Number((details.reaction_times && details.reaction_times.length > 1
      ? Math.sqrt(average(details.reaction_times.map((value) => (value - average(details.reaction_times)) ** 2))) : 0).toFixed(2)),
    false_starts: details.false_starts || undefined,
    omission_errors: details.omission_errors || undefined,
    commission_errors: details.commission_errors || undefined,
    immediate_total: details.immediate_total || undefined,
    immediate_recall_count: details.immediate_recall_count ?? undefined,
    delayed_total: details.delayed_total || undefined,
    delayed_recall_count: details.delayed_recall_count ?? undefined,
    recognition_hits: details.recognition_hits || undefined,
    recognition_misses: details.recognition_misses || undefined,
    recognition_false_alarms: details.recognition_false_alarms || undefined,
    recognition_correct_rejections: details.recognition_correct_rejections || undefined,
    distractor_taps: details.distractor_taps || undefined,
    target_count: details.target_count || undefined,
    lure_count: details.lure_count || undefined,
    task_parameters: details.task_parameters || undefined,
  };
}

function median(values) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

async function submitRound(telemetry, token) {
  setStageStatus('Mesa agents are reviewing this round…');
  try {
    const response = await apiPost('/api/score', {
      session_id: state.sessionId,
      telemetry,
    });
    if (token !== state.renderToken) return null;
    state.difficulty[telemetry.game] = response.dda_action.next_difficulty_level || state.difficulty[telemetry.game];
    if (response.dda_action.task_parameters) state.taskSettings[telemetry.game] = response.dda_action.task_parameters;
    const result = { telemetry, assessment: response.assessment, dda_action: response.dda_action };
    state.results.push(result);
    if (state.developerOpen) updateAgentPanel();
    return result;
  } catch (error) {
    showToast(`Couldn’t save this round: ${error.message}`, 5000);
    setStageStatus('The round was not saved. Check the local Mesa service and try again.', 'error');
    return null;
  }
}

function showFeedback(result, options) {
  const { title, message, buttonText, next } = options;
  const assessment = result.assessment || {};
  const dda = result.dda_action || {};
  const score = Math.round(assessment.Task_Performance_Score || 0);
  const accuracy = Math.round(assessment.Task_Accuracy_Percent || 0);
  const reaction = Math.round(assessment.Mean_RT_ms || 0);
  const mistakes = Number(assessment.Incorrect_Attempts || 0);
  const reason = dda.reason || 'The current difficulty is being kept steady.';
  const breakNote = dda.micro_break_recommended
    ? '<div class="micro-break-note"><b>A small reset might help.</b><span>The agent noticed a tricky round. Take a breath before continuing, or pause with Esc.</span></div>'
    : '';
  const screenerExplanation = assessment.Decision_Explanation || 'The screener used task-specific performance measurements.';
  const metricsUsed = (assessment.Metrics_Used || dda.metrics_used || []).join(', ') || 'Task metrics';
  const uncertainty = assessment.Uncertainty_95pct_Points == null ? 'Not enough evidence yet' : `±${Math.round(assessment.Uncertainty_95pct_Points)} score points (exploratory)`;
  const evidence = assessment.Evidence_Sample_Count == null ? 'Sample size not reported' : `${assessment.Evidence_Sample_Count} observations · confidence ${Math.round((assessment.Evidence_Confidence || 0) * 100)}%`;
  const settingsChanged = dda.before_parameters && dda.after_parameters
    ? `<div class="settings-diff"><span>Before <b>${escapeHTML(JSON.stringify(dda.before_parameters))}</b></span><span>After <b>${escapeHTML(JSON.stringify(dda.after_parameters))}</b></span></div>` : '';
  const qualityFlags = (assessment.Data_Quality_Flags || []).map((flag) => `<li>${escapeHTML(flag)}</li>`).join('');
  el('gameMount').innerHTML = `<div class="feedback-wrap">
    <div class="feedback-icon">✦</div>
    <div class="stage-kicker">ROUND REVIEW · MESA MULTI-AGENT ANALYSIS</div>
    <h3>${title}</h3>
    <p class="feedback-copy">${message}</p>
    <div class="feedback-score-row">
      <div class="feedback-score"><strong>${score}</strong><span>PLAY SCORE</span></div>
      <div class="feedback-stats">
        <div><strong>${accuracy}%</strong><span>Accuracy</span></div>
        <div><strong>${reaction}<small style="font-size:10px;color:var(--subtle)"> ms</small></strong><span>Average response</span></div>
        <div><strong>${mistakes}</strong><span>Misses / retries</span></div>
      </div>
    </div>
    <div class="feedback-reason"><b>Adaptive agent decision</b><p>${escapeHTML(reason)} Next setting: ${escapeHTML(dda.difficulty_name || 'Gentle')}.</p>${settingsChanged}</div>
    <details class="agent-explanation"><summary>Why did the agents decide this?</summary><p><b>ScreenerAgent:</b> ${escapeHTML(screenerExplanation)}</p><p><b>Metrics used:</b> ${escapeHTML(metricsUsed)}.</p><p><b>Evidence:</b> ${escapeHTML(evidence)}. Approximate score uncertainty: ${escapeHTML(uncertainty)}.</p>${qualityFlags ? `<p><b>Quality notes</b><ul>${qualityFlags}</ul></p>` : ''}<p class="agent-disclaimer">Performance analytics only. These values are not diagnostic probabilities or clinical reference scores.</p></details>
    ${breakNote}
    <button class="primary-button" id="continueButton" type="button"><span>${buttonText}</span><span class="button-arrow">↗</span></button>
  </div>`;
  el('continueButton').addEventListener('click', next, { once: true });
}

function nextTaskButtonLabel(isLastRound) {
  if (!isLastRound) return 'Next round';
  if (state.taskIndex === TASKS.length - 1) return 'View your profile';
  return 'Continue to next game';
}

function continueAfterRound(game, round, maxRound) {
  const isLastRound = round >= maxRound;
  if (isLastRound) {
    if (state.taskIndex === TASKS.length - 1) finishSession();
    else launchTask(state.taskIndex + 1);
    return;
  }
  state.currentRound = round + 1;
  if (game === 'color_pattern' || game === 'normal_pattern') {
    const count = game === 'color_pattern' ? PALETTE.length : 9;
    state.sequenceMemory[game].push(nextPatternValue(state.sequenceMemory[game], count));
  }
  if (game === 'pairs') startPairs(round + 1);
  else if (game === 'stroop') startStroopRound(round + 1);
  else if (game.startsWith('reflex_')) startReflexRound(game);
  else if (game === 'delayed_recall') startDelayedRecall();
  else startSequenceRound(game, round + 1);
}

// Game 1: associative memory, with increasingly large matching boards.
function startPairs(round) {
  state.currentRound = round;
  const task = TASKS[0];
  setGameHeader(task, round);
  const token = ++state.renderToken;
  const difficulty = clamp(state.difficulty.pairs || 1, 1, 3);
  const boardIndex = clamp(round + difficulty - 2, 1, PAIR_BOARDS.length);
  const board = PAIR_BOARDS[boardIndex - 1];
  const pairCount = (board.rows * board.cols) / 2;
  const symbols = shuffle(CARD_SYMBOLS).slice(0, pairCount);
  let cards = shuffle(symbols.flatMap((symbol, pairId) => [
    { symbol, pairId, flipped: false, matched: false, index: pairId * 2 },
    { symbol, pairId, flipped: false, matched: false, index: pairId * 2 + 1 },
  ])).map((card, index) => ({ ...card, index }));
  let flipped = [];
  let locked = false;
  let matches = 0;
  let attempts = 0;
  let errors = 0;
  let hesitationCount = 0;
  let reactionTimes = [];
  let lastAction = activeNow();
  const startedAt = activeNow();

  el('gameMount').innerHTML = `${stageHead(`BOARD ${round} OF ${PAIR_ROUNDS}`, 'Turn over two cards at a time and try to find every matching pair.', pairCount, 'Pairs', '0', 'Found')}
    <div class="pairs-board" id="pairsBoard" style="grid-template-columns:repeat(${board.cols},minmax(0,1fr));grid-template-rows:repeat(${board.rows},minmax(0,1fr))"></div>
    <div class="stage-status" id="stageStatus"><span class="status-indicator"></span><span>Choose any card to begin.</span></div>`;
  const boardNode = el('pairsBoard');
  cards.forEach((card) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'memory-card is-back';
    button.setAttribute('aria-label', `Card ${card.index + 1}, face down`);
    button.innerHTML = '<span class="card-glyph">✳</span>';
    button.addEventListener('click', () => flipCard(card, button));
    card.node = button;
    boardNode.appendChild(button);
  });

  function flipCard(card, button) {
    if (state.isPaused || token !== state.renderToken || locked || card.flipped || card.matched) return;
    const now = activeNow();
    const reaction = Math.max(0, now - lastAction);
    if (reaction > 0) {
      reactionTimes.push(reaction);
      if (reaction >= 3000) hesitationCount += 1;
    }
    lastAction = now;
    card.flipped = true;
    button.classList.remove('is-back');
    button.classList.add('is-front');
    button.setAttribute('aria-label', `Card ${card.index + 1}, ${card.symbol}`);
    button.innerHTML = `<span class="card-glyph">${card.symbol}</span>`;
    flipped.push(card);
    if (flipped.length < 2) return;

    attempts += 1;
    const [first, second] = flipped;
    if (first.pairId === second.pairId) {
      first.matched = true;
      second.matched = true;
      first.node.classList.remove('is-front');
      second.node.classList.remove('is-front');
      first.node.classList.add('is-matched');
      second.node.classList.add('is-matched');
      first.node.disabled = true;
      second.node.disabled = true;
      matches += 1;
      flipped = [];
      const stats = document.querySelectorAll('.stage-stat b');
      if (stats.length > 1) stats[1].textContent = String(matches);
      setStageStatus('Nice match. Keep going!', 'success');
      if (matches === pairCount) finishBoard();
    } else {
      errors += 1;
      locked = true;
      setStageStatus('Not a match this time. Have another look.', 'error');
      sleepActive(720, token).then((stillHere) => {
        if (!stillHere || token !== state.renderToken) return;
        first.flipped = false;
        second.flipped = false;
        for (const item of [first, second]) {
          item.node.classList.remove('is-front');
          item.node.classList.add('is-back');
          item.node.innerHTML = '<span class="card-glyph">✳</span>';
          item.node.setAttribute('aria-label', `Card ${item.index + 1}, face down`);
        }
        flipped = [];
        locked = false;
        lastAction = activeNow();
        setStageStatus('Ready when you are.');
      });
    }
  }

  async function finishBoard() {
    locked = true;
    const now = activeNow();
    const telemetry = makeRoundMetrics('pairs', round, {
      attempts,
      correct_attempts: matches,
      incorrect_attempts: errors,
      reaction_times: reactionTimes,
      hesitation_count: hesitationCount,
      completion_time_sec: (now - startedAt) / 1000,
      matches_found: matches,
      total_pairs: pairCount,
    });
    const result = await submitRound(telemetry, token);
    if (!result || token !== state.renderToken) return;
    const lastRound = round >= PAIR_ROUNDS;
    showFeedback(result, {
      title: lastRound ? 'Pairs, complete.' : 'Board cleared.',
      message: `You found ${matches} ${matches === 1 ? 'pair' : 'pairs'} on board ${round}. Each new board gives the agents another performance sample.`,
      buttonText: nextTaskButtonLabel(lastRound),
      next: () => continueAfterRound('pairs', round, PAIR_ROUNDS),
    });
  }
}

function nextPatternValue(sequence, optionCount) {
  let choices = Array.from({ length: optionCount }, (_, index) => index);
  if (sequence.length >= 2 && sequence[sequence.length - 1] === sequence[sequence.length - 2]) {
    choices = choices.filter((value) => value !== sequence[sequence.length - 1]);
  }
  return choices[Math.floor(Math.random() * choices.length)];
}

// Game 2 and 3: sequence memory. Both use a watch-then-repeat loop, but one
// scores color order and the other scores the locations of lit tiles.
function startSequenceRound(game, round) {
  state.currentRound = round;
  const task = TASKS.find((item) => item.key === game);
  setGameHeader(task, round);
  const token = ++state.renderToken;
  const difficulty = clamp(state.difficulty[game] || 1, 1, 3);
  const shape = game === 'normal_pattern' ? { rows: 3, cols: 3 } : { rows: 2, cols: 4 };
  const palette = game === 'color_pattern' ? PALETTE : null;
  const optionCount = game === 'color_pattern' ? PALETTE.length : 9;
  const sequence = [...state.sequenceMemory[game]];
  const sequenceLength = sequence.length;
  const flashTime = [760, 620, 500][difficulty - 1];
  const gapTime = [280, 230, 180][difficulty - 1];
  let input = [];
  let submissionCount = 0;
  let mistakes = 0;
  let hesitationCount = 0;
  let reactionTimes = [];
  let lastAction = 0;
  let waitingForInput = false;
  const startedAt = activeNow();

  const pads = Array.from({ length: optionCount }, (_, index) => {
    const label = game === 'color_pattern' ? palette[index].name : `Tile ${index + 1}`;
    const padStyle = game === 'color_pattern'
      ? `background:${palette[index].hex};--pad-glow:${palette[index].glow};${index >= 4 ? `grid-column:${index - 2};` : ''}`
      : 'background:linear-gradient(145deg,rgba(122,143,178,.36),rgba(67,80,113,.55));--pad-glow:rgba(142,229,225,.45);';
    return `<button class="sequence-pad" type="button" data-index="${index}" aria-label="${label}" style="${padStyle}" disabled><span class="pad-number">${game === 'color_pattern' ? '' : String(index + 1).padStart(2, '0')}</span></button>`;
  }).join('');
  const sequenceDots = Array.from({ length: sequenceLength }, () => '<span class="sequence-dot"></span>').join('');
  el('gameMount').innerHTML = `${stageHead(`LEVEL ${round} OF ${SEQUENCE_ROUNDS}`, game === 'color_pattern' ? 'Watch the color sequence, then tap each color in the same order.' : 'Watch the 3 × 3 grid light up, then tap the same tiles in order.', sequenceLength, 'Steps', '0', 'Recalled')}
    <div class="sequence-layout"><div class="sequence-grid" id="sequenceGrid" style="grid-template-columns:repeat(${shape.cols},minmax(0,1fr));grid-template-rows:repeat(${shape.rows},minmax(0,1fr))">${pads}</div>
    <div class="sequence-hint" id="sequenceHint"><span class="hint-icon">✦</span><span>Watch closely. The sequence is about to begin.</span></div>
    <div class="sequence-footer" id="sequenceDots">${sequenceDots}</div></div>
    <div class="stage-status" id="stageStatus"><span class="status-indicator"></span><span>Get ready to remember ${sequenceLength} steps.</span></div>`;
  const padNodes = [...document.querySelectorAll('.sequence-pad')];
  const dotNodes = [...document.querySelectorAll('.sequence-dot')];

  padNodes.forEach((pad) => pad.addEventListener('click', () => {
    if (state.isPaused || token !== state.renderToken || !waitingForInput || pad.disabled) return;
    const index = Number(pad.dataset.index);
    const now = activeNow();
    const reaction = Math.max(0, now - lastAction);
    reactionTimes.push(reaction);
    if (reaction >= 3000) hesitationCount += 1;
    lastAction = now;
    input.push(index);
    pad.classList.add('active');
    sleepActive(120, token).then((stillHere) => { if (stillHere) pad.classList.remove('active'); });
    if (dotNodes[input.length - 1]) dotNodes[input.length - 1].classList.add('filled');
    const sequenceStats = document.querySelectorAll('.stage-stat b');
    if (sequenceStats.length > 1) sequenceStats[1].textContent = String(input.length);
    if (input.length < sequence.length) return;

    waitingForInput = false;
    submissionCount += 1;
    const correct = input.every((value, position) => value === sequence[position]);
    if (correct) completeSequence();
    else {
      mistakes += 1;
      setStageStatus('Almost. Watch it once more and give it another try.', 'error');
      el('sequenceHint').innerHTML = '<span class="hint-icon">↻</span><span>Take another look. This level stays the same.</span>';
      sleepActive(600, token).then((stillHere) => { if (stillHere) previewSequence(); });
    }
  }));

  previewSequence();

  async function previewSequence() {
    if (token !== state.renderToken) return;
    waitingForInput = false;
    input = [];
    dotNodes.forEach((dot) => dot.classList.remove('filled'));
    padNodes.forEach((pad) => { pad.disabled = true; pad.classList.remove('active'); });
    el('sequenceHint').innerHTML = '<span class="hint-icon">✦</span><span>Watch the pattern. Your turn comes next.</span>';
    setStageStatus(`Memorize ${sequenceLength} steps.`);
    for (const index of sequence) {
      if (token !== state.renderToken) return;
      padNodes[index].classList.add('active');
      await sleepActive(flashTime, token);
      padNodes[index].classList.remove('active');
      await sleepActive(gapTime, token);
    }
    if (token !== state.renderToken) return;
    padNodes.forEach((pad) => { pad.disabled = false; });
    waitingForInput = true;
    lastAction = activeNow();
    el('sequenceHint').innerHTML = '<span class="hint-icon">↳</span><span>Your turn. Repeat the steps in order.</span>';
    setStageStatus('Tap the sequence from memory.');
  }

  async function completeSequence() {
    padNodes.forEach((pad) => { pad.disabled = true; });
    const telemetry = makeRoundMetrics(game, round, {
      attempts: submissionCount,
      correct_attempts: 1,
      incorrect_attempts: mistakes,
      reaction_times: reactionTimes,
      hesitation_count: hesitationCount,
      completion_time_sec: (activeNow() - startedAt) / 1000,
      sequence_length: sequenceLength,
    });
    const result = await submitRound(telemetry, token);
    if (!result || token !== state.renderToken) return;
    const lastRound = round >= SEQUENCE_ROUNDS;
    showFeedback(result, {
      title: lastRound ? 'Pattern master.' : 'Pattern recalled.',
      message: `You reproduced ${sequenceLength} steps in order${mistakes ? `, with ${mistakes} ${mistakes === 1 ? 'retry' : 'retries'} along the way` : ' on the first try'}. One new step is added to the sequence for the next level.`,
      buttonText: nextTaskButtonLabel(lastRound),
      next: () => continueAfterRound(game, round, SEQUENCE_ROUNDS),
    });
  }
}

function activeWait(milliseconds, token, shouldStop = () => false) {
  return (async () => {
    const startedAt = activeNow();
    while (activeNow() - startedAt < milliseconds) {
      if (token !== state.renderToken) return false;
      if (shouldStop()) return true;
      const remaining = milliseconds - (activeNow() - startedAt);
      if (!await sleepActive(Math.min(30, Math.max(1, remaining)), token)) return false;
    }
    return token === state.renderToken;
  })();
}

// Reflex Lab: trial-level logs are retained so median latency, variability,
// anticipations, omissions and inhibition slips remain visible to the agents.
function startReflexRound(game) {
  state.currentRound = 1;
  const task = TASKS.find((item) => item.key === game);
  setGameHeader(task, 1);
  const token = ++state.renderToken;
  const level = clamp(state.difficulty[game] || 1, 1, 3);
  const settings = getTaskSettings(game, level);
  const trials = [];
  const reactionTimes = [];
  let validTrialCount = 0;
  let correctCount = 0;
  let incorrectCount = 0;
  let falseStarts = 0;
  let omissionErrors = 0;
  let commissionErrors = 0;
  let phase = 'idle';
  let premature = false;
  let responded = false;
  let responseValue = null;
  let currentStimulus = null;
  let currentIsTarget = true;
  let onsetAt = 0;
  const startedAt = activeNow();
  const choiceButtons = game === 'reflex_choice'
    ? `<div class="reflex-choice-grid" id="reflexChoiceButtons">${CHOICE_STIMULI.map((item) => `<button class="reflex-choice" type="button" data-choice="${item.id}" hidden><span style="color:${item.color}">${item.glyph}</span><b>${item.label}</b></button>`).join('')}</div>`
    : '';
  el('gameMount').innerHTML = `${stageHead('REFLEX LAB · 12 TRIALS', task.subtitle, '0', 'Correct', '0', 'Trials')}
    <div class="reflex-layout">
      <p class="reflex-instruction" id="reflexInstruction">Press begin when you’re ready. Keep your hands relaxed and wait for each cue.</p>
      <div class="reflex-stimulus-wrap"><button id="reflexTarget" class="reflex-target is-ready" type="button" aria-label="Reaction target"><span class="reflex-target-glyph">✦</span><b>Ready?</b></button></div>
      ${choiceButtons}
      <div class="reflex-trial-progress" id="reflexTrialProgress"><span></span></div>
      <div class="reflex-live-stats"><span>False starts <b id="reflexFalseStarts">0</b></span><span>Median response <b id="reflexMedian">—</b></span></div>
      <button class="primary-button reflex-start" id="reflexStart" type="button">Begin 12 trials <span class="button-arrow">↗</span></button>
    </div>
    <div class="stage-status" id="stageStatus"><span class="status-indicator"></span><span>Ready when you are.</span></div>`;

  const targetNode = el('reflexTarget');
  const startNode = el('reflexStart');
  const choiceNodes = [...document.querySelectorAll('.reflex-choice')];

  function respond(value) {
    if (state.isPaused || token !== state.renderToken || phase === 'idle' || phase === 'between' || phase === 'done') return;
    if (phase === 'waiting') {
      premature = true;
      setStageStatus('That was early. Wait for the cue, then try again.', 'error');
      return;
    }
    if (phase !== 'active' || responded) return;
    responded = true;
    responseValue = value;
  }
  targetNode.addEventListener('click', () => { if (game === 'reflex_choice' && phase === 'active') return; respond('target'); });
  choiceNodes.forEach((button) => button.addEventListener('click', () => respond(button.dataset.choice)));

  async function runTrials() {
    startNode.disabled = true;
    startNode.classList.add('hidden');
    phase = 'waiting';
    const goNoGoPlan = Array(REFLEX_TRIALS).fill(true);
    if (game === 'reflex_gonogo') {
      const noGoCount = Math.max(2, Math.round(REFLEX_TRIALS * settings.no_go_rate));
      for (let i = 0; i < noGoCount; i += 1) goNoGoPlan[i] = false;
      shuffle(goNoGoPlan);
    }

    let attemptsGuard = 0;
    while (validTrialCount < REFLEX_TRIALS && attemptsGuard < REFLEX_TRIALS * 4) {
      attemptsGuard += 1;
      premature = false;
      responded = false;
      responseValue = null;
      const nextTrialNumber = validTrialCount + 1;
      const targetList = game === 'reflex_choice'
        ? shuffle(CHOICE_STIMULI).slice(0, settings.choice_count)
        : [];
      currentStimulus = game === 'reflex_choice'
        ? targetList[Math.floor(Math.random() * targetList.length)]
        : null;
      currentIsTarget = game === 'reflex_gonogo' ? goNoGoPlan[validTrialCount] : true;
      const waitMinimum = settings.wait_min_ms || 700;
      const waitMaximum = settings.wait_max_ms || 1700;
      const waitMs = waitMinimum + Math.random() * (waitMaximum - waitMinimum);
      phase = 'waiting';
      targetNode.className = 'reflex-target is-waiting';
      targetNode.innerHTML = '<span class="reflex-target-glyph">···</span><b>Wait for it</b>';
      choiceNodes.forEach((button) => {
        const item = CHOICE_STIMULI.find((entry) => entry.id === button.dataset.choice);
        button.hidden = game !== 'reflex_choice' || !targetList.some((choice) => choice.id === item.id);
        button.classList.remove('is-correct', 'is-wrong');
      });
      el('reflexInstruction').textContent = game === 'reflex_gonogo'
        ? 'Wait for the cue. Click GO cues only, and do nothing for NO-GO cues.'
        : game === 'reflex_choice' ? 'Wait for the symbol. Then choose the matching label.' : 'Wait until the target glows, then click it.';
      setStageStatus(`Trial ${nextTrialNumber} of ${REFLEX_TRIALS}. Wait for the cue.`);
      await activeWait(waitMs, token, () => premature);
      if (token !== state.renderToken) return;
      if (premature) {
        falseStarts += 1;
        incorrectCount += 1;
        trials.push({ trial: nextTrialNumber, kind: game, stimulus: 'anticipatory response', response: 'early_click', correct: false, outcome: 'false_start', reaction_time_ms: null, difficulty_level: level });
        el('reflexFalseStarts').textContent = String(falseStarts);
        phase = 'between';
        setStageStatus('Early response recorded. The trial will repeat.', 'error');
        await sleepActive(380, token);
        continue;
      }

      phase = 'active';
      onsetAt = activeNow();
      targetNode.className = `reflex-target ${game === 'reflex_gonogo' && !currentIsTarget ? 'is-no-go' : 'is-go'}`;
      if (game === 'reflex_simple') {
        targetNode.innerHTML = '<span class="reflex-target-glyph">✦</span><b>NOW</b>';
      } else if (game === 'reflex_choice') {
        targetNode.innerHTML = `<span class="reflex-choice-stimulus" style="color:${currentStimulus.color}">${currentStimulus.glyph}</span><b>Match the symbol</b>`;
      } else {
        targetNode.innerHTML = currentIsTarget
          ? '<span class="reflex-target-glyph">●</span><b>GO</b>'
          : '<span class="reflex-target-glyph">■</span><b>NO GO</b>';
      }
      setStageStatus(game === 'reflex_gonogo' && !currentIsTarget ? 'Hold your response for NO-GO.' : 'Respond now.');
      const windowMs = settings.response_window_ms;
      await activeWait(windowMs, token, () => responded);
      if (token !== state.renderToken) return;

      let isCorrect = false;
      let outcome = '';
      let rt = null;
      if (responded) {
        rt = Math.max(0, activeNow() - onsetAt);
        reactionTimes.push(rt);
        if (game === 'reflex_gonogo' && !currentIsTarget) {
          commissionErrors += 1;
          outcome = 'commission_error';
        } else if (game === 'reflex_choice') {
          isCorrect = responseValue === currentStimulus.id;
          outcome = isCorrect ? 'correct_choice' : 'incorrect_choice';
        } else {
          isCorrect = true;
          outcome = 'hit';
        }
      } else if (game === 'reflex_gonogo' && !currentIsTarget) {
        isCorrect = true;
        outcome = 'correct_withhold';
      } else {
        omissionErrors += 1;
        outcome = 'omission';
      }
      if (isCorrect) correctCount += 1;
      else incorrectCount += 1;
      trials.push({
        trial: nextTrialNumber, kind: game,
        stimulus: game === 'reflex_choice' ? currentStimulus.id : (game === 'reflex_gonogo' ? (currentIsTarget ? 'GO' : 'NO_GO') : 'target'),
        expected: game === 'reflex_choice' ? currentStimulus.id : (game === 'reflex_gonogo' ? (currentIsTarget ? 'respond' : 'withhold') : 'respond'),
        response: responded ? responseValue : 'none', correct: isCorrect, outcome,
        reaction_time_ms: rt == null ? null : Math.round(rt), target: currentIsTarget, difficulty_level: level,
      });
      validTrialCount += 1;
      el('reflexTrialProgress').innerHTML = `<span style="width:${(validTrialCount / REFLEX_TRIALS) * 100}%"></span>`;
      el('reflexTrialProgress').classList.add('is-animated');
      el('reflexTrialProgress').setAttribute('aria-label', `${validTrialCount} of ${REFLEX_TRIALS} trials complete`);
      el('reflexFalseStarts').textContent = String(falseStarts);
      el('reflexMedian').textContent = reactionTimes.length ? `${Math.round(median(reactionTimes))} ms` : '—';
      choiceNodes.forEach((button) => {
        if (game === 'reflex_choice' && button.dataset.choice === currentStimulus.id) button.classList.add(isCorrect ? 'is-correct' : 'is-wrong');
      });
      targetNode.className = `reflex-target ${isCorrect ? 'is-correct' : 'is-wrong'}`;
      targetNode.innerHTML = `<span class="reflex-target-glyph">${isCorrect ? '✓' : '·'}</span><b>${isCorrect ? 'Good response' : outcome === 'commission_error' ? 'Response held next time' : outcome === 'omission' ? 'No response recorded' : 'Check the cue'}</b>`;
      setStageStatus(`Trial ${validTrialCount} of ${REFLEX_TRIALS} complete: ${outcome.replaceAll('_', ' ')}.`, isCorrect ? 'success' : 'error');
      phase = 'between';
      await sleepActive(320, token);
    }
    if (token !== state.renderToken) return;
    phase = 'done';
    targetNode.className = 'reflex-target is-ready';
    targetNode.innerHTML = '<span class="reflex-target-glyph">✦</span><b>Block complete</b>';
    choiceNodes.forEach((button) => { button.hidden = true; });
    const telemetry = makeRoundMetrics(game, 1, {
      attempts: Math.max(1, correctCount + incorrectCount), correct_attempts: correctCount,
      incorrect_attempts: incorrectCount, reaction_times: reactionTimes,
      completion_time_sec: (activeNow() - startedAt) / 1000,
      trials, trial_count: trials.length, valid_trial_count: validTrialCount,
      false_starts: falseStarts, omission_errors: omissionErrors, commission_errors: commissionErrors,
      task_parameters: settings,
    });
    const result = await submitRound(telemetry, token);
    if (!result || token !== state.renderToken) return;
    const message = game === 'reflex_gonogo'
      ? `You completed ${validTrialCount} go/ no-go trials with ${commissionErrors} commission errors, ${omissionErrors} missed GO targets and ${falseStarts} early responses.`
      : `You completed ${validTrialCount} trials with a median response of ${Math.round(median(reactionTimes)) || 0} ms and ${falseStarts} early responses.`;
    showFeedback(result, {
      title: 'Reflex Lab, complete.', message,
      buttonText: nextTaskButtonLabel(true),
      next: () => continueAfterRound(game, 1, 1),
    });
  }
  startNode.addEventListener('click', runTrials, { once: true });
}

function normalizeRecallInput(value) {
  return value.toUpperCase().replace(/[^A-Z\s,;\n]/g, ' ').split(/[\s,;]+/).filter(Boolean);
}

function renderRecallEntry(stageTitle, prompt, total, onSubmit, token) {
  if (token !== state.renderToken) return;
  let submitted = false;
  el('gameMount').innerHTML = `${stageHead(stageTitle, prompt, total, 'Items in list', '—', 'Recall')}
    <div class="recall-entry-wrap"><div class="recall-entry-icon">✎</div><label for="recallAnswer" class="recall-entry-label">Type the words you remember</label><textarea id="recallAnswer" rows="3" autocomplete="off" spellcheck="false" placeholder="Separate words with commas or spaces"></textarea>
    <p class="recall-helper">Use any order. Spelling should be close enough to recognize the original word.</p><button class="primary-button" id="recallSubmit" type="button">Submit recall <span class="button-arrow">↗</span></button></div>
    <div class="stage-status" id="stageStatus"><span class="status-indicator"></span><span>Take a moment and enter the items you remember.</span></div>`;
  const submit = () => {
    if (submitted || token !== state.renderToken) return;
    submitted = true;
    const value = el('recallAnswer').value;
    el('recallSubmit').disabled = true;
    el('recallAnswer').disabled = true;
    onSubmit(value);
  };
  el('recallSubmit').addEventListener('click', submit, { once: true });
  el('recallAnswer').addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      submit();
    }
  });
  el('recallAnswer').focus();
}

// Delayed Recall separates initial encoding, immediate free recall, distraction,
// delayed free recall and recognition. Only counts are stored, not typed answer text.
function startDelayedRecall() {
  state.currentRound = 1;
  const task = TASKS.find((item) => item.key === 'delayed_recall');
  setGameHeader(task, 1);
  const token = ++state.renderToken;
  const level = clamp(state.difficulty.delayed_recall || 1, 1, 3);
  const settings = getTaskSettings('delayed_recall', level);
  const itemCount = settings.item_count;
  const studyItems = shuffle(RECALL_ITEMS).slice(0, itemCount);
  const targetWords = new Set(studyItems.map((item) => item.word));
  let immediateCount = 0;
  let delayedCount = 0;
  let distractorTaps = 0;
  const recognitionTrials = [];
  const recognitionTimes = [];
  const startedAt = activeNow();

  el('gameMount').innerHTML = `${stageHead('MEMORY LAB · LEARN', 'Study the words and symbols. They will disappear before the recall questions.', itemCount, 'Items', settings.study_seconds, 'Seconds')}
    <div class="recall-study-wrap"><div class="recall-countdown" id="recallCountdown">${settings.study_seconds}</div><div class="recall-study-grid">${studyItems.map((item) => `<div class="recall-study-item"><span>${item.symbol}</span><b>${item.word}</b></div>`).join('')}</div><p>Try to learn each word. You will be asked to recall them without seeing the list.</p></div>
    <div class="stage-status" id="stageStatus"><span class="status-indicator"></span><span>Study the list until the timer ends.</span></div>`;
  (async () => {
    const totalMs = settings.study_seconds * 1000;
    const beginAt = activeNow();
    while (activeNow() - beginAt < totalMs) {
      if (!await sleepActive(200, token)) return;
      const seconds = Math.max(0, Math.ceil((totalMs - (activeNow() - beginAt)) / 1000));
      const countdown = el('recallCountdown');
      if (countdown) countdown.textContent = String(seconds);
    }
    if (token !== state.renderToken) return;
    renderRecallEntry('MEMORY LAB · IMMEDIATE RECALL', 'The list has disappeared. Type any words you remember right now.', itemCount, (answer) => {
      const recalled = new Set(normalizeRecallInput(answer));
      immediateCount = [...targetWords].filter((word) => recalled.has(word)).length;
      const immediateIncorrect = Math.max(0, itemCount - immediateCount);
      (async () => {
        if (token !== state.renderToken) return;
        await runRecallDistractor(token, settings.delay_seconds, () => { distractorTaps += 1; });
        if (token !== state.renderToken) return;
        renderRecallEntry('MEMORY LAB · DELAYED RECALL', `After the brief distraction, recall the same ${itemCount} words again without seeing the list.`, itemCount, (delayedAnswer) => {
          const delayed = new Set(normalizeRecallInput(delayedAnswer));
          delayedCount = [...targetWords].filter((word) => delayed.has(word)).length;
          const lures = shuffle(RECALL_ITEMS.filter((item) => !targetWords.has(item.word))).slice(0, itemCount);
          const recognitionDeck = shuffle([
            ...studyItems.map((item) => ({ ...item, isTarget: true })),
            ...lures.map((item) => ({ ...item, isTarget: false })),
          ]);
          runRecognition(recognitionDeck, 0);
        }, token);
      })();
    }, token);
  })();

  async function runRecallDistractor(currentToken, durationSeconds, onTap) {
    el('gameMount').innerHTML = `${stageHead('MEMORY LAB · DISTRACTION', 'Tap the floating shape while the delay passes. This is a simple non-memory activity.', itemCount, 'Items learned', durationSeconds, 'Seconds')}
      <div class="distractor-stage" id="distractorStage"><div class="distractor-countdown" id="distractorCountdown">${durationSeconds}</div><button class="distractor-target" id="distractorTarget" type="button" aria-label="Tap the floating shape">✦</button><div class="distractor-tap-count">Taps <b id="distractorTapCount">0</b></div></div>
      <div class="stage-status" id="stageStatus"><span class="status-indicator"></span><span>Keep your attention on the floating shape.</span></div>`;
    const stage = el('distractorStage');
    const target = el('distractorTarget');
    target.addEventListener('click', () => {
      onTap();
      const count = el('distractorTapCount');
      if (count) count.textContent = String(distractorTaps);
      target.classList.remove('tap-pop');
      void target.offsetWidth;
      target.classList.add('tap-pop');
    });
    const durationMs = durationSeconds * 1000;
    const beginAt = activeNow();
    while (activeNow() - beginAt < durationMs) {
      if (!await sleepActive(220, currentToken)) return;
      const remaining = Math.max(0, Math.ceil((durationMs - (activeNow() - beginAt)) / 1000));
      const count = el('distractorCountdown');
      if (count) count.textContent = String(remaining);
      if (stage && target) {
        target.style.left = `${8 + Math.random() * 78}%`;
        target.style.top = `${18 + Math.random() * 55}%`;
      }
    }
  }

  function runRecognition(deck, index) {
    if (token !== state.renderToken) return;
    if (index >= deck.length) {
      finishDelayedRecall();
      return;
    }
    const item = deck[index];
    const onset = activeNow();
    el('gameMount').innerHTML = `${stageHead('MEMORY LAB · RECOGNITION', 'Did this word appear in the original list? Answer yes or no.', deck.length, 'Trials', index + 1, 'Current')}
      <div class="recognition-wrap"><div class="recognition-card"><span>${item.symbol}</span><b>${item.word}</b></div><div class="recognition-actions"><button class="secondary-button recognition-choice" id="recognitionNo" type="button">No, new word</button><button class="primary-button recognition-choice" id="recognitionYes" type="button">Yes, I saw it</button></div><div class="recognition-progress"><span style="width:${(index / deck.length) * 100}%"></span></div></div>
      <div class="stage-status" id="stageStatus"><span class="status-indicator"></span><span>Trust your memory. Do not worry about guessing.</span></div>`;
    const answer = (saw) => {
      const reaction = Math.max(0, activeNow() - onset);
      const correct = saw === item.isTarget;
      reactionTimesSafePush(recognitionTimes, reaction);
      if (item.isTarget && saw) recognitionStats.hits += 1;
      else if (item.isTarget && !saw) recognitionStats.misses += 1;
      else if (!item.isTarget && saw) recognitionStats.falseAlarms += 1;
      else recognitionStats.correctRejections += 1;
      recognitionTrials.push({ trial: index + 1, kind: 'recognition', stimulus: item.word, expected: item.isTarget ? 'yes' : 'no', response: saw ? 'yes' : 'no', correct, outcome: correct ? 'correct' : 'incorrect', reaction_time_ms: Math.round(reaction) });
      runRecognition(deck, index + 1);
    };
    el('recognitionNo').addEventListener('click', () => answer(false), { once: true });
    el('recognitionYes').addEventListener('click', () => answer(true), { once: true });
  }

  const recognitionStats = { hits: 0, misses: 0, falseAlarms: 0, correctRejections: 0 };
  function reactionTimesSafePush(list, value) {
    if (Number.isFinite(value) && value >= 0) list.push(value);
  }

  async function finishDelayedRecall() {
    const allTrials = [
      { trial: 1, kind: 'immediate_recall', target_count: itemCount, recalled_count: immediateCount, correct: immediateCount, outcome: 'free_recall' },
      { trial: 2, kind: 'delayed_recall', target_count: itemCount, recalled_count: delayedCount, correct: delayedCount, outcome: 'free_recall' },
      ...recognitionTrials,
    ];
    const correct = immediateCount + delayedCount + recognitionStats.hits + recognitionStats.correctRejections;
    const incorrect = (itemCount - immediateCount) + (itemCount - delayedCount) + recognitionStats.misses + recognitionStats.falseAlarms;
    const telemetry = makeRoundMetrics('delayed_recall', 1, {
      attempts: Math.max(1, correct + incorrect), correct_attempts: correct, incorrect_attempts: incorrect,
      reaction_times: recognitionTimes, completion_time_sec: (activeNow() - startedAt) / 1000,
      trials: allTrials, trial_count: allTrials.length, valid_trial_count: recognitionTrials.length,
      immediate_total: itemCount, immediate_recall_count: immediateCount,
      delayed_total: itemCount, delayed_recall_count: delayedCount,
      recognition_hits: recognitionStats.hits, recognition_misses: recognitionStats.misses,
      recognition_false_alarms: recognitionStats.falseAlarms,
      recognition_correct_rejections: recognitionStats.correctRejections,
      distractor_taps: distractorTaps, target_count: itemCount, lure_count: itemCount,
      task_parameters: settings,
    });
    const result = await submitRound(telemetry, token);
    if (!result || token !== state.renderToken) return;
    showFeedback(result, {
      title: 'Delayed recall, complete.',
      message: `Immediate recall: ${immediateCount}/${itemCount}. Delayed recall: ${delayedCount}/${itemCount}. Recognition hits: ${recognitionStats.hits}/${itemCount}; false recognitions: ${recognitionStats.falseAlarms}.`,
      buttonText: nextTaskButtonLabel(true),
      next: () => continueAfterRound('delayed_recall', 1, 1),
    });
  }
}

async function runRecallDistractor(token, durationSeconds, onTap) {
  // Replaced per-session by startDelayedRecall's closure implementation.
}


// Game 4: Stroop selective attention. The word, ink and button fill are
// separate cues; only the ink colour is the correct answer.
function chooseStroopPair(round, difficulty) {
  const saved = state.stroopSchedule[round - 1];
  if (saved) return saved;
  const used = state.stroopSchedule.filter(Boolean);
  const previous = used.length ? used[used.length - 1] : null;
  const incongruentRate = getTaskSettings('stroop', difficulty).incongruent_rate || CLIENT_TASK_SETTINGS.stroop[difficulty - 1].incongruent_rate;
  const desiredCongruency = round <= 2 || Math.random() < (1 - incongruentRate);
  const wordCounts = Array(STROOP_COLORS.length).fill(0);
  const inkCounts = Array(STROOP_COLORS.length).fill(0);
  const pairs = [];
  for (const pair of used) {
    wordCounts[pair.wordIndex] += 1;
    inkCounts[pair.inkIndex] += 1;
  }
  for (let wordIndex = 0; wordIndex < STROOP_COLORS.length; wordIndex += 1) {
    for (let inkIndex = 0; inkIndex < STROOP_COLORS.length; inkIndex += 1) {
      if ((wordIndex === inkIndex) !== desiredCongruency) continue;
      if (used.some((pair) => pair.wordIndex === wordIndex && pair.inkIndex === inkIndex)) continue;
      if (wordCounts[wordIndex] >= 2 || inkCounts[inkIndex] >= 2) continue;
      pairs.push({ wordIndex, inkIndex });
    }
  }
  let choices = pairs;
  if (previous) {
    const spaced = choices.filter((pair) => pair.wordIndex !== previous.wordIndex && pair.inkIndex !== previous.inkIndex);
    if (spaced.length) choices = spaced;
  }
  if (!choices.length) {
    for (let wordIndex = 0; wordIndex < STROOP_COLORS.length; wordIndex += 1) {
      for (let inkIndex = 0; inkIndex < STROOP_COLORS.length; inkIndex += 1) {
        if ((wordIndex === inkIndex) === desiredCongruency && !used.some((pair) => pair.wordIndex === wordIndex && pair.inkIndex === inkIndex)) {
          choices.push({ wordIndex, inkIndex });
        }
      }
    }
  }
  if (!choices.length) {
    for (let wordIndex = 0; wordIndex < STROOP_COLORS.length; wordIndex += 1) {
      for (let inkIndex = 0; inkIndex < STROOP_COLORS.length; inkIndex += 1) {
        if ((wordIndex === inkIndex) === desiredCongruency) choices.push({ wordIndex, inkIndex });
      }
    }
  }
  const pair = choices[Math.floor(Math.random() * choices.length)];
  state.stroopSchedule[round - 1] = pair;
  return pair;
}

function readableTextColor(hex) {
  const red = parseInt(hex.slice(1, 3), 16);
  const green = parseInt(hex.slice(3, 5), 16);
  const blue = parseInt(hex.slice(5, 7), 16);
  return 0.299 * red + 0.587 * green + 0.114 * blue > 140 ? '#10131d' : '#ffffff';
}

function startStroopRound(round) {
  state.currentRound = round;
  const task = TASKS[3];
  setGameHeader(task, round);
  const token = ++state.renderToken;
  const difficulty = clamp(state.difficulty.stroop || 1, 1, 3);
  const pair = chooseStroopPair(round, difficulty);
  const wordColor = STROOP_COLORS[pair.wordIndex];
  const inkColor = STROOP_COLORS[pair.inkIndex];
  let attempts = 0;
  let failures = 0;
  let wordReadingErrors = 0;
  let hesitationCount = 0;
  let reactionTimes = [];
  let lastAction = activeNow();
  let choiceLocked = false;
  let lastCorrectPosition = -1;
  const startedAt = activeNow();

  el('gameMount').innerHTML = `${stageHead(`TRIAL ${round} OF ${STROOP_ROUNDS}`, 'Choose the ink color. Ignore both the word and each button’s fill color.', STROOP_COLORS.length, 'Colors', attempts, 'Attempts')}
    <div class="stroop-layout"><div class="stroop-stimulus"><div class="stroop-word" style="color:${inkColor.hex}">${wordColor.name}</div></div>
    <div class="stroop-options" id="stroopOptions"></div><div class="stroop-helper">Read the letters’ ink color. The word meaning and button backgrounds are distractions.</div></div>
    <div class="stage-status" id="stageStatus"><span class="status-indicator"></span><span>Pick the ink color.</span></div>`;

  function renderOptions() {
    const ordered = shuffle(STROOP_COLORS);
    let correctPosition = ordered.findIndex((color) => color.name === inkColor.name);
    if (lastCorrectPosition >= 0 && correctPosition === lastCorrectPosition) {
      let swapPosition = Math.floor(Math.random() * (ordered.length - 1));
      if (swapPosition >= correctPosition) swapPosition += 1;
      [ordered[correctPosition], ordered[swapPosition]] = [ordered[swapPosition], ordered[correctPosition]];
      correctPosition = swapPosition;
    }
    lastCorrectPosition = correctPosition;

    // Assign a fresh random set of button fills, rejecting any fill that matches
    // the text printed on that button. The ink target itself never changes.
    let fills = shuffle(STROOP_COLORS);
    let tries = 0;
    while (ordered.some((color, index) => color.name === fills[index].name) && tries < 50) {
      fills = shuffle(STROOP_COLORS);
      tries += 1;
    }
    if (ordered.some((color, index) => color.name === fills[index].name)) {
      fills = ordered.map((color, index) => STROOP_COLORS[(STROOP_COLORS.findIndex((item) => item.name === color.name) + 1) % STROOP_COLORS.length]);
    }

    el('stroopOptions').innerHTML = ordered.map((color, index) => {
      const fill = fills[index];
      return `<button class="stroop-option" type="button" data-color="${color.name}" style="--option-fill:${fill.hex};--option-ink:${readableTextColor(fill.hex)}">${color.name}</button>`;
    }).join('');
    el('stroopOptions').querySelectorAll('.stroop-option').forEach((button) => {
      button.addEventListener('click', () => handleChoice(button));
    });
  }

  function updateAttempts() {
    const stats = document.querySelectorAll('.stage-stat b');
    if (stats.length > 1) stats[1].textContent = String(attempts);
  }

  async function handleChoice(button) {
    if (state.isPaused || token !== state.renderToken || button.disabled || choiceLocked) return;
    const now = activeNow();
    const reaction = Math.max(0, now - lastAction);
    reactionTimes.push(reaction);
    if (reaction >= 3000) hesitationCount += 1;
    lastAction = now;
    attempts += 1;
    const chosen = button.dataset.color;
    if (chosen === inkColor.name) {
      choiceLocked = true;
      button.classList.add('correct');
      el('stroopOptions').querySelectorAll('.stroop-option').forEach((item) => { item.disabled = true; });
      setStageStatus('Exactly. You followed the ink, not the word.', 'success');
      updateAttempts();
      completeStroop();
      return;
    }

    failures += 1;
    if (chosen === wordColor.name) wordReadingErrors += 1;
    choiceLocked = true;
    el('stroopOptions').querySelectorAll('.stroop-option').forEach((item) => { item.disabled = true; });
    setStageStatus(chosen === wordColor.name ? 'The word tried to trick you. Follow the ink instead.' : 'Not that color. Take another look at the letters.', 'error');
    button.animate([
      { transform: 'translateX(0)' }, { transform: 'translateX(-3px)' },
      { transform: 'translateX(3px)' }, { transform: 'translateX(0)' },
    ], { duration: 180, easing: 'ease-out' });
    updateAttempts();
    const stillHere = await sleepActive(220, token);
    if (!stillHere) return;
    renderOptions();
    choiceLocked = false;
    lastAction = activeNow();
    setStageStatus('Same word, same ink. The buttons have moved. Try again.');
  }

  renderOptions();

  async function completeStroop() {
    const telemetry = makeRoundMetrics('stroop', round, {
      attempts,
      correct_attempts: 1,
      incorrect_attempts: failures,
      reaction_times: reactionTimes,
      hesitation_count: hesitationCount,
      completion_time_sec: (activeNow() - startedAt) / 1000,
      word_reading_errors: wordReadingErrors,
    });
    const result = await submitRound(telemetry, token);
    if (!result || token !== state.renderToken) return;
    const lastRound = round >= STROOP_ROUNDS;
    showFeedback(result, {
      title: lastRound ? 'Focus, complete.' : 'Nice focus.',
      message: `You selected the ink color after ${attempts} ${attempts === 1 ? 'attempt' : 'attempts'}${wordReadingErrors ? `, including ${wordReadingErrors} word-based ${wordReadingErrors === 1 ? 'slip' : 'slips'}` : ''}.`,
      buttonText: nextTaskButtonLabel(lastRound),
      next: () => continueAfterRound('stroop', round, STROOP_ROUNDS),
    });
  }
}

async function finishSession() {
  try {
    const response = await apiPost('/api/session/finish', { session_id: state.sessionId });
    state.resultSummary = response;
    renderResults(response);
    setScreen('results');
    el('railProgressFill').style.width = '100%';
    showToast('Your session summary is ready.');
  } catch (error) {
    showToast(`Couldn’t finish the session: ${error.message}`, 5000);
  }
}

function renderResults(response) {
  const summary = response.summary || {};
  const profiles = summary.domain_scores || [];
  el('overallScore').textContent = Math.round(summary.overall_task_score || 0);
  el('roundsCount').textContent = String(summary.rounds_completed || 0);
  el('gamesCount').textContent = `${summary.games_completed || 0} / ${TASKS.length}`;
  el('resultsGreeting').textContent = state.participantCode ? `Well done, ${state.participantCode}.` : 'Nice work showing up.';
  el('resultsSubcopy').textContent = `You played ${summary.rounds_completed || 0} rounds across ${summary.games_completed || 0} different games. Scores summarize how the games went today.`;
  el('resultsNote').textContent = summary.note || 'These scores reflect performance in these games only. They cannot confirm or rule out a cognitive or medical condition.';
  const descriptors = {
    pairs: { glyph: '▦', title: 'Associative visual memory', copy: 'Matching pairs, visual recognition and recall.' },
    color_pattern: { glyph: '✳', title: 'Visual sequence memory', copy: 'Remembering a sequence of color cues.' },
    normal_pattern: { glyph: '⌗', title: 'Spatial sequence memory', copy: 'Remembering where a sequence appeared.' },
    stroop: { glyph: 'Aa', title: 'Selective attention', copy: 'Filtering a distracting word to follow its ink.' },
    reflex_simple: { glyph: '◉', title: 'Simple response speed', copy: 'Median reaction time, response variability and anticipations.' },
    reflex_choice: { glyph: '⌘', title: 'Choice reaction', copy: 'Speed and accuracy when selecting a matching response.' },
    reflex_gonogo: { glyph: '⏵', title: 'Response inhibition', copy: 'Target hits, missed targets and responses to no-go signals.' },
    delayed_recall: { glyph: '◷', title: 'Delayed recall', copy: 'Immediate recall, delayed retention and recognition errors.' },
  };
  el('profileGrid').innerHTML = profiles.map((profile) => {
    const info = descriptors[profile.game] || { glyph: '✦', title: profile.domain, copy: 'Task performance summary.' };
    const score = clamp(Math.round(profile.score || 0), 0, 100);
    return `<article class="profile-card">
      <div class="profile-card-head"><div class="profile-glyph">${info.glyph}</div><strong class="score">${score}<span style="font-size:12px;color:var(--subtle)">/100</span></strong></div>
      <h3>${info.title}</h3><p>${info.copy}</p>
      <div class="score-track"><span style="width:${score}%"></span></div>
      <div class="profile-meta"><span>Avg. accuracy ${Math.round(profile.average_accuracy || 0)}%</span><span>${profile.rounds} ${profile.rounds === 1 ? 'round' : 'rounds'}</span></div>
    </article>`;
  }).join('');
}

function exportResults() {
  if (!state.resultSummary) return;
  const payload = {
    application: 'MindSpring',
    session_id: state.resultSummary.session_id,
    exported_at: new Date().toISOString(),
    summary: state.resultSummary.summary,
    results: state.resultSummary.results,
    note: 'Game performance feedback only. Not a medical diagnosis or substitute for a validated clinical assessment.',
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `mindspring-${state.sessionId || 'session'}-summary.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function resetWelcome() {
  state.sessionId = null;
  state.results = [];
  state.resultSummary = null;
  state.taskIndex = 0;
  state.currentRound = 1;
  state.renderToken += 1;
  state.isPaused = false;
  state.pausedTotalMs = 0;
  el('pauseOverlay').classList.add('hidden');
  el('startForm').reset();
  setScreen('welcome');
}

function togglePause(forceValue) {
  if (el('gameScreen').classList.contains('hidden')) return;
  const nextValue = typeof forceValue === 'boolean' ? forceValue : !state.isPaused;
  if (nextValue === state.isPaused) return;
  if (nextValue) {
    state.isPaused = true;
    state.pauseStartedAt = performance.now();
    el('pauseOverlay').classList.remove('hidden');
  } else {
    state.pausedTotalMs += performance.now() - state.pauseStartedAt;
    state.isPaused = false;
    el('pauseOverlay').classList.add('hidden');
  }
}


function escapeHTML(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character]);
}

function setDeveloperPanel(open) {
  state.developerOpen = Boolean(open);
  el('developerPanel').classList.toggle('hidden', !state.developerOpen);
  el('developerViewToggle').classList.toggle('active', state.developerOpen);
  el('developerViewToggle').setAttribute('aria-expanded', String(state.developerOpen));
  if (state.developerOpen) updateAgentPanel();
}

function toggleDeveloperPanel() {
  setDeveloperPanel(!state.developerOpen);
}

async function updateAgentPanel() {
  const meta = el('developerMeta');
  try {
    const response = await fetch(`${API}/api/agents/state`, { cache: 'no-store' });
    if (!response.ok) throw new Error('Could not fetch the agent snapshot.');
    const data = await response.json();
    state.developerSnapshot = data;
    if (!data.active_session) {
      meta.textContent = 'No active session. Start a session to see live values and decisions.';
      el('agentCardGrid').innerHTML = '';
      el('agentDecisionList').innerHTML = '<p class="empty-agent-state">The Mesa model is ready, but no player rounds have been processed yet.</p>';
      return;
    }
    meta.textContent = `Round ${data.current_round} · Current task: ${data.current_game || '—'} · Values refresh after each scored round.`;
    const cards = (data.agents || []).map((agent) => {
      const stateText = JSON.stringify(agent.state || {}, null, 2);
      return `<article class="agent-dev-card"><div class="agent-dev-card-top"><span class="agent-live-dot"></span><b>${escapeHTML(agent.name)}</b></div><p>${escapeHTML(agent.role)}</p><span class="agent-mode">${escapeHTML(agent.mode)}</span><details><summary>Inspect current state</summary><pre>${escapeHTML(stateText)}</pre></details></article>`;
    }).join('');
    el('agentCardGrid').innerHTML = cards;
    const history = (data.decision_history || []).slice().reverse();
    el('agentDecisionList').innerHTML = history.length ? history.map((entry) => {
      const decisions = entry.agent_decisions || {};
      const agentRows = Object.values(decisions).map((decision) => {
        if (!decision || (!decision.explanation && !decision.decision)) return '';
        const explanation = decision.explanation || decision.decision || 'No explanation recorded.';
        const metrics = (decision.metrics_used || []).join(', ');
        return `<div class="agent-history-agent"><b>${escapeHTML(decision.agent || 'Mesa agent')}</b><p>${escapeHTML(explanation)}</p>${metrics ? `<small>Metrics: ${escapeHTML(metrics)}</small>` : ''}</div>`;
      }).join('');
      return `<article class="agent-history-item"><div class="agent-history-meta"><b>Round ${escapeHTML(entry.round)}</b><span>${escapeHTML(entry.game || 'task')}</span></div>${agentRows}</article>`;
    }).join('') : '<p class="empty-agent-state">Decision history will appear after the first round.</p>';
  } catch (error) {
    meta.textContent = `Agent state unavailable: ${error.message}`;
    el('agentCardGrid').innerHTML = '';
    el('agentDecisionList').innerHTML = '<p class="empty-agent-state">Check that the local Python Mesa service is running.</p>';
  }
}

el('startForm').addEventListener('submit', beginSession);
el('exportResults').addEventListener('click', exportResults);
el('restartSession').addEventListener('click', resetWelcome);
el('resumeButton').addEventListener('click', () => togglePause(false));
el('developerViewToggle').addEventListener('click', toggleDeveloperPanel);
el('closeAgentPanel').addEventListener('click', () => setDeveloperPanel(false));
el('refreshAgentState').addEventListener('click', updateAgentPanel);
el('quitSession').addEventListener('click', () => {
  if (window.confirm('Leave this session? Results already saved will remain on this computer.')) resetWelcome();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !el('gameScreen').classList.contains('hidden')) {
    event.preventDefault();
    togglePause();
  }
});

// Detect a backend failure after startup so the user is not left on a dead screen.
fetch(`${API}/api/health`).catch(() => {
  // The main process starts the Python service; the welcome form shows API errors if needed.
});
