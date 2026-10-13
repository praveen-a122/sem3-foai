"""
Mesa Cognitive Health Model & Closed-Loop Scheduler
===================================================
Course: 22AIE201 - Fundamentals of AI
Team 3 Deliverable: Member 1 (Praveen Asaithambi - BL.SC.U4AIE25035)

Coordinates the multi-agent cognitive assessment workflow:
  [Patient Action] -> [Screener Assessment] -> [Adaptive Agent DDA] -> [Feedback to Patient]

Supports:
1. Live Interactive Coupling with Pygame Frontend (Real-time telemetry ingestion)
2. Synthetic Longitudinal Simulation (Cohort testing over 30 days)
3. 2D Spatial Environment (mesa.space.SingleGrid) representing board tiles & multi-agent positions
4. Robust TileAgent lifecycle management preventing OccupiedError on dynamic resizing
5. DataCollector integration tracking fatigue, anxiety, error rates, predicted MMSE, and difficulty transitions.
"""

import mesa
from mesa.space import SingleGrid
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from .agents import (PatientAgent, ScreenerAgent, AdaptiveDifficultyAgent, TileAgent, MemoryAnalysisAgent, AttentionAnalysisAgent)


class CognitiveHealthModel(mesa.Model):
    """
    Agent-Based Model coordinating cognitive assessment, digital screening,
    and performance-adaptive difficulty scaling over a 2D spatial SingleGrid.
    """

    def __init__(
        self,
        cdr_level: float = 0.0,
        patient_age: int = 75,
        patient_educ: int = 3,
        target_profile: str = "Elderly",
        calibrated_params: Optional[Dict[str, float]] = None,
        enable_adaptive_dda: bool = True
    ):
        super().__init__()

        self.cdr_level = cdr_level
        self.patient_age = patient_age
        self.patient_educ = patient_educ
        self.target_profile = target_profile
        self.enable_adaptive_dda = enable_adaptive_dda

        # 2D Spatial Environment: mesa.space.SingleGrid (6x6)
        self.grid = SingleGrid(width=6, height=6, torus=False)

        # Instantiate Core Agents
        self.patient = PatientAgent(
            model=self,
            cdr_level=cdr_level,
            age=patient_age,
            educ=patient_educ,
            calibrated_params=calibrated_params
        )
        self.screener = ScreenerAgent(model=self)
        self.memory_agent = MemoryAnalysisAgent(model=self)
        self.attention_agent = AttentionAnalysisAgent(model=self)
        self.adaptive_agent = AdaptiveDifficultyAgent(
            model=self,
            target_profile=target_profile
        )
        self.agent_decision_history: List[Dict[str, Any]] = []

        # Place Core Agents on Grid Boundary Cells (Row 5)
        self.grid.place_agent(self.patient, (5, 0))
        self.grid.place_agent(self.screener, (5, 4))
        self.grid.place_agent(self.adaptive_agent, (5, 5))

        # Spatial Representation of Memory Board Cells
        self.tile_agents: Dict[Tuple[int, int], TileAgent] = {}
        self._update_tile_grid("3x4")

        # Active state holders for multi-agent closed loop
        self.latest_telemetry: Dict[str, Any] = {}
        self.latest_assessment: Dict[str, Any] = {}
        self.latest_dda_action: Dict[str, Any] = {
            "adapted": False,
            "grid_size": "3x4",
            "exposure_time_sec": 2.0,
            "difficulty_name": "Gentle / Baseline",
            "reason": "Initial Baseline Established",
            "micro_break_recommended": False
        }

        # Simulation history
        self.current_round: int = 0
        self.is_completed: bool = False
        self.history_records: List[Dict[str, Any]] = []

        # DataCollector for longitudinal evaluation
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Round": lambda m: m.current_round,
                "Grid_Size": lambda m: m.adaptive_agent.get_current_grid(),
                "Predicted_MMSE": lambda m: (
                    None if m.latest_assessment.get("Assessment_Method") == "task_specific_heuristic"
                    else m.screener.predicted_mmse
                ),
                "CSI": lambda m: (
                    None if m.latest_assessment.get("Assessment_Method") == "task_specific_heuristic"
                    else m.screener.cognitive_state_index
                ),
                "Task_Performance_Score": lambda m: m.latest_assessment.get("Task_Performance_Score"),
                "Cognitive_Domain": lambda m: m.latest_assessment.get("Cognitive_Domain", ""),
                "Patient_Fatigue": lambda m: m.patient.fatigue_level,
                "Patient_Anxiety": lambda m: m.patient.anxiety_index,
                "Patient_Dropped_Out": lambda m: m.patient.dropout,
                "Mean_RT_ms": lambda m: m.latest_telemetry.get(
                    "Mean_Reaction_Time_ms", m.latest_telemetry.get("mean_reaction_time_ms", 0.0)
                ),
                "Error_Rate": lambda m: m.latest_telemetry.get(
                    "Error_Rate", m.latest_telemetry.get("error_rate", 0.0)
                ),
                "Hesitations": lambda m: m.latest_telemetry.get(
                    "Hesitation_Intervals_Count", m.latest_telemetry.get("hesitation_count", 0)
                ),
                "Session_ID": lambda m: getattr(m, "session_id", "N/A")
            }
        )

    def _update_tile_grid(self, grid_size: str) -> None:
        """
        Cleanly removes all existing TileAgent instances from self.grid before placing new tiles,
        guaranteeing zero OccupiedError collisions on Mesa SingleGrid during dynamic resizing.
        """
        rows, cols = [int(x) for x in grid_size.lower().split("x")]
        current_coords = set(self.tile_agents.keys())
        target_coords = {(r, c) for r in range(rows) for c in range(cols)}
        if current_coords == target_coords:
            return  # Active board geometry already synchronized

        # 1. Cleanly remove existing tiles from the grid and Mesa model
        for pos in list(self.tile_agents.keys()):
            tile = self.tile_agents.pop(pos)
            if tile.pos is not None:
                self.grid.remove_agent(tile)
            tile.remove()
        self.tile_agents.clear()

        # 2. Place new tiles for updated grid dimensions
        for r in range(rows):
            for c in range(cols):
                pos = (r, c)
                if not self.grid.is_cell_empty(pos):
                    # Safety evacuation if occupied
                    resident = self.grid.get_cell_list_contents([pos])
                    for a in resident:
                        self.grid.remove_agent(a)
                        a.remove()

                tile = TileAgent(model=self)
                self.grid.place_agent(tile, pos)
                self.tile_agents[pos] = tile

    def _sync_spatial_board_grid(self, grid_size: str) -> None:
        """Alias for _update_tile_grid to ensure backwards compatibility."""
        self._update_tile_grid(grid_size)

    def _sync_spatial_state(self) -> None:
        """Synchronizes patient agent position and memory board tiles on Mesa SingleGrid."""
        target_pos = (5, min(self.adaptive_agent.current_grid_idx, 3))
        if self.patient.pos != target_pos and self.grid.is_cell_empty(target_pos):
            self.grid.move_agent(self.patient, target_pos)

        active_grid = self.latest_dda_action.get("grid_size", "3x4")
        self._update_tile_grid(active_grid)

    def step(self) -> Dict[str, Any]:
        """
        Native Mesa Staged Model Step:
        Dispatches turn execution through standard Mesa agent step() methods:
          1. PatientAgent.step()        -> Generates telemetry, updates fatigue & anxiety
          2. ScreenerAgent.step()       -> ML-driven clinical classification & MMSE prediction
          3. AdaptiveDifficultyAgent.step() -> Performance-based DDA tuning & restorative feedback
          4. SingleGrid Synchronization -> Spatial movement & collision-free tile updates
          5. DataCollector.collect()    -> Longitudinal telemetry logging
        """
        self.current_round += 1

        # Native Mesa Agent Turn Stepping
        self.patient.step()
        self.screener.step()
        self.memory_agent.step()
        self.attention_agent.step()
        self.adaptive_agent.step()

        # Synchronize 2D SingleGrid environment
        self._sync_spatial_state()

        # Record telemetry to DataCollector
        self.datacollector.collect(self)

        step_record = {
            "round": self.current_round,
            "telemetry": self.latest_telemetry,
            "assessment": self.latest_assessment,
            "dda_action": self.latest_dda_action
        }
        self.history_records.append(step_record)
        return step_record

    def step_synthetic_round(self) -> Dict[str, Any]:
        """
        Executes one full simulation cycle using native Mesa agent scheduling.
        Returns the step record containing telemetry, assessment, and dda_action.
        """
        self.step()
        return self.history_records[-1]

    def process_live_frontend_telemetry(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Closed feedback hook called by Pygame frontend when a real human finishes a round.
        Dispatches live human telemetry through native ScreenerAgent and AdaptiveDifficultyAgent turns.
        """
        self.current_round += 1
        self.latest_telemetry = telemetry

        # Step screener and adaptive agents with real human telemetry
        self.screener.step()
        self.memory_agent.step()
        self.attention_agent.step()
        self.adaptive_agent.step()

        # Synchronize spatial state and record metrics
        self._sync_spatial_state()
        self.datacollector.collect(self)

        step_record = {
            "round": self.current_round,
            "telemetry": self.latest_telemetry,
            "assessment": self.latest_assessment,
            "dda_action": self.latest_dda_action
        }
        self.history_records.append(step_record)

        return {
            "next_grid_size": self.latest_dda_action["grid_size"],
            "next_exposure_sec": self.latest_dda_action["exposure_time_sec"],
            "difficulty_name": self.latest_dda_action["difficulty_name"],
            "clinical_flag": self.latest_assessment["Clinical_Flag"],
            "predicted_mmse": self.latest_assessment["Predicted_MMSE"],
            "reason": self.latest_dda_action["reason"],
            "micro_break": self.latest_dda_action.get("micro_break_recommended", False)
        }

    def process_task_result(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Run one real Electron game result through the Mesa agent loop.

        Unlike the Pygame memory-board hook, this method accepts task-tagged
        telemetry from all eight Electron task mechanics. The screener uses the
        appropriate task rubric and the DDA agent tunes that game's next level.
        """
        self.current_round += 1
        self.latest_telemetry = dict(telemetry)

        # The order matters: assess this exact human result before adapting.
        self.screener.step()
        self.memory_agent.step()
        self.attention_agent.step()
        self.adaptive_agent.step()
        self._sync_spatial_state()
        self.datacollector.collect(self)

        agent_decisions = {
            "screener": dict(self.screener.latest_decision),
            "memory": dict(self.memory_agent.latest_analysis),
            "attention": dict(self.attention_agent.latest_analysis),
            "adaptive": {
                "agent": "AdaptiveDifficultyAgent",
                "decision": "change_difficulty" if self.latest_dda_action.get("adapted") else "hold_or_boundary",
                "explanation": self.latest_dda_action.get("reason", "No decision recorded."),
                "metrics_used": self.latest_dda_action.get("metrics_used", []),
                "decision_factors": self.latest_dda_action.get("decision_factors", []),
            },
        }
        record = {
            "round": self.current_round,
            "game": self.latest_telemetry.get("game", "legacy_simulation"),
            "agent_decisions": agent_decisions,
            "assessment": dict(self.latest_assessment),
            "dda_action": dict(self.latest_dda_action),
        }
        self.agent_decision_history.append(record)
        self.agent_decision_history = self.agent_decision_history[-60:]

        step_record = {
            "round": self.current_round,
            "telemetry": self.latest_telemetry,
            "assessment": self.latest_assessment,
            "dda_action": self.latest_dda_action,
            "agent_decisions": agent_decisions,
        }
        self.history_records.append(step_record)
        return step_record

    def get_agent_debug_state(self) -> Dict[str, Any]:
        """Return a developer-friendly snapshot of live Mesa agents and their decisions."""
        last_telemetry = self.latest_telemetry or {}
        adaptive_history = self.adaptive_agent.task_decision_history[-12:]
        return {
            "current_round": self.current_round,
            "current_game": last_telemetry.get("game", "None yet"),
            "agents": [
                {
                    "name": "ScreenerAgent",
                    "role": "Converts task telemetry into a transparent task-specific score, uncertainty estimate and explanation.",
                    "mode": "task-specific heuristic; no clinical probability",
                    "state": {
                        "latest_score": self.screener.latest_assessment.get("Task_Performance_Score"),
                        "latest_domain": self.screener.latest_assessment.get("Cognitive_Domain"),
                        "evidence_confidence": self.screener.latest_assessment.get("Evidence_Confidence"),
                        "uncertainty_95pct_points": self.screener.latest_assessment.get("Uncertainty_95pct_Points"),
                        "practice_exposure_count": self.screener.latest_assessment.get("Practice_Exposure_Count"),
                        "latest_decision": self.screener.latest_decision,
                    },
                    "history": self.screener.session_history[-8:],
                },
                {
                    "name": "MemoryAnalysisAgent",
                    "role": "Interprets recall, sequence span, pair learning and immediate-to-delayed retention metrics.",
                    "mode": "active for pairs, sequences and delayed recall",
                    "state": self.memory_agent.latest_analysis,
                    "history": self.memory_agent.history[-8:],
                },
                {
                    "name": "AttentionAnalysisAgent",
                    "role": "Tracks response consistency, inhibition slips, false starts, omissions and commission errors.",
                    "mode": "active for Stroop and Reflex Lab tasks",
                    "state": self.attention_agent.latest_analysis,
                    "history": self.attention_agent.history[-8:],
                },
                {
                    "name": "AdaptiveDifficultyAgent",
                    "role": "Adjusts each task independently using performance, uncertainty, practice trend and task-specific parameters.",
                    "mode": "active",
                    "state": {
                        "task_levels": dict(self.adaptive_agent.task_levels),
                        "task_performance_history": {
                            key: value[-8:] for key, value in self.adaptive_agent.task_performance_history.items()
                        },
                        "latest_action": self.latest_dda_action,
                    },
                    "history": adaptive_history,
                },
                {
                    "name": "PatientAgent",
                    "role": "Synthetic participant used by the legacy simulation/evaluation path. It does not simulate the real Electron participant.",
                    "mode": "simulation only in Electron sessions",
                    "state": {"fatigue_level": self.patient.fatigue_level, "anxiety_index": self.patient.anxiety_index,
                              "dropout": self.patient.dropout, "age_profile": self.patient.age},
                    "history": [],
                },
                {
                    "name": "TileAgent",
                    "role": "Represents cells in the legacy Pygame/Mesa spatial board; Electron board rendering runs in JavaScript.",
                    "mode": "legacy board representation",
                    "state": {"tile_count": len(self.tile_agents), "board_shape": "3x4 legacy default"},
                    "history": [],
                },
            ],
            "decision_history": self.agent_decision_history[-20:],
        }

    def get_simulation_dataframe(self) -> pd.DataFrame:
        """Returns collected simulation history as a pandas DataFrame."""
        return self.datacollector.get_model_vars_dataframe()
