#!/usr/bin/env python3
"""Validate generated experiment outputs before moving to full runs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "pipeline_validation"
DEFAULT_PERSONAS_FILE = DATA / "personas.csv"
DEFAULT_SPATIAL_CONTEXT_FILE = DATA / "spatial_context.csv"

DECISIONS = {"Evacuate now", "Delay evacuation", "Stay", "Uncertain"}
MODES = {"Private vehicle", "Ride with family/friend", "Public transit", "Walk", "Emergency transport", "Mixed/other", "No transportation"}
DESTINATIONS = {"Public shelter", "Friend/relative home", "Hotel/motel", "Medical facility", "Outside evacuation zone", "Stay in place", "Unknown"}
TRANSIT = {"Good", "Moderate", "Limited", "None"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def resolve_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate wildfire LLM experiment outputs.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--personas-file", default=str(DEFAULT_PERSONAS_FILE))
    parser.add_argument("--spatial-context-file", default=str(DEFAULT_SPATIAL_CONTEXT_FILE))
    args = parser.parse_args()
    output_dir = resolve_path(args.output_dir)
    errors: list[str] = []

    personas = read_csv(resolve_path(args.personas_file))
    spatial = read_csv(resolve_path(args.spatial_context_file))
    for path_name, rows in [(Path(args.personas_file).name, personas), (Path(args.spatial_context_file).name, spatial)]:
        for row in rows:
            if "transit_access" in row:
                require((row.get("transit_access") or "").strip() in TRANSIT, f"{path_name}: invalid transit_access for {row.get('persona_id')}: {row.get('transit_access')!r}", errors)

    parsed_path = output_dir / "llm_responses_parsed.csv"
    scores_path = output_dir / "feasibility_scores.csv"
    failures_path = output_dir / "failed_runs.csv"
    require(scores_path.exists(), f"missing {scores_path}", errors)
    if failures_path.exists():
        failures = read_csv(failures_path)
        require(not failures, f"{failures_path} contains {len(failures)} failed run(s)", errors)

    if parsed_path.exists():
        rows = read_csv(parsed_path)
        required_fields = ["persona_id", "decision", "transportation_mode", "destination_type", "departure_urgency", "key_constraints_considered", "reasoning"]
        for row in rows:
            run_id = row.get("run_id", "<missing run_id>")
            for field in required_fields:
                require(bool((row.get(field) or "").strip()), f"{run_id}: missing parsed field {field}", errors)
            require(row.get("decision") in DECISIONS, f"{run_id}: invalid decision {row.get('decision')!r}", errors)
            require(row.get("transportation_mode") in MODES, f"{run_id}: invalid transportation_mode {row.get('transportation_mode')!r}", errors)
            require(row.get("destination_type") in DESTINATIONS, f"{run_id}: invalid destination_type {row.get('destination_type')!r}", errors)
            require(row.get("transportation_mode") != "None", f"{run_id}: transportation_mode uses deprecated None label", errors)

    if scores_path.exists():
        score_rows = read_csv(scores_path)
        require(bool(score_rows), f"{scores_path} is empty", errors)
        required_score_fields = [
            "persona_id",
            "condition",
            "decision",
            "transportation_mode",
            "destination_type",
            "any_violation",
            "feasibility_score",
            "spatial_consistency_score",
        ]
        for row in score_rows:
            run_id = row.get("run_id", row.get("persona_id", "<missing id>"))
            for field in required_score_fields:
                require(field in row and bool((row.get(field) or "").strip()), f"{run_id}: missing score field {field}", errors)
            require(row.get("decision") in DECISIONS, f"{run_id}: invalid decision {row.get('decision')!r}", errors)
            require(row.get("transportation_mode") in MODES, f"{run_id}: invalid transportation_mode {row.get('transportation_mode')!r}", errors)
            require(row.get("destination_type") in DESTINATIONS, f"{run_id}: invalid destination_type {row.get('destination_type')!r}", errors)

    if errors:
        for error in errors[:50]:
            print(f"ERROR: {error}")
        if len(errors) > 50:
            print(f"ERROR: ... {len(errors) - 50} more")
        raise SystemExit(1)

    print(f"Validation passed for {output_dir}")


if __name__ == "__main__":
    main()
