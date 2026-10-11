"""
Threshold optimization module for multi-label classification.
Searches per-label thresholds on validation probabilities to maximize F1-score.
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score


def tune_label_thresholds(
    y_true: np.ndarray,
    y_probs: np.ndarray,
    label_names: List[str],
    step: float = 0.02,
    min_thresh: float = 0.15,
    max_thresh: float = 0.85,
    default_thresh: float = 0.50,
) -> Dict[str, Dict[str, float]]:
    """
    Finds optimal decision threshold for each label independently on validation set.
    Returns dictionary with per-label threshold, precision, recall, and optimal f1.
    """
    threshold_results = {}
    candidates = np.arange(min_thresh, max_thresh + step / 2, step)

    for idx, label in enumerate(label_names):
        true_col = y_true[:, idx]
        prob_col = y_probs[:, idx]

        best_f1 = -1.0
        best_t = default_thresh
        best_p = 0.0
        best_r = 0.0

        # If class has zero positive instances, use default
        if true_col.sum() == 0:
            threshold_results[label] = {
                "threshold": round(default_thresh, 4),
                "f1": 0.0,
                "precision": 0.0,
                "recall": 0.0,
            }
            continue

        for t in candidates:
            preds = (prob_col >= t).astype(int)
            if preds.sum() == 0:
                continue
            f1 = f1_score(true_col, preds, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_t = t
                best_p = precision_score(true_col, preds, zero_division=0)
                best_r = recall_score(true_col, preds, zero_division=0)

        threshold_results[label] = {
            "threshold": round(float(best_t), 4),
            "f1": round(float(best_f1), 4),
            "precision": round(float(best_p), 4),
            "recall": round(float(best_r), 4),
        }

    return threshold_results


def apply_thresholds(
    y_probs: np.ndarray,
    thresholds: Dict[str, float],
    label_names: List[str],
) -> np.ndarray:
    """Applies per-label thresholds to probability matrix to produce binary predictions."""
    y_preds = np.zeros_like(y_probs, dtype=int)
    for idx, label in enumerate(label_names):
        t = thresholds.get(label, 0.5)
        y_preds[:, idx] = (y_probs[:, idx] >= t).astype(int)
    return y_preds


def save_thresholds(thresholds_data: Dict[str, Any], filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(thresholds_data, f, indent=2)


def load_thresholds(filepath: Path) -> Dict[str, float]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Extract only the threshold values
    return {lbl: val["threshold"] if isinstance(val, dict) else float(val) for lbl, val in data.items()}
