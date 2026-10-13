"""Reproducible toy experiment comparing adaptive and fixed-level testing.

This is a synthetic engineering benchmark, not clinical validation. It checks
whether adaptive level selection reaches a confident estimate of an artificial
participant's task ability in fewer trials than repeatedly using level 2.

Run from the project root:
    python evaluation/compare_adaptive_fixed.py
"""
from __future__ import annotations

import json
import math
import random
import statistics
from pathlib import Path

SEED = 20261013
PARTICIPANTS = 600
TRIALS_PER_PERSON = 24
BLOCK_SIZE = 6
LEVELS = (1, 2, 3)
ABILITIES = (1, 2, 3)


def p_correct(ability: int, level: int, practice_block: int) -> float:
    """Toy psychometric curve with a small, explicit early practice effect."""
    base = 0.08 + 0.90 / (1.0 + math.exp(1.6 * (level - ability - 0.65)))
    practice_boost = 0.055 if practice_block == 0 else (0.025 if practice_block == 1 else 0.0)
    return min(0.98, base + practice_boost)


def update_posterior(posterior: dict[int, float], level: int, correct: bool, block: int) -> dict[int, float]:
    updated = {}
    for ability, prior in posterior.items():
        probability = p_correct(ability, level, block)
        likelihood = probability if correct else (1.0 - probability)
        updated[ability] = prior * likelihood
    total = sum(updated.values()) or 1.0
    return {ability: value / total for ability, value in updated.items()}


def normalized_entropy(posterior: dict[int, float]) -> float:
    entropy = -sum(p * math.log(max(p, 1e-12), 2) for p in posterior.values())
    return entropy / math.log(len(posterior), 2)


def run_person_with_adaptation(rng: random.Random, true_ability: int, adaptive: bool) -> dict:
    posterior = {ability: 1.0 / len(ABILITIES) for ability in ABILITIES}
    level = 1 if adaptive else 2
    results = []
    levels_used = []
    posterior_confidence_trial = None
    prior_block_accuracy = None
    same_level_blocks = 0

    for trial_index in range(TRIALS_PER_PERSON):
        block = trial_index // BLOCK_SIZE
        levels_used.append(level)
        correct = rng.random() < p_correct(true_ability, level, block)
        results.append(correct)
        posterior = update_posterior(posterior, level, correct, block)
        if posterior_confidence_trial is None and max(posterior.values()) >= 0.75:
            posterior_confidence_trial = trial_index + 1

        if adaptive and (trial_index + 1) % BLOCK_SIZE == 0:
            block_accuracy = sum(results[-BLOCK_SIZE:]) / BLOCK_SIZE
            if block_accuracy < 0.60 and level > 1:
                level -= 1
                same_level_blocks = 0
            elif (prior_block_accuracy is not None and same_level_blocks >= 1
                  and (prior_block_accuracy + block_accuracy) / 2 >= 0.88
                  and block_accuracy >= 0.88 and level < 3):
                level += 1
                same_level_blocks = 0
            else:
                same_level_blocks += 1
            prior_block_accuracy = block_accuracy

    return {
        "true_ability": true_ability,
        "estimated_ability": max(posterior, key=posterior.get),
        "final_entropy": normalized_entropy(posterior),
        "trials_to_confidence": posterior_confidence_trial or TRIALS_PER_PERSON + 1,
        "levels_used": levels_used,
        "mean_level": statistics.mean(levels_used),
    }


def evaluate_method(rng: random.Random, adaptive: bool) -> dict:
    records = []
    for _ in range(PARTICIPANTS):
        ability = rng.choice(ABILITIES)
        records.append(run_person_with_adaptation(rng, ability, adaptive))
    confidence_trials = [r["trials_to_confidence"] for r in records if r["trials_to_confidence"] <= TRIALS_PER_PERSON]
    return {
        "method": "adaptive" if adaptive else "fixed_level_2",
        "participants": PARTICIPANTS,
        "trials_per_person": TRIALS_PER_PERSON,
        "ability_classification_accuracy_percent": round(100 * sum(r["estimated_ability"] == r["true_ability"] for r in records) / len(records), 2),
        "mean_final_normalized_entropy": round(statistics.mean(r["final_entropy"] for r in records), 4),
        "median_trials_to_75pct_posterior": round(statistics.median(confidence_trials), 1) if confidence_trials else None,
        "participants_reaching_75pct_posterior_percent": round(100 * len(confidence_trials) / len(records), 2),
        "mean_level_used": round(statistics.mean(r["mean_level"] for r in records), 3),
    }


def main() -> None:
    adaptive_rng = random.Random(SEED)
    fixed_rng = random.Random(SEED + 1)
    results = {
        "experiment": "synthetic adaptive versus fixed cognitive-task testing",
        "seed": SEED,
        "simulation_only": True,
        "clinical_validity_claim": False,
        "model_note": "Toy response curves and simulated participants only; results do not imply performance on real people or disease detection.",
        "methods": [evaluate_method(adaptive_rng, True), evaluate_method(fixed_rng, False)],
    }
    output = Path(__file__).with_name("adaptive_vs_fixed_results.json")
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"\nSaved: {output}")


if __name__ == "__main__":
    main()
