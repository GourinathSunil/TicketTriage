"""Data loading utilities for TicketTriage."""
from pathlib import Path
from typing import List, Optional
import pandas as pd
from core.domain_loader import load_domain_pack


REQUIRED_COLUMNS = ["id", "subject", "body", "customer_tier", "created_at", "labels"]


def load_tickets_csv(file_path: Path, domain_name: Optional[str] = None) -> pd.DataFrame:
    """
    Loads tickets CSV, validates required columns and domain labels.
    Returns DataFrame with 'labels_list' parsed as List[str].
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Tickets dataset not found at {file_path}")

    df = pd.read_csv(file_path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV {file_path} is missing required columns: {missing}")

    # Fill any null values
    df["subject"] = df["subject"].fillna("").astype(str)
    df["body"] = df["body"].fillna("").astype(str)
    df["customer_tier"] = df["customer_tier"].fillna("free").astype(str)
    df["labels"] = df["labels"].fillna("").astype(str)

    # Parse pipe-separated labels
    df["labels_list"] = df["labels"].apply(
        lambda x: [item.strip() for item in x.split("|") if item.strip()]
    )

    # Validate against domain pack if available
    pack = load_domain_pack(domain_name)
    valid_labels = set(pack.label_ids)

    # Check for any unexpected labels
    all_assigned = {lbl for sublist in df["labels_list"] for lbl in sublist}
    invalid_labels = all_assigned - valid_labels
    if invalid_labels:
        raise ValueError(
            f"Dataset contains labels not defined in domain '{pack.domain_name}': {sorted(list(invalid_labels))}"
        )

    return df
