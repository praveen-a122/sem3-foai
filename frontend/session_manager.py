"""Timestamped participant sessions and game-result persistence."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path


ROUNDS_BY_DIFFICULTY = {"Easy": 3, "Medium": 5, "Hard": 10}


class SessionManager:
    def __init__(self):
        self.root = Path(__file__).resolve().parent.parent / "sessions"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = None
        self.data = None

    def start(self, participant, games, difficulty):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.path = self.root / f"{stamp}_{uuid.uuid4().hex[:6]}"
        self.path.mkdir(parents=True, exist_ok=True)

        self.data = {
            "session_id": self.path.name,
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "participant": participant,
            "allowed_games": games,
            "difficulty": difficulty,
            "target_rounds": ROUNDS_BY_DIFFICULTY[difficulty],
            "status": "in_progress",
            "attempts": [],
            "rounds": [],
        }
        self._save()

    def record(self, game, success, round_number=None, error=None):
        if self.data is None:
            return
        self.data["attempts"].append({
            "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "game": game,
            "success": bool(success),
            "round": round_number,
            "error": error,
        })
        self._save()

    def record_round_telemetry(self, game, round_number, telemetry):
        if self.data is None:
            return
        self.data.setdefault("rounds", []).append({
            "game": game,
            "round": round_number,
            "telemetry": dict(telemetry),
        })
        self._save()

    def finish(self):
        if self.data is None:
            return
        attempts = self.data["attempts"]
        successes = sum(item["success"] for item in attempts)
        self.data["status"] = "completed"
        self.data["completed_at"] = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )
        self.data["summary"] = {
            "tries": len(attempts),
            "successes": successes,
            "errors": len(attempts) - successes,
            "success_rate": round(successes / len(attempts) * 100, 2)
            if attempts else 0.0,
        }
        self._save()

    def _save(self):
        target = self.path / "session.json"
        temporary = self.path / "session.json.tmp"
        temporary.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        os.replace(temporary, target)

    def list_sessions(self):
        records = []
        for file in self.root.glob("*/session.json"):
            try:
                records.append(json.loads(file.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return sorted(records, key=lambda item: item.get("timestamp", ""), reverse=True)