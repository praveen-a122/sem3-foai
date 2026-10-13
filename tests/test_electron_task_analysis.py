"""Regression tests for task-aware Mesa assessment and adaptive difficulty."""

import pytest

pytest.importorskip("mesa")

from simulation.model import CognitiveHealthModel


@pytest.mark.parametrize(
    ("game", "domain"),
    [
        ("pairs", "Associative visual memory"),
        ("color_pattern", "Visual sequence memory"),
        ("normal_pattern", "Spatial sequence memory"),
        ("stroop", "Selective attention and inhibition"),
        ("reflex_simple", "Simple response speed and consistency"),
        ("reflex_choice", "Choice response and stimulus discrimination"),
        ("reflex_gonogo", "Response inhibition and sustained attention"),
        ("delayed_recall", "Immediate and delayed episodic recall"),
    ],
)
def test_each_game_uses_task_specific_mesa_assessment(game, domain):
    model = CognitiveHealthModel(patient_age=70, enable_adaptive_dda=True)
    result = model.process_task_result({
        "game": game,
        "round": 1,
        "difficulty_level": 1,
        "attempts": 4,
        "correct_attempts": 3,
        "incorrect_attempts": 1,
        "accuracy": 0.75,
        "error_rate": 0.25,
        "mean_reaction_time_ms": 1100,
        "hesitation_count": 0,
    })

    assessment = result["assessment"]
    action = result["dda_action"]
    assert assessment["Cognitive_Domain"] == domain
    assert assessment["Assessment_Method"] == "task_specific_heuristic"
    assert 0 <= assessment["Task_Performance_Score"] <= 100
    assert "Predicted_MMSE" not in assessment
    assert action["task"] == game
    assert action["next_difficulty_level"] in (1, 2, 3)
    assert result["round"] == 1


def test_repeated_accurate_rounds_can_raise_only_that_game_difficulty():
    model = CognitiveHealthModel(enable_adaptive_dda=True)
    telemetry = {
        "game": "color_pattern",
        "attempts": 8,
        "trial_count": 8,
        "valid_trial_count": 8,
        "correct_attempts": 8,
        "incorrect_attempts": 0,
        "accuracy": 1.0,
        "error_rate": 0.0,
        "mean_reaction_time_ms": 500,
        "median_reaction_time_ms": 500,
        "reaction_time_variability_ms": 0,
        "hesitation_count": 0,
    }

    model.process_task_result(telemetry)
    result = model.process_task_result(telemetry)

    assert result["dda_action"]["next_difficulty_level"] == 2
    assert model.adaptive_agent.task_levels["pairs"] == 1
    assert model.adaptive_agent.task_levels["stroop"] == 1


def test_high_error_round_does_not_return_clinical_diagnosis():
    model = CognitiveHealthModel(enable_adaptive_dda=True)
    result = model.process_task_result({
        "game": "normal_pattern",
        "attempts": 5,
        "correct_attempts": 1,
        "incorrect_attempts": 4,
        "accuracy": 0.2,
        "error_rate": 0.8,
        "mean_reaction_time_ms": 4200,
        "hesitation_count": 3,
    })

    assert result["assessment"]["Clinical_Flag"] == "Task performance only; not a diagnosis"
    assert result["dda_action"]["next_difficulty_level"] == 1
    assert result["dda_action"]["micro_break_recommended"] is True


def test_pairs_assessment_includes_pair_progress_metrics():
    model = CognitiveHealthModel(enable_adaptive_dda=True)
    result = model.process_task_result({
        "game": "pairs",
        "attempts": 10,
        "correct_attempts": 8,
        "incorrect_attempts": 2,
        "mean_reaction_time_ms": 1500,
        "matches_found": 8,
        "total_pairs": 8,
        "difficulty_level": 1,
    })

    assert result["assessment"]["Matches_Found"] == 8
    assert result["assessment"]["Total_Pairs"] == 8
    assert result["assessment"]["Difficulty_Level"] == 1


def test_stroop_assessment_tracks_word_reading_slips_separately():
    model = CognitiveHealthModel(enable_adaptive_dda=True)
    result = model.process_task_result({
        "game": "stroop",
        "attempts": 3,
        "correct_attempts": 1,
        "incorrect_attempts": 2,
        "error_rate": 2 / 3,
        "mean_reaction_time_ms": 900,
        "word_reading_errors": 2,
    })

    assert result["assessment"]["Word_Reading_Errors"] == 2
    assert result["assessment"]["Inhibition_Accuracy_Percent"] == pytest.approx(33.3, abs=0.1)


@pytest.mark.parametrize("game", ["reflex_simple", "reflex_choice", "reflex_gonogo"])
def test_reflex_tasks_keep_trial_level_evidence_and_attention_metrics(game):
    model = CognitiveHealthModel(enable_adaptive_dda=True)
    trials = [
        {"trial": 1, "kind": game, "correct": True, "reaction_time_ms": 310, "outcome": "hit"},
        {"trial": 2, "kind": game, "correct": False, "reaction_time_ms": 450, "outcome": "omission"},
        {"trial": 3, "kind": game, "correct": True, "reaction_time_ms": 330, "outcome": "hit"},
        {"trial": 4, "kind": game, "correct": True, "reaction_time_ms": 370, "outcome": "hit"},
        {"trial": 5, "kind": game, "correct": False, "reaction_time_ms": 520, "outcome": "commission_error"},
        {"trial": 6, "kind": game, "correct": True, "reaction_time_ms": 340, "outcome": "hit"},
    ]
    result = model.process_task_result({
        "game": game,
        "attempts": 6,
        "trial_count": 6,
        "valid_trial_count": 6,
        "correct_attempts": 4,
        "incorrect_attempts": 2,
        "accuracy": 4 / 6,
        "error_rate": 2 / 6,
        "mean_reaction_time_ms": 386.7,
        "median_reaction_time_ms": 355,
        "reaction_time_variability_ms": 75.0,
        "false_starts": 1,
        "omission_errors": 1,
        "commission_errors": 1,
        "trials": trials,
    })

    assessment = result["assessment"]
    attention = model.attention_agent.latest_analysis
    assert assessment["Valid_Trial_Count"] == 6
    assert assessment["Reaction_Time_Variability_ms"] == 75.0
    assert assessment["False_Starts"] == 1
    assert len(model.latest_telemetry["trials"]) == 6
    assert attention["game"] == game
    assert attention["omission_errors"] == 1
    assert attention["commission_errors"] == 1
    assert "variability" in attention["explanation"]


def test_delayed_recall_distinguishes_immediate_delayed_and_recognition():
    model = CognitiveHealthModel(enable_adaptive_dda=True)
    result = model.process_task_result({
        "game": "delayed_recall",
        "difficulty_level": 1,
        "attempts": 24,
        "trial_count": 14,
        "valid_trial_count": 12,
        "correct_attempts": 12,
        "incorrect_attempts": 12,
        "accuracy": 0.5,
        "error_rate": 0.5,
        "mean_reaction_time_ms": 1300,
        "median_reaction_time_ms": 1220,
        "immediate_total": 6,
        "immediate_recall_count": 4,
        "delayed_total": 6,
        "delayed_recall_count": 3,
        "recognition_hits": 5,
        "recognition_misses": 1,
        "recognition_false_alarms": 2,
        "recognition_correct_rejections": 4,
        "trials": [{"trial": i + 1, "kind": "recognition", "correct": i % 2 == 0} for i in range(12)],
    })

    assessment = result["assessment"]
    memory = model.memory_agent.latest_analysis
    assert assessment["Immediate_Recall_Percent"] == pytest.approx(66.7, abs=0.1)
    assert assessment["Delayed_Recall_Percent"] == 50.0
    assert assessment["Recognition_Accuracy_Percent"] == 75.0
    assert assessment["Retention_Ratio"] == 0.75
    assert memory["metrics"]["recognition_hits"] == 5
    assert "distraction interval" in memory["explanation"]


def test_debug_state_exposes_agent_roles_state_and_decision_history():
    model = CognitiveHealthModel(enable_adaptive_dda=True)
    model.process_task_result({
        "game": "reflex_simple", "attempts": 8, "trial_count": 8,
        "valid_trial_count": 8, "correct_attempts": 7, "incorrect_attempts": 1,
        "accuracy": 0.875, "error_rate": 0.125,
        "mean_reaction_time_ms": 320, "median_reaction_time_ms": 315,
        "reaction_time_variability_ms": 35,
    })

    snapshot = model.get_agent_debug_state()
    names = {agent["name"] for agent in snapshot["agents"]}
    assert {"ScreenerAgent", "MemoryAnalysisAgent", "AttentionAnalysisAgent", "AdaptiveDifficultyAgent"}.issubset(names)
    assert snapshot["decision_history"]
    decisions = snapshot["decision_history"][-1]["agent_decisions"]
    assert decisions["screener"]["metrics_used"]
    assert decisions["adaptive"]["explanation"]
    assert decisions["memory"]["status"] == "idle_for_task"


def test_uncertain_single_sequence_response_does_not_immediately_change_level():
    model = CognitiveHealthModel(enable_adaptive_dda=True)
    model.adaptive_agent.task_levels["color_pattern"] = 2
    result = model.process_task_result({
        "game": "color_pattern", "attempts": 1, "trial_count": 1,
        "correct_attempts": 0, "incorrect_attempts": 1,
        "accuracy": 0.0, "error_rate": 1.0,
        "mean_reaction_time_ms": 900, "median_reaction_time_ms": 900,
        "sequence_length": 3,
    })

    assert result["assessment"]["Uncertainty_95pct_Points"] > 30
    assert result["dda_action"]["next_difficulty_level"] == 2
    assert "sample is too small" in result["dda_action"]["reason"]


def test_practice_adjustment_does_not_compare_different_levels():
    model = CognitiveHealthModel(enable_adaptive_dda=True)
    first = {
        "game": "color_pattern", "difficulty_level": 1, "attempts": 8,
        "trial_count": 8, "correct_attempts": 6, "incorrect_attempts": 2,
        "accuracy": 0.75, "mean_reaction_time_ms": 1000,
    }
    model.screener.evaluate_task_telemetry(first)
    second = dict(first, difficulty_level=2, correct_attempts=8, incorrect_attempts=0, accuracy=1.0)
    second_assessment = model.screener.evaluate_task_telemetry(second)

    assert second_assessment["Observed_Practice_Gain_Points"] == 0.0
    assert second_assessment["Practice_Adjustment_Points"] == 0.0


def test_memory_agent_signal_can_inform_delayed_recall_adaptation():
    model = CognitiveHealthModel(enable_adaptive_dda=True)
    model.adaptive_agent.task_levels["delayed_recall"] = 2
    result = model.process_task_result({
        "game": "delayed_recall", "difficulty_level": 2,
        "attempts": 24, "trial_count": 18, "valid_trial_count": 16,
        "correct_attempts": 15, "incorrect_attempts": 9,
        "accuracy": 15 / 24, "error_rate": 9 / 24,
        "mean_reaction_time_ms": 1400, "median_reaction_time_ms": 1300,
        "immediate_total": 8, "immediate_recall_count": 7,
        "delayed_total": 8, "delayed_recall_count": 2,
        "recognition_hits": 7, "recognition_misses": 1,
        "recognition_false_alarms": 0, "recognition_correct_rejections": 8,
    })

    assert model.memory_agent.latest_analysis["metrics"]["retention_ratio"] == pytest.approx(2 / 7, abs=0.001)
    assert result["dda_action"]["next_difficulty_level"] == 1
    assert "MemoryAnalysisAgent observed lower delayed-than-immediate recall retention" in result["dda_action"]["reason"]
    assert "memory_agent_retention_ratio" in result["dda_action"]["metrics_used"]


def test_attention_agent_signal_can_inform_go_nogo_adaptation():
    model = CognitiveHealthModel(enable_adaptive_dda=True)
    model.adaptive_agent.task_levels["reflex_gonogo"] = 2
    result = model.process_task_result({
        "game": "reflex_gonogo", "difficulty_level": 2,
        "attempts": 12, "trial_count": 12, "valid_trial_count": 12,
        "correct_attempts": 8, "incorrect_attempts": 4,
        "accuracy": 8 / 12, "error_rate": 4 / 12,
        "mean_reaction_time_ms": 420, "median_reaction_time_ms": 410,
        "reaction_time_variability_ms": 60,
        "false_starts": 0, "omission_errors": 0, "commission_errors": 4,
    })

    assert result["dda_action"]["next_difficulty_level"] == 1
    assert "AttentionAnalysisAgent observed repeated responses to NO-GO cues" in result["dda_action"]["reason"]
    assert "attention_agent_commission_error_rate" in result["dda_action"]["metrics_used"]


def test_backend_trial_sanitizer_preserves_valid_timing_but_drops_unknown_fields():
    from electron_backend.server import _sanitize_trial_records

    records = [
        {"trial": 1, "kind": "reflex_simple", "reaction_time_ms": 318, "correct": True,
         "outcome": "hit", "raw_answer_text": "not allowed", "unexpected": {"private": "data"}},
    ] * 305
    cleaned = _sanitize_trial_records(records)

    assert len(cleaned) == 300
    assert cleaned[0]["reaction_time_ms"] == 318
    assert cleaned[0]["correct"] is True
    assert "raw_answer_text" not in cleaned[0]
    assert "unexpected" not in cleaned[0]
