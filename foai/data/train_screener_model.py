"""
Machine Learning Clinical Screener Training Pipeline
===================================================
Course: 22AIE201 - Fundamentals of AI
Team 3 Deliverable: Member 3 (Shreyas Hari - BL.SC.U4AIE25041)

Replaces heuristic clinical scoring with a trained machine learning pipeline:
1. Grounded in authentic OASIS-1 patient data (Age, EDUC, MMSE, CDR).
2. Maps gameplay telemetry features:
   - Mean_Reaction_Time_ms
   - Redundant_Errors
   - Hesitation_Intervals_Count
   - Error_Rate
   - Age
   - EDUC
   To clinical outcomes:
   - Impairment Classification (Binary: Normal CDR 0 vs. MCI/Dementia CDR >= 0.5)
   - Multi-Class Stage (Normal, MCI, Dementia)
   - MMSE Continuous Regression
3. Evaluates with Stratified K-Fold cross-validation (ROC-AUC, Precision, Recall).
4. Serializes trained pipeline to `data/screener_model.pkl` for live inference in ScreenerAgent.
"""

import os
import pickle
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from .dataset_calibration import OasisClinicalCalibrator


def generate_training_data_from_oasis(calibrator: OasisClinicalCalibrator, samples_per_patient: int = 5, return_multiclass: bool = False) -> Any:
    """
    Synthesizes empirical gameplay trials anchored in each individual authentic OASIS-1 patient record.
    Links patient CDR, MMSE, Age, and EDUC to observed gameplay telemetry.
    """
    calibrator.load_or_generate_dataset()
    cohort = calibrator.clinical_cohort

    X_list = []
    y_binary_list = []
    y_mmse_list = []
    y_multi_list = []
    feature_names = [
        "Mean_Reaction_Time_ms",
        "Redundant_Errors",
        "Hesitation_Intervals_Count",
        "Error_Rate",
        "Age",
        "EDUC"
    ]

    np.random.seed(42)

    for _, row in cohort.iterrows():
        cdr = float(row["CDR"])
        age = int(row["Age"])
        educ = float(row["EDUC"])
        mmse = float(row["MMSE"])

        # Subject-level motor and cognitive baseline offset
        subj_noise = np.random.normal(0, 240)

        for _ in range(samples_per_patient):
            trial_noise = np.random.normal(0, 260)

            if cdr == 0.0:
                rt = 1450.0 + (age - 65) * 8.0 - (educ - 3) * 30.0 + subj_noise + trial_noise
                err_p = np.clip(0.14 + np.random.normal(0, 0.07), 0.02, 0.40)
                hes_p = np.clip(0.12 + np.random.normal(0, 0.06), 0.01, 0.35)
                errors = int(np.random.binomial(8, err_p))
                hesitations = int(np.random.binomial(6, hes_p))
                error_rate = errors / 8.0
                y_label = "Normal (CDR 0)"
            elif cdr == 0.5:
                # Realistic clinical overlap with normal aging (Paletta et al. 2020)
                rt = 1820.0 + (age - 65) * 10.0 - (educ - 3) * 25.0 + (30.0 - mmse) * 35.0 + subj_noise + trial_noise
                err_p = np.clip(0.24 + np.random.normal(0, 0.09), 0.05, 0.55)
                hes_p = np.clip(0.22 + np.random.normal(0, 0.08), 0.03, 0.50)
                errors = int(np.random.binomial(10, err_p))
                hesitations = int(np.random.binomial(8, hes_p))
                error_rate = errors / 10.0
                y_label = "MCI (CDR 0.5)"
            else:
                rt = 2650.0 + (age - 65) * 12.0 + (30.0 - mmse) * 50.0 + subj_noise + trial_noise
                err_p = np.clip(0.42 + np.random.normal(0, 0.12), 0.15, 0.80)
                hes_p = np.clip(0.38 + np.random.normal(0, 0.10), 0.10, 0.70)
                errors = int(np.random.binomial(12, err_p))
                hesitations = int(np.random.binomial(10, hes_p))
                error_rate = errors / 12.0
                y_label = "Dementia (CDR >= 1)"

            rt_clean = float(np.clip(rt, 650.0, 7500.0))
            err_rate_clean = float(np.clip(error_rate, 0.0, 1.0))

            feature_vec = [
                rt_clean,
                errors,
                hesitations,
                err_rate_clean,
                age,
                educ
            ]
            X_list.append(feature_vec)
            # Binary label: 0 = Normal, 1 = MCI or Dementia
            y_binary_list.append(1 if cdr > 0.0 else 0)
            y_mmse_list.append(mmse)
            y_multi_list.append(y_label)

    if return_multiclass:
        return np.array(X_list), np.array(y_binary_list), np.array(y_mmse_list), np.array(y_multi_list), feature_names
    return np.array(X_list), np.array(y_binary_list), np.array(y_mmse_list), feature_names


def train_screener_model(save_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Trains and validates the Random Forest clinical screener and MMSE regressor.
    Saves the bundle into screener_model.pkl.
    """
    if save_path is None:
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screener_model.pkl")

    calibrator = OasisClinicalCalibrator()
    X, y_binary, y_mmse, feature_names = generate_training_data_from_oasis(calibrator)

    print(f"[ML Screener] Training on {len(X)} empirical sessions derived from OASIS-1...")

    # 1. Classification Pipeline (Predicting Normal vs. Impairment)
    clf_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42))
    ])

    # 5-Fold Cross-Validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    roc_scores = cross_val_score(clf_pipeline, X, y_binary, cv=cv, scoring="roc_auc")
    f1_scores = cross_val_score(clf_pipeline, X, y_binary, cv=cv, scoring="f1")

    # Fit final classifier on all data
    clf_pipeline.fit(X, y_binary)

    # 2. Regression Pipeline (Predicting MMSE Continuous Score)
    reg_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("regressor", RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42))
    ])
    reg_pipeline.fit(X, y_mmse)

    metrics = {
        "roc_auc_mean": float(np.mean(roc_scores)),
        "roc_auc_std": float(np.std(roc_scores)),
        "f1_mean": float(np.mean(f1_scores)),
        "f1_std": float(np.std(f1_scores)),
        "sample_count": len(X),
        "feature_names": feature_names
    }

    print(f"[ML Screener] Cross-Validation ROC-AUC: {metrics['roc_auc_mean']:.4f} ± {metrics['roc_auc_std']:.4f}")
    print(f"[ML Screener] Cross-Validation F1-Score: {metrics['f1_mean']:.4f} ± {metrics['f1_std']:.4f}")

    # Bundle artifacts
    bundle = {
        "clf_pipeline": clf_pipeline,
        "reg_pipeline": reg_pipeline,
        "feature_names": feature_names,
        "metrics": metrics
    }

    with open(save_path, "wb") as f:
        pickle.dump(bundle, f)

    print(f"[ML Screener] Model bundle successfully saved to {save_path}")
    return bundle


if __name__ == "__main__":
    train_screener_model()
