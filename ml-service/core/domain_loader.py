"""Domain loader: reads DOMAIN env var, validates pack schemas, and provides domain metadata."""
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
from pydantic import BaseModel, Field, model_validator


class TeamConfig(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""


class LabelConfig(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    team: str
    color: Optional[str] = "#3B82F6"


class PriorityDeadlines(BaseModel):
    first_response_minutes: int = Field(gt=0)
    resolution_minutes: int = Field(gt=0)


class PriorityConfig(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    rank: int = Field(gt=0)  # 1 is highest priority
    deadlines: PriorityDeadlines
    color: Optional[str] = "#3B82F6"
    always_24x7: bool = False


class PriorityRule(BaseModel):
    priority: str
    description: Optional[str] = ""
    any_labels: Optional[List[str]] = None
    all_labels: Optional[List[str]] = None
    keywords_any: Optional[List[str]] = None


class CustomerTierConfig(BaseModel):
    name: str
    deadline_multiplier: float = Field(gt=0.0)
    priority_bump: int = 0
    priority_bump_labels: Optional[List[str]] = None


class BusinessHoursConfig(BaseModel):
    enabled: bool = False
    timezone: str = "UTC"
    work_start_hour: int = 9
    work_end_hour: int = 17
    workdays: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])


class SLAThresholdsConfig(BaseModel):
    at_risk_percentage: float = 0.70
    confidence_gate_margin: float = 0.10


class DomainLabelsFile(BaseModel):
    domain_name: str
    display_name: str
    description: Optional[str] = ""
    teams: List[TeamConfig]
    labels: List[LabelConfig]

    @model_validator(mode="after")
    def validate_teams_and_labels(self):
        team_ids = {t.id for t in self.teams}
        if len(team_ids) != len(self.teams):
            raise ValueError("Duplicate team ID found in teams list")
        
        label_ids = set()
        for label in self.labels:
            if label.id in label_ids:
                raise ValueError(f"Duplicate label ID: '{label.id}'")
            label_ids.add(label.id)
            if label.team not in team_ids:
                raise ValueError(
                    f"Label '{label.id}' references undefined team '{label.team}'. "
                    f"Available teams: {sorted(list(team_ids))}"
                )
        return self


class DomainRulesFile(BaseModel):
    domain_name: str
    priorities: List[PriorityConfig]
    priority_rules: List[PriorityRule]
    customer_tiers: Dict[str, CustomerTierConfig] = Field(default_factory=dict)
    business_hours: BusinessHoursConfig = Field(default_factory=BusinessHoursConfig)
    sla_status_thresholds: SLAThresholdsConfig = Field(default_factory=SLAThresholdsConfig)

    @model_validator(mode="after")
    def validate_rules(self):
        priority_ids = {p.id for p in self.priorities}
        if len(priority_ids) != len(self.priorities):
            raise ValueError("Duplicate priority ID in priorities list")
        
        # Validate rules reference existing priorities
        for rule in self.priority_rules:
            if rule.priority not in priority_ids:
                raise ValueError(
                    f"Priority rule references unknown priority '{rule.priority}'. "
                    f"Available priorities: {sorted(list(priority_ids))}"
                )
            if not rule.any_labels and not rule.all_labels:
                raise ValueError(f"Priority rule for '{rule.priority}' must specify at least one of any_labels or all_labels")
        return self


class DomainPack(BaseModel):
    domain_name: str
    display_name: str
    description: str
    teams: List[TeamConfig]
    labels: List[LabelConfig]
    priorities: List[PriorityConfig]
    priority_rules: List[PriorityRule]
    customer_tiers: Dict[str, CustomerTierConfig]
    business_hours: BusinessHoursConfig
    sla_status_thresholds: SLAThresholdsConfig
    pack_dir: Path

    @property
    def label_ids(self) -> List[str]:
        return [l.id for l in self.labels]

    @property
    def team_ids(self) -> List[str]:
        return [t.id for t in self.teams]

    @property
    def label_to_team(self) -> Dict[str, str]:
        return {l.id: l.team for l in self.labels}

    @property
    def priority_by_id(self) -> Dict[str, PriorityConfig]:
        return {p.id: p for p in self.priorities}


def get_domains_root_dir() -> Path:
    """Finds the domains directory relative to ml-service."""
    # Try relative to this file
    current_dir = Path(__file__).resolve().parent
    # ml-service/core -> ml-service/domains
    domains_dir = current_dir.parent / "domains"
    if domains_dir.exists():
        return domains_dir
    # fallback to workspace root
    cwd_candidate = Path.cwd() / "ml-service" / "domains"
    if cwd_candidate.exists():
        return cwd_candidate
    return domains_dir


def load_domain_pack(domain_name: Optional[str] = None) -> DomainPack:
    """
    Loads and validates a domain pack from domains/<DOMAIN>/.
    Defaults to the DOMAIN environment variable, or 'saas'.
    Fails fast with clear descriptive errors.
    """
    if domain_name is None:
        domain_name = os.getenv("DOMAIN", "saas").strip().lower()

    domains_root = get_domains_root_dir()
    pack_dir = domains_root / domain_name

    if not pack_dir.exists():
        available = [p.name for p in domains_root.iterdir() if p.is_dir() and not p.name.startswith("_")] if domains_root.exists() else []
        raise FileNotFoundError(
            f"Domain pack directory not found for domain '{domain_name}' at {pack_dir}. "
            f"Available domains: {available}"
        )

    labels_file = pack_dir / "labels.yaml"
    rules_file = pack_dir / "rules.yaml"

    if not labels_file.exists():
        raise FileNotFoundError(f"Missing required labels.yaml in domain pack {pack_dir}")
    if not rules_file.exists():
        raise FileNotFoundError(f"Missing required rules.yaml in domain pack {pack_dir}")

    try:
        with open(labels_file, "r", encoding="utf-8") as f:
            labels_raw = yaml.safe_load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse {labels_file} as YAML: {e}") from e

    try:
        with open(rules_file, "r", encoding="utf-8") as f:
            rules_raw = yaml.safe_load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse {rules_file} as YAML: {e}") from e

    # Validate individual files
    labels_config = DomainLabelsFile.model_validate(labels_raw)
    rules_config = DomainRulesFile.model_validate(rules_raw)

    # Cross-validation: every label in rules.yaml must exist in labels.yaml
    valid_label_ids = {l.id for l in labels_config.labels}
    for rule in rules_config.priority_rules:
        if rule.any_labels:
            for lbl in rule.any_labels:
                if lbl not in valid_label_ids:
                    raise ValueError(
                        f"Cross-validation error in rules.yaml: rule '{rule.description or rule.priority}' "
                        f"references unknown label '{lbl}'. Valid labels are: {sorted(list(valid_label_ids))}"
                    )
        if rule.all_labels:
            for lbl in rule.all_labels:
                if lbl not in valid_label_ids:
                    raise ValueError(
                        f"Cross-validation error in rules.yaml: rule '{rule.description or rule.priority}' "
                        f"references unknown label '{lbl}'. Valid labels are: {sorted(list(valid_label_ids))}"
                    )

    # Validate tier priority_bump_labels if any
    for tier_id, tier in rules_config.customer_tiers.items():
        if tier.priority_bump_labels:
            for lbl in tier.priority_bump_labels:
                if lbl not in valid_label_ids:
                    raise ValueError(
                        f"Customer tier '{tier_id}' references unknown priority_bump_label '{lbl}'"
                    )

    return DomainPack(
        domain_name=labels_config.domain_name,
        display_name=labels_config.display_name,
        description=labels_config.description or "",
        teams=labels_config.teams,
        labels=labels_config.labels,
        priorities=rules_config.priorities,
        priority_rules=rules_config.priority_rules,
        customer_tiers=rules_config.customer_tiers,
        business_hours=rules_config.business_hours,
        sla_status_thresholds=rules_config.sla_status_thresholds,
        pack_dir=pack_dir,
    )
