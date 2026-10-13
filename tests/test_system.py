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
import threading
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
from frontend.session_manager import (
    SessionManager,
    calculate_failed_attempt_metrics,
    calculate_repeated_tile_metrics,
    classify_metric_band,
)
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

    def test_repeated_tile_misses_count_only_wrong_reopened_tiles(self, tmp_path):
        logger = TelemetryLogger(
            log_filepath=str(tmp_path / "repeated_tile_misses.csv")
        )
        logger.start_round(round_num=1)

        logger.record_card_flip(0, "Sun")
        logger.record_card_flip(1, "Moon")
        assert logger.record_pair_attempt(0, "Sun", 1, "Moon") is False
        assert logger.last_attempt_repeated_tiles == 0

        logger.record_card_flip(0, "Sun")
        logger.record_card_flip(2, "Star")
        assert logger.record_pair_attempt(0, "Sun", 2, "Star") is False
        assert logger.last_attempt_repeated_tiles == 1

        logger.record_card_flip(1, "Moon")
        logger.record_card_flip(2, "Star")
        assert logger.record_pair_attempt(1, "Moon", 2, "Star") is False
        assert logger.last_attempt_repeated_tiles == 2
        assert logger.repeated_tile_misses == 3

        logger.record_card_flip(0, "Sun")
        logger.record_card_flip(3, "Sun")
        assert logger.record_pair_attempt(0, "Sun", 3, "Sun") is True
        assert logger.last_attempt_repeated_tiles == 0
        assert logger.repeated_tile_misses == 3

        summary = logger.complete_round(total_pairs=6)
        assert summary["Repeated_Tile_Misses"] == 3


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

    def test_model_initialization_does_not_wait_for_optional_ml(self, monkeypatch):
        loader_started = threading.Event()
        allow_loader_to_finish = threading.Event()
        initialization_finished = threading.Event()
        models = []
        initialization_errors = []

        def blocked_ml_load(_agent):
            loader_started.set()
            allow_loader_to_finish.wait(timeout=5)

        def initialize_model():
            try:
                models.append(CognitiveHealthModel())
            except Exception as exc:
                initialization_errors.append(exc)
            finally:
                initialization_finished.set()

        monkeypatch.setattr(ScreenerAgent, "_load_ml_model", blocked_ml_load)
        initializer = threading.Thread(target=initialize_model)
        initializer.start()
        try:
            assert loader_started.wait(timeout=5)
            assert initialization_finished.wait(timeout=5), (
                "Mesa model initialization waited for the optional ML load"
            )
            assert not initialization_errors
            assessment = models[0].screener.evaluate_telemetry({})
            assert assessment["Assessment_Method"] == "heuristic_fallback"
        finally:
            allow_loader_to_finish.set()
            initializer.join(timeout=5)
            if models:
                models[0].screener._ml_model_load_thread.join(timeout=5)

        assert not initializer.is_alive()

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
        assert len(model.agents) == 17

        # Resize up to 4x4 (16 tiles)
        model._update_tile_grid("4x4")
        assert len(model.tile_agents) == 16
        assert len(model.agents) == 21
        for r in range(4):
            for c in range(4):
                assert not model.grid.is_cell_empty((r, c))

        # Resize down to 3x4 (12 tiles) - verify row 3 is cleanly evacuated
        model._update_tile_grid("3x4")
        assert len(model.tile_agents) == 12
        assert len(model.agents) == 17
        assert len({agent.unique_id for agent in model.agents}) == len(model.agents)
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
        assert screener._ml_model_loaded.wait(timeout=60), "ML model loading did not complete"
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

    def test_pattern_modes_initialize_input_state(self, tmp_path):
        from frontend.game import CognitiveMemoryGame

        game = CognitiveMemoryGame(
            headless=True,
            enable_mesa_coupling=False,
            log_filepath=str(tmp_path / "pattern_start.csv"),
        )

        game._start_pattern_game()
        assert game.phase == "color_pattern"
        assert game.pattern_playing is True
        assert game.pattern_input == []
        assert len(game.pattern_sequence) == 3
        assert game.pattern_message == "Watch the pattern"
        assert game.max_pattern_levels == 10

        game._start_normal_pattern_game()
        assert game.phase == "normal_pattern"
        assert game.pattern_playing is True
        assert game.pattern_input == []
        assert len(game.pattern_sequence) == 3
        assert game.pattern_message == "Watch the pattern"
        assert len(game.pattern_color_order) == len(game.pattern_colors)

        game._start_pattern_game()
        assert game.phase == "color_pattern"
        assert len(game.pattern_color_order) == len(game.pattern_colors)

    def test_enter_submission_advances_and_finishes_free_play(self, tmp_path):
        from frontend.game import CognitiveMemoryGame

        game = CognitiveMemoryGame(
            headless=True,
            enable_mesa_coupling=False,
            log_filepath=str(tmp_path / "pattern_submit.csv"),
        )
        game._start_pattern_game()
        game.pattern_playing = False
        game.pattern_input = list(game.pattern_sequence)

        game._submit_pattern()
        assert game.pattern_level == 2
        assert len(game.pattern_sequence) == 4
        assert game.pattern_playing is True

        game.pattern_playing = False
        game.pattern_level = game.max_pattern_levels
        game.pattern_input = list(game.pattern_sequence)
        game._submit_pattern()
        assert game.phase == "pattern_complete"
        assert game.pattern_message == "You completed all 10 levels!"

    def test_color_pattern_records_color_not_position(self, tmp_path, monkeypatch):
        from frontend.game import CognitiveMemoryGame

        game = CognitiveMemoryGame(
            headless=True,
            enable_mesa_coupling=False,
            log_filepath=str(tmp_path / "color_identity.csv"),
        )
        game._start_pattern_game()
        game.pattern_color_order = [3, 0, 5, 1, 6, 2, 4]
        game.pattern_playing = False

        # Clicking the cell currently showing GREEN records GREEN's identity (3),
        # rather than that cell's position (0).
        game._handle_pattern_click(game.pattern_cells[0].center)
        assert game.pattern_input == [3]

        game.pattern_sequence = [0, 1, 2]
        previous_order = list(game.pattern_color_order)
        monkeypatch.setattr("frontend.game.random.shuffle", lambda order: order.reverse())
        game._replay_pattern()
        assert game.pattern_sequence == [0, 1, 2]
        assert game.pattern_color_order == list(reversed(previous_order))
        assert game.pattern_playing is True

    def test_normal_pattern_flashes_one_of_nine_cells(self, tmp_path, monkeypatch):
        import pygame
        from frontend.game import CognitiveMemoryGame

        pygame.font.init()
        monkeypatch.setattr(pygame.display, "flip", lambda: None)
        game = CognitiveMemoryGame(
            headless=True,
            enable_mesa_coupling=False,
            log_filepath=str(tmp_path / "normal_pattern_flash.csv"),
        )
        game.screen = pygame.Surface((game.width, game.height))
        game.font_header = pygame.font.SysFont(None, 30)
        game.font_sub = pygame.font.SysFont(None, 20)
        game.font_small = pygame.font.SysFont(None, 14)
        game._start_normal_pattern_game()

        assert len(game.normal_pattern_cells) == 9
        game.pattern_next_at = 0
        game.update()
        assert game.pattern_active_cell in range(9)

        active_cell = game.pattern_active_cell
        game.draw()
        assert game.screen.get_at(
            game.normal_pattern_cells[active_cell].center
        )[:3] == (245, 245, 245)

    def test_session_performance_metrics_and_threshold_bands(self):
        session = {
            "attempts": [
                {"game": "pairs", "success": False, "repeated_tile_count": 1},
                {"game": "pairs", "success": True, "repeated_tile_count": 0},
                {"game": "color_pattern", "success": False},
                {"game": "pairs", "success": False, "repeated_tile_count": 2},
            ]
        }
        failed = calculate_failed_attempt_metrics(session)
        repeated = calculate_repeated_tile_metrics(session)

        assert failed == {
            "failed_attempts": 3,
            "total_attempts": 4,
            "failed_percentage": 75.0,
        }
        assert repeated == {
            "repeated_tile_misses": 3,
            "total_pair_card_flips": 6,
            "tracked_pair_attempts": 3,
            "repeated_tile_percentage": 50.0,
        }
        assert classify_metric_band(24.9, 25, 50) == "Healthy-range"
        assert classify_metric_band(25, 25, 50) == "Borderline"
        assert classify_metric_band(50, 25, 50) == "High concern (red)"

    def test_telemetry_settings_menu_adjusts_percentage_sliders(
        self, tmp_path, monkeypatch
    ):
        import pygame
        from frontend.game import CognitiveMemoryGame

        pygame.font.init()
        monkeypatch.setattr(pygame.display, "flip", lambda: None)
        game = CognitiveMemoryGame(
            headless=True,
            enable_mesa_coupling=False,
            log_filepath=str(tmp_path / "settings.csv"),
        )
        game.screen = pygame.Surface((game.width, game.height))
        game.font_header = pygame.font.SysFont(None, 30)
        game.font_sub = pygame.font.SysFont(None, 20)
        game.font_small = pygame.font.SysFont(None, 14)
        game.phase = "session_detail"
        assert game._handle_section_click(game.telemetry_settings_button.center)
        assert game.phase == "telemetry_settings"
        game.draw()

        high_slider = game.telemetry_threshold_sliders["failed_high"]
        game._set_telemetry_threshold_from_x(
            "failed_high", high_slider.left + round(high_slider.width * 0.6)
        )
        assert game.telemetry_thresholds["failed_high"] == 60

        borderline_slider = game.telemetry_threshold_sliders["failed_borderline"]
        game._set_telemetry_threshold_from_x(
            "failed_borderline", borderline_slider.right
        )
        assert game.telemetry_thresholds["failed_borderline"] == 59

        assert game._handle_section_click(game.menu_button.center)
        assert game.phase == "session_detail"

    def test_game_records_reopened_wrong_tile_in_patient_session(self, tmp_path):
        import time
        from frontend.game import CognitiveMemoryGame

        game = CognitiveMemoryGame(
            headless=True,
            enable_mesa_coupling=False,
            log_filepath=str(tmp_path / "repeat_tile_session.csv"),
        )
        manager = SessionManager()
        manager.root = tmp_path / "sessions"
        manager.root.mkdir()
        manager.start({"name": "Patient"}, ["pairs"], "Easy")
        game.session_manager = manager
        game.testing_active = True
        game.phase = "pairs"
        game._setup_round()

        first_card = game.cards[0]
        first_wrong_pair = next(
            card for card in game.cards if card.pair_id != first_card.pair_id
        )
        game.handle_click(first_card.rect.center)
        game.handle_click(first_wrong_pair.rect.center)
        assert manager.data["attempts"][-1]["repeated_tile_count"] == 0

        game.mismatch_timer = time.time() - game.exposure_time_sec - 0.1
        game.update()
        second_wrong_pair = next(
            card for card in game.cards
            if card.pair_id != first_card.pair_id
            and card is not first_wrong_pair
        )
        game.handle_click(first_card.rect.center)
        game.handle_click(second_wrong_pair.rect.center)

        assert manager.data["attempts"][-1]["repeated_tile_count"] == 1
        assert calculate_repeated_tile_metrics(manager.data)[
            "repeated_tile_misses"
        ] == 1

    def test_session_saves_patient_profile_photo_and_telemetry(self, tmp_path):
        import pygame

        manager = SessionManager()
        manager.root = tmp_path / "sessions"
        manager.root.mkdir()
        photo_source = tmp_path / "patient.png"
        pygame.image.save(pygame.Surface((32, 32)), photo_source)

        participant = {
            "name": "Test Patient",
            "age": "76",
            "gender": "Female",
            "previous_medical_history": "Hypertension",
        }
        manager.start(
            participant,
            ["pairs"],
            "Easy",
            photo_path=photo_source,
        )
        manager.record_round_telemetry(
            "pairs",
            1,
            {"Mean_Reaction_Time_ms": 1250.0, "Error_Rate": 0.1},
        )

        record = manager.list_sessions()[0]
        saved_photo = manager.photo_path_for(record)
        assert saved_photo is not None and saved_photo.is_file()
        assert record["participant"]["name"] == "Test Patient"
        assert record["participant"]["age"] == "76"
        assert record["participant"]["gender"] == "Female"
        assert record["participant"]["previous_medical_history"] == "Hypertension"
        assert record["rounds"][0]["telemetry"]["Mean_Reaction_Time_ms"] == 1250.0
        assert participant.get("photo_file") is None

        no_photo_manager = SessionManager()
        no_photo_manager.root = tmp_path / "sessions_without_photo"
        no_photo_manager.root.mkdir()
        no_photo_manager.start(participant, ["pairs"], "Easy")
        no_photo_record = no_photo_manager.list_sessions()[0]
        assert "photo_file" not in no_photo_record["participant"]
        assert no_photo_manager.photo_path_for(no_photo_record) is None

    def test_medical_history_tag_opens_its_session_telemetry(self, tmp_path):
        from frontend.game import CognitiveMemoryGame

        game = CognitiveMemoryGame(
            headless=True,
            enable_mesa_coupling=False,
            log_filepath=str(tmp_path / "tag_click.csv"),
        )
        record = {
            "session_id": "selected-patient",
            "participant": {
                "name": "Selected Patient",
                "previous_medical_history": "Asthma",
            },
            "rounds": [{"telemetry": {"Mean_Reaction_Time_ms": 1400.0}}],
        }
        game.phase = "sessions"
        game.session_records = [record]

        assert game._handle_section_click((200, 175))
        assert game.phase == "session_detail"
        assert game.selected_session is record
        assert game.selected_session["rounds"][0]["telemetry"][
            "Mean_Reaction_Time_ms"
        ] == 1400.0

    def test_patient_card_and_scrollable_telemetry_render(self, tmp_path, monkeypatch):
        import pygame
        from frontend.game import CognitiveMemoryGame

        pygame.font.init()
        monkeypatch.setattr(pygame.display, "flip", lambda: None)
        game = CognitiveMemoryGame(
            headless=True,
            enable_mesa_coupling=False,
            log_filepath=str(tmp_path / "patient_card.csv"),
        )
        game.screen = pygame.Surface((game.width, game.height))
        game.font_header = pygame.font.SysFont(None, 30)
        game.font_sub = pygame.font.SysFont(None, 20)
        game.font_small = pygame.font.SysFont(None, 14)

        manager = SessionManager()
        manager.root = tmp_path / "sessions"
        manager.root.mkdir()
        photo_path = tmp_path / "patient.png"
        pygame.image.save(pygame.Surface((32, 32)), photo_path)
        manager.start(
            {
                "name": "Patient",
                "age": "75",
                "gender": "Other",
                "previous_medical_history": "Long medical history " * 20,
            },
            ["pairs"],
            "Easy",
            photo_path=photo_path,
        )
        for round_number in range(12):
            manager.record_round_telemetry(
                "pairs", round_number + 1, {"Mean_Reaction_Time_ms": 1200.0}
            )

        game.session_manager = manager
        game.session_records = manager.list_sessions()
        game.phase = "sessions"
        game._draw_section()
        assert len(game.session_photo_cache) == 1

        game.selected_session = game.session_records[0]
        game.phase = "session_detail"
        game._draw_section()
        game.session_detail_scroll = 1000
        game._draw_section()
        assert game.session_detail_scroll > 0

    def test_game_initialization_and_card_clicks(self, tmp_path):
        from frontend.game import CognitiveMemoryGame
        game_log = str(tmp_path / "test_game_init.csv")
        game = CognitiveMemoryGame(headless=True, enable_mesa_coupling=True, initial_grid="3x4", log_filepath=game_log)
        game._handle_section_click(game.home_buttons[0].center)
        assert game.phase == "menu"
        assert game._handle_game_menu_click(game.pair_menu_button.center)
        assert game.phase == "pairs"
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

    def test_testing_session_starts_selected_pairs_game(self, tmp_path):
        from frontend.game import CognitiveMemoryGame

        game = CognitiveMemoryGame(
            headless=True,
            enable_mesa_coupling=False,
            log_filepath=str(tmp_path / "testing_pairs.csv"),
        )
        game.session_manager = SessionManager()
        game.session_manager.root = tmp_path / "sessions"
        game.session_manager.root.mkdir()

        game._handle_section_click(game.home_buttons[1].center)
        assert game.phase == "testing_form"
        game.testing_fields["Participant name"] = "Test Patient"
        game.testing_fields["Age"] = "72"
        game._handle_section_click((400, 630))
        assert game.phase == "testing_config"

        game._handle_section_click((300, 235))
        assert game.game_checks[0] is True
        game._handle_section_click((480, 565))

        assert game.phase == "pairs"
        assert game.testing_active is True
        assert game.testing_games == ["pairs"]
        assert len(game.cards) == 12

    def test_pair_tiles_are_randomized_without_adjacent_matches(self, tmp_path):
        from frontend.game import CognitiveMemoryGame

        game = CognitiveMemoryGame(
            headless=True,
            enable_mesa_coupling=False,
            log_filepath=str(tmp_path / "pair_layout.csv"),
        )
        game._start_pairs_game()

        for round_number, grid_size in enumerate(game.PAIR_ROUND_GRIDS, start=1):
            game.round_number = round_number
            game._setup_round()
            rows, cols = map(int, grid_size.split("x"))
            pair_ids = [card.pair_id for card in game.cards]

            assert len(pair_ids) == rows * cols
            assert all(pair_ids.count(pair_id) == 2 for pair_id in set(pair_ids))
            for row in range(rows):
                for col in range(cols):
                    index = row * cols + col
                    if col + 1 < cols:
                        assert pair_ids[index] != pair_ids[index + 1]
                    if row + 1 < rows:
                        assert pair_ids[index] != pair_ids[index + cols]

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
