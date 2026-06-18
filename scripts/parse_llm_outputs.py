#!/usr/bin/env python3
"""Parse structured LLM raw output into normalized response fields."""

from __future__ import annotations

import csv
import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "pipeline_validation"


LABELS = {
    "Persona ID": "persona_id_from_response",
    "Decision": "decision",
    "Transportation mode": "transportation_mode",
    "Likely destination type": "destination_type",
    "Departure urgency": "departure_urgency",
    "Key constraints considered": "key_constraints_considered",
    "Reasoning": "reasoning",
}

DECISIONS = ["Evacuate now", "Delay evacuation", "Stay", "Uncertain"]
MODES = ["Private vehicle", "Ride with family/friend", "Public transit", "Walk", "Emergency transport", "Mixed/other", "No transportation"]
DESTINATIONS = ["Public shelter", "Friend/relative home", "Hotel/motel", "Medical facility", "Outside evacuation zone", "Stay in place", "Unknown"]


def clean_label(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^[#>*_`\\-\\s]+", "", value)
    value = re.sub(r"[*_`\\s]+$", "", value)
    return value.strip()


def clean_value(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^[>*_`\\-\\s]+", "", value)
    value = re.sub(r"[*_`\\s]+$", "", value)
    return value.strip()


def normalize_choice(value: str, choices: list[str]) -> str:
    cleaned = clean_value(value)
    lowered = cleaned.lower()
    for choice in choices:
        if lowered == choice.lower() or lowered.startswith(choice.lower() + " ") or lowered.startswith(choice.lower() + " ("):
            return choice
    return cleaned


def parse_response(raw: str) -> dict[str, str]:
    parsed = {v: "" for v in LABELS.values()}
    current = None
    for line in raw.splitlines():
        if ":" in line:
            label, value = line.split(":", 1)
            label = clean_label(label)
            if label in LABELS:
                current = LABELS[label]
                parsed[current] = clean_value(value)
                continue
        if current and line.strip():
            parsed[current] = (parsed[current] + " " + clean_value(line)).strip()
    return parsed


def normalize_decision(value: str) -> str:
    return normalize_choice(value, DECISIONS)


def normalize_transportation_mode(value: str) -> str:
    if value.strip().lower() in {"none", "n/a", "not applicable"}:
        return "No transportation"
    return normalize_choice(value, MODES)


def normalize_destination_type(value: str) -> str:
    return normalize_choice(value, DESTINATIONS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse structured LLM output.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    with (output_dir / "llm_responses_raw.csv").open(newline="", encoding="utf-8") as f:
        raw_rows = list(csv.DictReader(f))

    rows = []
    for row in raw_rows:
        parsed = parse_response(row["raw_response"])
        parsed["decision"] = normalize_decision(parsed["decision"])
        parsed["transportation_mode"] = normalize_transportation_mode(parsed["transportation_mode"])
        parsed["destination_type"] = normalize_destination_type(parsed["destination_type"])
        clean = dict(row)
        clean.update(parsed)
        rows.append(clean)

    fieldnames = list(rows[0].keys())
    with (output_dir / "llm_responses_parsed.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote parsed responses to {output_dir / 'llm_responses_parsed.csv'}")


if __name__ == "__main__":
    main()
