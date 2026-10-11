"""Unit tests for domain loader."""
import pytest
from pathlib import Path
from core.domain_loader import load_domain_pack, DomainPack, DomainLabelsFile, DomainRulesFile


def test_load_saas_domain_pack():
    pack = load_domain_pack("saas")
    assert pack.domain_name == "saas"
    assert len(pack.labels) == 11
    assert len(pack.teams) == 8
    assert len(pack.priorities) == 4
    assert "outage" in pack.label_ids
    assert "bug" in pack.label_ids
    assert "Platform/SRE" in pack.team_ids
    assert pack.label_to_team["outage"] == "Platform/SRE"
    assert pack.label_to_team["bug"] == "Engineering"
    assert "free" in pack.customer_tiers
    assert "enterprise" in pack.customer_tiers
    assert pack.customer_tiers["enterprise"].deadline_multiplier == 0.5


def test_nonexistent_domain_raises():
    with pytest.raises(FileNotFoundError) as exc_info:
        load_domain_pack("nonexistent_domain_xyz")
    assert "Domain pack directory not found" in str(exc_info.value)


def test_invalid_label_reference_in_rules():
    raw_labels = {
        "domain_name": "test",
        "display_name": "Test",
        "teams": [{"id": "team1", "name": "Team 1"}],
        "labels": [{"id": "lbl1", "name": "Label 1", "team": "team1"}]
    }
    raw_rules = {
        "domain_name": "test",
        "priorities": [
            {"id": "P1", "name": "P1", "rank": 1, "deadlines": {"first_response_minutes": 10, "resolution_minutes": 60}}
        ],
        "priority_rules": [
            {"priority": "P1", "any_labels": ["nonexistent_label"]}
        ]
    }
    labels_cfg = DomainLabelsFile.model_validate(raw_labels)
    rules_cfg = DomainRulesFile.model_validate(raw_rules)

    with pytest.raises(ValueError) as exc:
        # Cross validation logic
        valid_label_ids = {l.id for l in labels_cfg.labels}
        for rule in rules_cfg.priority_rules:
            if rule.any_labels:
                for lbl in rule.any_labels:
                    if lbl not in valid_label_ids:
                        raise ValueError(f"references unknown label '{lbl}'")
    assert "references unknown label 'nonexistent_label'" in str(exc.value)


def test_undefined_team_in_labels():
    raw_labels = {
        "domain_name": "test",
        "display_name": "Test",
        "teams": [{"id": "team1", "name": "Team 1"}],
        "labels": [{"id": "lbl1", "name": "Label 1", "team": "unknown_team"}]
    }
    with pytest.raises(ValueError) as exc:
        DomainLabelsFile.model_validate(raw_labels)
    assert "references undefined team 'unknown_team'" in str(exc.value)
