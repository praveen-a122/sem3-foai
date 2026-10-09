"""
High-Resolution Telemetry & Latency Logger Module
=================================================
Course: 22AIE201 - Fundamentals of AI
Team 3 Deliverable: Member 2 (Prahlad Vedhanarayanan - BL.SC.U4AIE25034)

Logs sub-second human interactions during cognitive gameplay tasks.
Tracks:
- Card flip timestamps with millisecond precision
- Inter-flip reaction times (RT_ms)
- Repetitive errors (flipping previously seen non-matching cards)
- Hesitation pauses (> 3000 ms, Torabgar et al., 2025)
- Per-round completion time, total flips, and error rates
- Real-time serialization to `data/session_logs.csv`
- Pause / resume latency tracking to exclude non-interactive animation delays.
"""

import os
import time
import csv
from typing import List, Dict, Any, Optional


class TelemetryLogger:
    """
    Sub-second event logger capturing micro-behaviors, reaction latencies,
    and cognitive error patterns during gameplay.
    """

    HESITATION_THRESHOLD_MS = 3000.0  # Pauses > 3s indicate cognitive hesitation (Torabgar et al., 2025)

    def __init__(self, log_filepath: Optional[str] = None):
        if log_filepath is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_filepath = os.path.join(base_dir, "data", "session_logs.csv")
        self.log_filepath = log_filepath
        self._ensure_csv_headers()

        # Session state
        self.session_id: str = f"SESSION_{int(time.time())}"
        self.round_number: int = 1
        self.difficulty_level: str = "Medium"
        self.grid_size: str = "3x4"

        # Round tracking
        self.round_start_time: float = 0.0
        self.last_action_timestamp: float = 0.0
        self.flip_events: List[Dict[str, Any]] = []
        self.seen_cards: set = set()
        self.revealed_pairs: set = set()

        # Cumulative counters for round
        self.total_flips: int = 0
        self.match_attempts: int = 0
        self.successful_matches: int = 0
        self.redundant_errors: int = 0
        self.hesitation_count: int = 0
        self.reaction_times_ms: List[float] = []

        # Pause tracking for animation delays & micro-breaks
        self._is_timer_paused: bool = False
        self._pause_start_timestamp: float = 0.0

    def _ensure_csv_headers(self) -> None:
        """Creates the session_logs.csv file with headers if it does not already exist."""
        os.makedirs(os.path.dirname(self.log_filepath), exist_ok=True)
        if not os.path.exists(self.log_filepath) or os.path.getsize(self.log_filepath) == 0:
            headers = [
                "Session_ID",
                "Round_Number",
                "Grid_Size",
                "Difficulty_Level",
                "Total_Flips",
                "Total_Pairs",
                "Matches_Found",
                "Redundant_Errors",
                "Error_Rate",
                "Mean_Reaction_Time_ms",
                "Median_Reaction_Time_ms",
                "Std_Reaction_Time_ms",
                "Hesitation_Intervals_Count",
                "Round_Completion_Time_sec",
                "Timestamp"
            ]
            with open(self.log_filepath, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

    def start_round(self, round_num: int, grid_size: str = "3x4", difficulty: str = "Medium") -> None:
        """Initializes state tracking for a new round."""
        self.round_number = round_num
        self.grid_size = grid_size
        self.difficulty_level = difficulty
        self.round_start_time = time.perf_counter()
        self.last_action_timestamp = self.round_start_time

        self.flip_events.clear()
        self.seen_cards.clear()
        self.revealed_pairs.clear()
        self.reaction_times_ms.clear()

        self.total_flips = 0
        self.match_attempts = 0
        self.successful_matches = 0
        self.redundant_errors = 0
        self.hesitation_count = 0

        self._is_timer_paused = False
        self._pause_start_timestamp = 0.0

    def pause_latency_timer(self) -> None:
        """
        Pauses the latency timer during non-interactive intervals
        (e.g., mismatch card display animations or restorative micro-breaks)
        so animation wait time is NOT erroneously counted as patient hesitation.
        """
        if not self._is_timer_paused:
            self._pause_start_timestamp = time.perf_counter()
            self._is_timer_paused = True

    def resume_latency_timer(self) -> None:
        """
        Resumes the latency timer when interactive gameplay resumes.
        Shifts the last_action_timestamp forward by the exact paused duration.
        """
        if self._is_timer_paused:
            pause_duration = time.perf_counter() - self._pause_start_timestamp
            self.last_action_timestamp += pause_duration
            self._is_timer_paused = False

    def record_card_flip(self, card_idx: int, card_value: Any) -> float:
        """
        Records an individual card flip event, computes reaction time from last interaction,
        and detects if a hesitation interval occurred (> 3.0 seconds).
        Returns the reaction time in milliseconds.
        """
        now = time.perf_counter()
        if self._is_timer_paused:
            self.resume_latency_timer()

        delta_sec = now - self.last_action_timestamp
        delta_ms = max(0.0, delta_sec * 1000.0)

        # Disregard the very first flip pause from round start if it's brief
        if self.total_flips > 0:
            self.reaction_times_ms.append(delta_ms)
            if delta_ms >= self.HESITATION_THRESHOLD_MS:
                self.hesitation_count += 1

        self.total_flips += 1
        self.last_action_timestamp = now

        event = {
            "flip_index": self.total_flips,
            "card_idx": card_idx,
            "card_value": card_value,
            "reaction_time_ms": delta_ms,
            "is_hesitation": delta_ms >= self.HESITATION_THRESHOLD_MS,
            "timestamp": now
        }
        self.flip_events.append(event)
        return delta_ms

    def record_pair_attempt(self, card1_idx: int, val1: Any, card2_idx: int, val2: Any) -> bool:
        """
        Evaluates a pair attempt.
        Tracks whether failure represents a 'working memory error' (redundant error),
        meaning one or both cards had already been exposed previously.
        """
        self.match_attempts += 1
        is_match = (val1 == val2)

        if is_match:
            self.successful_matches += 1
            self.revealed_pairs.add(val1)
        else:
            # Check if this error was on cards already seen earlier
            if card1_idx in self.seen_cards or card2_idx in self.seen_cards:
                self.redundant_errors += 1

        self.seen_cards.add(card1_idx)
        self.seen_cards.add(card2_idx)
        return is_match

    def complete_round(self, total_pairs: int) -> Dict[str, Any]:
        """
        Finalizes the round metrics and appends the aggregated summary to session_logs.csv.
        """
        now = time.perf_counter()
        completion_time_sec = now - self.round_start_time

        error_rate = (self.redundant_errors / max(1, self.match_attempts))
        mean_rt = float(sum(self.reaction_times_ms) / max(1, len(self.reaction_times_ms))) if self.reaction_times_ms else 0.0

        # Median and Std
        sorted_rt = sorted(self.reaction_times_ms) if self.reaction_times_ms else [0.0]
        n = len(sorted_rt)
        median_rt = sorted_rt[n // 2] if n % 2 != 0 else (sorted_rt[n // 2 - 1] + sorted_rt[n // 2]) / 2.0
        std_rt = float((sum((x - mean_rt) ** 2 for x in sorted_rt) / max(1, n)) ** 0.5)

        efficiency_ratio = round(
            total_pairs * 2 / max(1, self.total_flips), 3
        )

        round_summary = {
            "Session_ID": self.session_id,
            "Round_Number": self.round_number,
            "Grid_Size": self.grid_size,
            "Difficulty_Level": self.difficulty_level,
            "Total_Flips": self.total_flips,
            "Total_Pairs": total_pairs,
            "Matches_Found": self.successful_matches,
            "Redundant_Errors": self.redundant_errors,
            "Error_Rate": round(error_rate, 4),
            "Efficiency_Ratio": efficiency_ratio,
            "Mean_Reaction_Time_ms": round(mean_rt, 2),
            "Median_Reaction_Time_ms": round(median_rt, 2),
            "Std_Reaction_Time_ms": round(std_rt, 2),
            "Hesitation_Intervals_Count": self.hesitation_count,
            "Round_Completion_Time_sec": round(completion_time_sec, 2),
            "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # Append to CSV
        with open(self.log_filepath, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                round_summary["Session_ID"],
                round_summary["Round_Number"],
                round_summary["Grid_Size"],
                round_summary["Difficulty_Level"],
                round_summary["Total_Flips"],
                round_summary["Total_Pairs"],
                round_summary["Matches_Found"],
                round_summary["Redundant_Errors"],
                round_summary["Error_Rate"],
                round_summary["Mean_Reaction_Time_ms"],
                round_summary["Median_Reaction_Time_ms"],
                round_summary["Std_Reaction_Time_ms"],
                round_summary["Hesitation_Intervals_Count"],
                round_summary["Round_Completion_Time_sec"],
                round_summary["Timestamp"]
            ])

        return round_summary
