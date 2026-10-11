"""Tests for data generation and loading."""
from pathlib import Path
import pytest
from data.loader import load_tickets_csv
from data.generate_synthetic import generate_dataset


def test_generate_and_load_dataset(tmp_path):
    output_file = tmp_path / "test_tickets.csv"
    generate_dataset("saas", count=200, output_path=output_file, seed=123)

    assert output_file.exists()
    df = load_tickets_csv(output_file, domain_name="saas")
    assert len(df) == 200
    assert "labels_list" in df.columns
    assert all(isinstance(lbls, list) and len(lbls) > 0 for lbls in df["labels_list"])
    assert set(df.columns).issuperset({"id", "subject", "body", "customer_tier", "created_at", "labels"})
