"""
SLA Engine for TicketTriage.
Applies domain-specific SLA rules, priority ranking, customer tier modifiers,
business-hours calculations, confidence gating, and team routing.
"""
import datetime
from typing import Dict, List, Optional, Tuple, Any
from dateutil import tz
from core.domain_loader import DomainPack, load_domain_pack


class SLAEngine:
    """Evaluates support ticket SLA and routing against active domain rules."""

    def __init__(self, domain_pack: Optional[DomainPack] = None, domain_name: Optional[str] = None):
        if domain_pack is not None:
            self.pack = domain_pack
        else:
            self.pack = load_domain_pack(domain_name)

    def _parse_datetime(self, dt: Any) -> datetime.datetime:
        """Converts string or datetime object to UTC datetime."""
        if isinstance(dt, datetime.datetime):
            if dt.tzinfo is None:
                return dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc)
        elif isinstance(dt, str):
            # Strip trailing Z if present and parse
            clean_str = dt.rstrip("Z")
            parsed = datetime.datetime.fromisoformat(clean_str)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=datetime.timezone.utc)
            return parsed.astimezone(datetime.timezone.utc)
        else:
            return datetime.datetime.now(datetime.timezone.utc)

    def calculate_due_date(
        self,
        start_dt: datetime.datetime,
        duration_minutes: int,
        is_24x7: bool = False,
    ) -> datetime.datetime:
        """
        Calculates due date given duration in minutes.
        If is_24x7 or business hours disabled, adds minutes directly.
        Otherwise, respects business hours schedule.
        """
        start_utc = self._parse_datetime(start_dt)
        bh = self.pack.business_hours

        if is_24x7 or not bh.enabled:
            return start_utc + datetime.timedelta(minutes=duration_minutes)

        # Convert to business hours timezone
        try:
            target_tz = tz.gettz(bh.timezone) or tz.tzutc()
        except Exception:
            target_tz = tz.tzutc()

        current = start_utc.astimezone(target_tz)
        minutes_remaining = duration_minutes

        # Advance minute by minute / chunk through business hours
        while minutes_remaining > 0:
            weekday = current.weekday()
            is_workday = weekday in bh.workdays

            if not is_workday:
                # Fast-forward to start of next day at work_start_hour
                current = (current + datetime.timedelta(days=1)).replace(
                    hour=bh.work_start_hour, minute=0, second=0, microsecond=0
                )
                continue

            # It's a workday
            work_start = current.replace(hour=bh.work_start_hour, minute=0, second=0, microsecond=0)
            work_end = current.replace(hour=bh.work_end_hour, minute=0, second=0, microsecond=0)

            if current < work_start:
                current = work_start
                continue
            elif current >= work_end:
                # Beyond work hours today, forward to next day
                current = (current + datetime.timedelta(days=1)).replace(
                    hour=bh.work_start_hour, minute=0, second=0, microsecond=0
                )
                continue

            # Within working hours today
            available_minutes_today = int((work_end - current).total_seconds() / 60)
            if minutes_remaining <= available_minutes_today:
                current += datetime.timedelta(minutes=minutes_remaining)
                minutes_remaining = 0
            else:
                minutes_remaining -= available_minutes_today
                current = (current + datetime.timedelta(days=1)).replace(
                    hour=bh.work_start_hour, minute=0, second=0, microsecond=0
                )

        return current.astimezone(datetime.timezone.utc)

    def determine_status(
        self,
        created_at: datetime.datetime,
        due_at: datetime.datetime,
        now: datetime.datetime,
        at_risk_ratio: float = 0.70,
        is_completed: bool = False,
    ) -> str:
        """Determines if SLA target is on_track, at_risk, or breached."""
        if is_completed:
            return "on_track"

        if now >= due_at:
            return "breached"

        total_window = (due_at - created_at).total_seconds()
        if total_window <= 0:
            return "breached"

        elapsed = (now - created_at).total_seconds()
        ratio = max(0.0, elapsed / total_window)

        if ratio >= at_risk_ratio:
            return "at_risk"
        return "on_track"

    def apply_sla(
        self,
        labels: List[str],
        probabilities: Optional[Dict[str, float]] = None,
        created_at: Optional[Any] = None,
        customer_tier: str = "free",
        ticket_text: str = "",
        is_first_responded: bool = False,
        is_resolved: bool = False,
        reference_time: Optional[Any] = None,
        thresholds: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Executes full SLA routing and priority determination.
        Returns comprehensive routing and deadline details.
        """
        created_dt = self._parse_datetime(created_at) if created_at else datetime.datetime.now(datetime.timezone.utc)
        now_dt = self._parse_datetime(reference_time) if reference_time else datetime.datetime.now(datetime.timezone.utc)
        tier_key = (customer_tier or "free").lower().strip()
        tier_config = self.pack.customer_tiers.get(tier_key, None)

        reasons = []
        labels_set = set(labels)
        text_lower = (ticket_text or "").lower()

        # Step 1: Match Priority Rules (Highest match wins by rank)
        matched_priority_id = None
        matched_rule_desc = None
        primary_driving_label = None

        # Build priority map sorted by priority rank (1 = highest)
        sorted_priorities = sorted(self.pack.priorities, key=lambda p: p.rank)
        priority_map = {p.id: p for p in self.pack.priorities}

        for rule in self.pack.priority_rules:
            # Check any_labels
            any_match = False
            first_any_lbl = None
            if rule.any_labels:
                for lbl in rule.any_labels:
                    if lbl in labels_set:
                        any_match = True
                        first_any_lbl = lbl
                        break

            # Check all_labels
            all_match = False
            if rule.all_labels:
                if all(lbl in labels_set for lbl in rule.all_labels):
                    all_match = True

            # Check keywords if specified
            keyword_match = True
            if rule.keywords_any:
                keyword_match = any(kw.lower() in text_lower for kw in rule.keywords_any)

            rule_fired = False
            rule_driving_lbl = None
            if rule.any_labels and not rule.all_labels and any_match and keyword_match:
                rule_fired = True
                rule_driving_lbl = first_any_lbl
            elif rule.all_labels and not rule.any_labels and all_match and keyword_match:
                rule_fired = True
                rule_driving_lbl = rule.all_labels[0]
            elif rule.any_labels and rule.all_labels and any_match and all_match and keyword_match:
                rule_fired = True
                rule_driving_lbl = first_any_lbl

            if rule_fired:
                candidate_p = priority_map[rule.priority]
                if matched_priority_id is None:
                    matched_priority_id = rule.priority
                    matched_rule_desc = rule.description or f"Matched rule for {rule.priority}"
                    primary_driving_label = rule_driving_lbl
                else:
                    current_p = priority_map[matched_priority_id]
                    if candidate_p.rank < current_p.rank:  # Lower rank number = higher priority
                        matched_priority_id = rule.priority
                        matched_rule_desc = rule.description or f"Matched higher rule for {rule.priority}"
                        primary_driving_label = rule_driving_lbl

        # Default fallback priority if no rules matched
        if matched_priority_id is None:
            # Use lowest priority (highest rank number)
            lowest_p = sorted_priorities[-1]
            matched_priority_id = lowest_p.id
            matched_rule_desc = f"Default fallback to {lowest_p.name} (no specific rules triggered)"
            reasons.append(matched_rule_desc)
        else:
            reasons.append(f"Priority {matched_priority_id}: {matched_rule_desc}")

        # Step 2: Customer Tier Modifier
        base_priority = priority_map[matched_priority_id]
        final_priority = base_priority
        deadline_multiplier = 1.0

        if tier_config:
            deadline_multiplier = tier_config.deadline_multiplier
            reasons.append(f"Customer Tier '{tier_config.name}': deadline multiplier x{deadline_multiplier}")

            # Check tier priority bump
            if tier_config.priority_bump > 0 and base_priority.rank > 1:
                bump_eligible = True
                if tier_config.priority_bump_labels:
                    bump_eligible = any(lbl in labels_set for lbl in tier_config.priority_bump_labels)

                if bump_eligible:
                    target_rank = max(1, base_priority.rank - tier_config.priority_bump)
                    # Find priority with target_rank
                    for p in sorted_priorities:
                        if p.rank == target_rank:
                            reasons.append(
                                f"Customer Tier '{tier_config.name}' bumped priority from {final_priority.id} to {p.id}"
                            )
                            final_priority = p
                            break

        # Step 3: Routing - Labels to Teams
        label_to_team = self.pack.label_to_team
        assigned_teams = []
        for lbl in labels:
            team = label_to_team.get(lbl)
            if team and team not in assigned_teams:
                assigned_teams.append(team)

        if not assigned_teams:
            # Default to first team if none
            fallback_team = self.pack.teams[0].id if self.pack.teams else "Support"
            assigned_teams = [fallback_team]
            reasons.append(f"No label matched team; routed to default {fallback_team}")

        # Primary team
        primary_team = None
        if primary_driving_label and primary_driving_label in label_to_team:
            primary_team = label_to_team[primary_driving_label]
        elif assigned_teams:
            primary_team = assigned_teams[0]
        else:
            primary_team = self.pack.teams[0].id

        # Step 4: Deadlines Calculation
        first_resp_min = int(round(final_priority.deadlines.first_response_minutes * deadline_multiplier))
        resol_min = int(round(final_priority.deadlines.resolution_minutes * deadline_multiplier))
        first_resp_min = max(5, first_resp_min)
        resol_min = max(15, resol_min)

        is_24x7 = final_priority.always_24x7
        first_resp_due = self.calculate_due_date(created_dt, first_resp_min, is_24x7=is_24x7)
        resol_due = self.calculate_due_date(created_dt, resol_min, is_24x7=is_24x7)

        # Step 5: SLA Status
        at_risk_ratio = self.pack.sla_status_thresholds.at_risk_percentage
        first_resp_status = self.determine_status(
            created_dt, first_resp_due, now_dt, at_risk_ratio=at_risk_ratio, is_completed=is_first_responded
        )
        resol_status = self.determine_status(
            created_dt, resol_due, now_dt, at_risk_ratio=at_risk_ratio, is_completed=is_resolved
        )

        # Overall status is worst of the two
        if first_resp_status == "breached" or resol_status == "breached":
            sla_status = "breached"
        elif first_resp_status == "at_risk" or resol_status == "at_risk":
            sla_status = "at_risk"
        else:
            sla_status = "on_track"

        # Step 6: Confidence Gate
        needs_human_review = False
        margin = self.pack.sla_status_thresholds.confidence_gate_margin

        if not labels:
            needs_human_review = True
            reasons.append("Confidence Gate: No labels predicted; requires manual review")
        elif probabilities:
            # Check if top predicted label's probability is near its threshold
            for lbl in labels:
                prob = probabilities.get(lbl, 0.0)
                thresh = (thresholds or {}).get(lbl, 0.50)
                if abs(prob - thresh) <= margin:
                    needs_human_review = True
                    reasons.append(
                        f"Confidence Gate: Label '{lbl}' probability ({prob:.2f}) within margin of threshold ({thresh:.2f})"
                    )
                    break

        return {
            "priority": final_priority.id,
            "priority_rank": final_priority.rank,
            "priority_name": final_priority.name,
            "priority_color": final_priority.color,
            "primary_team": primary_team,
            "teams": assigned_teams,
            "first_response_due": first_resp_due.isoformat() + "Z",
            "resolution_due": resol_due.isoformat() + "Z",
            "first_response_minutes": first_resp_min,
            "resolution_minutes": resol_min,
            "sla_status": sla_status,
            "first_response_status": first_resp_status,
            "resolution_status": resol_status,
            "needs_human_review": needs_human_review,
            "reasons": reasons,
        }
