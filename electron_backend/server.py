"""Local JSON bridge between the Electron games and the Mesa agent model."""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulation.model import CognitiveHealthModel  # noqa: E402

HOST = "127.0.0.1"
PORT = 8765
SESSION_ROOT = PROJECT_ROOT / "electron_sessions"
ALLOWED_GAMES = {"pairs", "color_pattern", "normal_pattern", "stroop"}

_state_lock = threading.Lock()
_active_session: dict[str, Any] | None = None


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_session(session: dict[str, Any]) -> None:
    """Use an atomic replace so a crash cannot leave a half-written JSON file."""
    folder = SESSION_ROOT / session["session_id"]
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "session.json"
    temporary = folder / "session.json.tmp"
    temporary.write_text(json.dumps(session, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(temporary, target)


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def _session_summary(session: dict[str, Any]) -> dict[str, Any]:
    by_game: dict[str, list[dict[str, Any]]] = {}
    for result in session.get("results", []):
        game = result.get("telemetry", {}).get("game")
        if game in ALLOWED_GAMES:
            by_game.setdefault(game, []).append(result)

    domain_scores = []
    for game in ("pairs", "color_pattern", "normal_pattern", "stroop"):
        rounds = by_game.get(game, [])
        if not rounds:
            continue
        latest_assessment = rounds[-1].get("assessment", {})
        scores = [
            float(item.get("assessment", {}).get("Task_Performance_Score", 0.0))
            for item in rounds
        ]
        domain_scores.append({
            "game": game,
            "domain": latest_assessment.get("Cognitive_Domain", game),
            "score": _mean(scores),
            "rounds": len(rounds),
            "average_accuracy": _mean([
                float(item.get("assessment", {}).get("Task_Accuracy_Percent", 0.0))
                for item in rounds
            ]),
            "average_reaction_time_ms": _mean([
                float(item.get("assessment", {}).get("Mean_RT_ms", 0.0))
                for item in rounds
            ]),
        })
    scores = [item["score"] for item in domain_scores]
    return {
        "overall_task_score": _mean(scores),
        "games_completed": len(domain_scores),
        "rounds_completed": len(session.get("results", [])),
        "domain_scores": domain_scores,
        "note": (
            "These scores describe performance in this set of games. They are not a "
            "medical diagnosis or a substitute for a validated clinical assessment."
        ),
    }


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "MindSpringLocal/1.0"

    def log_message(self, format_string: str, *args: Any) -> None:
        # Keep the terminal useful without printing request bodies or participant data.
        print(f"[MindSpring] {self.address_string()} - {format_string % args}")

    def end_headers(self) -> None:
        origin = self.headers.get("Origin", "")
        # Electron's local file page sends a null/file origin. Do not expose the
        # local session API to arbitrary websites in the user's browser.
        if origin == "null" or origin.startswith("file://"):
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json(200, {"ok": True, "service": "mindspring-mesa", "version": 1})
            return
        self._send_json(404, {"ok": False, "error": "Unknown endpoint"})

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            if self.path == "/api/session/start":
                self._start_session(payload)
            elif self.path == "/api/score":
                self._score_round(payload)
            elif self.path == "/api/session/finish":
                self._finish_session(payload)
            else:
                self._send_json(404, {"ok": False, "error": "Unknown endpoint"})
        except ValueError as exc:
            self._send_json(400, {"ok": False, "error": str(exc)})
        except Exception as exc:  # Return a helpful local error instead of hanging Electron.
            print(f"[MindSpring] Request failed: {type(exc).__name__}: {exc}")
            self._send_json(500, {
                "ok": False,
                "error": "The local analysis service could not process that request.",
            })

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid request size") from exc
        if length <= 0 or length > 1_000_000:
            raise ValueError("Request body is empty or too large")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Request body must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("JSON request must be an object")
        return payload

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _start_session(self, payload: dict[str, Any]) -> None:
        global _active_session
        participant_code = str(payload.get("participant_code", "")).strip()[:40]
        participant_code = re.sub(r"[^a-zA-Z0-9 _.-]", "", participant_code)
        age_value = payload.get("age")
        age = None
        if age_value not in (None, ""):
            try:
                age = int(age_value)
            except (TypeError, ValueError) as exc:
                raise ValueError("Age must be a whole number") from exc
            if age < 18 or age > 110:
                raise ValueError("Age must be between 18 and 110, or left blank")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        session_id = f"electron_{timestamp}_{uuid.uuid4().hex[:6]}"
        model = CognitiveHealthModel(
            cdr_level=0.0,
            patient_age=age if age is not None else 75,
            patient_educ=3,
            target_profile="Elderly",
            enable_adaptive_dda=True,
        )
        session = {
            "session_id": session_id,
            "started_at": _now(),
            "participant": {
                "participant_code": participant_code or "Anonymous",
                "age": age,
            },
            "application": "MindSpring Electron",
            "allowed_games": ["pairs", "color_pattern", "normal_pattern", "stroop"],
            "status": "in_progress",
            "results": [],
        }
        with _state_lock:
            _active_session = {"session": session, "model": model}
            _write_session(session)
        self._send_json(200, {
            "ok": True,
            "session_id": session_id,
            "difficulty_levels": dict(model.adaptive_agent.task_levels),
        })

    def _get_active(self, payload: dict[str, Any]) -> dict[str, Any]:
        active = _active_session
        if active is None:
            raise ValueError("Start a session before sending results")
        if payload.get("session_id") != active["session"]["session_id"]:
            raise ValueError("This session is no longer active. Start a new session.")
        return active

    def _score_round(self, payload: dict[str, Any]) -> None:
        with _state_lock:
            active = self._get_active(payload)
            telemetry = payload.get("telemetry")
            if not isinstance(telemetry, dict):
                raise ValueError("A telemetry object is required")
            game = telemetry.get("game")
            if game not in ALLOWED_GAMES:
                raise ValueError("Unsupported game type")

            # Use a whitelist so renderer-supplied assessment fields cannot replace
            # the results generated by Mesa agents.
            accepted_fields = {
                "game", "round", "difficulty_level", "attempts",
                "correct_attempts", "incorrect_attempts", "accuracy",
                "error_rate", "mean_reaction_time_ms", "median_reaction_time_ms",
                "hesitation_count", "completion_time_sec", "sequence_length",
                "matches_found", "total_pairs", "word_reading_errors",
            }
            clean_telemetry = {key: telemetry[key] for key in accepted_fields if key in telemetry}
            clean_telemetry["game"] = game
            step = active["model"].process_task_result(clean_telemetry)
            result = {
                "round": step["round"],
                "telemetry": clean_telemetry,
                "assessment": step["assessment"],
                "dda_action": step["dda_action"],
            }
            active["session"]["results"].append(result)
            active["session"]["updated_at"] = _now()
            _write_session(active["session"])

            self._send_json(200, {
                "ok": True,
                "round": result["round"],
                "assessment": result["assessment"],
                "dda_action": result["dda_action"],
                "rounds_completed": len(active["session"]["results"]),
            })

    def _finish_session(self, payload: dict[str, Any]) -> None:
        with _state_lock:
            active = self._get_active(payload)
            session = active["session"]
            session["status"] = "completed"
            session["completed_at"] = _now()
            session["summary"] = _session_summary(session)
            _write_session(session)
            self._send_json(200, {
                "ok": True,
                "session_id": session["session_id"],
                "summary": session["summary"],
                "results": session["results"],
            })


def main() -> None:
    SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        server = ThreadingHTTPServer((HOST, PORT), RequestHandler)
    except OSError as exc:
        raise SystemExit(
            f"Could not start the local analysis service on {HOST}:{PORT}: {exc}"
        ) from exc
    server.daemon_threads = True
    print(f"MindSpring Mesa service ready at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
