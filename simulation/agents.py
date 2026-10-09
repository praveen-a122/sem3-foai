import os
import pickle
import mesa
import numpy as np
from typing import Dict, Any, Optional, List, Tuple


class TileAgent(mesa.Agent):
    """
    Spatial Agent representing an interactive tile cell on the 2D Mesa SingleGrid.
    Supports Solara/Canvas visualization and spatial board modeling for 22AIE201.
    States: 'FACE_DOWN', 'FACE_UP', 'MATCHED', 'INACTIVE'
    """

    def __init__(
        self,
        model: mesa.Model,
        unique_id: int,
        pos: Optional[Tuple[int, int]] = None,
        pair_id: int = -1,
        symbol: str = ""
    ):
        try:
            super().__init__(model)
        except TypeError:
            super().__init__(unique_id, model)

        # Guarantee unique_id is always explicitly defined across Mesa versions
        self.unique_id = unique_id
        self.pos: Optional[Tuple[int, int]] = None
        self.pair_id = pair_id
        self.symbol = symbol
        self.tile_state: str = "FACE_DOWN"  # "FACE_DOWN", "FACE_UP", "MATCHED", "INACTIVE"

    def step(self) -> None:
        """Called each simulation tick."""
        pass


class PatientAgent(mesa.Agent):
    """
    Simulates an individual patient undergoing cognitive gameplay assessment.
    Maintains internal physiological and psychological state:
    - cognitive_capacity: Working memory and processing speed efficiency [0.1, 1.0]
    - fatigue_level: Accumulated fatigue across rounds [0.0, 1.0]
    - anxiety_index: Test anxiety / frustration index [0.0, 1.0]
    - pos: Coordinates on the Mesa 2D SingleGrid
    """

    def __init__(
        self,
        model: mesa.Model,
        unique_id: Optional[int] = None,
        cdr_level: float = 0.0,
        age: int = 75,
        educ: int = 3,
        calibrated_params: Optional[Dict[str, float]] = None
    ):
        uid = unique_id if unique_id is not None else 1
        try:
            super().__init__(model)
        except TypeError:
            super().__init__(uid, model)

        self.unique_id = uid
        self.cdr_level = cdr_level
        self.age = age
        self.educ = educ
        self.pos: Optional[Tuple[int, int]] = None

        # Default or calibrated baselines
        params = calibrated_params or {}
        self.cognitive_capacity = params.get("cognitive_capacity", 0.85 if cdr_level == 0.0 else (0.65 if cdr_level == 0.5 else 0.45))
        self.rt_mean_base_ms = params.get("reaction_time_mean_ms", 1200.0 if cdr_level == 0.0 else (2100.0 if cdr_level == 0.5 else 3400.0))
        self.rt_std_base_ms = params.get("reaction_time_std_ms", 250.0)
        self.base_error_prob = params.get("error_probability", 0.12 if cdr_level == 0.0 else (0.32 if cdr_level == 0.5 else 0.58))
        self.hesitation_prob = params.get("hesitation_probability", 0.08 if cdr_level == 0.0 else (0.28 if cdr_level == 0.5 else 0.55))
        self.fatigue_rate = params.get("fatigue_accumulation_rate", 0.02)

        # Dynamic state
        self.fatigue_level: float = 0.0
        self.anxiety_index: float = 0.10
        self.dropout: bool = False
        self.consecutive_failures: int = 0
        self.last_round_telemetry: Dict[str, Any] = {}

    def step(self) -> None:
        """
        Autonomous Patient Agent Turn:
        1. Inspects environment/model difficulty parameters (grid size & exposure duration).
        2. Simulates human gameplay action (latencies, errors, hesitations).
        3. Updates internal physiological/psychological state (fatigue accumulation & test anxiety).
        4. Evaluates dropout condition and publishes telemetry to self.model.latest_telemetry.
        """
        if self.dropout:
            self.last_round_telemetry = {
                "status": "dropped_out",
                "Dropped_Out": True,
                "Patient_Fatigue": round(self.fatigue_level, 3),
                "Patient_Anxiety": round(self.anxiety_index, 3)
            }
            if hasattr(self.model, "latest_telemetry"):
                self.model.latest_telemetry = self.last_round_telemetry
            return

        # Determine active difficulty parameters from model or default
        grid_size = "3x4"
        exposure = 1.5
        if hasattr(self.model, "adaptive_agent"):
            grid_size = self.model.adaptive_agent.get_current_grid() if getattr(self.model, "enable_adaptive_dda", True) else "4x4"
            exposure = self.model.adaptive_agent.get_current_exposure() if getattr(self.model, "enable_adaptive_dda", True) else 1.5

        # Execute simulated gameplay round
        self.last_round_telemetry = self.simulate_gameplay_round(grid_size, exposure)

        # Fatigue gradually accumulates per round
        self.fatigue_level = float(np.clip(self.fatigue_level + self.fatigue_rate, 0.0, 1.0))

        # Test anxiety triggers if consecutive failures or excessive cognitive load
        if self.consecutive_failures >= 2:
            self.anxiety_index = float(np.clip(self.anxiety_index + 0.18, 0.0, 1.0))
        else:
            self.anxiety_index = float(np.clip(self.anxiety_index - 0.08, 0.05, 1.0))

        # Mezrar & Bendella (2022): High anxiety + excessive fatigue leads to assessment dropout
        if self.anxiety_index > 0.85 and self.fatigue_level > 0.80:
            self.dropout = True

        self.last_round_telemetry["Patient_Fatigue"] = round(self.fatigue_level, 3)
        self.last_round_telemetry["Patient_Anxiety"] = round(self.anxiety_index, 3)
        self.last_round_telemetry["Dropped_Out"] = self.dropout

        if hasattr(self.model, "latest_telemetry"):
            self.model.latest_telemetry = self.last_round_telemetry

    def simulate_gameplay_round(self, grid_size: str, exposure_time_sec: float) -> Dict[str, Any]:
        """
        Simulates human round performance based on internal state and current task parameters.
        Returns a telemetry dictionary matching real PyGame output.
        """
        if self.dropout:
            return {"status": "dropped_out"}

        # Determine number of pairs from grid size
        grid_dims = [int(x) for x in grid_size.lower().split("x")]
        total_tiles = grid_dims[0] * grid_dims[1]
        total_pairs = total_tiles // 2

        # Complexity penalty
        complexity_scale = total_pairs / 6.0  # 3x4 = 6 pairs baseline

        # Fatigue & anxiety penalties on processing speed and memory
        effective_capacity = self.cognitive_capacity * (1.0 - 0.35 * self.fatigue_level) * (1.0 - 0.25 * self.anxiety_index)
        effective_capacity = max(0.05, effective_capacity)

        # Reaction time calculation (Sirály et al., 2015; Paletta et al., 2020)
        rt_multiplier = 1.0 + (1.0 - effective_capacity) * 1.2 + (self.fatigue_level * 0.5)
        round_rt_mean = self.rt_mean_base_ms * rt_multiplier * np.sqrt(complexity_scale)
        round_rt_mean = float(np.clip(np.random.normal(round_rt_mean, self.rt_std_base_ms), 600.0, 8000.0))

        # Hesitation count (pauses > 3000ms, Torabgar et al., 2025)
        exposure_benefit = max(0.0, (exposure_time_sec - 1.0) * 0.15)
        effective_hesitation_prob = np.clip(self.hesitation_prob * (1.0 + self.fatigue_level * 0.6) - exposure_benefit, 0.02, 0.90)
        hesitation_count = int(np.random.binomial(total_pairs * 2, effective_hesitation_prob))

        # Error rate calculation (Oliveira et al., 2022)
        effective_error_prob = np.clip(self.base_error_prob * (1.0 / effective_capacity) * (complexity_scale ** 0.8), 0.05, 0.85)
        redundant_errors = int(np.random.binomial(int(total_pairs * 2.2), effective_error_prob))
        total_flips = (total_pairs * 2) + (redundant_errors * 2)
        match_attempts = total_flips // 2
        error_rate = redundant_errors / max(1, match_attempts)

        completion_time_sec = (total_flips * (round_rt_mean / 1000.0)) + (hesitation_count * 3.5)

        # Track failure for anxiety
        if error_rate > 0.40:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0

        self.last_round_telemetry = {
            "Grid_Size": grid_size,
            "Total_Pairs": total_pairs,
            "Total_Flips": total_flips,
            "Matches_Found": total_pairs,
            "Redundant_Errors": redundant_errors,
            "Error_Rate": round(error_rate, 4),
            "Mean_Reaction_Time_ms": round(round_rt_mean, 2),
            "Hesitation_Intervals_Count": hesitation_count,
            "Round_Completion_Time_sec": round(completion_time_sec, 2),
            "Patient_Fatigue": round(self.fatigue_level, 3),
            "Patient_Anxiety": round(self.anxiety_index, 3),
            "Dropped_Out": self.dropout
        }
        return self.last_round_telemetry

    def apply_adaptive_feedback(self, difficulty_adapted: bool, break_given: bool = False) -> None:
        """
        Feedback loop callback from AdaptiveDifficultyAgent.
        Adapting difficulty reduces frustration; breaks reduce fatigue.
        """
        if break_given:
            self.fatigue_level = max(0.0, self.fatigue_level - 0.25)
        if difficulty_adapted:
            self.anxiety_index = max(0.05, self.anxiety_index - 0.15)


class ScreenerAgent(mesa.Agent):
    """
    Clinical Assessment & Screening Agent (Shreyas Hari - BL.SC.U4AIE25041)
    Powered by a trained scikit-learn Machine Learning Pipeline (`data/screener_model.pkl`).
    Grounded in OASIS-1 empirical distributions and session telemetry features.
    """

    def __init__(self, model: mesa.Model, unique_id: Optional[int] = None):
        uid = unique_id if unique_id is not None else 2
        try:
            super().__init__(model)
        except TypeError:
            super().__init__(uid, model)

        self.unique_id = uid
        self.pos: Optional[Tuple[int, int]] = None
        self.session_history: List[Dict[str, Any]] = []
        self.predicted_mmse: float = 30.0
        self.cognitive_state_index: float = 100.0
        self.clinical_flag: str = "Normal Cognition"
        self.confidence_score: float = 0.95
        self.latest_assessment: Dict[str, Any] = {}

        # Machine Learning Pipelines
        self.clf_pipeline = None
        self.reg_pipeline = None
        self.ml_trained: bool = False
        self._load_ml_model()

    def _load_ml_model(self) -> None:
        """Load the optional ML model; keep the screener usable if unavailable."""
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "screener_model.pkl",
        )

        try:
            if os.path.exists(model_path):
                with open(model_path, "rb") as model_file:
                    bundle = pickle.load(model_file)
            else:
                from data.train_screener_model import train_screener_model
                bundle = train_screener_model(model_path)

            if not isinstance(bundle, dict):
                raise ValueError("Model bundle must be a dictionary")

            clf_pipeline = bundle.get("clf_pipeline")
            reg_pipeline = bundle.get("reg_pipeline")
            if clf_pipeline is None or reg_pipeline is None:
                raise ValueError("Model bundle is missing a classifier or regressor")

            self.clf_pipeline = clf_pipeline
            self.reg_pipeline = reg_pipeline
            self.ml_trained = True

        except Exception as exc:
            # Includes blocked DLL/import errors from Windows Application Control.
            self.clf_pipeline = None
            self.reg_pipeline = None
            self.ml_trained = False
            print(
                "[ScreenerAgent Warning] ML unavailable; using heuristic fallback. "
                f"Details: {exc}"
            )

    def step(self) -> None:
        """
        Autonomous Screener Agent Turn:
        1. Reads latest telemetry generated by patient or human player.
        2. Evaluates features through scikit-learn ML pipeline.
        3. Updates predicted MMSE, CSI, and clinical risk flags.
        4. Publishes assessment to self.model.latest_assessment.
        """
        telemetry = getattr(self.model, "latest_telemetry", None)
        if not telemetry and hasattr(self.model, "patient"):
            telemetry = getattr(self.model.patient, "last_round_telemetry", None)

        if telemetry:
            age = getattr(self.model, "patient_age", 75)
            educ = getattr(self.model, "patient_educ", 3)
            self.latest_assessment = self.evaluate_telemetry(telemetry, patient_age=age, patient_educ=educ)
            if hasattr(self.model, "latest_assessment"):
                self.model.latest_assessment = self.latest_assessment

    def evaluate_telemetry(
        self,
        telemetry: Dict[str, Any],
        patient_age: int = 75,
        patient_educ: int = 3,
    ) -> Dict[str, Any]:
        """Assess telemetry with ML when usable, otherwise use the heuristic."""
        if telemetry.get("status") == "dropped_out" or telemetry.get("Dropped_Out", False):
            self.clinical_flag = "Assessment Incomplete (High Fatigue/Dropout)"
            return {
                "Clinical_Flag": self.clinical_flag,
                "Predicted_MMSE": self.predicted_mmse,
                "Assessment_Method": "incomplete",
                "ML_Available": self.ml_trained,
            }

        rt_ms = float(telemetry.get("Mean_Reaction_Time_ms", 1200.0))
        error_rate = float(telemetry.get("Error_Rate", 0.0))
        hesitations = float(telemetry.get("Hesitation_Intervals_Count", 0))
        total_flips = max(1, int(telemetry.get("Total_Flips", 12)))
        redundant_errors = float(
            telemetry.get(
                "Redundant_Errors",
                int(error_rate * max(1, total_flips // 2)),
            )
        )

        used_ml = False
        if (
            self.ml_trained
            and self.clf_pipeline is not None
            and self.reg_pipeline is not None
        ):
            try:
                features = np.array([[
                    rt_ms,
                    redundant_errors,
                    hesitations,
                    error_rate,
                    float(patient_age),
                    float(patient_educ),
                ]])
                probabilities = self.clf_pipeline.predict_proba(features)[0]
                prob_impaired = float(
                    probabilities[1] if len(probabilities) > 1 else probabilities[0]
                )
                raw_mmse = float(self.reg_pipeline.predict(features)[0])

                self.predicted_mmse = round(float(np.clip(raw_mmse, 10.0, 30.0)), 1)
                self.cognitive_state_index = round(
                    float(np.clip(100.0 * (1.0 - prob_impaired), 5.0, 100.0)), 1
                )
                self.confidence_score = round(
                    max(prob_impaired, 1.0 - prob_impaired), 3
                )

                if prob_impaired < 0.35 or self.predicted_mmse >= 27.0:
                    self.clinical_flag = "Normal Cognition"
                elif prob_impaired < 0.70 or self.predicted_mmse >= 21.0:
                    self.clinical_flag = "Mild Cognitive Impairment (MCI) Alert"
                else:
                    self.clinical_flag = (
                        "Significant Cognitive Decline / Dementia Alert"
                    )
                used_ml = True

            except Exception as exc:
                # Prediction can also fail if a compiled dependency is blocked.
                self.clf_pipeline = None
                self.reg_pipeline = None
                self.ml_trained = False
                print(
                    "[ScreenerAgent Warning] ML inference failed; "
                    f"using heuristic fallback. Details: {exc}"
                )

        if not used_ml:
            hesitation_ratio = hesitations / total_flips
            age_correction = (patient_age - 65) * 0.05
            educ_bonus = (patient_educ - 3) * 0.6

            rt_penalty = max(0.0, (rt_ms - 1100.0) / 75.0)
            error_penalty = error_rate * 45.0
            hesitation_penalty = hesitation_ratio * 30.0

            csi = (
                100.0
                - rt_penalty
                - error_penalty
                - hesitation_penalty
                - age_correction
                + educ_bonus
            )
            self.cognitive_state_index = float(np.clip(csi, 10.0, 100.0))
            raw_mmse = 11.0 + (self.cognitive_state_index / 100.0) * 19.0
            self.predicted_mmse = round(
                float(np.clip(raw_mmse, 10.0, 30.0)), 1
            )

            if self.predicted_mmse >= 27.0:
                self.clinical_flag = "Normal Cognition"
                self.confidence_score = 0.92
            elif self.predicted_mmse >= 21.0:
                self.clinical_flag = "Mild Cognitive Impairment (MCI) Alert"
                self.confidence_score = 0.88
            else:
                self.clinical_flag = (
                    "Significant Cognitive Decline / Dementia Alert"
                )
                self.confidence_score = 0.94

        assessment_record = {
            "Round": len(self.session_history) + 1,
            "CSI": round(self.cognitive_state_index, 2),
            "Predicted_MMSE": self.predicted_mmse,
            "Clinical_Flag": self.clinical_flag,
            "Confidence": self.confidence_score,
            "Mean_RT_ms": rt_ms,
            "Error_Rate": error_rate,
            "Assessment_Method": "machine_learning" if used_ml else "heuristic_fallback",
            "ML_Available": self.ml_trained,
        }
        self.session_history.append(assessment_record)
        return assessment_record


class AdaptiveDifficultyAgent(mesa.Agent):
    """
    Dynamic Difficulty Adjustment (DDA) Agent (Praveen Asaithambi - BL.SC.U4AIE25035)
    Faculty Remark: "Single agent to decide difficulty level based on performance - suggesting elder people or adolescent".

    Implements:
    - Real-time DDA (Eun et al., 2022)
    - Multimodal parameter scaling: Grid Size, Card Exposure Duration, Pacing Delays (Goumopoulos et al., 2023)
    - Fatigue & Anxiety mitigation to avert assessment dropout (Mezrar & Bendella, 2022)
    """

    GRID_LEVELS = ["3x4", "4x4", "4x5"]  # 6 pairs, 8 pairs, 10 pairs
    EXPOSURE_LEVELS = [2.0, 1.5, 1.0]     # Card preview seconds (Elder vs Adolescent)

    def __init__(
        self,
        model: mesa.Model,
        unique_id: Optional[int] = None,
        target_profile: str = "Elderly"  # "Elderly" or "Adolescent"
    ):
        uid = unique_id if unique_id is not None else 3
        try:
            super().__init__(model)
        except TypeError:
            super().__init__(uid, model)

        self.unique_id = uid
        self.pos: Optional[Tuple[int, int]] = None
        self.target_profile = target_profile
        self.current_grid_idx: int = 0         # Starts at 3x4 (safe baseline)
        self.current_exposure_idx: int = 0     # Starts at 2.0s preview
        self.difficulty_name: str = "Gentle / Baseline"

        self.recent_performance: List[float] = []
        self.last_adjustment_reason: str = "Initial Baseline Established"
        self.needs_micro_break: bool = False
        self.latest_dda_action: Dict[str, Any] = {
            "adapted": False,
            "grid_size": "3x4",
            "exposure_time_sec": 2.0,
            "difficulty_name": "Gentle / Baseline",
            "reason": "Initial Baseline Established",
            "micro_break_recommended": False
        }

    def step(self) -> None:
        """
        Autonomous Adaptive Difficulty Agent Turn:
        1. Ingests latest telemetry and screener clinical assessment.
        2. Evaluates cognitive performance index P_t and moving average.
        3. Dynamically adjusts grid complexity and card exposure durations.
        4. Transmits adaptive restorative feedback to PatientAgent.
        5. Publishes decision to self.model.latest_dda_action.
        """
        telemetry = getattr(self.model, "latest_telemetry", None)
        if not telemetry and hasattr(self.model, "patient"):
            telemetry = getattr(self.model.patient, "last_round_telemetry", None)

        assessment = getattr(self.model, "latest_assessment", None)
        if not assessment and hasattr(self.model, "screener"):
            assessment = getattr(self.model.screener, "latest_assessment", {})

        if telemetry:
            if getattr(self.model, "enable_adaptive_dda", True):
                self.latest_dda_action = self.evaluate_and_adapt(telemetry, assessment or {})
                if hasattr(self.model, "patient"):
                    self.model.patient.apply_adaptive_feedback(
                        difficulty_adapted=self.latest_dda_action["adapted"],
                        break_given=self.latest_dda_action.get("micro_break_recommended", False)
                    )
            else:
                self.latest_dda_action = {
                    "adapted": False,
                    "grid_size": "4x4",
                    "exposure_time_sec": 1.5,
                    "difficulty_name": "Static 4x4",
                    "reason": "Static Difficulty (Ablation Benchmark)",
                    "micro_break_recommended": False
                }

            if hasattr(self.model, "latest_dda_action"):
                self.model.latest_dda_action = self.latest_dda_action

    def evaluate_and_adapt(
        self,
        telemetry: Dict[str, Any],
        clinical_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Core DDA Decision Function (Eun et al., 2022; Goumopoulos et al., 2023).
        Calculates performance score P_t and determines whether to:
        1. Downgrade difficulty & grant restorative break (Fatigue/Errors)
        2. Upgrade difficulty (Mastery / Low latency)
        3. Maintain stable baseline
        """
        if telemetry.get("status") == "dropped_out" or telemetry.get("Dropped_Out", False):
            return {"action": "no_change", "grid_size": self.get_current_grid(), "reason": "Patient dropped out"}

        error_rate = telemetry.get("Error_Rate", 0.0)
        rt_ms = telemetry.get("Mean_Reaction_Time_ms", 2000.0)
        hesitations = telemetry.get("Hesitation_Intervals_Count", 0)
        fatigue = telemetry.get("Patient_Fatigue", 0.0)
        anxiety = telemetry.get("Patient_Anxiety", 0.0)

        # Baseline reaction time expectations
        baseline_rt = 1400.0 if self.target_profile == "Elderly" else 850.0

        # Performance metric P_t in [0.0, 1.0]
        accuracy_score = 1.0 - error_rate
        speed_score = float(np.clip(baseline_rt / max(1.0, rt_ms), 0.2, 1.5))
        p_t = (0.50 * accuracy_score) + (0.35 * speed_score) - (0.15 * (hesitations / max(1, telemetry.get("Total_Flips", 12))))
        self.recent_performance.append(p_t)
        if len(self.recent_performance) > 5:
            self.recent_performance.pop(0)

        moving_avg_p = float(np.mean(self.recent_performance))
        adapted = False
        self.needs_micro_break = False

        # Faculty Requirement Logic: Elder vs Adolescent Tuning Profile
        error_threshold_downgrade = 0.35 if self.target_profile == "Elderly" else 0.45
        fatigue_threshold = 0.60 if self.target_profile == "Elderly" else 0.80

        # 1. DOWNGRADE CRITERIA (Eun et al., 2022; Mezrar & Bendella, 2022)
        if error_rate >= error_threshold_downgrade or (rt_ms > baseline_rt * 1.5) or (fatigue > fatigue_threshold) or (anxiety > 0.65):
            if self.current_grid_idx > 0:
                self.current_grid_idx -= 1
                adapted = True
                self.last_adjustment_reason = f"Downgraded to {self.GRID_LEVELS[self.current_grid_idx]} due to error rate ({error_rate:.1%}) & latency slowing"
            elif self.current_exposure_idx > 0:
                self.current_exposure_idx -= 1
                adapted = True
                self.last_adjustment_reason = f"Increased exposure preview to {self.EXPOSURE_LEVELS[self.current_exposure_idx]}s to relieve cognitive overload"
            else:
                self.last_adjustment_reason = "Maintained minimum floor (3x4, 2.0s) and triggered calming pacing break"

            # Offer micro-break if fatigue is severe
            if fatigue > fatigue_threshold or anxiety > 0.60:
                self.needs_micro_break = True

        # 2. UPGRADE CRITERIA (Accuracy > 85%, stable speed, low anxiety)
        elif moving_avg_p >= 0.85 and error_rate <= 0.15 and anxiety < 0.30:
            if self.current_grid_idx < len(self.GRID_LEVELS) - 1:
                self.current_grid_idx += 1
                adapted = True
                self.last_adjustment_reason = f"Upgraded to {self.GRID_LEVELS[self.current_grid_idx]} due to high accuracy ({accuracy_score:.1%})"
            elif self.current_exposure_idx < len(self.EXPOSURE_LEVELS) - 1:
                self.current_exposure_idx += 1
                adapted = True
                self.last_adjustment_reason = f"Reduced exposure preview to {self.EXPOSURE_LEVELS[self.current_exposure_idx]}s to test memory retention"
            else:
                self.last_adjustment_reason = "Patient operating smoothly at maximum difficulty ceiling"

        else:
            self.last_adjustment_reason = "Performance stable within optimal challenge window"

        # Update difficulty label
        grid = self.GRID_LEVELS[self.current_grid_idx]
        if grid == "3x4":
            self.difficulty_name = "Gentle / 6 Pairs"
        elif grid == "4x4":
            self.difficulty_name = "Moderate / 8 Pairs"
        else:
            self.difficulty_name = "Challenging / 10 Pairs"

        return {
            "adapted": adapted,
            "grid_size": self.get_current_grid(),
            "exposure_time_sec": self.get_current_exposure(),
            "difficulty_name": self.difficulty_name,
            "reason": self.last_adjustment_reason,
            "performance_index": round(p_t, 3),
            "moving_avg_p": round(moving_avg_p, 3),
            "micro_break_recommended": self.needs_micro_break
        }

    def get_current_grid(self) -> str:
        return self.GRID_LEVELS[self.current_grid_idx]

    def get_current_exposure(self) -> float:
        return self.EXPOSURE_LEVELS[self.current_exposure_idx]
