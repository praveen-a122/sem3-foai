"""
Comprehensive Automated Verification Test Suite
================================================
Course: 22AIE201 - Fundamentals of AI
Validates all requirements for Team 3:
1. Authentic OASIS Dataset Ingestion & Calibration (CO3)
2. High-Resolution Telemetry & Latency Logging with Pause/Resume Tracking (CO1, Question Pool #38, #41)
3. Mesa Multi-Agent Closed-Loop Engine & 2D SingleGrid Representation (CO4, Faculty Directive: Single agent DDA)
4. ScreenerAgent Machine Learning Pipeline & Clinical Classification (Item B)
5. Dynamic Difficulty Adjustment (Eun et al., 2022)
6. Card Assets Expansion (30 items) & Permutation Fallbacks (Item 1)
7. Spatial Mesa Grid Cleanup on Resizing (Item 3)
8. Atomic is_analyzing_telemetry Input Guard (Item 4)
"""

import os
import sys
import time
import pytest
import numpy as np

# Ensure root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from data.dataset_calibration import OasisClinicalCalibrator
from frontend.ui_assets import (
    CARD_SYMBOLS,
    COLORS,
    get_symbols_for_pairs,
    calculate_relative_luminance,
    calculate_contrast_ratio,
    is_wcag_aa_compliant,
    is_wcag_aaa_compliant,
)
from frontend.telemetry_logger import TelemetryLogger
from simulation.agents import PatientAgent, ScreenerAgent, AdaptiveDifficultyAgent, TileAgent
from simulation.model import CognitiveHealthModel
from mesa.space import SingleGrid


class TestOasisCalibration:
    """Verifies empirical clinical calibration from authentic OASIS-1 dementia dataset."""

    def test_dataset_loading_and_strata(self):
        calibrator = OasisClinicalCalibrator()
        df = calibrator.load_or_generate_dataset()
        assert not df.empty
        assert "CDR" in df.columns
        assert "MMSE" in df.columns
        assert "Age" in df.columns

        strata = calibrator.compute_strata_statistics()
        assert 0.0 in strata
        assert 0.5 in strata
        assert 1.0 in strata

        # Clinical validity check: MMSE in healthy controls (CDR=0) > MCI (CDR=0.5) > Dementia (CDR=1)
        assert strata[0.0]["mmse_mean"] > strata[0.5]["mmse_mean"]
        assert strata[0.5]["mmse_mean"] > strata[1.0]["mmse_mean"]

    def test_calibrated_agent_parameters(self):
        calibrator = OasisClinicalCalibrator()
        p_normal = calibrator.get_calibrated_agent_parameters(cdr_level=0.0, age=75, educ=3)
        p_mci = calibrator.get_calibrated_agent_parameters(cdr_level=0.5, age=75, educ=3)
        p_dem = calibrator.get_calibrated_agent_parameters(cdr_level=1.0, age=75, educ=3)

        # Normal has higher capacity and faster reaction time than MCI and Dementia
        assert p_normal["cognitive_capacity"] > p_mci["cognitive_capacity"]
        assert p_mci["cognitive_capacity"] > p_dem["cognitive_capacity"]
        assert p_normal["reaction_time_mean_ms"] < p_mci["reaction_time_mean_ms"]
        assert p_normal["error_probability"] < p_dem["error_probability"]


class TestTelemetryLogger:
    """Verifies sub-second telemetry logging, hesitation interval capture, and timer pause/resume."""

    def test_logging_and_hesitation(self, tmp_path):
        log_file = tmp_path / "test_session_logs.csv"
        logger = TelemetryLogger(log_filepath=str(log_file))

        logger.start_round(round_num=1, grid_size="3x4", difficulty="Gentle")

        # Simulate 2 flips
        rt1 = logger.record_card_flip(card_idx=0, card_value="Sun")
        rt2 = logger.record_card_flip(card_idx=1, card_value="Sun")
        is_match = logger.record_pair_attempt(0, "Sun", 1, "Sun")
        assert is_match is True

        summary = logger.complete_round(total_pairs=6)
        assert summary["Total_Flips"] == 2
        assert summary["Matches_Found"] == 1
        assert os.path.exists(log_file)

    def test_pause_resume_latency_timer(self, tmp_path):
        """Ensures non-interactive exposure pauses are deducted from player reaction times."""
        log_file = tmp_path / "test_pause_logs.csv"
        logger = TelemetryLogger(log_filepath=str(log_file))
        logger.start_round(round_num=1, grid_size="3x4")

        # First flip
        logger.record_card_flip(card_idx=0, card_value="Sun")

        # Pause timer during mismatch display (e.g. 80ms)
        logger.pause_latency_timer()
        time.sleep(0.08)
        logger.resume_latency_timer()

        # Immediate second flip
        rt2 = logger.record_card_flip(card_idx=1, card_value="Moon")
        # Reaction time should be minimal (< 70ms) despite 80ms sleep
        assert rt2 < 70.0


class TestCardAssetsAndGenerator:
    """Verifies expanded 30 symbols and robust fallback permutation generation."""

    def test_expanded_card_symbols_count(self):
        assert len(CARD_SYMBOLS) >= 30
        names = [s["name"] for s in CARD_SYMBOLS]
        assert len(names) == len(set(names))  # All unique

    def test_get_symbols_for_pairs_fallback(self):
        # Normal sampling
        syms_10 = get_symbols_for_pairs(10)
        assert len(syms_10) == 10

        # Boundary: request 30
        syms_30 = get_symbols_for_pairs(30)
        assert len(syms_30) == 30

        # Exceeds base population (e.g. 45 pairs): should dynamically generate permutations without error
        syms_45 = get_symbols_for_pairs(45)
        assert len(syms_45) == 45
        assert len(set(s["name"] for s in syms_45)) == 45

    def test_w3c_contrast_ratios(self):
        """Verifies W3C relative luminance, contrast formulas, and WCAG AA/AAA compliance."""
        # 1. Mathematical boundary checks
        black = (0, 0, 0)
        white = (255, 255, 255)
        assert abs(calculate_relative_luminance(black) - 0.0) < 1e-4
        assert abs(calculate_relative_luminance(white) - 1.0) < 1e-4
        assert abs(calculate_contrast_ratio(black, white) - 21.0) < 1e-2

        # 2. UI Layout Palette compliance checks
        # TEXT_LIGHT on dark BACKGROUND and PANEL_BG must be >= 7.0:1 (WCAG AAA)
        assert is_wcag_aaa_compliant(COLORS["TEXT_LIGHT"], COLORS["BACKGROUND"])
        assert is_wcag_aaa_compliant(COLORS["TEXT_LIGHT"], COLORS["PANEL_BG"])
        assert is_wcag_aaa_compliant(COLORS["TEXT_MUTED"], COLORS["BACKGROUND"])

        # 3. Card Front Symbol Contrast checks (>= 4.5:1 against CARD_FRONT_BG for all 30 symbols)
        bg = COLORS["CARD_FRONT_BG"]
        for sym in CARD_SYMBOLS:
            ratio = calculate_contrast_ratio(sym["color"], bg)
            assert ratio >= 4.5, f"Symbol {sym['name']} color {sym['color']} ratio {ratio:.2f} is below 4.5:1"
            assert is_wcag_aa_compliant(sym["color"], bg)


class TestMesaMultiAgentSpatialClosedLoop:
    """Verifies Mesa model, PatientAgent, ScreenerAgent, AdaptiveDifficultyAgent, and 2D SingleGrid."""

    def test_spatial_singlegrid_representation(self):
        model = CognitiveHealthModel(
            cdr_level=0.0,
            patient_age=72,
            patient_educ=4,
            target_profile="Elderly",
            enable_adaptive_dda=True
        )

        # Spatial grid verification
        assert isinstance(model.grid, SingleGrid)
        assert model.grid.width == 6
        assert model.grid.height == 6

        # Check core agents placed on dedicated cells
        assert model.patient.pos == (5, 0)
        assert model.screener.pos == (5, 4)
        assert model.adaptive_agent.pos == (5, 5)

        # Check tile agents populated for 3x4 board (12 tiles)
        assert len(model.tile_agents) == 12
        for (r, c), tile in model.tile_agents.items():
            assert 0 <= r < 3
            assert 0 <= c < 4
            assert tile.pos == (r, c)
            assert isinstance(tile, TileAgent)
            assert hasattr(tile, "unique_id") and tile.unique_id is not None

    def test_spatial_tile_grid_dynamic_resizing_cleanup(self):
        """Ensures resizing from 3x4 to 4x4 and back cleanly removes tiles without OccupiedError."""
        model = CognitiveHealthModel()
        assert len(model.tile_agents) == 12

        # Resize up to 4x4 (16 tiles)
        model._update_tile_grid("4x4")
        assert len(model.tile_agents) == 16
        for r in range(4):
            for c in range(4):
                assert not model.grid.is_cell_empty((r, c))

        # Resize down to 3x4 (12 tiles) - verify row 3 is cleanly evacuated
        model._update_tile_grid("3x4")
        assert len(model.tile_agents) == 12
        for c in range(4):
            # Row 3 must be empty now
            assert model.grid.is_cell_empty((3, c))

    def test_model_synthetic_step_and_spatial_movement(self):
        model = CognitiveHealthModel(
            cdr_level=0.0,
            patient_age=72,
            patient_educ=4,
            target_profile="Elderly",
            enable_adaptive_dda=True
        )

        step_res = model.step_synthetic_round()
        assert "telemetry" in step_res
        assert "assessment" in step_res
        assert "dda_action" in step_res

        # Check screener assessment
        assert "Predicted_MMSE" in step_res["assessment"]
        assert 10.0 <= step_res["assessment"]["Predicted_MMSE"] <= 30.0

        # Check DDA action
        assert "grid_size" in step_res["dda_action"]
        assert step_res["dda_action"]["grid_size"] in ["3x4", "4x4", "4x5"]

        # Check patient coordinate on SingleGrid reflects difficulty state
        assert model.patient.pos[0] == 5
        assert 0 <= model.patient.pos[1] <= 3

    def test_native_mesa_model_step(self):
        """Verifies direct Mesa model.step() advances simulation time and agent turn cycles."""
        model = CognitiveHealthModel(cdr_level=0.5, patient_age=78, patient_educ=2)
        assert model.current_round == 0
        assert len(model.history_records) == 0

        # Direct Mesa model step invocation
        model.step()

        assert model.current_round == 1
        assert len(model.history_records) == 1
        last = model.history_records[-1]
        assert last["round"] == 1
        assert "Mean_Reaction_Time_ms" in last["telemetry"]
        assert "Predicted_MMSE" in last["assessment"]
        assert "grid_size" in last["dda_action"]
        assert len(model.datacollector.get_model_vars_dataframe()) == 1

    def test_dda_downgrade_under_high_error(self):
        """Tests that AdaptiveDifficultyAgent downgrades complexity if error rate is high."""
        model = CognitiveHealthModel(cdr_level=0.5, enable_adaptive_dda=True)
        adaptive_agent = model.adaptive_agent
        adaptive_agent.current_grid_idx = 1  # 4x4

        # Artificial high error telemetry
        telemetry = {
            "Error_Rate": 0.55,
            "Mean_Reaction_Time_ms": 3200.0,
            "Hesitation_Intervals_Count": 4,
            "Total_Flips": 20,
            "Patient_Fatigue": 0.75,
            "Patient_Anxiety": 0.80
        }
        clinical_state = {"Clinical_Flag": "Mild Cognitive Impairment (MCI) Alert"}

        action = adaptive_agent.evaluate_and_adapt(telemetry, clinical_state)
        # Should downgrade back to 3x4 and recommend a micro-break
        assert action["grid_size"] == "3x4"
        assert action["micro_break_recommended"] is True

    def test_screener_ml_model_inference_and_stratification(self):
        """Tests that ScreenerAgent uses the ML model to accurately classify healthy vs deficit."""
        model = CognitiveHealthModel()
        screener = model.screener
        assert screener.ml_trained is True

        # Healthy telemetry: Fast RT, minimal errors, zero hesitations
        telemetry_healthy = {
            "Mean_Reaction_Time_ms": 1150.0,
            "Error_Rate": 0.05,
            "Hesitation_Intervals_Count": 0,
            "Redundant_Errors": 0,
            "Total_Flips": 12
        }
        res_h = screener.evaluate_telemetry(telemetry_healthy, patient_age=70, patient_educ=4)
        assert res_h["Clinical_Flag"] == "Normal Cognition"
        assert res_h["Predicted_MMSE"] >= 27.0
        assert res_h["Confidence"] >= 0.50

        # Severely impaired telemetry: High RT, high error rate, heavy hesitation
        telemetry_impaired = {
            "Mean_Reaction_Time_ms": 4200.0,
            "Error_Rate": 0.65,
            "Hesitation_Intervals_Count": 8,
            "Redundant_Errors": 8,
            "Total_Flips": 24
        }
        res_i = screener.evaluate_telemetry(telemetry_impaired, patient_age=82, patient_educ=2)
        assert "Dementia" in res_i["Clinical_Flag"] or "MCI" in res_i["Clinical_Flag"]
        assert res_i["Predicted_MMSE"] < 27.0


class TestPygameGameFlow:
    """Verifies that the Pygame Serious Game integrates seamlessly with Mesa closed loop."""

    def test_game_initialization_and_card_clicks(self, tmp_path):
        from frontend.game import CognitiveMemoryGame
        game_log = str(tmp_path / "test_game_init.csv")
        game = CognitiveMemoryGame(headless=True, enable_mesa_coupling=True, initial_grid="3x4", log_filepath=game_log)
        assert len(game.cards) == 12  # 3x4 = 12 cards (6 pairs)
        assert game.round_number == 1

        # Simulate clicking two cards
        c1 = game.cards[0]
        c2 = game.cards[1]
        game.handle_click(c1.rect.center)
        assert c1.is_flipped is True
        game.handle_click(c2.rect.center)
        assert c2.is_flipped is True

        # Trigger round completion manually to test closed loop
        for c in game.cards:
            c.is_matched = True
        game._on_round_completed()
        assert game.round_completed is True
        assert game.last_clinical_flag != "Awaiting First Assessment"

    def test_game_input_lock_behavior(self, tmp_path):
        """Verifies that is_analyzing_telemetry lock prevents advancing rounds during calibration."""
        from frontend.game import CognitiveMemoryGame
        game_log = str(tmp_path / "test_game_lock.csv")
        game = CognitiveMemoryGame(headless=True, enable_mesa_coupling=True, log_filepath=game_log)

        # Engage lock
        game.is_analyzing_telemetry = True
        initial_round = game.round_number
        game.advance_to_next_round()
        # Round should NOT advance while telemetry analysis lock is engaged
        assert game.round_number == initial_round

        # Release lock
        game.is_analyzing_telemetry = False
        game.advance_to_next_round()
        assert game.round_number == initial_round + 1
