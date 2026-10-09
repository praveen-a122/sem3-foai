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
from .agents import PatientAgent, ScreenerAgent, AdaptiveDifficultyAgent, TileAgent


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
        self.adaptive_agent = AdaptiveDifficultyAgent(
            model=self,
            target_profile=target_profile
        )

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
                "Predicted_MMSE": lambda m: m.screener.predicted_mmse,
                "CSI": lambda m: m.screener.cognitive_state_index,
                "Patient_Fatigue": lambda m: m.patient.fatigue_level,
                "Patient_Anxiety": lambda m: m.patient.anxiety_index,
                "Patient_Dropped_Out": lambda m: m.patient.dropout,
                "Mean_RT_ms": lambda m: m.patient.last_round_telemetry.get("Mean_Reaction_time_ms", 0.0),
                "Error_Rate": lambda m: m.patient.last_round_telemetry.get("Error_Rate", 0.0),
                "Hesitations": lambda m: m.patient.last_round_telemetry.get("Hesitation_Intervals_Count", 0),
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

    def get_simulation_dataframe(self) -> pd.DataFrame:
        """Returns collected simulation history as a pandas DataFrame."""
        return self.datacollector.get_model_vars_dataframe()
