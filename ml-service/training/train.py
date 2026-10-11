"""
Model training and evaluation pipeline for TicketTriage.
Trains 4 model architectures on identical train/val/test splits:
1. RandomForestClassifier (MultiOutput)
2. XGBoostClassifier (MultiOutput)
3. ClassifierChain (using the better of RF / XGBoost)
4. AdaBoostClassifier (MultiOutput baseline)

Performs validation threshold tuning, held-out test evaluation,
benchmark latency measurement, diagnostic plotting, and artifact serialization.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.multioutput import MultiOutputClassifier, ClassifierChain
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

# Support both direct script execution and module imports
current_dir = Path(__file__).resolve().parent
ml_service_dir = current_dir.parent
if str(ml_service_dir) not in sys.path:
    sys.path.insert(0, str(ml_service_dir))

from core.domain_loader import load_domain_pack
from data.loader import load_tickets_csv
from training.features import TicketFeatureExtractor
from training.thresholds import tune_label_thresholds, apply_thresholds, save_thresholds
from training.evaluate import (
    evaluate_model_predictions,
    benchmark_inference_latency,
    create_comparison_tables,
    generate_evaluation_plots,
)


def split_dataset(
    df: pd.DataFrame,
    y_binary: np.ndarray,
    train_size: float = 0.70,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    """
    Splits dataset into train, val, test splits.
    Attempts iterative stratification; falls back to power-set seeded stratification.
    """
    try:
        from skmultilearn.model_selection import iterative_train_test_split
        # First split into train and temp (val + test)
        temp_ratio = val_size + test_size
        x_indices = np.arange(len(df)).reshape(-1, 1)
        x_tr_idx, y_train, x_temp_idx, y_temp = iterative_train_test_split(x_indices, y_binary, test_size=temp_ratio)
        
        # Next split temp into val and test (equal ratio of remainder)
        val_sub_ratio = val_size / temp_ratio
        x_val_idx, y_val, x_te_idx, y_test = iterative_train_test_split(x_temp_idx, y_temp, test_size=1.0 - val_sub_ratio)
        
        df_train = df.iloc[x_tr_idx.flatten()].reset_index(drop=True)
        df_val = df.iloc[x_val_idx.flatten()].reset_index(drop=True)
        df_test = df.iloc[x_te_idx.flatten()].reset_index(drop=True)
        print("Used scikit-multilearn iterative_train_test_split for multi-label stratification.")
        return df_train, df_val, df_test, y_train, y_val, y_test
    except Exception:
        # Fallback: Powerset label signature stratification
        label_signatures = ["-".join(map(str, row)) for row in y_binary]
        # For very rare combinations with count < 2, group as 'other'
        counts = pd.Series(label_signatures).value_counts()
        strat_col = [sig if counts[sig] >= 2 else "other" for sig in label_signatures]

        df_train_temp, df_test, y_train_temp, y_test, strat_temp, _ = train_test_split(
            df, y_binary, strat_col, test_size=test_size, random_state=random_state, stratify=strat_col
        )
        
        # Recalculate stratification for second split
        counts_temp = pd.Series(strat_temp).value_counts()
        strat_temp_adj = [s if counts_temp[s] >= 2 else "other" for s in strat_temp]
        val_adj_ratio = val_size / (train_size + val_size)

        df_train, df_val, y_train, y_val = train_test_split(
            df_train_temp, y_train_temp, test_size=val_adj_ratio, random_state=random_state, stratify=strat_temp_adj
        )

        print("Used powerset signature stratified split for multi-label balance.")
        return df_train, df_val, df_test, y_train, y_val, y_test


def get_model_probabilities(model, x_matrix, n_labels: int) -> np.ndarray:
    """Safely extracts predicted probabilities for multi-label outputs."""
    if hasattr(model, "predict_proba"):
        probs_output = model.predict_proba(x_matrix)
        # MultiOutputClassifier returns a list of (n_samples, 2) arrays
        if isinstance(probs_output, list):
            n_samples = x_matrix.shape[0]
            y_probs = np.zeros((n_samples, len(probs_output)))
            for j, p in enumerate(probs_output):
                if p.shape[1] == 2:
                    y_probs[:, j] = p[:, 1]
                else:
                    # In degenerate case of single class present
                    y_probs[:, j] = p[:, 0]
            return y_probs
        elif isinstance(probs_output, np.ndarray) and probs_output.ndim == 2:
            return probs_output
    # Fallback to decision_function or binary predict
    preds = model.predict(x_matrix)
    if isinstance(preds, list):
        preds = np.column_stack(preds)
    return preds.astype(float)


def train_pipeline(
    domain_name: str,
    dataset_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Runs complete multi-label training, tuning, benchmarking, and export."""
    pack = load_domain_pack(domain_name)
    print(f"\n=======================================================")
    print(f"Starting TicketTriage training for domain: {domain_name}")
    print(f"Labels ({len(pack.labels)}): {pack.label_ids}")
    print(f"=======================================================")

    # 1. Load data
    if dataset_path is None:
        dataset_path = pack.pack_dir.parent.parent / "data" / f"tickets_{domain_name}.csv"
    
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}. Run generate_synthetic.py first.")

    print(f"Loading dataset from: {dataset_path}")
    df = load_tickets_csv(dataset_path, domain_name=domain_name)
    print(f"Loaded {len(df)} tickets.")

    # 2. Extract features
    extractor = TicketFeatureExtractor(domain_label_ids=pack.label_ids, max_features=12000)
    extractor.fit(df)
    y_all = extractor.transform_y(df)

    # 3. Stratified Split
    df_train, df_val, df_test, y_train, y_val, y_test = split_dataset(df, y_all, random_state=42)
    print(f"Splits -> Train: {len(df_train)}, Val: {len(df_val)}, Test: {len(df_test)}")

    x_train = extractor.transform_x(df_train)
    x_val = extractor.transform_x(df_val)
    x_test = extractor.transform_x(df_test)

    # 4. Define candidate model architectures
    models_to_train = {
        "RandomForest": MultiOutputClassifier(
            RandomForestClassifier(
                n_estimators=80,
                max_depth=20,
                min_samples_split=4,
                n_jobs=-1,
                random_state=42,
            )
        ),
        "XGBoost": MultiOutputClassifier(
            XGBClassifier(
                n_estimators=60,
                max_depth=5,
                learning_rate=0.2,
                subsample=0.85,
                colsample_bytree=0.85,
                eval_metric="logloss",
                random_state=42,
                n_jobs=-1,
            )
        ),
        "AdaBoost": MultiOutputClassifier(
            AdaBoostClassifier(
                n_estimators=25,
                learning_rate=0.8,
                random_state=42,
            )
        ),
    }

    trained_models = {}
    model_evaluations = []
    val_probs_cache = {}
    test_probs_cache = {}
    tuned_thresholds_cache = {}

    for name, clf in models_to_train.items():
        print(f"\n--- Training {name} ---")
        t0 = time.time()
        clf.fit(x_train, y_train)
        train_time = time.time() - t0
        print(f"Finished training {name} in {train_time:.2f}s")
        trained_models[name] = clf

        # Validation probabilities & threshold tuning
        val_probs = get_model_probabilities(clf, x_val, len(pack.label_ids))
        val_probs_cache[name] = val_probs
        threshold_info = tune_label_thresholds(y_val, val_probs, pack.label_ids)
        tuned_thresholds_cache[name] = {k: v["threshold"] for k, v in threshold_info.items()}

        # Held-out test evaluation
        test_probs = get_model_probabilities(clf, x_test, len(pack.label_ids))
        test_probs_cache[name] = test_probs
        y_test_pred = apply_thresholds(test_probs, tuned_thresholds_cache[name], pack.label_ids)

        eval_res = evaluate_model_predictions(
            y_test, y_test_pred, test_probs, pack.label_ids, train_time_sec=train_time, model_name=name
        )

        # Latency benchmark
        latency_info = benchmark_inference_latency(clf, x_test[:10])
        eval_res.update(latency_info)
        model_evaluations.append(eval_res)
        print(f"Results for {name}: Macro F1={eval_res['macro_f1']}, Micro F1={eval_res['micro_f1']}, Latency p50={eval_res['latency_p50_ms']}ms")

    # 5. ClassifierChain with the better of RF or XGBoost
    rf_macro = next(m["macro_f1"] for m in model_evaluations if m["model_name"] == "RandomForest")
    xgb_macro = next(m["macro_f1"] for m in model_evaluations if m["model_name"] == "XGBoost")
    base_name = "XGBoost" if xgb_macro >= rf_macro else "RandomForest"
    print(f"\nBuilding ClassifierChain with best base model: {base_name}")

    if base_name == "XGBoost":
        chain_base = XGBClassifier(
            n_estimators=80,
            max_depth=5,
            learning_rate=0.15,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )
    else:
        chain_base = RandomForestClassifier(
            n_estimators=80,
            max_depth=20,
            n_jobs=-1,
            random_state=42,
        )

    chain_model = ClassifierChain(chain_base, order="random", random_state=42)
    t0 = time.time()
    chain_model.fit(x_train, y_train)
    chain_train_time = time.time() - t0
    trained_models["ClassifierChain"] = chain_model

    val_probs_chain = get_model_probabilities(chain_model, x_val, len(pack.label_ids))
    val_probs_cache["ClassifierChain"] = val_probs_chain
    chain_threshold_info = tune_label_thresholds(y_val, val_probs_chain, pack.label_ids)
    tuned_thresholds_cache["ClassifierChain"] = {k: v["threshold"] for k, v in chain_threshold_info.items()}

    test_probs_chain = get_model_probabilities(chain_model, x_test, len(pack.label_ids))
    test_probs_cache["ClassifierChain"] = test_probs_chain
    y_test_pred_chain = apply_thresholds(test_probs_chain, tuned_thresholds_cache["ClassifierChain"], pack.label_ids)

    chain_eval = evaluate_model_predictions(
        y_test, y_test_pred_chain, test_probs_chain, pack.label_ids, train_time_sec=chain_train_time, model_name=f"ClassifierChain({base_name})"
    )
    chain_latency = benchmark_inference_latency(chain_model, x_test[:10])
    chain_eval.update(chain_latency)
    model_evaluations.append(chain_eval)
    print(f"Results for ClassifierChain: Macro F1={chain_eval['macro_f1']}, Micro F1={chain_eval['micro_f1']}, Latency p50={chain_eval['latency_p50_ms']}ms")

    # 6. Select Best Model
    # Sort primarily by Macro F1 (balances rare and frequent classes), then Micro F1
    sorted_models = sorted(model_evaluations, key=lambda x: (x["macro_f1"], x["micro_f1"]), reverse=True)
    best_eval = sorted_models[0]
    best_model_name = best_eval["model_name"]
    # Map back to model dict key
    key_map = {
        "RandomForest": "RandomForest",
        "XGBoost": "XGBoost",
        "AdaBoost": "AdaBoost",
        f"ClassifierChain({base_name})": "ClassifierChain",
    }
    best_key = key_map.get(best_model_name, "XGBoost")
    best_model = trained_models[best_key]
    best_thresholds = tuned_thresholds_cache[best_key]
    best_test_probs = test_probs_cache[best_key]

    print(f"\n=======================================================")
    print(f"BEST MODEL SELECTED: {best_model_name}")
    print(f"Macro F1: {best_eval['macro_f1']}, Micro F1: {best_eval['micro_f1']}, Rare F1: {best_eval['rare_macro_f1']}")
    print(f"=======================================================\n")

    # 7. Setup output directory under models/<DOMAIN>/
    if output_dir is None:
        output_dir = pack.pack_dir.parent.parent / "models" / domain_name
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "plots"

    # 8. Save comparison tables & plots
    comparison_csv = output_dir / "comparison.csv"
    comparison_md = output_dir / "comparison.md"
    create_comparison_tables(model_evaluations, comparison_csv, comparison_md)

    generate_evaluation_plots(
        y_true=y_test,
        y_probs=best_test_probs,
        label_names=pack.label_ids,
        per_label_metrics=best_eval["per_label"],
        plots_dir=plots_dir,
    )

    # 9. Save artifacts
    model_path = output_dir / "model.joblib"
    vectorizer_path = output_dir / "vectorizer.joblib"
    mlb_path = output_dir / "mlb.joblib"
    thresholds_path = output_dir / "thresholds.json"
    metrics_path = output_dir / "metrics.json"

    joblib.dump(best_model, model_path)
    joblib.dump(extractor.vectorizer, vectorizer_path)
    joblib.dump(extractor.mlb, mlb_path)
    save_thresholds(best_thresholds, thresholds_path)

    summary_metrics = {
        "domain_name": domain_name,
        "best_model_name": best_model_name,
        "evaluation": best_eval,
        "all_models": model_evaluations,
        "timestamp": time.time(),
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(summary_metrics, f, indent=2)

    print(f"Successfully saved all artifacts to: {output_dir}")
    print(f" - Model: {model_path}")
    print(f" - Vectorizer: {vectorizer_path}")
    print(f" - MLB: {mlb_path}")
    print(f" - Thresholds: {thresholds_path}")
    print(f" - Metrics: {metrics_path}")
    print(f" - Comparison: {comparison_md}")

    return summary_metrics


def main():
    parser = argparse.ArgumentParser(description="Train TicketTriage models for domain")
    parser.add_argument("--domain", type=str, default=os.getenv("DOMAIN", "saas"), help="Domain name")
    parser.add_argument("--dataset", type=str, default=None, help="Dataset CSV path")
    parser.add_argument("--output", type=str, default=None, help="Output models directory")
    args = parser.parse_args()

    ds_path = Path(args.dataset) if args.dataset else None
    out_dir = Path(args.output) if args.output else None
    train_pipeline(args.domain, ds_path, out_dir)


if __name__ == "__main__":
    main()
