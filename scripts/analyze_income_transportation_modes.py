#!/usr/bin/env python3
"""Analyze transportation mode choice by income group."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PERSONAS = ROOT / "data" / "personas_acs_200.csv"
DEFAULT_SCORES = ROOT / "outputs" / "main_experiment_gpt_acs_200" / "feasibility_scores.csv"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "main_experiment_gpt_acs_200"

MODES = [
    "Private vehicle",
    "Public transit",
    "Ride with family/friend",
    "Emergency transport",
    "Walk",
    "Mixed/other",
    "No transportation",
]

MODE_COLUMNS = {
    "Private vehicle": "Private vehicle",
    "Public transit": "Public transit",
    "Ride with family/friend": "Ride with family/friend",
    "Emergency transport": "Emergency transport",
    "Walk": "Walk",
    "Mixed/other": "Mixed/other",
    "No transportation": "No transportation",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def income_group(row: dict[str, str]) -> str:
    return "Lower income" if row.get("is_low_income") == "1" else "Higher income"


def condition_label(condition: str) -> str:
    return {
        "baseline": "Baseline",
        "spatial_grounded": "Spatially grounded",
    }.get(condition, condition)


def cell(percent: float, count: int) -> str:
    return f"{percent:.1f}% (n={count})"


def pct(count: int, total: int) -> float:
    return 100.0 * count / total if total else 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze income-group transportation mode choice.")
    parser.add_argument("--personas-file", default=str(DEFAULT_PERSONAS))
    parser.add_argument("--scores-file", default=str(DEFAULT_SCORES))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    personas = read_csv(Path(args.personas_file))
    scores = read_csv(Path(args.scores_file))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    long_rows: list[dict[str, object]] = []
    table_rows: list[dict[str, str]] = []

    for group in ["Lower income", "Higher income"]:
        for condition in ["baseline", "spatial_grounded"]:
            subset = [
                row for row in scores
                if income_group(row) == group and row["condition"] == condition
            ]
            counts = Counter(row["transportation_mode"] for row in subset)
            total = len(subset)
            table_row = {
                "Income group": group,
                "Condition": condition_label(condition),
                "Total responses": str(total),
            }
            for mode in MODES:
                count = counts[mode]
                percent = pct(count, total)
                long_rows.append({
                    "income_group": group,
                    "condition": condition_label(condition),
                    "condition_raw": condition,
                    "transportation_mode": mode,
                    "count": count,
                    "percentage": round(percent, 3),
                    "total_responses": total,
                })
                table_row[MODE_COLUMNS[mode]] = cell(percent, count)
            table_rows.append(table_row)

    analysis_path = output_dir / "income_transportation_mode_analysis.csv"
    with analysis_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "income_group",
            "condition",
            "condition_raw",
            "transportation_mode",
            "count",
            "percentage",
            "total_responses",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(long_rows)

    headers = ["Income group", "Condition", *MODES]
    lines = [
        "# Income Group by Transportation Mode",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in table_rows:
        lines.append("| " + " | ".join(row.get(header, "") for header in headers) + " |")
    table_path = output_dir / "income_transportation_mode_table.md"
    table_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Persona-level caveat: income and vehicle access are correlated in the synthetic personas.
    persona_counts = defaultdict(Counter)
    for persona in personas:
        group = "Lower income" if persona.get("income_level") in {"Low", "Lower-middle"} else "Higher income"
        persona_counts[group][persona.get("vehicle_access", "")] += 1

    def row_for(group: str, condition: str, mode: str) -> dict[str, object]:
        for row in long_rows:
            if row["income_group"] == group and row["condition"] == condition and row["transportation_mode"] == mode:
                return row
        raise KeyError((group, condition, mode))

    lower_baseline_private = row_for("Lower income", "Baseline", "Private vehicle")
    higher_baseline_private = row_for("Higher income", "Baseline", "Private vehicle")
    lower_spatial_private = row_for("Lower income", "Spatially grounded", "Private vehicle")
    higher_spatial_private = row_for("Higher income", "Spatially grounded", "Private vehicle")
    lower_baseline_transit = row_for("Lower income", "Baseline", "Public transit")
    higher_baseline_transit = row_for("Higher income", "Baseline", "Public transit")
    lower_spatial_ride = row_for("Lower income", "Spatially grounded", "Ride with family/friend")
    higher_spatial_ride = row_for("Higher income", "Spatially grounded", "Ride with family/friend")

    lower_vehicle_total = sum(persona_counts["Lower income"].values())
    higher_vehicle_total = sum(persona_counts["Higher income"].values())
    lower_no_vehicle_rate = pct(persona_counts["Lower income"]["No"], lower_vehicle_total)
    higher_no_vehicle_rate = pct(persona_counts["Higher income"]["No"], higher_vehicle_total)

    summary = [
        "# Income Transportation Mode Summary",
        "",
        (
            f"Higher-income households received private-vehicle recommendations more often than lower-income households "
            f"in both baseline ({higher_baseline_private['percentage']:.1f}% vs. {lower_baseline_private['percentage']:.1f}%) "
            f"and spatially grounded prompting ({higher_spatial_private['percentage']:.1f}% vs. {lower_spatial_private['percentage']:.1f}%)."
        ),
        (
            f"Lower-income households received more public-transit recommendations in the baseline condition "
            f"({lower_baseline_transit['percentage']:.1f}% vs. {higher_baseline_transit['percentage']:.1f}%), "
            f"while ride-based recommendations in the spatially grounded condition were "
            f"{lower_spatial_ride['percentage']:.1f}% for lower-income households and {higher_spatial_ride['percentage']:.1f}% for higher-income households."
        ),
        (
            "Spatially grounded prompting shifted both income groups strongly toward public-shelter-oriented evacuation planning, "
            "and transportation mode distributions should be interpreted alongside the prompt design and feasibility rules rather than as direct behavioral prediction."
        ),
        (
            f"Income-group differences in transportation mode may partly reflect differences in vehicle access across income groups: "
            f"{lower_no_vehicle_rate:.1f}% of lower-income personas and {higher_no_vehicle_rate:.1f}% of higher-income personas had no vehicle access."
        ),
        (
            "This result should therefore be framed as an exploratory association between income group and recommended transportation mode, not as evidence that income directly causes mode choice."
        ),
        "",
        "For a 2-page SRC abstract, the 100% stacked bar chart is likely more compact and easier to compare than the four pie charts; the pie small multiples are useful for discussion with the professor but less efficient for the final paper.",
    ]
    (output_dir / "income_transportation_mode_summary.md").write_text("\n\n".join(summary) + "\n", encoding="utf-8")

    print(f"Wrote {analysis_path}")
    print(f"Wrote {table_path}")
    print(f"Wrote {output_dir / 'income_transportation_mode_summary.md'}")


if __name__ == "__main__":
    main()
