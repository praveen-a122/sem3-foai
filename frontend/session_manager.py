"""Timestamped participant sessions and game-result persistence."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path


ROUNDS_BY_DIFFICULTY = {"Easy": 3, "Medium": 5, "Hard": 10}


def calculate_failed_attempt_metrics(session):
    """Calculate the failed-attempt count and percentage for one session."""
    attempts = session.get("attempts", [])
    total_attempts = len(attempts)
    failed_attempts = sum(not attempt.get("success", False) for attempt in attempts)
    return {
        "failed_attempts": failed_attempts,
        "total_attempts": total_attempts,
        "failed_percentage": (
            round(failed_attempts * 100.0 / total_attempts, 1)
            if total_attempts
            else 0.0
        ),
    }


def calculate_repeated_tile_metrics(session):
    """Calculate repeated tile picks that belonged to unsuccessful memory pairs."""
    tracked_attempts = [
        attempt
        for attempt in session.get("attempts", [])
        if attempt.get("game") == "pairs"
        and "repeated_tile_count" in attempt
    ]
    repeated_tile_misses = sum(
        min(2, max(0, int(attempt.get("repeated_tile_count", 0))))
        for attempt in tracked_attempts
    )
    total_pair_card_flips = len(tracked_attempts) * 2
    return {
        "repeated_tile_misses": repeated_tile_misses,
        "total_pair_card_flips": total_pair_card_flips,
        "tracked_pair_attempts": len(tracked_attempts),
        "repeated_tile_percentage": (
            round(repeated_tile_misses * 100.0 / total_pair_card_flips, 1)
            if total_pair_card_flips
            else 0.0
        ),
    }


def classify_metric_band(value, borderline_threshold, high_threshold):
    """Map a gameplay percentage to a configurable, non-diagnostic band."""
    if value >= high_threshold:
        return "High concern (red)"
    if value >= borderline_threshold:
        return "Borderline"
    return "Healthy-range"


class SessionManager:
    def __init__(self):
        self.root = Path(__file__).resolve().parent.parent / "sessions"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = None
        self.data = None

    def start(self, participant, games, difficulty, photo_path=None):
        photo_source = None
        photo_name = None
        if photo_path is not None:
            photo_source = Path(photo_path).expanduser()
            if not photo_source.is_file():
                raise FileNotFoundError(f"Patient photo not found: {photo_source}")
            suffix = photo_source.suffix.lower()
            if suffix not in {".bmp", ".gif", ".jpg", ".jpeg", ".png"}:
                raise ValueError("Patient photo must be a BMP, GIF, JPEG, or PNG file")
            photo_name = f"patient_photo{suffix}"

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.path = self.root / f"{stamp}_{uuid.uuid4().hex[:6]}"
        self.path.mkdir(parents=True, exist_ok=True)

        participant_record = dict(participant)
        if photo_source is not None and photo_name is not None:
            shutil.copy2(photo_source, self.path / photo_name)
            participant_record["photo_file"] = photo_name

        self.data = {
            "session_id": self.path.name,
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "participant": participant_record,
            "allowed_games": games,
            "difficulty": difficulty,
            "target_rounds": ROUNDS_BY_DIFFICULTY[difficulty],
            "status": "in_progress",
            "attempts": [],
            "rounds": [],
        }
        self._save()

    def record(
        self,
        game,
        success,
        round_number=None,
        error=None,
        repeated_tile_count=None,
    ):
        if self.data is None:
            return
        attempt = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "game": game,
            "success": bool(success),
            "round": round_number,
            "error": error,
        }
        if repeated_tile_count is not None:
            attempt["repeated_tile_count"] = min(
                2, max(0, int(repeated_tile_count))
            )
        self.data["attempts"].append(attempt)
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

    def photo_path_for(self, session):
        """Return the saved photo path for a session, if one exists."""
        session_id = session.get("session_id")
        photo_file = session.get("participant", {}).get("photo_file")
        if (
            not isinstance(session_id, str)
            or Path(session_id).name != session_id
            or not isinstance(photo_file, str)
            or Path(photo_file).name != photo_file
        ):
            return None

        photo_path = self.root / session_id / photo_file
        return photo_path if photo_path.is_file() else None