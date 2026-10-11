"""
FastAPI service for TicketTriage.
Provides endpoints for configuration, prediction, ticket CRUD, SLA tracking, and metrics.
Completely driven by domain pack and DOMAIN env var.
"""
import datetime
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Add ml-service to path
current_dir = Path(__file__).resolve().parent
ml_service_dir = current_dir.parent
if str(ml_service_dir) not in sys.path:
    sys.path.insert(0, str(ml_service_dir))

from core.domain_loader import load_domain_pack, DomainPack
from sla.engine import SLAEngine
from api.db import init_db, get_db, TicketModel, FeedbackModel
from api.schemas import (
    ConfigResponse,
    DomainLabelInfo,
    DomainTeamInfo,
    DomainPriorityInfo,
    DomainCustomerTierInfo,
    PredictRequest,
    PredictResponse,
    SLAOutput,
    TicketCreate,
    TicketPatch,
    TicketResponse,
    TicketListResponse,
    MetricsResponse,
    SLAMetricsSummary,
)

app = FastAPI(
    title="TicketTriage API",
    description="Domain-configurable multi-label ticket classifier with SLA routing engine",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ModelPredictor:
    """Manages loaded ML model, vectorizer, MLB, and thresholds for active domain."""

    def __init__(self, domain_name: str, domain_pack: DomainPack):
        self.domain_name = domain_name
        self.pack = domain_pack
        self.model = None
        self.vectorizer = None
        self.mlb = None
        self.thresholds = {lbl: 0.50 for lbl in self.pack.label_ids}
        self.loaded = False
        self.load_artifacts()

    def load_artifacts(self):
        models_dir = self.pack.pack_dir.parent.parent / "models" / self.domain_name
        model_file = models_dir / "model.joblib"
        vec_file = models_dir / "vectorizer.joblib"
        mlb_file = models_dir / "mlb.joblib"
        thresh_file = models_dir / "thresholds.json"

        if model_file.exists() and vec_file.exists() and mlb_file.exists():
            try:
                self.model = joblib.load(model_file)
                self.vectorizer = joblib.load(vec_file)
                self.mlb = joblib.load(mlb_file)
                if thresh_file.exists():
                    with open(thresh_file, "r", encoding="utf-8") as f:
                        t_data = json.load(f)
                    self.thresholds = {
                        k: v["threshold"] if isinstance(v, dict) else float(v)
                        for k, v in t_data.items()
                    }
                self.loaded = True
                print(f"[ModelPredictor] Successfully loaded model artifacts for domain '{self.domain_name}'")
            except Exception as e:
                print(f"[ModelPredictor] Error loading model artifacts: {e}")
                self.loaded = False
        else:
            print(f"[ModelPredictor] Artifacts not found at {models_dir}; using rule-based fallback predictor.")
            self.loaded = False

    def predict(self, subject: str, body: str) -> Tuple[List[str], Dict[str, float]]:
        combined_text = f"{subject} {subject} {body}".strip()
        probabilities: Dict[str, float] = {}

        if self.loaded and self.model and self.vectorizer:
            x_vec = self.vectorizer.transform([combined_text])
            if hasattr(self.model, "predict_proba"):
                probs_raw = self.model.predict_proba(x_vec)
                if isinstance(probs_raw, list):
                    for j, lbl in enumerate(self.pack.label_ids):
                        p = probs_raw[j]
                        val = float(p[0, 1]) if p.shape[1] == 2 else float(p[0, 0])
                        probabilities[lbl] = round(val, 4)
                elif isinstance(probs_raw, np.ndarray) and probs_raw.ndim == 2:
                    for j, lbl in enumerate(self.pack.label_ids):
                        probabilities[lbl] = round(float(probs_raw[0, j]), 4)
            else:
                preds = self.model.predict(x_vec)
                for j, lbl in enumerate(self.pack.label_ids):
                    probabilities[lbl] = 1.0 if preds[0, j] == 1 else 0.0

            predicted_labels = [
                lbl for lbl, prob in probabilities.items()
                if prob >= self.thresholds.get(lbl, 0.50)
            ]
            return predicted_labels, probabilities

        # Heuristic / Keyword Fallback when model is not yet saved to disk
        text_lower = combined_text.lower()
        keyword_maps = {
            "outage": ["outage", "down", "500", "502", "503", "unreachable", "crash", "incident"],
            "security": ["security", "vulnerability", "breach", "unauthorized", "idor", "cve"],
            "performance": ["latency", "slow", "timeout", "degraded", "5000ms", "lag"],
            "billing": ["invoice", "charge", "charged", "card", "payment", "subscription", "billed"],
            "refund-request": ["refund", "money back", "cancel subscription", "credit"],
            "account-access": ["locked out", "login", "password", "sso", "mfa", "saml", "auth"],
            "integration-issue": ["api", "webhook", "endpoint", "rate limit", "zapier", "oauth"],
            "bug": ["bug", "error", "broken", "glitch", "typeerror", "exception", "defect"],
            "data-export-deletion": ["gdpr", "erasure", "deletion", "dump", "export data", "ccpa"],
            "feature-request": ["feature", "request", "suggestion", "dark mode", "enhancement"],
            "how-to-question": ["how to", "guide", "documentation", "how do i", "help with"],
        }
        predicted_labels = []
        for lbl in self.pack.label_ids:
            keywords = keyword_maps.get(lbl, [lbl])
            matches = sum(1 for kw in keywords if kw in text_lower)
            prob = min(0.95, 0.15 + 0.35 * matches) if matches > 0 else 0.08
            probabilities[lbl] = round(prob, 4)
            if prob >= 0.45:
                predicted_labels.append(lbl)

        return predicted_labels, probabilities


# Active domain setup
active_domain = os.getenv("DOMAIN", "saas").strip().lower()
pack: DomainPack = load_domain_pack(active_domain)
sla_engine = SLAEngine(domain_pack=pack)
predictor = ModelPredictor(active_domain, pack)


# Ensure tables exist on load
init_db()

@app.on_event("startup")
def startup_event():
    init_db()
    # Check if we should seed default tickets if empty
    db = next(get_db())
    try:
        count = db.query(TicketModel).filter(TicketModel.domain == active_domain).count()
        if count == 0:
            seed_sample_tickets(db, count=50)
    finally:
        db.close()


def seed_sample_tickets(db: Session, count: int = 50):
    """Populates initial sample tickets for instant dashboard visualization."""
    dataset_file = pack.pack_dir.parent.parent / "data" / f"tickets_{active_domain}.csv"
    if dataset_file.exists():
        df = pd.read_csv(dataset_file).head(count)
        now = datetime.datetime.now(datetime.timezone.utc)
        for _, row in df.iterrows():
            sub = str(row["subject"])
            bod = str(row["body"])
            tier = str(row.get("customer_tier", "free"))
            created_str = str(row.get("created_at", now.isoformat()))
            parsed_created = sla_engine._parse_datetime(created_str)

            # Predict & apply SLA
            preds, probs = predictor.predict(sub, bod)
            sla_res = sla_engine.apply_sla(
                labels=preds,
                probabilities=probs,
                created_at=parsed_created,
                customer_tier=tier,
                ticket_text=f"{sub} {bod}",
                thresholds=predictor.thresholds,
            )

            # Assign some responded / resolved states based on age
            age_hours = (now - parsed_created).total_seconds() / 3600.0
            is_responded = age_hours > 2.0
            is_resolved = age_hours > 8.0 and not sla_res["needs_human_review"]

            ticket = TicketModel(
                id=str(row["id"]),
                domain=active_domain,
                subject=sub,
                body=bod,
                customer_tier=tier,
                created_at=parsed_created,
                predicted_labels=json.dumps(preds),
                corrected_labels=None,
                label_probabilities=json.dumps(probs),
                needs_human_review=sla_res["needs_human_review"],
                priority=sla_res["priority"],
                priority_rank=sla_res["priority_rank"],
                primary_team=sla_res["primary_team"],
                assigned_teams=json.dumps(sla_res["teams"]),
                first_response_due=sla_engine._parse_datetime(sla_res["first_response_due"]),
                resolution_due=sla_engine._parse_datetime(sla_res["resolution_due"]),
                first_response_minutes=sla_res["first_response_minutes"],
                resolution_minutes=sla_res["resolution_minutes"],
                sla_status=sla_res["sla_status"],
                first_response_status=sla_res["first_response_status"],
                resolution_status=sla_res["resolution_status"],
                reasons=json.dumps(sla_res["reasons"]),
                is_responded=is_responded,
                responded_at=parsed_created + datetime.timedelta(minutes=30) if is_responded else None,
                is_resolved=is_resolved,
                resolved_at=parsed_created + datetime.timedelta(hours=4) if is_resolved else None,
            )
            db.add(ticket)
        db.commit()
        print(f"[Seed] Successfully seeded {len(df)} initial tickets into SQLite")


@app.get("/health")
def get_health():
    # Reload model if it just became available
    if not predictor.loaded:
        predictor.load_artifacts()

    return {
        "status": "ok",
        "domain": active_domain,
        "model_loaded": predictor.loaded,
        "total_labels": len(pack.labels),
        "total_teams": len(pack.teams),
    }


@app.get("/config", response_model=ConfigResponse)
def get_config():
    """Returns domain configuration dynamically for frontend rendering."""
    labels_info = [
        DomainLabelInfo(
            id=l.id,
            name=l.name,
            description=l.description or "",
            team=l.team,
            color=l.color or "#3B82F6",
        )
        for l in pack.labels
    ]
    teams_info = [
        DomainTeamInfo(
            id=t.id,
            name=t.name,
            description=t.description or "",
        )
        for t in pack.teams
    ]
    priorities_info = [
        DomainPriorityInfo(
            id=p.id,
            name=p.name,
            description=p.description or "",
            rank=p.rank,
            color=p.color or "#3B82F6",
            first_response_minutes=p.deadlines.first_response_minutes,
            resolution_minutes=p.deadlines.resolution_minutes,
            always_24x7=p.always_24x7,
        )
        for p in pack.priorities
    ]
    tiers_info = [
        DomainCustomerTierInfo(
            id=tier_id,
            name=tier_cfg.name,
            deadline_multiplier=tier_cfg.deadline_multiplier,
            priority_bump=tier_cfg.priority_bump,
        )
        for tier_id, tier_cfg in pack.customer_tiers.items()
    ]

    return ConfigResponse(
        domain=pack.domain_name,
        display_name=pack.display_name,
        description=pack.description,
        labels=labels_info,
        teams=teams_info,
        priorities=priorities_info,
        customer_tiers=tiers_info,
    )


@app.post("/predict", response_model=PredictResponse)
def predict_endpoint(payload: PredictRequest):
    """Predicts labels and evaluates SLA without creating a ticket record."""
    if not predictor.loaded:
        predictor.load_artifacts()

    preds, probs = predictor.predict(payload.subject, payload.body)
    now = datetime.datetime.now(datetime.timezone.utc)
    sla_res = sla_engine.apply_sla(
        labels=preds,
        probabilities=probs,
        created_at=now,
        customer_tier=payload.customer_tier or "free",
        ticket_text=f"{payload.subject} {payload.body}",
        thresholds=predictor.thresholds,
    )

    return PredictResponse(
        predicted_labels=preds,
        label_probabilities=probs,
        sla=SLAOutput(**sla_res),
    )


@app.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    """Creates a new ticket, executes ML prediction & SLA rules, and persists to DB."""
    if not predictor.loaded:
        predictor.load_artifacts()

    ticket_id = f"TICK-{active_domain.upper()}-{uuid.uuid4().hex[:6].upper()}"
    created_dt = sla_engine._parse_datetime(payload.created_at) if payload.created_at else datetime.datetime.now(datetime.timezone.utc)

    preds, probs = predictor.predict(payload.subject, payload.body)
    sla_res = sla_engine.apply_sla(
        labels=preds,
        probabilities=probs,
        created_at=created_dt,
        customer_tier=payload.customer_tier or "free",
        ticket_text=f"{payload.subject} {payload.body}",
        thresholds=predictor.thresholds,
    )

    ticket = TicketModel(
        id=ticket_id,
        domain=active_domain,
        subject=payload.subject,
        body=payload.body,
        customer_tier=payload.customer_tier or "free",
        created_at=created_dt,
        predicted_labels=json.dumps(preds),
        corrected_labels=None,
        label_probabilities=json.dumps(probs),
        needs_human_review=sla_res["needs_human_review"],
        priority=sla_res["priority"],
        priority_rank=sla_res["priority_rank"],
        primary_team=sla_res["primary_team"],
        assigned_teams=json.dumps(sla_res["teams"]),
        first_response_due=sla_engine._parse_datetime(sla_res["first_response_due"]),
        resolution_due=sla_engine._parse_datetime(sla_res["resolution_due"]),
        first_response_minutes=sla_res["first_response_minutes"],
        resolution_minutes=sla_res["resolution_minutes"],
        sla_status=sla_res["sla_status"],
        first_response_status=sla_res["first_response_status"],
        resolution_status=sla_res["resolution_status"],
        reasons=json.dumps(sla_res["reasons"]),
        is_responded=False,
        is_resolved=False,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return TicketResponse(**ticket.to_dict())


@app.get("/tickets", response_model=TicketListResponse)
def list_tickets(
    label: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    sla_status: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    needs_human_review: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Lists tickets with filters.
    Sorted by priority rank (highest priority first) then first_response_due date.
    """
    query = db.query(TicketModel).filter(TicketModel.domain == active_domain)

    if priority:
        query = query.filter(TicketModel.priority == priority)
    if team:
        query = query.filter(TicketModel.primary_team == team)
    if sla_status:
        query = query.filter(TicketModel.sla_status == sla_status)
    if tier:
        query = query.filter(TicketModel.customer_tier == tier)
    if needs_human_review is not None:
        query = query.filter(TicketModel.needs_human_review == needs_human_review)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (TicketModel.subject.ilike(search_pattern)) | (TicketModel.body.ilike(search_pattern))
        )

    # Order by priority_rank ASC (P1=1, P2=2...), then first_response_due ASC
    query = query.order_by(TicketModel.priority_rank.asc(), TicketModel.first_response_due.asc())
    tickets = query.all()

    # Re-evaluate live SLA status dynamically for active tickets
    now = datetime.datetime.now(datetime.timezone.utc)
    res_list = []
    for t in tickets:
        d = t.to_dict()
        if not t.is_resolved:
            # Refresh live status
            live_resp_status = sla_engine.determine_status(
                t.created_at.replace(tzinfo=datetime.timezone.utc) if t.created_at.tzinfo is None else t.created_at,
                t.first_response_due.replace(tzinfo=datetime.timezone.utc) if t.first_response_due.tzinfo is None else t.first_response_due,
                now,
                is_completed=t.is_responded,
            )
            live_resol_status = sla_engine.determine_status(
                t.created_at.replace(tzinfo=datetime.timezone.utc) if t.created_at.tzinfo is None else t.created_at,
                t.resolution_due.replace(tzinfo=datetime.timezone.utc) if t.resolution_due.tzinfo is None else t.resolution_due,
                now,
                is_completed=t.is_resolved,
            )
            d["first_response_status"] = live_resp_status
            d["resolution_status"] = live_resol_status
            d["sla_status"] = "breached" if (live_resp_status == "breached" or live_resol_status == "breached") else (
                "at_risk" if (live_resp_status == "at_risk" or live_resol_status == "at_risk") else "on_track"
            )

        if label:
            # Filter in Python on effective_labels
            if label not in d["effective_labels"]:
                continue

        res_list.append(TicketResponse(**d))

    return TicketListResponse(total=len(res_list), tickets=res_list)


@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """Retrieves a single ticket by ID."""
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

    d = ticket.to_dict()
    now = datetime.datetime.now(datetime.timezone.utc)
    if not ticket.is_resolved:
        live_resp_status = sla_engine.determine_status(
            ticket.created_at.replace(tzinfo=datetime.timezone.utc) if ticket.created_at.tzinfo is None else ticket.created_at,
            ticket.first_response_due.replace(tzinfo=datetime.timezone.utc) if ticket.first_response_due.tzinfo is None else ticket.first_response_due,
            now,
            is_completed=ticket.is_responded,
        )
        live_resol_status = sla_engine.determine_status(
            ticket.created_at.replace(tzinfo=datetime.timezone.utc) if ticket.created_at.tzinfo is None else ticket.created_at,
            ticket.resolution_due.replace(tzinfo=datetime.timezone.utc) if ticket.resolution_due.tzinfo is None else ticket.resolution_due,
            now,
            is_completed=ticket.is_resolved,
        )
        d["first_response_status"] = live_resp_status
        d["resolution_status"] = live_resol_status
        d["sla_status"] = "breached" if (live_resp_status == "breached" or live_resol_status == "breached") else (
            "at_risk" if (live_resp_status == "at_risk" or live_resol_status == "at_risk") else "on_track"
        )

    return TicketResponse(**d)


@app.patch("/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket(ticket_id: str, patch: TicketPatch, db: Session = Depends(get_db)):
    """
    Updates ticket state:
    - If corrected_labels supplied, re-applies SLA engine, updates routing, and logs feedback table.
    - If is_responded or is_resolved modified, records timestamps.
    """
    ticket = db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. Corrected labels handling
    if patch.corrected_labels is not None:
        original = json.loads(ticket.corrected_labels) if ticket.corrected_labels else json.loads(ticket.predicted_labels or "[]")
        ticket.corrected_labels = json.dumps(patch.corrected_labels)

        # Log feedback
        feedback = FeedbackModel(
            ticket_id=ticket.id,
            original_labels=json.dumps(original),
            corrected_labels=json.dumps(patch.corrected_labels),
            agent_notes=patch.agent_notes,
            created_at=now,
        )
        db.add(feedback)

        # Re-apply SLA with corrected labels
        probs = json.loads(ticket.label_probabilities or "{}")
        created_dt = ticket.created_at.replace(tzinfo=datetime.timezone.utc) if ticket.created_at.tzinfo is None else ticket.created_at
        sla_res = sla_engine.apply_sla(
            labels=patch.corrected_labels,
            probabilities=probs,
            created_at=created_dt,
            customer_tier=ticket.customer_tier,
            ticket_text=f"{ticket.subject} {ticket.body}",
            is_first_responded=ticket.is_responded,
            is_resolved=ticket.is_resolved,
            thresholds=predictor.thresholds,
        )

        ticket.priority = sla_res["priority"]
        ticket.priority_rank = sla_res["priority_rank"]
        ticket.primary_team = sla_res["primary_team"]
        ticket.assigned_teams = json.dumps(sla_res["teams"])
        ticket.first_response_due = sla_engine._parse_datetime(sla_res["first_response_due"])
        ticket.resolution_due = sla_engine._parse_datetime(sla_res["resolution_due"])
        ticket.first_response_minutes = sla_res["first_response_minutes"]
        ticket.resolution_minutes = sla_res["resolution_minutes"]
        ticket.sla_status = sla_res["sla_status"]
        ticket.first_response_status = sla_res["first_response_status"]
        ticket.resolution_status = sla_res["resolution_status"]
        ticket.needs_human_review = False  # Human has reviewed & corrected
        reasons_list = json.loads(ticket.reasons or "[]")
        reasons_list.append(f"Agent corrected labels to: {patch.corrected_labels}")
        ticket.reasons = json.dumps(reasons_list)

    # 2. Responded flag
    if patch.is_responded is not None:
        ticket.is_responded = patch.is_responded
        if patch.is_responded and not ticket.responded_at:
            ticket.responded_at = now
            ticket.first_response_status = "on_track"

    # 3. Resolved flag
    if patch.is_resolved is not None:
        ticket.is_resolved = patch.is_resolved
        if patch.is_resolved:
            ticket.resolved_at = now
            ticket.sla_status = "on_track"
            ticket.resolution_status = "on_track"

    db.commit()
    db.refresh(ticket)
    return TicketResponse(**ticket.to_dict())


@app.get("/metrics", response_model=MetricsResponse)
def get_metrics(db: Session = Depends(get_db)):
    """Returns model benchmark comparison and live SLA statistics."""
    models_dir = pack.pack_dir.parent.parent / "models" / active_domain
    metrics_file = models_dir / "metrics.json"
    comparison_file = models_dir / "comparison.csv"

    model_metrics = None
    model_comparison = None

    if metrics_file.exists():
        try:
            with open(metrics_file, "r", encoding="utf-8") as f:
                model_metrics = json.load(f)
        except Exception:
            pass

    if comparison_file.exists():
        try:
            comp_df = pd.read_csv(comparison_file)
            model_comparison = comp_df.to_dict(orient="records")
        except Exception:
            pass

    # Live SLA statistics from DB
    tickets = db.query(TicketModel).filter(TicketModel.domain == active_domain).all()
    total_count = len(tickets)
    active_count = sum(1 for t in tickets if not t.is_resolved)
    responded_count = sum(1 for t in tickets if t.is_responded)
    resolved_count = sum(1 for t in tickets if t.is_resolved)
    needs_review_count = sum(1 for t in tickets if t.needs_human_review)

    by_priority = {p.id: 0 for p in pack.priorities}
    by_team = {t.id: 0 for t in pack.teams}
    by_label = {l.id: 0 for l in pack.labels}
    breached_count = 0
    at_risk_count = 0
    on_track_count = 0

    now = datetime.datetime.now(datetime.timezone.utc)
    for t in tickets:
        by_priority[t.priority] = by_priority.get(t.priority, 0) + 1
        by_team[t.primary_team] = by_team.get(t.primary_team, 0) + 1

        effective_lbls = json.loads(t.corrected_labels) if t.corrected_labels else json.loads(t.predicted_labels or "[]")
        for lbl in effective_lbls:
            by_label[lbl] = by_label.get(lbl, 0) + 1

        # Current status
        if t.is_resolved:
            on_track_count += 1
        else:
            live_status = sla_engine.determine_status(
                t.created_at.replace(tzinfo=datetime.timezone.utc) if t.created_at.tzinfo is None else t.created_at,
                t.first_response_due.replace(tzinfo=datetime.timezone.utc) if t.first_response_due.tzinfo is None else t.first_response_due,
                now,
                is_completed=t.is_responded,
            )
            if live_status == "breached":
                breached_count += 1
            elif live_status == "at_risk":
                at_risk_count += 1
            else:
                on_track_count += 1

    breach_rate = round((breached_count / total_count * 100), 2) if total_count > 0 else 0.0

    sla_metrics = SLAMetricsSummary(
        total_tickets=total_count,
        active_tickets=active_count,
        responded_tickets=responded_count,
        resolved_tickets=resolved_count,
        needs_review_count=needs_review_count,
        breached_count=breached_count,
        at_risk_count=at_risk_count,
        on_track_count=on_track_count,
        breach_rate_pct=breach_rate,
        by_priority=by_priority,
        by_team=by_team,
        by_label=by_label,
    )

    return MetricsResponse(
        domain=active_domain,
        model_metrics=model_metrics,
        model_comparison=model_comparison,
        sla_metrics=sla_metrics,
    )
