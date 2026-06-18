#!/usr/bin/env python3
"""Evaluate transportation and destination feasibility with rule-based metrics."""

from __future__ import annotations

import csv
import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "pipeline_validation"
DEFAULT_PERSONAS_FILE = DATA / "personas.csv"
DEFAULT_SPATIAL_CONTEXT_FILE = DATA / "spatial_context.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def resolve_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_personas(personas_file: Path, spatial_context_file: Path) -> dict[str, dict[str, str]]:
    personas = read_csv(personas_file)
    spatial = {row["persona_id"]: row for row in read_csv(spatial_context_file)} if spatial_context_file.exists() else {}
    merged = {}
    for persona in personas:
        row = dict(persona)
        row.update(spatial.get(persona["persona_id"], {}))
        merged[row["persona_id"]] = row
    return merged


def has_children(p: dict[str, str]) -> bool:
    return "children" in p["family_structure"].lower() or "child" in p["medical_caregiving_responsibilities"].lower()


def has_medical(p: dict[str, str]) -> bool:
    return p["medical_caregiving_responsibilities"] != "None"


def is_elderly(p: dict[str, str]) -> bool:
    return int(p["age_household_head"]) >= 67


def mentions_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def score_row(row: dict[str, str], p: dict[str, str]) -> dict[str, str | float | int]:
    mode = row["transportation_mode"]
    dest = row["destination_type"]
    decision = row["decision"]
    reasoning = (row.get("reasoning") or "").lower()
    constraints = (row.get("key_constraints_considered") or "").lower()
    vehicle = p["vehicle_access"] == "Yes"
    transit = p["transit_access"].lower()
    low_income = p["income_level"] in {"Low", "Lower-middle"}
    medical = has_medical(p)
    children = has_children(p)
    elderly = is_elderly(p)
    shelter_miles = float(p["distance_to_nearest_shelter"])
    shelter_time = int(float(p["road_travel_time_to_shelter"]))
    hazard_miles = float(p["distance_to_hazard_zone"])
    high_risk = p["wildfire_risk_level"] in {"High", "Very high"}

    hard = []
    soft = []
    inconsistencies = []

    if not vehicle and mode == "Private vehicle":
        hard.append("mode_private_vehicle_without_vehicle")
    if mode == "Walk" and (elderly or medical):
        hard.append("mode_walk_with_elderly_or_medical_need")
    if mode == "Walk" and children:
        soft.append("mode_walk_with_children")
    if mode == "Public transit" and transit in {"none", "limited"}:
        soft.append("mode_public_transit_low_access")
    if mode in {"None", "No transportation"} and decision == "Evacuate now":
        hard.append("mode_none_for_evacuation")

    if dest == "Public shelter" and shelter_time > 45:
        soft.append("destination_shelter_long_travel_time")
    if dest == "Hotel/motel" and low_income:
        soft.append("destination_hotel_low_income")
    if dest == "Stay in place" and high_risk:
        hard.append("destination_stay_in_high_risk")
    if dest == "Medical facility" and not medical:
        soft.append("destination_medical_without_medical_need")
    if medical and dest not in {"Medical facility", "Public shelter", "Friend/relative home", "Outside evacuation zone"}:
        soft.append("destination_does_not_reflect_medical_need")

    combined_text = f"{reasoning} {constraints}"
    if mentions_any(combined_text, [r"\bdrive\b", r"\bdriving\b", r"\bcar\b", r"\bvehicle access\b"]) and not vehicle:
        inconsistencies.append("reasoning_implies_vehicle_without_access")
    if mentions_any(reasoning, [r"nearby shelter", r"nearest shelter", r"close shelter", r"shelter is close"]) and (shelter_miles > 5 or shelter_time > 35):
        inconsistencies.append("reasoning_calls_distant_shelter_nearby")
    if mentions_any(reasoning, [r"public transit available", r"transit is available", r"reliable transit", r"bus service"]) and transit in {"none", "limited"}:
        inconsistencies.append("reasoning_overstates_transit")
    if mentions_any(reasoning, [r"safe distance", r"far from (the )?(fire|hazard)", r"not close to (the )?(fire|hazard)"]) and hazard_miles < 2.0:
        inconsistencies.append("reasoning_calls_near_hazard_safe_distance")
    if dest == "Public shelter" and shelter_time > 45 and not mentions_any(reasoning, [r"long", r"far", r"\d+\s*min", r"travel time", r"distance"]):
        inconsistencies.append("shelter_choice_ignores_long_travel_time")
    if decision in {"Stay", "Delay evacuation"} and high_risk and not mentions_any(reasoning, [r"high", r"very high", r"risk", r"hazard", r"smoke", r"warning"]):
        inconsistencies.append("delay_or_stay_ignores_high_risk")
    if row["condition"] == "spatial_grounded":
        spatial_cues = [r"\d+(\.\d+)?\s*(mile|mi)", r"\d+\s*min", r"transit", r"risk", r"hazard", r"shelter"]
        if not mentions_any(reasoning, spatial_cues):
            inconsistencies.append("spatial_grounded_reasoning_omits_spatial_context")

    hard_count = len(hard)
    soft_count = len(soft)
    inconsistency_count = len(inconsistencies)
    feasibility_score = max(0.0, 1.0 - hard_count * 0.35 - soft_count * 0.15 - inconsistency_count * 0.10)
    spatial_consistency_score = max(0.0, 1.0 - inconsistency_count * 0.25)

    return {
        "mode_hard_violation": int(any(v.startswith("mode_") for v in hard)),
        "destination_hard_violation": int(any(v.startswith("destination_") for v in hard)),
        "mode_soft_issue": int(any(v.startswith("mode_") for v in soft)),
        "destination_soft_issue": int(any(v.startswith("destination_") for v in soft)),
        "soft_feasibility_issue": int(bool(soft)),
        "hard_violation_count": hard_count,
        "soft_violation_count": soft_count,
        "spatial_inconsistency_count": inconsistency_count,
        "any_hard_violation": int(bool(hard)),
        "any_soft_issue": int(bool(soft)),
        "any_violation": int(bool(hard or soft or inconsistencies)),
        "mode_feasible": int(not any(v.startswith("mode_") for v in hard) and not any(w.startswith("mode_") for w in soft)),
        "destination_feasible": int(not any(v.startswith("destination_") for v in hard) and not any(w.startswith("destination_") for w in soft)),
        "feasibility_score": round(feasibility_score, 3),
        "spatial_consistency_score": round(spatial_consistency_score, 3),
        "hard_violation_notes": "; ".join(hard),
        "soft_violation_notes": "; ".join(soft),
        "spatial_inconsistency_notes": "; ".join(inconsistencies),
        "violation_notes": "; ".join(hard + soft + inconsistencies),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate response feasibility.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--personas-file", default=str(DEFAULT_PERSONAS_FILE))
    parser.add_argument("--spatial-context-file", default=str(DEFAULT_SPATIAL_CONTEXT_FILE))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    personas = load_personas(resolve_path(args.personas_file), resolve_path(args.spatial_context_file))
    responses = read_csv(output_dir / "llm_responses_parsed.csv")
    rows = []
    persona_fields = [
        "income_level",
        "vehicle_access",
        "family_structure",
        "medical_caregiving_responsibilities",
        "wildfire_risk_level",
        "transit_access",
        "distance_to_nearest_shelter",
        "road_travel_time_to_shelter",
        "distance_to_hazard_zone",
    ]
    for row in responses:
        p = personas[row["persona_id"]]
        out = {k: row[k] for k in [
            "run_id", "condition", "persona_id", "repeat", "decision",
            "transportation_mode", "destination_type", "departure_urgency",
        ]}
        out.update({k: p[k] for k in persona_fields})
        out.update({
            "has_children": int(has_children(p)),
            "has_medical_need": int(has_medical(p)),
            "is_low_income": int(p["income_level"] in {"Low", "Lower-middle"}),
        })
        out.update(score_row(row, p))
        rows.append(out)

    fieldnames = list(rows[0].keys())
    with (output_dir / "feasibility_scores.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote feasibility scores to {output_dir / 'feasibility_scores.csv'}")


if __name__ == "__main__":
    main()
