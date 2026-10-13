"""Integration checks for the local Electron-to-Mesa JSON bridge."""

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import electron_backend.server as api


def _request(base_url, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_session_start_and_live_agent_decisions(monkeypatch, tmp_path):
    """All task settings are returned and a scored round exposes agent explanations."""
    monkeypatch.setattr(api, "SESSION_ROOT", tmp_path)
    monkeypatch.setattr(api, "_active_session", None)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), api.RequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        started = _request(base_url, "/api/session/start", {"participant_code": "test-only"})
        expected_tasks = {
            "pairs", "color_pattern", "normal_pattern", "stroop",
            "reflex_simple", "reflex_choice", "reflex_gonogo", "delayed_recall",
        }
        assert started["ok"] is True
        assert set(started["task_settings"]) == expected_tasks
        assert started["task_settings"]["delayed_recall"]["item_count"] == 6

        state = _request(base_url, "/api/agents/state")
        assert state["active_session"] is True
        assert {agent["name"] for agent in state["agents"]} >= {
            "ScreenerAgent", "MemoryAnalysisAgent", "AttentionAnalysisAgent",
            "AdaptiveDifficultyAgent",
        }

        trial = {
            "trial": 1, "kind": "go_nogo", "stimulus": "GO",
            "expected": "respond", "response": "respond", "correct": True,
            "reaction_time_ms": 410,
        }
        scored = _request(base_url, "/api/score", {
            "session_id": started["session_id"],
            "telemetry": {
                "game": "reflex_gonogo", "round": 1, "difficulty_level": 1,
                "attempts": 8, "correct_attempts": 6, "incorrect_attempts": 2,
                "accuracy": 0.75, "error_rate": 0.25,
                "trial_count": 8, "valid_trial_count": 8,
                "median_reaction_time_ms": 410, "mean_reaction_time_ms": 430,
                "reaction_time_variability_ms": 55, "commission_errors": 1,
                "omission_errors": 1, "false_starts": 0, "trials": [trial],
            },
        })
        assert scored["ok"] is True
        assert scored["assessment"]["Assessment_Method"] == "task_specific_heuristic"
        assert {"screener", "memory", "attention", "adaptive"} <= set(scored["agent_decisions"])
        assert scored["agent_decisions"]["attention"]["agent"] == "AttentionAnalysisAgent"
        assert scored["agent_decisions"]["adaptive"]["metrics_used"]
        saved_session = next(tmp_path.glob(f"{started['session_id']}/session.json"))
        saved = json.loads(saved_session.read_text(encoding="utf-8"))
        assert saved["results"][0]["telemetry"]["trials"][0]["reaction_time_ms"] == 410
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
        with api._state_lock:
            api._active_session = None
