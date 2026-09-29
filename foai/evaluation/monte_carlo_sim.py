"""
Monte Carlo Cohort Simulation & Longitudinal Validation Engine
==============================================================
Course: 22AIE201 - Fundamentals of AI
Team 3 Deliverable: Member 3 (Shreyas Hari) & Member 1 (Praveen Asaithambi)

Simulates a cohort of N = 50 synthetic patient agents across a 30-day intervention period:
1. Directly sampled from authentic OASIS-1 clinical records (Marcus et al., 2007).
2. Directly compares:
   - Dynamic Difficulty Adjustment (DDA Enabled) via Mesa AdaptiveDifficultyAgent
   - Static Difficulty (DDA Disabled / Ablation Baseline)
3. Evaluates:
   - Clinical screening accuracy of the ML-powered ScreenerAgent
   - Prevention of patient dropout and anxiety mitigation (Mezrar & Bendella, 2022)
4. Saves longitudinal results to `data/simulation_cohort_results.csv`.
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, Any, List

# Ensure parent directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.dataset_calibration import OasisClinicalCalibrator
from simulation.model import CognitiveHealthModel


class MonteCarloSimulationCohort:
    """
    Orchestrates batch simulations of diverse patient cohorts
    sampled directly from authentic OASIS-1 clinical data over longitudinal intervention periods.
    """

    def __init__(self, n_patients: int = 50, days: int = 30):
        self.n_patients = n_patients
        self.days = days
        self.calibrator = OasisClinicalCalibrator()
        self.oasis_df = self.calibrator.load_or_generate_dataset()
        self.results: List[Dict[str, Any]] = []

    def run_cohort_experiment(self, force_fresh: bool = True) -> pd.DataFrame:
        """
        Executes parallel runs across the cohort under both:
        (1) Agentic Dynamic Adaptation
        (2) Static Difficulty Control
        """
        np.random.seed(42)
        print(f"[Monte Carlo] Initializing cohort from authentic OASIS-1 data: N={self.n_patients} patients over {self.days} days...")

        # Sample directly from authentic OASIS-1 clinically assessed cohort
        cohort_pool = self.calibrator.clinical_cohort
        if len(cohort_pool) >= self.n_patients:
            sampled_patients = cohort_pool.sample(n=self.n_patients, replace=False, random_state=42)
        else:
            sampled_patients = cohort_pool.sample(n=self.n_patients, replace=True, random_state=42)

        for patient_idx, (_, row) in enumerate(sampled_patients.iterrows()):
            subject_id = str(row["Subject_ID"])
            cdr = float(row["CDR"])
            age = int(row["Age"])
            educ = float(row["EDUC"])
            true_mmse = float(row["MMSE"])

            # Calibrate patient parameters from authentic OASIS dataset record
            calib_params = self.calibrator.get_calibrated_agent_parameters(cdr_level=cdr, age=age, educ=int(educ))

            # Test both DDA and Static modes for the exact same patient profile
            for mode_adaptive in [True, False]:
                condition_label = "Adaptive_DDA" if mode_adaptive else "Static_Control"

                # Instantiate Mesa Model with SingleGrid
                model = CognitiveHealthModel(
                    cdr_level=cdr,
                    patient_age=age,
                    patient_educ=int(educ),
                    target_profile="Elderly",
                    calibrated_params=calib_params,
                    enable_adaptive_dda=mode_adaptive
                )

                # Run simulation over days/rounds
                for d in range(1, self.days + 1):
                    step_result = model.step_synthetic_round()
                    telemetry = step_result["telemetry"]
                    assessment = step_result["assessment"]
                    dda = step_result["dda_action"]

                    # Check if dropped out
                    dropped = telemetry.get("status") == "dropped_out" or telemetry.get("Dropped_Out", False)

                    self.results.append({
                        "Patient_ID": f"PATIENT_{patient_idx+1:03d}_{subject_id}",
                        "OASIS_ID": subject_id,
                        "Condition": condition_label,
                        "Day": d,
                        "True_CDR": cdr,
                        "True_MMSE": true_mmse,
                        "Age": age,
                        "EDUC": educ,
                        "Dropped_Out": dropped,
                        "Error_Rate": telemetry.get("Error_Rate", 1.0) if not dropped else np.nan,
                        "Mean_RT_ms": telemetry.get("Mean_Reaction_Time_ms", np.nan) if not dropped else np.nan,
                        "Hesitations": telemetry.get("Hesitation_Intervals_Count", np.nan) if not dropped else np.nan,
                        "Patient_Fatigue": telemetry.get("Patient_Fatigue", np.nan) if not dropped else np.nan,
                        "Patient_Anxiety": telemetry.get("Patient_Anxiety", np.nan) if not dropped else np.nan,
                        "Predicted_MMSE": assessment.get("Predicted_MMSE", np.nan),
                        "Clinical_Flag": assessment.get("Clinical_Flag", "Dropped"),
                        "Grid_Size": dda.get("grid_size", "4x4")
                    })

                    if dropped:
                        # Once dropped out, patient ceases further rounds in that intervention
                        break

        df_results = pd.DataFrame(self.results)
        output_csv = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "simulation_cohort_results.csv")
        df_results.to_csv(output_csv, index=False)
        print(f"[Monte Carlo] Experiment complete. {len(df_results)} round records saved to {output_csv}.")
        return df_results


if __name__ == "__main__":
    runner = MonteCarloSimulationCohort(n_patients=50, days=30)
    df = runner.run_cohort_experiment()
    print("\nSummary Statistics by Condition:")
    print(df.groupby("Condition")[["Dropped_Out", "Error_Rate", "Patient_Anxiety"]].mean())
