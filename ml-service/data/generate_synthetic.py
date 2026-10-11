"""
Synthetic ticket dataset generator for TicketTriage.
Generates realistic multi-label tickets based on domain templates, slot filling,
co-occurrence probabilities, label frequency distributions, tone variations, and noise.
"""
import argparse
import datetime
import os
import random
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
import pandas as pd
import yaml

# Support both direct script execution and package imports
current_dir = Path(__file__).resolve().parent
ml_service_dir = current_dir.parent
if str(ml_service_dir) not in sys.path:
    sys.path.insert(0, str(ml_service_dir))

from core.domain_loader import load_domain_pack


TYPO_CHAR_PAIRS = [
    ("e", "r"), ("r", "t"), ("t", "y"), ("a", "s"), ("s", "d"),
    ("d", "f"), ("i", "o"), ("o", "p"), ("n", "m"), ("b", "v")
]


def inject_typos(text: str, typo_prob: float = 0.04) -> str:
    """Injects occasional realistic typing errors."""
    if random.random() > typo_prob:
        return text
    chars = list(text)
    if not chars:
        return text
    idx = random.randint(0, len(chars) - 1)
    c = chars[idx].lower()
    for c1, c2 in TYPO_CHAR_PAIRS:
        if c == c1:
            chars[idx] = c2
            break
        elif c == c2:
            chars[idx] = c1
            break
    return "".join(chars)


def fill_slots(template: str, slots: Dict[str, List[str]]) -> str:
    """Fills placeholders in templates with random slot values."""
    res = template
    for key, values in slots.items():
        placeholder = f"{{{key}}}"
        while placeholder in res:
            replacement = random.choice(values)
            res = res.replace(placeholder, replacement, 1)
    return res


def sample_labels(
    label_ids: List[str],
    frequencies: Dict[str, float],
    co_occurrences: List[Dict[str, Any]],
) -> List[str]:
    """
    Samples 1 to 3 labels for a ticket using base frequencies and co-occurrence rules.
    Guarantees at least 1 label.
    """
    chosen: Set[str] = set()

    # Step 1: Pick a primary label based on weights
    weights = [frequencies.get(lbl, 0.1) for lbl in label_ids]
    primary = random.choices(label_ids, weights=weights, k=1)[0]
    chosen.add(primary)

    # Step 2: Check co-occurrence rules for the primary label
    for rule in co_occurrences:
        if rule.get("primary") == primary:
            for correlated, prob in rule.get("correlates_with", {}).items():
                if correlated in label_ids and random.random() < prob:
                    chosen.add(correlated)

    # Step 3: Small chance of adding another random label with lower probability
    if len(chosen) < 3 and random.random() < 0.15:
        secondary = random.choices(label_ids, weights=weights, k=1)[0]
        chosen.add(secondary)

    # Step 4: Ensure maximum 3 labels to keep it realistic
    return sorted(list(chosen))[:3]


def generate_ticket(
    ticket_id: str,
    labels: List[str],
    templates: Dict[str, Any],
    slots: Dict[str, List[str]],
    tones: Dict[str, Any],
    tiers: List[str],
    start_time: datetime.datetime,
) -> Dict[str, Any]:
    """Generates a single synthetic ticket record with subject, body, tier, and timestamp."""
    # Pick a tone
    tone_name = random.choices(
        ["neutral", "polite", "urgent", "angry"],
        weights=[0.45, 0.30, 0.15, 0.10],
        k=1
    )[0]
    tone_info = tones.get(tone_name, {})

    # Generate subject and body from the labels
    subject_parts = []
    body_parts = []

    for lbl in labels:
        lbl_templates = templates.get(lbl, {})
        subj_candidates = lbl_templates.get("subjects", [f"Issue reported with {lbl}"])
        body_candidates = lbl_templates.get("bodies", [f"We encountered an issue relating to {lbl}."])

        subj_tmpl = random.choice(subj_candidates)
        body_tmpl = random.choice(body_candidates)

        subject_parts.append(fill_slots(subj_tmpl, slots))
        body_parts.append(fill_slots(body_tmpl, slots))

    # Compose subject
    prefix = ""
    if tone_info.get("prefixes") and random.random() < 0.7:
        prefix = random.choice(tone_info["prefixes"])

    if len(subject_parts) == 1:
        raw_subject = f"{prefix}{subject_parts[0]}"
    else:
        # Combined subject for multi-label tickets
        raw_subject = f"{prefix}{subject_parts[0]} and {subject_parts[1].lower()}"

    # Compose body
    body_text = " ".join(body_parts)

    # Add tone closing
    if tone_info.get("body_closings") and random.random() < 0.8:
        closing = random.choice(tone_info["body_closings"])
        body_text += f"\n\n{closing}"

    # Vary length (short snippet, or expanded details with ticket details / repro)
    length_variant = random.random()
    if length_variant < 0.2:
        # Short ticket
        pass
    elif length_variant < 0.8:
        # Standard ticket with metadata
        env = random.choice(["Production (US-East)", "Staging", "Production (EU-West)", "Cluster-04"])
        body_text += f"\nEnvironment: {env}. Browser/Client: Chrome 124.0 on Windows/macOS."
    else:
        # Longer ticket with technical stack trace or error log
        body_text += (
            f"\n\nStack trace / debug snippet:\n"
            f"[ErrorLog] Timestamp: {datetime.datetime.now().isoformat()} - Code: ERR_REQ_FAILED\n"
            f"Trace: at RequestPipeline.execute (client.js:142) -> Status: 500 Internal Failure"
        )

    # Inject minor typos
    final_subject = inject_typos(raw_subject, typo_prob=0.03)
    final_body = inject_typos(body_text, typo_prob=0.04)

    # Tier sampling
    customer_tier = random.choices(tiers, weights=[0.55, 0.30, 0.15], k=1)[0]

    # Timestamp within last 30 days
    delta_minutes = random.randint(0, 30 * 24 * 60)
    created_at = start_time - datetime.timedelta(minutes=delta_minutes)

    return {
        "id": ticket_id,
        "subject": final_subject,
        "body": final_body,
        "customer_tier": customer_tier,
        "created_at": created_at.isoformat() + "Z",
        "labels": "|".join(labels),
    }


def generate_dataset(
    domain_name: str,
    count: int,
    output_path: Optional[Path] = None,
    seed: int = 42,
) -> Path:
    """Generates synthetic dataset for specified domain."""
    random.seed(seed)
    pack = load_domain_pack(domain_name)

    templates_file = pack.pack_dir / "templates.yaml"
    if not templates_file.exists():
        raise FileNotFoundError(f"Missing templates.yaml in {pack.pack_dir}")

    with open(templates_file, "r", encoding="utf-8") as f:
        tmpl_config = yaml.safe_load(f)

    slots = tmpl_config.get("slots", {})
    frequencies = tmpl_config.get("label_frequencies", {})
    co_occurrences = tmpl_config.get("co_occurrences", [])
    tones = tmpl_config.get("tones", {})
    templates = tmpl_config.get("templates", {})
    tiers = list(pack.customer_tiers.keys()) if pack.customer_tiers else ["free", "pro", "enterprise"]

    now = datetime.datetime.now(datetime.timezone.utc)
    records = []

    for i in range(1, count + 1):
        ticket_id = f"TICK-{domain_name.upper()}-{i:05d}"
        labels = sample_labels(pack.label_ids, frequencies, co_occurrences)
        record = generate_ticket(
            ticket_id=ticket_id,
            labels=labels,
            templates=templates,
            slots=slots,
            tones=tones,
            tiers=tiers,
            start_time=now,
        )
        records.append(record)

    df = pd.DataFrame(records)

    if output_path is None:
        data_dir = pack.pack_dir.parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_path = data_dir / f"tickets_{domain_name}.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} synthetic tickets for domain '{domain_name}' at {output_path}")

    # Print label distribution
    all_labels = [lbl for sublist in df["labels"].str.split("|") for lbl in sublist]
    label_counts = pd.Series(all_labels).value_counts()
    print("\nLabel Distribution:")
    for lbl, cnt in label_counts.items():
        print(f"  {lbl:24s}: {cnt:5d} ({cnt / len(df) * 100:.1f}%)")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic ticket dataset for TicketTriage")
    parser.add_argument("--domain", type=str, default=os.getenv("DOMAIN", "saas"), help="Domain pack name")
    parser.add_argument("--count", type=int, default=10000, help="Number of tickets to generate (default 10,000)")
    parser.add_argument("--output", type=str, default=None, help="Custom output CSV path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    out_p = Path(args.output) if args.output else None
    generate_dataset(args.domain, args.count, out_p, seed=args.seed)


if __name__ == "__main__":
    main()
