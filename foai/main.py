"""
Master Execution Pipeline: Multi-Agent Cognitive Assessment & DDA Gaming
========================================================================
Course: 22AIE201 - Fundamentals of AI
Faculty / Evaluator: Dr. Sajitha Krishnan
Team 3:
- Praveen Asaithambi (BL.SC.U4AIE25035) -> Mesa Architecture & Adaptive Feedback Loop
- Prahlad Vedhanarayanan (BL.SC.U4AIE25034) -> Pygame Frontend & Telemetry Engine
- Shreyas Hari (BL.SC.U4AIE25041)       -> Clinical Dataset Analytics & Screener Agent

Usage:
  python main.py --mode game                  # Launches interactive Pygame serious game
  python main.py --mode evaluate              # Runs N=50 cohort simulation & generates Plots A, B, C
  python main.py --mode calibrate             # Inspects OASIS-1 dataset & parametric distributions
  python main.py --mode test                  # Runs full automated test suite
"""

import sys
import os
import argparse
import subprocess

# Ensure base directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def run_game(headless: bool = False):
    print("=================================================================")
    print(" 22AIE201: Pygame Cognitive Task + Mesa Multi-Agent Closed Loop  ")
    print("=================================================================")
    from frontend.game import CognitiveMemoryGame
    game = CognitiveMemoryGame(headless=headless, enable_mesa_coupling=True)
    game.run()


def run_evaluation(n_patients: int = 50, days: int = 30, force_fresh: bool = True):
    print("=================================================================")
    print(f" 22AIE201: Monte Carlo Simulation (N={n_patients}, {days} Days)           ")
    print("=================================================================")
    from evaluation.generate_plots import run_full_evaluation_pipeline
    plots = run_full_evaluation_pipeline(n_patients=n_patients, days=days, force_fresh=force_fresh)
    print("\nEvaluation completed successfully! Generated Plots:")
    for p in plots:
        print(f"  • {p}")


def run_calibration():
    print("=================================================================")
    print(" 22AIE201: OASIS-1 Clinical Dementia Benchmark Ingestion         ")
    print("=================================================================")
    from data.dataset_calibration import OasisClinicalCalibrator
    calibrator = OasisClinicalCalibrator()
    df = calibrator.load_or_generate_dataset()
    print(f"Dataset Loaded Successfully: {len(df)} patient records.")
    print("\nSample OASIS Records:")
    print(df[["Subject_ID", "Gender", "Age", "EDUC", "MMSE", "CDR", "Clinical_Class"]].head(10).to_string(index=False))

    summary = calibrator.compute_strata_statistics()
    print("\nEmpirical Strata Summary (CDR 0 vs 0.5 vs 1.0):")
    for cdr, s in summary.items():
        print(f"  • CDR {cdr:3.1f} ({s['count']} subjects): Age = {s['age_mean']:.1f} ± {s['age_std']:.1f} | MMSE = {s['mmse_mean']:.1f} ± {s['mmse_std']:.1f} | WholeBrainVol = {s['nwbv_mean']:.3f}")


def run_tests():
    print("=================================================================")
    print(" 22AIE201: Executing Automated Test Suite                        ")
    print("=================================================================")
    import pytest
    test_path = os.path.join(BASE_DIR, "tests")
    exit_code = pytest.main(["-v", test_path])
    if exit_code == 0:
        print("\nAll automated tests PASSED successfully!")
    else:
        print(f"\nTests finished with exit code {exit_code}")
    return exit_code


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Cognitive Health & DDA System")
    parser.add_argument(
        "--mode",
        choices=["game", "evaluate", "calibrate", "test"],
        default="evaluate",
        help="Operating mode: 'game', 'evaluate', 'calibrate', or 'test'"
    )
    parser.add_argument("--patients", type=int, default=50, help="Number of cohort patients for simulation")
    parser.add_argument("--days", type=int, default=30, help="Number of intervention days")
    parser.add_argument("--headless", action="store_true", help="Run Pygame in headless mode (no display)")

    args = parser.parse_args()

    if args.mode == "game":
        run_game(headless=args.headless)
    elif args.mode == "evaluate":
        run_evaluation(n_patients=args.patients, days=args.days)
    elif args.mode == "calibrate":
        run_calibration()
    elif args.mode == "test":
        run_tests()


if __name__ == "__main__":
    main()
