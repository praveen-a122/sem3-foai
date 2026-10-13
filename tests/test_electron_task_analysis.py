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
        "attempts": 1,
        "correct_attempts": 1,
        "incorrect_attempts": 0,
        "accuracy": 1.0,
        "error_rate": 0.0,
        "mean_reaction_time_ms": 500,
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
