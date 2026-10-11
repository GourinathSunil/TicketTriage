"""
Pydantic schemas for TicketTriage API.
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class DomainTeamInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""


class DomainLabelInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    team: str
    color: str


class DomainPriorityInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    rank: int
    color: str
    first_response_minutes: int
    resolution_minutes: int
    always_24x7: bool


class DomainCustomerTierInfo(BaseModel):
    id: str
    name: str
    deadline_multiplier: float
    priority_bump: int


class ConfigResponse(BaseModel):
    domain: str
    display_name: str
    description: str
    labels: List[DomainLabelInfo]
    teams: List[DomainTeamInfo]
    priorities: List[DomainPriorityInfo]
    customer_tiers: List[DomainCustomerTierInfo]


class PredictRequest(BaseModel):
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    customer_tier: Optional[str] = "free"


class SLAOutput(BaseModel):
    priority: str
    priority_rank: int
    priority_name: str
    priority_color: str
    primary_team: str
    teams: List[str]
    first_response_due: str
    resolution_due: str
    first_response_minutes: int
    resolution_minutes: int
    sla_status: str
    first_response_status: str
    resolution_status: str
    needs_human_review: bool
    reasons: List[str]


class PredictResponse(BaseModel):
    predicted_labels: List[str]
    label_probabilities: Dict[str, float]
    sla: SLAOutput


class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    customer_tier: Optional[str] = "free"
    created_at: Optional[str] = None


class TicketPatch(BaseModel):
    corrected_labels: Optional[List[str]] = None
    is_responded: Optional[bool] = None
    is_resolved: Optional[bool] = None
    agent_notes: Optional[str] = None


class TicketResponse(BaseModel):
    id: str
    domain: str
    subject: str
    body: str
    customer_tier: str
    created_at: str
    predicted_labels: List[str]
    corrected_labels: Optional[List[str]] = None
    effective_labels: List[str]
    label_probabilities: Dict[str, float]
    needs_human_review: bool
    priority: str
    priority_rank: int
    primary_team: str
    assigned_teams: List[str]
    first_response_due: str
    resolution_due: str
    first_response_minutes: int
    resolution_minutes: int
    sla_status: str
    first_response_status: str
    resolution_status: str
    reasons: List[str]
    is_responded: bool
    responded_at: Optional[str] = None
    is_resolved: bool
    resolved_at: Optional[str] = None


class TicketListResponse(BaseModel):
    total: int
    tickets: List[TicketResponse]


class ModelEvaluationSummary(BaseModel):
    best_model_name: str
    micro_f1: float
    macro_f1: float
    subset_accuracy: float
    hamming_loss: float
    rare_macro_f1: float
    common_macro_f1: float
    latency_p50_ms: float
    per_label: Dict[str, Any]


class SLAMetricsSummary(BaseModel):
    total_tickets: int
    active_tickets: int
    responded_tickets: int
    resolved_tickets: int
    needs_review_count: int
    breached_count: int
    at_risk_count: int
    on_track_count: int
    breach_rate_pct: float
    by_priority: Dict[str, int]
    by_team: Dict[str, int]
    by_label: Dict[str, int]


class MetricsResponse(BaseModel):
    domain: str
    model_metrics: Optional[Dict[str, Any]] = None
    model_comparison: Optional[List[Dict[str, Any]]] = None
    sla_metrics: SLAMetricsSummary
