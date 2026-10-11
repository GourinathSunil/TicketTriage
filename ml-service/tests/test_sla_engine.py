"""Unit tests for SLA Engine."""
import datetime
import pytest
from core.domain_loader import load_domain_pack
from sla.engine import SLAEngine


@pytest.fixture
def saas_engine():
    pack = load_domain_pack("saas")
    return SLAEngine(domain_pack=pack)


def test_priority_p1_outage(saas_engine):
    res = saas_engine.apply_sla(
        labels=["outage", "bug"],
        created_at="2026-10-08T10:00:00",
        customer_tier="free",
    )
    assert res["priority"] == "P1"
    assert "Platform/SRE" in res["teams"]
    assert res["primary_team"] == "Platform/SRE"
    assert res["first_response_minutes"] == 15
    assert res["resolution_minutes"] == 240


def test_priority_p1_account_access_with_urgency(saas_engine):
    res = saas_engine.apply_sla(
        labels=["account-access"],
        ticket_text="URGENT: Executive locked out of production tenant immediately",
        customer_tier="free",
    )
    assert res["priority"] == "P1"
    assert "Identity/Auth" in res["teams"]


def test_priority_p3_account_access_without_urgency(saas_engine):
    res = saas_engine.apply_sla(
        labels=["account-access"],
        ticket_text="Question about resetting user password in test workspace",
        customer_tier="free",
    )
    assert res["priority"] == "P3"


def test_priority_p2_bug_and_billing(saas_engine):
    res = saas_engine.apply_sla(
        labels=["bug", "billing"],
        customer_tier="free",
    )
    assert res["priority"] == "P2"
    assert "Engineering" in res["teams"]
    assert "Billing" in res["teams"]


def test_priority_p4_feature_request(saas_engine):
    res = saas_engine.apply_sla(
        labels=["feature-request"],
        customer_tier="free",
    )
    assert res["priority"] == "P4"
    assert res["primary_team"] == "Product"


def test_customer_tier_enterprise_multiplier_and_bump(saas_engine):
    # Free tier performance issue -> P2
    free_res = saas_engine.apply_sla(
        labels=["performance"],
        customer_tier="free",
    )
    # Enterprise tier performance issue -> bumped to P1 and halved deadline
    ent_res = saas_engine.apply_sla(
        labels=["performance"],
        customer_tier="enterprise",
    )
    assert free_res["priority"] == "P2"
    assert ent_res["priority"] == "P1"  # Bumped from P2 to P1
    # P1 base first response is 15 minutes, enterprise multiplier x0.5 gives 8 minutes
    assert ent_res["first_response_minutes"] == int(round(15 * 0.5))


def test_sla_status_on_track_at_risk_breached(saas_engine):
    created = datetime.datetime(2026, 10, 8, 10, 0, 0, tzinfo=datetime.timezone.utc)
    
    # 5 minutes later for 15 minute SLA (ratio ~ 0.33) -> on_track
    now_early = created + datetime.timedelta(minutes=5)
    res_early = saas_engine.apply_sla(
        labels=["outage"],
        created_at=created,
        reference_time=now_early,
    )
    assert res_early["sla_status"] == "on_track"

    # 12 minutes later (ratio = 12/15 = 0.80 >= 0.70 at_risk threshold) -> at_risk
    now_risk = created + datetime.timedelta(minutes=12)
    res_risk = saas_engine.apply_sla(
        labels=["outage"],
        created_at=created,
        reference_time=now_risk,
    )
    assert res_risk["sla_status"] == "at_risk"

    # 20 minutes later (> 15 minutes due) -> breached
    now_breach = created + datetime.timedelta(minutes=20)
    res_breach = saas_engine.apply_sla(
        labels=["outage"],
        created_at=created,
        reference_time=now_breach,
    )
    assert res_breach["sla_status"] == "breached"


def test_business_hours_weekend_skipping(saas_engine):
    # Friday 16:30 UTC
    friday_pm = datetime.datetime(2026, 10, 9, 16, 30, 0, tzinfo=datetime.timezone.utc)
    # P3 first response is 240 business minutes
    # Friday has 30 mins left (16:30 to 17:00).
    # Monday starts at 9:00 UTC and has remaining 210 mins (3.5 hrs) -> should be Monday 12:30 UTC
    due_p3 = saas_engine.calculate_due_date(friday_pm, 240, is_24x7=False)
    assert due_p3.weekday() == 0  # Monday
    assert due_p3.hour == 12
    assert due_p3.minute == 30

    # For P1 (24x7), 240 mins from Friday 16:30 is Friday 20:30 UTC directly
    due_p1 = saas_engine.calculate_due_date(friday_pm, 240, is_24x7=True)
    assert due_p1.hour == 20
    assert due_p1.minute == 30


def test_confidence_gate(saas_engine):
    # Empty labels triggers review
    empty_res = saas_engine.apply_sla(labels=[])
    assert empty_res["needs_human_review"] is True
    assert any("Confidence Gate" in r for r in empty_res["reasons"])

    # Borderline probability triggers review
    border_res = saas_engine.apply_sla(
        labels=["outage"],
        probabilities={"outage": 0.52},
        thresholds={"outage": 0.50},  # diff is 0.02 <= 0.10 margin
    )
    assert border_res["needs_human_review"] is True

    # High confidence does not trigger review
    conf_res = saas_engine.apply_sla(
        labels=["outage"],
        probabilities={"outage": 0.95},
        thresholds={"outage": 0.50},
    )
    assert conf_res["needs_human_review"] is False
