import os
import pickle
import threading
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
        pair_id: int = -1,
        symbol: str = ""
    ):
        super().__init__(model)
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
        cdr_level: float = 0.0,
        age: int = 75,
        educ: int = 3,
        calibrated_params: Optional[Dict[str, float]] = None
    ):
        super().__init__(model)
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

    def __init__(self, model: mesa.Model):
        super().__init__(model)
        self.pos: Optional[Tuple[int, int]] = None
        self.session_history: List[Dict[str, Any]] = []
        self.predicted_mmse: float = 30.0
        self.cognitive_state_index: float = 100.0
        self.clinical_flag: str = "Normal Cognition"
        self.confidence_score: float = 0.95
        self.latest_assessment: Dict[str, Any] = {}
        self.task_history: Dict[str, List[Dict[str, Any]]] = {}
        self.latest_decision: Dict[str, Any] = {
            "agent": "ScreenerAgent",
            "decision": "waiting_for_first_round",
            "explanation": "The screener is waiting for valid task telemetry.",
            "metrics_used": [],
        }

        # Machine Learning Pipelines
        self.clf_pipeline = None
        self.reg_pipeline = None
        self.ml_trained: bool = False
        self._ml_model_loaded = threading.Event()
        self._ml_model_load_thread = threading.Thread(
            target=self._load_ml_model,
            name=f"ScreenerAgent-{self.unique_id}-ml-loader",
            daemon=True,
        )
        self._ml_model_load_thread.start()

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
        finally:
            self._ml_model_loaded.set()

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
        """Assess a legacy Pairs round or a task-aware Electron round."""
        if telemetry.get("game") in self.TASK_DOMAINS:
            return self.evaluate_task_telemetry(
                telemetry, patient_age=patient_age, patient_educ=patient_educ
            )

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

    TASK_DOMAINS = {
        "pairs": "Associative visual memory",
        "color_pattern": "Visual sequence memory",
        "normal_pattern": "Spatial sequence memory",
        "stroop": "Selective attention and inhibition",
        "reflex_simple": "Simple response speed and consistency",
        "reflex_choice": "Choice response and stimulus discrimination",
        "reflex_gonogo": "Response inhibition and sustained attention",
        "delayed_recall": "Immediate and delayed episodic recall",
    }

    TASK_BASELINE_RT_MS = {
        "pairs": 1800.0,
        "color_pattern": 1400.0,
        "normal_pattern": 1600.0,
        "stroop": 1000.0,
        "reflex_simple": 350.0,
        "reflex_choice": 650.0,
        "reflex_gonogo": 500.0,
        "delayed_recall": 2500.0,
    }

    @staticmethod
    def _bounded_number(value: Any, minimum: float, maximum: float, default: float) -> float:
        """Convert untrusted gameplay input to a finite number in a safe range."""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        if not np.isfinite(number):
            return default
        return float(np.clip(number, minimum, maximum))

    def evaluate_task_telemetry(
        self,
        telemetry: Dict[str, Any],
        patient_age: int = 75,
        patient_educ: int = 3,
    ) -> Dict[str, Any]:
        """Produce task-specific, inspectable gameplay metrics (never a diagnosis)."""
        game = str(telemetry.get("game", "pairs"))
        if game not in self.TASK_DOMAINS:
            raise ValueError(f"Unsupported task: {game}")
        domain = self.TASK_DOMAINS[game]
        trials = telemetry.get("trials", [])
        if not isinstance(trials, list):
            trials = []
        trial_count = int(self._bounded_number(
            telemetry.get("trial_count", len(trials) or telemetry.get("attempts", 1)),
            1, 10000, 1
        ))
        attempts = max(1, int(self._bounded_number(
            telemetry.get("attempts", trial_count), 1, 100000, trial_count
        )))
        correct = int(self._bounded_number(telemetry.get("correct_attempts", 0), 0, 100000, 0))
        incorrect = int(self._bounded_number(telemetry.get("incorrect_attempts", 0), 0, 100000, 0))
        if "correct_attempts" not in telemetry and "incorrect_attempts" not in telemetry:
            supplied_accuracy = telemetry.get("accuracy")
            accuracy = self._bounded_number(supplied_accuracy, 0.0, 1.0, 0.0) if supplied_accuracy is not None else 0.0
        else:
            accuracy = correct / max(1, correct + incorrect)
        accuracy = float(np.clip(accuracy, 0.0, 1.0))

        # Prefer robust median latency for response-time tasks; retain mean too for historical reports.
        rt_ms = self._bounded_number(
            telemetry.get("median_reaction_time_ms", telemetry.get("mean_reaction_time_ms", telemetry.get("Mean_Reaction_Time_ms", 0.0))),
            0.0, 60000.0, 0.0
        )
        mean_rt_ms = self._bounded_number(
            telemetry.get("mean_reaction_time_ms", telemetry.get("Mean_Reaction_Time_ms", rt_ms)),
            0.0, 60000.0, rt_ms
        )
        rt_variability = self._bounded_number(telemetry.get("reaction_time_variability_ms", 0.0), 0.0, 60000.0, 0.0)
        hesitation_count = int(self._bounded_number(telemetry.get("hesitation_count", telemetry.get("Hesitation_Intervals_Count", 0)), 0, 100000, 0))
        sequence_length = int(self._bounded_number(telemetry.get("sequence_length", 0), 0, 100, 0))
        matches_found = int(self._bounded_number(telemetry.get("matches_found", telemetry.get("Matches_Found", 0)), 0, 1000, 0))
        total_pairs = int(self._bounded_number(telemetry.get("total_pairs", telemetry.get("Total_Pairs", 0)), 0, 1000, 0))
        word_reading_errors = int(self._bounded_number(telemetry.get("word_reading_errors", 0), 0, attempts, 0))
        difficulty_level = int(self._bounded_number(telemetry.get("difficulty_level", 1), 1, 3, 1))

        baseline_rt = self.TASK_BASELINE_RT_MS[game]
        # Speed is capped to avoid rewarding ultra-fast guessing.
        speed_score = float(np.clip(1.0 - max(0.0, rt_ms - baseline_rt) / (2.0 * baseline_rt), 0.0, 1.0))
        hesitation_penalty = min(0.12, (hesitation_count / max(1, attempts)) * 0.08)
        component_weights: Dict[str, float]
        component_scores: Dict[str, float]

        if game == "delayed_recall":
            immediate_total = max(1, int(self._bounded_number(telemetry.get("immediate_total", 8), 1, 50, 8)))
            delayed_total = max(1, int(self._bounded_number(telemetry.get("delayed_total", immediate_total), 1, 50, immediate_total)))
            immediate_count = int(self._bounded_number(telemetry.get("immediate_recall_count", 0), 0, immediate_total, 0))
            delayed_count = int(self._bounded_number(telemetry.get("delayed_recall_count", 0), 0, delayed_total, 0))
            hits = int(self._bounded_number(telemetry.get("recognition_hits", 0), 0, 100, 0))
            misses = int(self._bounded_number(telemetry.get("recognition_misses", 0), 0, 100, 0))
            false_alarms = int(self._bounded_number(telemetry.get("recognition_false_alarms", 0), 0, 100, 0))
            correct_rejections = int(self._bounded_number(telemetry.get("recognition_correct_rejections", 0), 0, 100, 0))
            immediate_accuracy = immediate_count / immediate_total
            delayed_accuracy = delayed_count / delayed_total
            recognition_accuracy = (hits + correct_rejections) / max(1, hits + misses + false_alarms + correct_rejections)
            false_alarm_rate = false_alarms / max(1, false_alarms + correct_rejections)
            retention = delayed_count / max(1, immediate_count)
            performance = float(np.clip(0.20 * immediate_accuracy + 0.50 * delayed_accuracy + 0.30 * recognition_accuracy - 0.15 * false_alarm_rate, 0.0, 1.0))
            component_weights = {"immediate_recall": 0.20, "delayed_recall": 0.50, "recognition": 0.30, "false_recognition_penalty": -0.15}
            component_scores = {"immediate_recall_percent": round(immediate_accuracy * 100, 1), "delayed_recall_percent": round(delayed_accuracy * 100, 1), "recognition_accuracy_percent": round(recognition_accuracy * 100, 1), "false_alarm_rate_percent": round(false_alarm_rate * 100, 1)}
            metrics_used = ["immediate_recall_count", "delayed_recall_count", "recognition_hits", "recognition_misses", "recognition_false_alarms", "recognition_correct_rejections", "retention_ratio"]
            task_metrics = {
                "Immediate_Recall_Count": immediate_count,
                "Immediate_Recall_Total": immediate_total,
                "Immediate_Recall_Percent": round(immediate_accuracy * 100, 1),
                "Delayed_Recall_Count": delayed_count,
                "Delayed_Recall_Total": delayed_total,
                "Delayed_Recall_Percent": round(delayed_accuracy * 100, 1),
                "Recognition_Hits": hits,
                "Recognition_Misses": misses,
                "Recognition_False_Alarms": false_alarms,
                "Recognition_Correct_Rejections": correct_rejections,
                "Recognition_Accuracy_Percent": round(recognition_accuracy * 100, 1),
                "Retention_Ratio": round(retention, 3),
                "False_Alarm_Rate_Percent": round(false_alarm_rate * 100, 1),
            }
        elif game.startswith("reflex_"):
            false_starts = int(self._bounded_number(telemetry.get("false_starts", 0), 0, 100000, 0))
            omission_errors = int(self._bounded_number(telemetry.get("omission_errors", 0), 0, 100000, 0))
            commission_errors = int(self._bounded_number(telemetry.get("commission_errors", 0), 0, 100000, 0))
            valid_trial_count = max(0, int(self._bounded_number(telemetry.get("valid_trial_count", trial_count), 0, 10000, trial_count)))
            consistency_score = float(np.clip(1.0 - rt_variability / max(baseline_rt, 1.0), 0.0, 1.0))
            if game == "reflex_gonogo":
                performance = float(np.clip(0.55 * accuracy + 0.25 * speed_score + 0.20 * consistency_score - min(0.25, commission_errors / valid_trial_count * 0.35) - min(0.15, false_starts / max(1, attempts) * 0.10), 0.0, 1.0))
                component_weights = {"accuracy": 0.55, "speed": 0.25, "consistency": 0.20, "commission_error_penalty": -0.35}
            elif game == "reflex_choice":
                performance = float(np.clip(0.60 * accuracy + 0.25 * speed_score + 0.15 * consistency_score - min(0.15, false_starts / max(1, attempts) * 0.10), 0.0, 1.0))
                component_weights = {"accuracy": 0.60, "speed": 0.25, "consistency": 0.15}
            else:
                performance = float(np.clip(0.65 * accuracy + 0.20 * speed_score + 0.15 * consistency_score - min(0.15, false_starts / max(1, attempts) * 0.10), 0.0, 1.0))
                component_weights = {"accuracy": 0.65, "speed": 0.20, "consistency": 0.15}
            component_scores = {"accuracy_percent": round(accuracy * 100, 1), "median_rt_ms": round(rt_ms, 1), "rt_variability_ms": round(rt_variability, 1), "false_starts": false_starts, "omission_errors": omission_errors, "commission_errors": commission_errors}
            metrics_used = ["trial_level_reaction_times", "median_reaction_time_ms", "reaction_time_variability_ms", "accuracy", "false_starts", "omission_errors", "commission_errors"]
            task_metrics = {"False_Starts": false_starts, "Omission_Errors": omission_errors, "Commission_Errors": commission_errors, "Valid_Trial_Count": valid_trial_count, "RT_Variability_ms": round(rt_variability, 1)}
        elif game == "stroop":
            inhibition_accuracy = float(np.clip(1.0 - word_reading_errors / max(1, attempts), 0.0, 1.0))
            performance = float(np.clip(0.65 * accuracy + 0.25 * speed_score + 0.10 * inhibition_accuracy - hesitation_penalty, 0.0, 1.0))
            component_weights = {"accuracy": 0.65, "speed": 0.25, "inhibition_accuracy": 0.10, "hesitation_penalty": -1.0}
            component_scores = {"accuracy_percent": round(accuracy * 100, 1), "speed_score_percent": round(speed_score * 100, 1), "inhibition_accuracy_percent": round(inhibition_accuracy * 100, 1), "word_reading_errors": word_reading_errors}
            metrics_used = ["correct_attempts", "incorrect_attempts", "reaction_time_ms", "word_reading_errors", "hesitation_count"]
            task_metrics = {"Word_Reading_Errors": word_reading_errors, "Inhibition_Accuracy_Percent": round(inhibition_accuracy * 100, 1)}
        else:
            performance = float(np.clip(0.75 * accuracy + 0.25 * speed_score - hesitation_penalty, 0.0, 1.0))
            component_weights = {"accuracy": 0.75, "speed": 0.25, "hesitation_penalty": -1.0}
            component_scores = {"accuracy_percent": round(accuracy * 100, 1), "speed_score_percent": round(speed_score * 100, 1), "hesitation_penalty_percent": round(hesitation_penalty * 100, 1)}
            metrics_used = ["correct_attempts", "incorrect_attempts", "reaction_time_ms", "hesitation_count"]
            task_metrics = {
                "Sequence_Length": sequence_length if sequence_length else None,
                "Matches_Found": matches_found if game == "pairs" else None,
                "Total_Pairs": total_pairs if game == "pairs" else None,
            }

        score = round(performance * 100.0, 1)
        accuracy_percent = round(accuracy * 100.0, 1)
        prior = self.task_history.setdefault(game, [])
        # Compare like with like: performance at different task difficulties is not
        # a clean estimate of practice-related improvement.
        same_level_scores = [
            float(item.get("raw_score", 0.0)) for item in prior
            if int(item.get("difficulty_level", difficulty_level)) == difficulty_level
        ]
        practice_gain = max(0.0, same_level_scores[-1] - same_level_scores[0]) if len(same_level_scores) >= 2 else 0.0
        practice_adjustment = min(15.0, practice_gain * 0.5) if len(same_level_scores) >= 2 else 0.0
        practice_adjusted_score = round(max(0.0, score - practice_adjustment), 1)

        if game.startswith("reflex_"):
            evidence_n = max(1, int(self._bounded_number(
                telemetry.get("valid_trial_count", trial_count), 0, 10000, trial_count
            )))
        elif game == "delayed_recall":
            # Count item decisions across immediate recall, delayed recall and recognition.
            evidence_n = (
                int(self._bounded_number(telemetry.get("immediate_total", 0), 0, 100, 0))
                + int(self._bounded_number(telemetry.get("delayed_total", 0), 0, 100, 0))
                + int(self._bounded_number(telemetry.get("recognition_hits", 0), 0, 100, 0))
                + int(self._bounded_number(telemetry.get("recognition_misses", 0), 0, 100, 0))
                + int(self._bounded_number(telemetry.get("recognition_false_alarms", 0), 0, 100, 0))
                + int(self._bounded_number(telemetry.get("recognition_correct_rejections", 0), 0, 100, 0))
            )
            evidence_n = max(1, evidence_n)
        else:
            evidence_n = max(1, trial_count or sequence_length or attempts)

        # Wilson-style interval avoids the misleading zero uncertainty produced by
        # a tiny sample with either 0% or 100% accuracy. This remains exploratory.
        z = 1.96
        denominator = 1.0 + (z * z / evidence_n)
        uncertainty_95 = min(100.0, (
            z * np.sqrt(max(0.0, accuracy * (1.0 - accuracy) / evidence_n)
                        + (z * z / (4.0 * evidence_n * evidence_n)))
            / denominator
        ) * 100.0)
        evidence_confidence = float(np.clip(evidence_n / (evidence_n + 6.0), 0.0, 1.0))
        quality_flags = []
        if evidence_n < 6:
            quality_flags.append("Small sample: interpret this round cautiously")
        if rt_ms <= 0:
            quality_flags.append("No valid response-time sample was supplied")
        if len(prior) < 2:
            quality_flags.append("Early familiarization: practice effects may be present")
        if game.startswith("reflex_") and int(task_metrics.get("Valid_Trial_Count", 0)) == 0:
            quality_flags.append("No valid response trials were completed; do not interpret this round")
        if game == "delayed_recall" and telemetry.get("immediate_recall_count") is None:
            quality_flags.append("Immediate recall data are incomplete")

        explanation = f"{domain}: score {score:.1f}/100 from task-specific gameplay metrics. "
        if game == "delayed_recall":
            explanation += f"Immediate recall {task_metrics['Immediate_Recall_Percent']:.1f}%, delayed recall {task_metrics['Delayed_Recall_Percent']:.1f}%, recognition {task_metrics['Recognition_Accuracy_Percent']:.1f}%; retention ratio {task_metrics['Retention_Ratio']:.2f}."
        elif game.startswith("reflex_"):
            explanation += f"Median response {rt_ms:.0f} ms, variability {rt_variability:.0f} ms, {task_metrics['False_Starts']} false starts, {task_metrics['Omission_Errors']} omissions and {task_metrics['Commission_Errors']} commission errors."
        else:
            explanation += f"Accuracy {accuracy_percent:.1f}%, median response {rt_ms:.0f} ms, and hesitation count {hesitation_count}."
        if quality_flags:
            explanation += " Evidence note: " + "; ".join(quality_flags) + "."
        assessment_record = {
            "Round": len(self.session_history) + 1,
            "Game": game,
            "Cognitive_Domain": domain,
            "Task_Performance_Score": score,
            "Task_Accuracy_Percent": accuracy_percent,
            "Mean_RT_ms": round(mean_rt_ms, 2),
            "Median_RT_ms": round(rt_ms, 2),
            "Reaction_Time_Variability_ms": round(rt_variability, 2),
            "Hesitation_Count": hesitation_count,
            "Attempt_Count": attempts,
            "Correct_Attempts": correct,
            "Incorrect_Attempts": incorrect,
            "Difficulty_Level": difficulty_level,
            "Sequence_Length": sequence_length if sequence_length else None,
            "Matches_Found": matches_found if game == "pairs" else None,
            "Total_Pairs": total_pairs if game == "pairs" else None,
            "Word_Reading_Errors": word_reading_errors if game == "stroop" else None,
            "Inhibition_Accuracy_Percent": task_metrics.get("Inhibition_Accuracy_Percent"),
            **task_metrics,
            "Score_Components": component_scores,
            "Component_Weights": component_weights,
            "Metrics_Used": metrics_used,
            "Decision_Explanation": explanation,
            "Practice_Exposure_Count": len(prior) + 1,
            "Observed_Practice_Gain_Points": round(practice_gain, 1),
            "Practice_Adjustment_Points": round(practice_adjustment, 1),
            "Practice_Adjusted_Score": practice_adjusted_score,
            "Evidence_Sample_Count": evidence_n,
            "Evidence_Confidence": round(evidence_confidence, 3),
            "Uncertainty_95pct_Points": round(float(uncertainty_95), 1),
            "Data_Quality_Flags": quality_flags,
            "Assessment_Method": "task_specific_heuristic",
            "Clinical_Flag": "Task performance only; not a diagnosis",
            "ML_Used": False,
            "ML_Model_Ready": self.ml_trained,
        }
        prior.append({
            "raw_score": score,
            "adjusted_score": practice_adjusted_score,
            "accuracy": accuracy,
            "median_rt_ms": rt_ms,
            "difficulty_level": difficulty_level,
        })
        self.session_history.append(assessment_record)
        self.latest_assessment = assessment_record
        self.latest_decision = {
            "agent": "ScreenerAgent",
            "decision": "score_task_performance",
            "explanation": explanation,
            "metrics_used": metrics_used,
            "score_components": component_scores,
            "evidence_confidence": round(evidence_confidence, 3),
            "uncertainty_95pct_points": round(float(uncertainty_95), 1),
            "data_quality_flags": quality_flags,
            "practice_exposure_count": len(prior),
        }
        # These are gameplay measures only; never convert this task rubric to a diagnostic probability.
        self.confidence_score = 0.0
        return assessment_record


class MemoryAnalysisAgent(mesa.Agent):
    """Summarizes memory-task evidence without assigning a clinical label."""

    MEMORY_TASKS = {"pairs", "color_pattern", "normal_pattern", "delayed_recall"}

    def __init__(self, model: mesa.Model):
        super().__init__(model)
        self.latest_analysis: Dict[str, Any] = {
            "agent": "MemoryAnalysisAgent", "status": "waiting",
            "decision": "await_memory_task", "metrics_used": [],
            "explanation": "No memory task has been scored yet.",
        }
        self.history: List[Dict[str, Any]] = []

    def step(self) -> None:
        telemetry = getattr(self.model, "latest_telemetry", {}) or {}
        game = telemetry.get("game")
        if game not in self.MEMORY_TASKS:
            self.latest_analysis = {
                "agent": "MemoryAnalysisAgent",
                "status": "idle_for_task",
                "decision": "no_action_not_applicable",
                "metrics_used": [],
                "round": self.model.current_round,
                "game": game,
                "explanation": f"No memory analysis for {game or 'this task'}; it is outside this agent's task domain.",
                "metrics": {},
            }
            return
        assessment = getattr(self.model, "latest_assessment", {}) or {}
        if game == "delayed_recall":
            immediate = int(assessment.get("Immediate_Recall_Count", 0))
            delayed = int(assessment.get("Delayed_Recall_Count", 0))
            immediate_total = max(1, int(assessment.get("Immediate_Recall_Total", 1)))
            delayed_total = max(1, int(assessment.get("Delayed_Recall_Total", immediate_total)))
            retention = float(assessment.get("Retention_Ratio", delayed / max(1, immediate)))
            explanation = (f"Delayed recall profile: {immediate}/{immediate_total} items recalled immediately, "
                           f"{delayed}/{delayed_total} after a distraction interval; retention ratio {retention:.2f}. "
                           "Recognition and false alarms provide a separate retrieval cue measure.")
            metrics = {"immediate_recall": immediate, "delayed_recall": delayed,
                       "retention_ratio": round(retention, 3),
                       "recognition_hits": assessment.get("Recognition_Hits", 0),
                       "false_alarms": assessment.get("Recognition_False_Alarms", 0)}
            metrics_used = ["Immediate_Recall_Count", "Delayed_Recall_Count", "Retention_Ratio", "Recognition_Hits", "Recognition_False_Alarms"]
        else:
            score = float(assessment.get("Task_Performance_Score", 0.0))
            accuracy = float(assessment.get("Task_Accuracy_Percent", 0.0))
            span = assessment.get("Sequence_Length")
            pairs = assessment.get("Matches_Found")
            explanation = f"{self.model.screener.TASK_DOMAINS.get(game, game)} result: score {score:.1f}/100, accuracy {accuracy:.1f}%."
            if span:
                explanation += f" The recalled sequence contained {span} steps."
            if pairs is not None:
                explanation += f" {pairs} matching pairs were found."
            metrics = {"task_score": score, "accuracy_percent": accuracy, "sequence_length": span, "matches_found": pairs}
            metrics_used = ["Task_Performance_Score", "Task_Accuracy_Percent", "Sequence_Length", "Matches_Found"]
        record = {
            "agent": "MemoryAnalysisAgent", "decision": "analyze_memory_task",
            "round": self.model.current_round, "game": game, "metrics": metrics,
            "metrics_used": metrics_used, "explanation": explanation,
        }
        self.latest_analysis = {"status": "updated", **record}
        self.history.append(record)
        self.history = self.history[-30:]


class AttentionAnalysisAgent(mesa.Agent):
    """Tracks selective attention and response-control evidence across relevant tasks."""

    ATTENTION_TASKS = {"stroop", "reflex_simple", "reflex_choice", "reflex_gonogo"}

    def __init__(self, model: mesa.Model):
        super().__init__(model)
        self.latest_analysis: Dict[str, Any] = {
            "agent": "AttentionAnalysisAgent", "status": "waiting",
            "decision": "await_attention_task", "metrics_used": [],
            "explanation": "No attention/response task has been scored yet.",
        }
        self.history: List[Dict[str, Any]] = []

    def step(self) -> None:
        telemetry = getattr(self.model, "latest_telemetry", {}) or {}
        game = telemetry.get("game")
        if game not in self.ATTENTION_TASKS:
            self.latest_analysis = {
                "agent": "AttentionAnalysisAgent",
                "status": "idle_for_task",
                "decision": "no_action_not_applicable",
                "metrics_used": [],
                "round": self.model.current_round,
                "game": game,
                "explanation": f"No attention/response analysis for {game or 'this task'}; it is outside this agent's task domain.",
                "metrics": {},
            }
            return
        assessment = getattr(self.model, "latest_assessment", {}) or {}
        score = float(assessment.get("Task_Performance_Score", 0.0))
        median_rt = float(assessment.get("Median_RT_ms", assessment.get("Mean_RT_ms", 0.0)))
        variability = float(assessment.get("Reaction_Time_Variability_ms", 0.0))
        commission = int(assessment.get("Commission_Errors", 0) or 0)
        omissions = int(assessment.get("Omission_Errors", 0) or 0)
        false_starts = int(assessment.get("False_Starts", 0) or 0)
        word_slips = int(assessment.get("Word_Reading_Errors", 0) or 0)
        explanation = (f"Response/attention profile: score {score:.1f}/100, median response {median_rt:.0f} ms, "
                       f"response-time variability {variability:.0f} ms, false starts {false_starts}, "
                       f"omissions {omissions}, commission errors {commission}, word-based slips {word_slips}. "
                       "These results are task-specific and can be influenced by device, fatigue, vision and practice.")
        record = {"agent": "AttentionAnalysisAgent", "decision": "analyze_attention_response_task",
                  "round": self.model.current_round, "game": game, "score": score,
                  "median_rt_ms": median_rt, "rt_variability_ms": variability,
                  "false_starts": false_starts, "omission_errors": omissions,
                  "commission_errors": commission, "word_reading_errors": word_slips,
                  "metrics_used": ["Task_Performance_Score", "Median_RT_ms", "Reaction_Time_Variability_ms", "False_Starts", "Omission_Errors", "Commission_Errors", "Word_Reading_Errors"],
                  "explanation": explanation}
        self.latest_analysis = {"status": "updated", **record}
        self.history.append(record)
        self.history = self.history[-30:]


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
    EXPOSURE_LEVELS = [2.0, 1.5, 1.0]     # Legacy Pygame board preview seconds
    TASK_SETTINGS = {
        "pairs": [
            {"pairs": 6, "board": "3x4"}, {"pairs": 8, "board": "4x4"}, {"pairs": 10, "board": "4x5"},
        ],
        "color_pattern": [
            {"flash_ms": 760, "gap_ms": 280}, {"flash_ms": 620, "gap_ms": 230}, {"flash_ms": 500, "gap_ms": 180},
        ],
        "normal_pattern": [
            {"flash_ms": 760, "gap_ms": 280, "grid": "3x3"}, {"flash_ms": 620, "gap_ms": 230, "grid": "3x3"}, {"flash_ms": 500, "gap_ms": 180, "grid": "3x3"},
        ],
        "stroop": [
            {"incongruent_rate": 0.55, "response_window_ms": 2500}, {"incongruent_rate": 0.75, "response_window_ms": 2200}, {"incongruent_rate": 0.88, "response_window_ms": 1900},
        ],
        "reflex_simple": [
            {"response_window_ms": 2200, "wait_min_ms": 900, "wait_max_ms": 2200}, {"response_window_ms": 1800, "wait_min_ms": 800, "wait_max_ms": 1900}, {"response_window_ms": 1500, "wait_min_ms": 700, "wait_max_ms": 1600},
        ],
        "reflex_choice": [
            {"response_window_ms": 2600, "choice_count": 2}, {"response_window_ms": 2200, "choice_count": 3}, {"response_window_ms": 1800, "choice_count": 4},
        ],
        "reflex_gonogo": [
            {"response_window_ms": 1100, "no_go_rate": 0.25}, {"response_window_ms": 950, "no_go_rate": 0.33}, {"response_window_ms": 850, "no_go_rate": 0.40},
        ],
        "delayed_recall": [
            {"item_count": 6, "study_seconds": 8, "delay_seconds": 12}, {"item_count": 8, "study_seconds": 7, "delay_seconds": 15}, {"item_count": 10, "study_seconds": 6, "delay_seconds": 18},
        ],
    }

    def __init__(
        self,
        model: mesa.Model,
        target_profile: str = "Elderly"  # "Elderly" or "Adolescent"
    ):
        super().__init__(model)
        self.pos: Optional[Tuple[int, int]] = None
        self.target_profile = target_profile
        self.current_grid_idx: int = 0         # Starts at 3x4 (safe baseline)
        self.current_exposure_idx: int = 0     # Starts at 2.0s preview
        self.difficulty_name: str = "Gentle / Baseline"

        self.recent_performance: List[float] = []
        self.task_levels: Dict[str, int] = {
            "pairs": 1,
            "color_pattern": 1,
            "normal_pattern": 1,
            "stroop": 1,
            "reflex_simple": 1,
            "reflex_choice": 1,
            "reflex_gonogo": 1,
            "delayed_recall": 1,
        }
        self.task_performance_history: Dict[str, List[Dict[str, Any]]] = {
            game: [] for game in self.task_levels
        }
        self.task_decision_history: List[Dict[str, Any]] = []
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
                if telemetry.get("game") in self.task_levels:
                    self.latest_dda_action = self.evaluate_task_and_adapt(
                        telemetry, assessment or {}
                    )
                else:
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

    @staticmethod
    def _decision_attempt_count(telemetry: Dict[str, Any]) -> int:
        try:
            return max(0, int(telemetry.get("attempts", telemetry.get("trial_count", 0)) or 0))
        except (TypeError, ValueError):
            return 0

    def evaluate_task_and_adapt(
        self,
        telemetry: Dict[str, Any],
        assessment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Task-specific closed-loop adaptation with evidence and practice safeguards."""
        game = str(telemetry.get("game", "pairs"))
        if game not in self.task_levels:
            return self.latest_dda_action

        current_level = self.task_levels[game]
        old_settings = dict(self.TASK_SETTINGS[game][current_level - 1])
        raw_accuracy = ScreenerAgent._bounded_number(
            assessment.get("Task_Accuracy_Percent", 100.0 * ScreenerAgent._bounded_number(telemetry.get("accuracy", 0.0), 0.0, 1.0, 0.0)),
            0.0, 100.0, 0.0
        ) / 100.0
        raw_error_rate = ScreenerAgent._bounded_number(
            telemetry.get("error_rate", telemetry.get("Error_Rate", 1.0 - raw_accuracy)), 0.0, 1.0, 1.0 - raw_accuracy
        )
        rt_ms = ScreenerAgent._bounded_number(
            assessment.get("Median_RT_ms", telemetry.get("median_reaction_time_ms", telemetry.get("mean_reaction_time_ms", 0.0))),
            0.0, 60000.0, 0.0
        )
        baseline_rt = ScreenerAgent.TASK_BASELINE_RT_MS.get(game, 1500.0)
        rt_variability = ScreenerAgent._bounded_number(assessment.get("Reaction_Time_Variability_ms", telemetry.get("reaction_time_variability_ms", 0.0)), 0.0, 60000.0, 0.0)
        practice_adjusted = ScreenerAgent._bounded_number(
            assessment.get("Practice_Adjusted_Score", assessment.get("Task_Performance_Score", raw_accuracy * 100.0)),
            0.0, 100.0, raw_accuracy * 100.0
        ) / 100.0
        confidence = ScreenerAgent._bounded_number(assessment.get("Evidence_Confidence", 0.0), 0.0, 1.0, 0.0)
        uncertainty = ScreenerAgent._bounded_number(assessment.get("Uncertainty_95pct_Points", 100.0), 0.0, 100.0, 100.0)
        task_score = ScreenerAgent._bounded_number(
            assessment.get("Task_Performance_Score", raw_accuracy * 100.0), 0.0, 100.0, raw_accuracy * 100.0
        ) / 100.0
        domain_metrics: Dict[str, Any] = {}
        domain_reasons: List[str] = []

        # Use the domain agents' current-round output as additional evidence for
        # the adaptive decision. Their metrics remain task signals, not diagnoses.
        memory_state = getattr(getattr(self.model, "memory_agent", None), "latest_analysis", {}) or {}
        if game == "delayed_recall" and memory_state.get("game") == game and memory_state.get("round") == getattr(self.model, "current_round", None):
            retention = ScreenerAgent._bounded_number(memory_state.get("metrics", {}).get("retention_ratio", 1.0), 0.0, 5.0, 1.0)
            domain_metrics["memory_agent_retention_ratio"] = round(retention, 3)
            if retention < 0.45:
                domain_reasons.append("MemoryAnalysisAgent observed lower delayed-than-immediate recall retention")

        attention_state = getattr(getattr(self.model, "attention_agent", None), "latest_analysis", {}) or {}
        if game == "reflex_gonogo" and attention_state.get("game") == game and attention_state.get("round") == getattr(self.model, "current_round", None):
            commission = max(0, int(assessment.get("Commission_Errors", 0) or 0))
            valid = max(1, int(assessment.get("Valid_Trial_Count", 1) or 1))
            commission_rate = commission / valid
            domain_metrics["attention_agent_commission_error_rate"] = round(commission_rate, 3)
            if commission_rate >= 0.25:
                domain_reasons.append("AttentionAnalysisAgent observed repeated responses to NO-GO cues")

        history = self.task_performance_history[game]
        history.append({"accuracy": raw_accuracy, "score": float(assessment.get("Task_Performance_Score", raw_accuracy * 100)), "level": current_level, "confidence": confidence})
        if len(history) > 8:
            history.pop(0)
        moving_accuracy = float(np.mean([record["accuracy"] for record in history]))
        same_level_history = [record for record in history if record["level"] == current_level]
        stable_same_level = len(same_level_history) >= 2

        old_level = current_level
        reasons: List[str] = []
        factors: List[Dict[str, Any]] = [
            {"metric": "accuracy", "value": round(raw_accuracy * 100, 1), "unit": "%"},
            {"metric": "error_rate", "value": round(raw_error_rate * 100, 1), "unit": "%"},
            {"metric": "median_reaction_time", "value": round(rt_ms, 1), "unit": "ms"},
            {"metric": "reaction_time_variability", "value": round(rt_variability, 1), "unit": "ms"},
            {"metric": "evidence_confidence", "value": round(confidence, 3), "unit": "0-1"},
            {"metric": "practice_adjusted_score", "value": round(practice_adjusted * 100, 1), "unit": "/100"},
            {"metric": "task_specific_performance_score", "value": round(task_score * 100, 1), "unit": "/100"},
        ]
        factors.extend(
            {"metric": key, "value": value, "unit": "ratio"}
            for key, value in domain_metrics.items()
        )
        micro_break = False
        poor_performance = (
            raw_error_rate >= 0.40 or raw_accuracy < 0.60 or task_score < 0.60
            or bool(domain_reasons) or (rt_ms > baseline_rt * 2.5 and rt_ms > 0)
        )
        low_evidence = confidence < 0.35 or uncertainty > 35.0
        repeated_poor_performance = len(history) >= 2 and moving_accuracy < 0.50
        enough_errors_to_confirm = self._decision_attempt_count(telemetry) >= 4 and raw_error_rate >= 0.70
        very_slow_response = rt_ms > baseline_rt * 3.5 and rt_ms > 0
        # A one-response sequence round is noisy. Ease on repeated poor evidence,
        # a larger task sample, or an unusually slow response; otherwise collect another sample.
        if poor_performance and low_evidence and not (
            repeated_poor_performance or enough_errors_to_confirm or very_slow_response
        ):
            if current_level > 1:
                reasons.append("A low-confidence round looked difficult, but the sample is too small to change difficulty safely; collecting another result")
            else:
                reasons.append("The round looked difficult, but the sample is too small to infer a repeated problem; keeping the easiest level and collecting another result")
        elif poor_performance:
            if current_level > 1:
                current_level -= 1
                reasons.append("Difficulty decreased because task score, accuracy, errors or latency indicate that the current challenge may be too high")
            else:
                reasons.append("Already at the easiest level; keeping the level and suggesting a short reset")
            micro_break = raw_error_rate >= 0.55 or (rt_ms > baseline_rt * 3.0 and rt_ms > 0)
        # To raise difficulty, require repeated evidence at one level, adequate precision,
        # stable response times, and a practice-adjusted score above the target band.
        elif (len(history) >= 2 and stable_same_level and moving_accuracy >= 0.88
              and raw_error_rate <= 0.15 and (rt_ms <= baseline_rt * 1.35 or rt_ms == 0)
              and (rt_variability <= baseline_rt * 0.75 or rt_variability == 0)
              and practice_adjusted >= 0.85 and confidence >= 0.35 and uncertainty <= 30.0):
            if current_level < 3:
                current_level += 1
                reasons.append("Difficulty increased after repeated accurate performance at the same level with sufficient evidence")
            else:
                reasons.append("Strong performance at the highest available level; difficulty stays capped")
        else:
            if len(history) < 2:
                reasons.append("Gathering another sample before increasing difficulty")
            elif not stable_same_level:
                reasons.append("A level changed recently, so more evidence at the current level is needed")
            elif confidence < 0.35 or uncertainty > 30.0:
                reasons.append("Evidence is still uncertain, so difficulty is held steady until a more precise estimate is available")
            elif rt_variability > baseline_rt * 0.75 and rt_variability > 0:
                reasons.append("Response-time variability is high, so another stable sample is needed before increasing difficulty")
            elif practice_adjusted < 0.85 and raw_accuracy >= 0.85:
                reasons.append("Possible practice-related improvement is discounted for the upgrade decision")
            else:
                reasons.append("Metrics remain inside the current challenge band")

        self.task_levels[game] = current_level
        new_settings = dict(self.TASK_SETTINGS[game][current_level - 1])
        if game == "pairs":
            grid = new_settings["board"]
            exposure = self.EXPOSURE_LEVELS[current_level - 1]
        elif game == "normal_pattern":
            grid = "3x3"
            exposure = new_settings["flash_ms"] / 1000.0
        elif game == "color_pattern":
            grid = "2x4"
            exposure = new_settings["flash_ms"] / 1000.0
        else:
            # Keep the legacy spatial visualization on a valid rectangular grid;
            # new task complexity is represented by task_parameters, not a fake grid shape.
            grid = "3x4"
            exposure = float(new_settings.get("study_seconds", new_settings.get("response_window_ms", 0) / 1000.0))
        adapted = current_level != old_level
        action = {
            "task": game,
            "agent": "AdaptiveDifficultyAgent",
            "adapted": adapted,
            "current_difficulty_level": old_level,
            "next_difficulty_level": current_level,
            "difficulty_name": ["Gentle", "Steady", "Challenge"][current_level - 1],
            "reason": ". ".join(reasons + domain_reasons) + ".",
            "decision_factors": factors,
            "metrics_used": ["accuracy", "error_rate", "task_specific_performance_score", "median_reaction_time", "reaction_time_variability", "evidence_confidence", "practice_adjusted_score", "same_level_history", *domain_metrics.keys()],
            "domain_agent_metrics": domain_metrics,
            "moving_average_accuracy": round(moving_accuracy, 3),
            "history_rounds": len(history),
            "stable_rounds_at_level": len(same_level_history),
            "evidence_confidence": round(confidence, 3),
            "uncertainty_95pct_points": round(uncertainty, 1),
            "practice_effect_discount_points": round(max(0.0, float(assessment.get("Task_Performance_Score", 0.0)) - float(assessment.get("Practice_Adjusted_Score", assessment.get("Task_Performance_Score", 0.0)))), 1),
            "before_parameters": old_settings,
            "after_parameters": new_settings,
            "task_parameters": new_settings,
            "grid_size": grid,
            "exposure_time_sec": exposure,
            "performance_index": round(float(assessment.get("Task_Performance_Score", raw_accuracy * 100.0)) / 100.0, 3),
            "moving_avg_p": round(moving_accuracy, 3),
            "micro_break_recommended": micro_break,
        }
        self.latest_dda_action = action
        self.task_decision_history.append({
            "round": getattr(self.model, "current_round", 0), "game": game,
            "from_level": old_level, "to_level": current_level,
            "adapted": adapted, "reason": action["reason"],
            "decision_factors": factors, "before_parameters": old_settings,
            "after_parameters": new_settings, "metrics_used": action["metrics_used"],
        })
        self.task_decision_history = self.task_decision_history[-50:]
        return action

    def get_current_grid(self) -> str:
        return self.GRID_LEVELS[self.current_grid_idx]

    def get_current_exposure(self) -> float:
        return self.EXPOSURE_LEVELS[self.current_exposure_idx]
