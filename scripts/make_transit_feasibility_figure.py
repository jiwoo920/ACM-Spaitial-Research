#!/usr/bin/env python3
"""Create transit feasibility Figure 1 candidate."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "main_experiment_gpt_acs_200"
FIGURE_DIR = ROOT / "figures" / "main_experiment_gpt_acs_200"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    transit = read_csv(OUTPUT_DIR / "transit_access_mode_analysis.csv")
    subgroup = read_csv(OUTPUT_DIR / "no_vehicle_transit_access_analysis.csv")

    def limited_public(condition: str) -> float:
        rows = [
            row for row in transit
            if row["condition"] == condition
            and row["transit_access"] == "Limited"
            and row["transportation_mode"] == "Public transit"
        ]
        return float(rows[0]["rate"]) * 100.0

    def subgroup_value(condition: str, field: str) -> float:
        rows = [
            row for row in subgroup
            if row["condition"] == condition
            and row["subgroup"] == "no_vehicle_limited_or_no_transit"
        ]
        return float(rows[0][field]) * 100.0

    rows = [
        {
            "check": "Public transit selected\nwhen transit is limited",
            "condition": "Baseline",
            "rate": limited_public("baseline"),
        },
        {
            "check": "Public transit selected\nwhen transit is limited",
            "condition": "Spatially grounded",
            "rate": limited_public("spatial_grounded"),
        },
        {
            "check": "Public transit selected for\nno-vehicle + limited/no transit",
            "condition": "Baseline",
            "rate": subgroup_value("baseline", "public_transit_rate"),
        },
        {
            "check": "Public transit selected for\nno-vehicle + limited/no transit",
            "condition": "Spatially grounded",
            "rate": subgroup_value("spatial_grounded", "public_transit_rate"),
        },
        {
            "check": "Violation/inconsistency for\nno-vehicle + limited/no transit",
            "condition": "Baseline",
            "rate": subgroup_value("baseline", "violation_or_spatial_inconsistency_rate"),
        },
        {
            "check": "Violation/inconsistency for\nno-vehicle + limited/no transit",
            "condition": "Spatially grounded",
            "rate": subgroup_value("spatial_grounded", "violation_or_spatial_inconsistency_rate"),
        },
    ]

    out = OUTPUT_DIR / "transit_feasibility_figure_data.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["check", "condition", "rate"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
