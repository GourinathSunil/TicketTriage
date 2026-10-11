"""
Database persistence layer for TicketTriage using SQLite and SQLAlchemy.
Stores incoming tickets, routing metadata, SLA timestamps, and agent feedback/corrections.
"""
import datetime
import json
import os
from pathlib import Path
from typing import List, Optional, Generator
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Float,
    Integer,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()


class TicketModel(Base):
    __tablename__ = "tickets"

    id = Column(String(64), primary_key=True, index=True)
    domain = Column(String(32), index=True, default="saas")
    subject = Column(String(512), nullable=False)
    body = Column(Text, nullable=False)
    customer_tier = Column(String(32), default="free", index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    # ML Predictions & Confidence
    predicted_labels = Column(Text, default="[]")  # JSON list
    corrected_labels = Column(Text, nullable=True)   # JSON list or null
    label_probabilities = Column(Text, default="{}") # JSON dict
    needs_human_review = Column(Boolean, default=False, index=True)

    # SLA and Routing
    priority = Column(String(16), index=True)
    priority_rank = Column(Integer, default=4)
    primary_team = Column(String(64), index=True)
    assigned_teams = Column(Text, default="[]")      # JSON list
    first_response_due = Column(DateTime, nullable=False, index=True)
    resolution_due = Column(DateTime, nullable=False)
    first_response_minutes = Column(Integer, default=60)
    resolution_minutes = Column(Integer, default=480)

    # SLA Tracking Status
    sla_status = Column(String(32), default="on_track", index=True) # on_track, at_risk, breached
    first_response_status = Column(String(32), default="on_track")
    resolution_status = Column(String(32), default="on_track")
    reasons = Column(Text, default="[]")             # JSON list of rule explanations

    # Lifecycle State
    is_responded = Column(Boolean, default=False)
    responded_at = Column(DateTime, nullable=True)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "domain": self.domain,
            "subject": self.subject,
            "body": self.body,
            "customer_tier": self.customer_tier,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "predicted_labels": json.loads(self.predicted_labels or "[]"),
            "corrected_labels": json.loads(self.corrected_labels) if self.corrected_labels else None,
            "effective_labels": json.loads(self.corrected_labels) if self.corrected_labels else json.loads(self.predicted_labels or "[]"),
            "label_probabilities": json.loads(self.label_probabilities or "{}"),
            "needs_human_review": bool(self.needs_human_review),
            "priority": self.priority,
            "priority_rank": self.priority_rank,
            "primary_team": self.primary_team,
            "assigned_teams": json.loads(self.assigned_teams or "[]"),
            "first_response_due": self.first_response_due.isoformat() + "Z" if self.first_response_due else None,
            "resolution_due": self.resolution_due.isoformat() + "Z" if self.resolution_due else None,
            "first_response_minutes": self.first_response_minutes,
            "resolution_minutes": self.resolution_minutes,
            "sla_status": self.sla_status,
            "first_response_status": self.first_response_status,
            "resolution_status": self.resolution_status,
            "reasons": json.loads(self.reasons or "[]"),
            "is_responded": bool(self.is_responded),
            "responded_at": self.responded_at.isoformat() + "Z" if self.responded_at else None,
            "is_resolved": bool(self.is_resolved),
            "resolved_at": self.resolved_at.isoformat() + "Z" if self.resolved_at else None,
        }


class FeedbackModel(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(64), index=True)
    original_labels = Column(Text, default="[]")
    corrected_labels = Column(Text, default="[]")
    agent_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


def get_db_path() -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    db_dir = base_dir / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "tickettriage.db"


engine = create_engine(
    f"sqlite:///{get_db_path()}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
