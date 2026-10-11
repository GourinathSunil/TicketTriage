"""
Evaluation and diagnostic plotting module for TicketTriage multi-label models.
Computes Hamming loss, micro/macro/weighted F1, subset accuracy, per-label metrics,
rare vs common frequency breakdown, inference latency benchmarks, comparison tables,
and saves diagnostic plots.
"""
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    hamming_loss,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    precision_recall_curve,
    average_precision_score,
)


def evaluate_model_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_probs: np.ndarray,
    label_names: List[str],
    train_time_sec: float = 0.0,
    model_name: str = "model",
) -> Dict[str, Any]:
    """Computes comprehensive multi-label evaluation metrics."""
    # Global metrics
    h_loss = float(hamming_loss(y_true, y_pred))
    sub_acc = float(accuracy_score(y_true, y_pred))
    micro_f1 = float(f1_score(y_true, y_pred, average="micro", zero_division=0))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

    # Per-label metrics
    per_label = {}
    supports = y_true.sum(axis=0)
    total_samples = len(y_true)

    for idx, name in enumerate(label_names):
        p = float(precision_score(y_true[:, idx], y_pred[:, idx], zero_division=0))
        r = float(recall_score(y_true[:, idx], y_pred[:, idx], zero_division=0))
        f1 = float(f1_score(y_true[:, idx], y_pred[:, idx], zero_division=0))
        sup = int(supports[idx])
        per_label[name] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "support": sup,
            "frequency_pct": round((sup / total_samples) * 100, 2),
        }

    # Rare vs common labels breakdown
    # Rare defined as bottom 30% by support (e.g. security, data-export-deletion, outage)
    median_support = np.median(supports)
    rare_labels = [name for idx, name in enumerate(label_names) if supports[idx] <= median_support]
    common_labels = [name for idx, name in enumerate(label_names) if supports[idx] > median_support]

    rare_f1s = [per_label[lbl]["f1"] for lbl in rare_labels]
    common_f1s = [per_label[lbl]["f1"] for lbl in common_labels]

    rare_macro_f1 = float(np.mean(rare_f1s)) if rare_f1s else 0.0
    common_macro_f1 = float(np.mean(common_f1s)) if common_f1s else 0.0

    return {
        "model_name": model_name,
        "hamming_loss": round(h_loss, 4),
        "subset_accuracy": round(sub_acc, 4),
        "micro_f1": round(micro_f1, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "rare_macro_f1": round(rare_macro_f1, 4),
        "common_macro_f1": round(common_macro_f1, 4),
        "train_time_sec": round(train_time_sec, 2),
        "per_label": per_label,
        "rare_labels": rare_labels,
        "common_labels": common_labels,
    }


def benchmark_inference_latency(
    model,
    x_sample,
    n_runs: int = 100,
) -> Dict[str, float]:
    """Measures single-sample inference latency (p50, p95, mean) in milliseconds."""
    # Warm-up
    for _ in range(5):
        _ = model.predict_proba(x_sample[:1])

    latencies = []
    sample = x_sample[:1]
    for _ in range(n_runs):
        t0 = time.perf_counter()
        _ = model.predict_proba(sample)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    latencies_arr = np.array(latencies)
    return {
        "latency_mean_ms": round(float(np.mean(latencies_arr)), 3),
        "latency_p50_ms": round(float(np.percentile(latencies_arr, 50)), 3),
        "latency_p95_ms": round(float(np.percentile(latencies_arr, 95)), 3),
    }


def create_comparison_tables(
    models_metrics: List[Dict[str, Any]],
    output_csv_path: Path,
    output_md_path: Path,
) -> pd.DataFrame:
    """Generates comparison table across evaluated models."""
    rows = []
    for m in models_metrics:
        rows.append({
            "Model": m["model_name"],
            "Micro F1": m["micro_f1"],
            "Macro F1": m["macro_f1"],
            "Weighted F1": m["weighted_f1"],
            "Subset Accuracy": m["subset_accuracy"],
            "Hamming Loss": m["hamming_loss"],
            "Rare Labels F1": m["rare_macro_f1"],
            "Common Labels F1": m["common_macro_f1"],
            "Train Time (s)": m["train_time_sec"],
            "Latency p50 (ms)": m.get("latency_p50_ms", 0.0),
            "Latency p95 (ms)": m.get("latency_p95_ms", 0.0),
        })

    df = pd.DataFrame(rows)
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv_path, index=False)

    try:
        table_str = df.to_markdown(index=False)
    except Exception:
        headers = list(df.columns)
        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for _, row in df.iterrows():
            lines.append("| " + " | ".join(str(val) for val in row) + " |")
        table_str = "\n".join(lines)

    md_content = "# Model Comparison Results\n\n" + table_str
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return df


def generate_evaluation_plots(
    y_true: np.ndarray,
    y_probs: np.ndarray,
    label_names: List[str],
    per_label_metrics: Dict[str, Dict[str, float]],
    plots_dir: Path,
) -> None:
    """Generates per-label F1 plot, label co-occurrence heatmap, and rare PR curves."""
    plots_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    # 1. Per-label F1 Bar Chart
    fig, ax = plt.subplots(figsize=(10, 6))
    f1_values = [per_label_metrics[lbl]["f1"] for lbl in label_names]
    supports = [per_label_metrics[lbl]["support"] for lbl in label_names]
    sorted_indices = np.argsort(f1_values)[::-1]
    sorted_labels = [label_names[i] for i in sorted_indices]
    sorted_f1s = [f1_values[i] for i in sorted_indices]
    sorted_supports = [supports[i] for i in sorted_indices]

    palette = sns.color_palette("mako", len(sorted_labels))
    bars = ax.barh(sorted_labels, sorted_f1s, color=palette)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("F1-Score")
    ax.set_title("Per-Label F1 Performance (Held-out Test Set)", fontsize=14, fontweight="bold")

    for bar, sup in zip(bars, sorted_supports):
        width = bar.get_width()
        ax.text(
            width + 0.02,
            bar.get_y() + bar.get_height() / 2,
            f"{width:.3f} (n={sup})",
            va="center",
            fontsize=9,
        )

    plt.tight_layout()
    f1_plot_path = plots_dir / "per_label_f1.png"
    plt.savefig(f1_plot_path, dpi=200)
    plt.close()

    # 2. Label Co-occurrence Heatmap
    fig, ax = plt.subplots(figsize=(9, 8))
    cooccur = np.dot(y_true.T, y_true)
    # Normalize by diagonal to see correlation / conditional co-occurrence
    diag = np.diag(cooccur).astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        norm_cooccur = cooccur / np.sqrt(np.outer(diag, diag))
        np.nan_to_num(norm_cooccur, copy=False)

    sns.heatmap(
        norm_cooccur,
        xticklabels=label_names,
        yticklabels=label_names,
        annot=True,
        fmt=".2f",
        cmap="Blues",
        ax=ax,
    )
    ax.set_title("Label Co-occurrence Correlation Matrix", fontsize=14, fontweight="bold")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    cooccur_plot_path = plots_dir / "label_cooccurrence_heatmap.png"
    plt.savefig(cooccur_plot_path, dpi=200)
    plt.close()

    # 3. Precision-Recall Curves for Rare Labels
    supports_arr = y_true.sum(axis=0)
    median_sup = np.median(supports_arr)
    rare_indices = [i for i, s in enumerate(supports_arr) if s <= median_sup]

    fig, ax = plt.subplots(figsize=(8, 6))
    for idx in rare_indices:
        lbl = label_names[idx]
        prec, rec, _ = precision_recall_curve(y_true[:, idx], y_probs[:, idx])
        ap = average_precision_score(y_true[:, idx], y_probs[:, idx])
        ax.plot(rec, prec, lw=2, label=f"{lbl} (AP={ap:.3f}, n={int(supports_arr[idx])})")

    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_ylim([0.0, 1.05])
    ax.set_xlim([0.0, 1.0])
    ax.set_title("Precision-Recall Curves for Low-Frequency (Rare) Labels", fontsize=13, fontweight="bold")
    ax.legend(loc="lower left", fontsize=9)
    plt.tight_layout()
    pr_plot_path = plots_dir / "pr_curves_rare_labels.png"
    plt.savefig(pr_plot_path, dpi=200)
    plt.close()

    print(f"Generated diagnostic plots in {plots_dir}")
