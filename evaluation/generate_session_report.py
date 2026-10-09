"""Generate per-session performance summaries and longitudinal plots.

Performance bands are descriptive software metrics, not clinical assessments.
Use generate_reports(model=...) to source telemetry from a Mesa model exposing
get_simulation_dataframe(); otherwise the script reads session_logs.csv.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SESSIONS_DIR = PROJECT_ROOT / "sessions"
DEFAULT_LOGS_PATH = PROJECT_ROOT / "session_logs.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "evaluation" / "session_reports"

# Recognize common logger and simulation column names.
ALIASES = {
    "session_id": ("session_id", "Session_ID", "session", "sessionid"),
    "round": ("round", "Round", "round_number", "Round_Number"),
    "game": ("game", "Game", "game_name", "Game_Name"),
    "reaction_time": (
        "Mean_Reaction_Time_ms", "mean_reaction_time_ms", "Mean_RT_ms",
        "reaction_time_ms", "Reaction_Time_ms",
    ),
    "error_rate": ("Error_Rate", "error_rate"),
    "hesitations": (
        "Hesitation_Intervals_Count", "hesitations", "hesitation_count",
    ),
    "total_flips": ("Total_Flips", "total_flips", "actual_moves"),
    "total_pairs": ("Total_Pairs", "total_pairs", "pairs"),
    "efficiency": ("Efficiency_Ratio", "efficiency_ratio"),
    "success": ("success", "Success"),
}


def _find_column(frame: pd.DataFrame, key: str) -> str | None:
    """Find a column case-insensitively from the known aliases."""
    by_lower = {str(column).lower(): column for column in frame.columns}
    for alias in ALIASES[key]:
        if alias.lower() in by_lower:
            return by_lower[alias.lower()]
    return None


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _session_dataframe(
    model: Any = None,
    logs_path: Path = DEFAULT_LOGS_PATH,
) -> tuple[pd.DataFrame, str]:
    """Get telemetry from Mesa when supplied, otherwise load the CSV."""
    if model is not None:
        getter = getattr(model, "get_simulation_dataframe", None)
        if callable(getter):
            try:
                result = getter()
                if isinstance(result, pd.DataFrame):
                    return result.copy(), "Mesa model"
                return pd.DataFrame(result), "Mesa model"
            except Exception as exc:
                print(f"Warning: Mesa telemetry unavailable ({exc}); trying CSV.")

    if logs_path.is_file():
        try:
            return pd.read_csv(logs_path), str(logs_path)
        except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
            print(f"Warning: Could not read {logs_path}: {exc}")

    return pd.DataFrame(), "no telemetry source"


def _embedded_rounds(session: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in session.get("rounds", []) or []:
        if not isinstance(item, dict):
            continue
        telemetry = item.get("telemetry", item)
        if not isinstance(telemetry, dict):
            continue
        row = dict(telemetry)
        row.setdefault("game", item.get("game"))
        row.setdefault("round", item.get("round"))
        rows.append(row)
    return pd.DataFrame(rows)


def _rows_for_session(
    session: dict[str, Any],
    source: pd.DataFrame,
) -> pd.DataFrame:
    """Combine telemetry embedded in session.json with matching CSV/model rows."""
    embedded = _embedded_rounds(session)
    matching = pd.DataFrame()

    if not source.empty:
        sid_column = _find_column(source, "session_id")
        if sid_column:
            matching = source[
                source[sid_column].astype(str) == str(session.get("session_id", ""))
            ].copy()

    if embedded.empty:
        return matching.reset_index(drop=True)
    if matching.empty:
        return embedded.reset_index(drop=True)

    return pd.concat([embedded, matching], ignore_index=True, sort=False)


def _domain_scores(
    row: dict[str, Any],
) -> dict[str, float | None]:
    """Convert available round metrics to transparent 0–100 domain scores."""
    rt = _number(row.get("reaction_time"))
    error = _number(row.get("error_rate"))
    efficiency = _number(row.get("efficiency"))

    flips = _number(row.get("total_flips"))
    pairs = _number(row.get("total_pairs"))
    if efficiency is None and flips is not None and pairs is not None and flips > 0:
        efficiency = (pairs * 2.0) / flips

    # The fixed bounds are reporting scales, not clinical norms.
    speed = (
        max(0.0, min(100.0, (8000.0 - rt) / (8000.0 - 600.0) * 100.0))
        if rt is not None else None
    )
    accuracy = (
        max(0.0, min(100.0, (1.0 - error) * 100.0))
        if error is not None else None
    )
    memory_efficiency = (
        max(0.0, min(100.0, efficiency * 100.0))
        if efficiency is not None else None
    )

    return {
        "Processing speed": speed,
        "Accuracy": accuracy,
        "Memory / move efficiency": memory_efficiency,
    }


def _round_epi(row: dict[str, Any]) -> float | None:
    scores = _domain_scores(row)
    # Weighted mean over available metrics; renormalize when a metric is absent.
    weights = {
        "Processing speed": 0.30,
        "Accuracy": 0.40,
        "Memory / move efficiency": 0.30,
    }
    available = [
        (scores[name], weight)
        for name, weight in weights.items()
        if scores[name] is not None
    ]
    if not available:
        return None
    return sum(score * weight for score, weight in available) / sum(
        weight for _, weight in available
    )


def _record_value(row: pd.Series, key: str) -> Any:
    column = _find_column(pd.DataFrame([row]), key)
    return row.get(column) if column else None


def _attempt_summary(session: dict[str, Any]) -> tuple[int, int, float | None]:
    attempts = session.get("attempts", []) or []
    tries = len(attempts)
    successes = sum(
        1 for attempt in attempts
        if isinstance(attempt, dict) and bool(attempt.get("success", False))
    )
    rate = successes / tries * 100.0 if tries else None
    return tries, successes, rate


def _build_report(
    session: dict[str, Any],
    rows: pd.DataFrame,
    source_name: str,
) -> dict[str, Any]:
    round_records: list[dict[str, Any]] = []
    score_columns = {
        "Processing speed": [],
        "Accuracy": [],
        "Memory / move efficiency": [],
    }
    epi_values: list[float] = []

    for index, series in rows.iterrows():
        row = series.to_dict()
        scores = _domain_scores(row)
        epi = _round_epi(row)
        round_number = _number(_record_value(series, "round"))
        round_records.append({
            "round": int(round_number) if round_number is not None else index + 1,
            "game": _record_value(series, "game"),
            "executive_performance_index": round(epi, 2) if epi is not None else None,
            "domains": {
                name: round(value, 2) if value is not None else None
                for name, value in scores.items()
            },
            "reaction_time_ms": _number(row.get("reaction_time")),
            "error_rate": _number(row.get("error_rate")),
            "efficiency_ratio": _number(row.get("efficiency")),
        })
        if epi is not None:
            epi_values.append(epi)
        for name, value in scores.items():
            if value is not None:
                score_columns[name].append(value)

    attempts, successes, success_rate = _attempt_summary(session)
    mean_epi = sum(epi_values) / len(epi_values) if epi_values else None

    # If no telemetry exists, use task success rate as a clearly labeled proxy.
    epi_source = "round telemetry"
    if mean_epi is None and success_rate is not None:
        mean_epi = success_rate
        epi_source = "attempt success-rate proxy"

    if mean_epi is None:
        risk_band = "Insufficient data"
    elif mean_epi >= 75:
        risk_band = "Higher performance"
    elif mean_epi >= 50:
        risk_band = "Review performance"
    else:
        risk_band = "Lower performance"

    domain_table = [
        {
            "domain": name,
            "mean_score_0_to_100": (
                round(sum(values) / len(values), 2) if values else None
            ),
            "rounds_available": len(values),
        }
        for name, values in score_columns.items()
    ]

    return {
        "session_id": session.get("session_id"),
        "timestamp": session.get("timestamp"),
        "participant": session.get("participant", {}),
        "status": session.get("status"),
        "difficulty": session.get("difficulty"),
        "data_source": source_name,
        "executive_performance_index": {
            "score_0_to_100": round(mean_epi, 2) if mean_epi is not None else None,
            "source": epi_source if mean_epi is not None else "unavailable",
            "interpretation": "Descriptive game-performance metric; not a clinical score.",
        },
        "cognitive_domain_breakdown": domain_table,
        "risk_stratification": {
            "performance_band": risk_band,
            "basis": "EPI reporting bands; not clinical risk stratification.",
        },
        "attempt_summary": {
            "tries": attempts,
            "successes": successes,
            "success_rate_percent": round(success_rate, 2)
            if success_rate is not None else None,
        },
        "longitudinal_rounds": round_records,
        "notes": (
            ["No round telemetry was found; domain scores and telemetry EPI are unavailable."]
            if rows.empty else []
        ),
    }


def _plot_trend(report: dict[str, Any], output_path: Path) -> None:
    """Save a per-session longitudinal EPI trend using matplotlib."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    points = [
        item for item in report["longitudinal_rounds"]
        if item["executive_performance_index"] is not None
    ]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    if points:
        x = [item["round"] for item in points]
        y = [item["executive_performance_index"] for item in points]
        ax.plot(x, y, marker="o", linewidth=2, color="#52734D")
        ax.set_ylim(0, 100)
        ax.set_xlabel("Round")
        ax.set_ylabel("Executive Performance Index (0–100)")
        ax.set_title("Longitudinal game-performance trend")
        ax.grid(True, alpha=0.3)
    else:
        ax.text(
            0.5, 0.5,
            "No round telemetry available for this session",
            ha="center", va="center", transform=ax.transAxes,
        )
        ax.set_axis_off()

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_reports(
    model: Any = None,
    sessions_dir: Path = DEFAULT_SESSIONS_DIR,
    logs_path: Path = DEFAULT_LOGS_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> list[Path]:
    """Write one JSON summary and PNG trend plot per session.json."""
    sessions_dir = Path(sessions_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source, source_name = _session_dataframe(model=model, logs_path=Path(logs_path))
    written: list[Path] = []

    for session_path in sorted(sessions_dir.glob("*/session.json")):
        try:
            session = json.loads(session_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Skipping {session_path}: {exc}")
            continue

        rows = _rows_for_session(session, source)
        report = _build_report(session, rows, source_name)
        safe_id = str(session.get("session_id") or session_path.parent.name)
        json_path = output_dir / f"{safe_id}_summary.json"
        plot_path = output_dir / f"{safe_id}_trend.png"

        json_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False),
            encoding="utf-8",
        )
        _plot_trend(report, plot_path)
        written.append(json_path)
        print(f"Wrote {json_path} and {plot_path}")

    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate per-session performance reports and trend plots."
    )
    parser.add_argument("--sessions-dir", type=Path, default=DEFAULT_SESSIONS_DIR)
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOGS_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    generate_reports(
        sessions_dir=args.sessions_dir,
        logs_path=args.logs,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()