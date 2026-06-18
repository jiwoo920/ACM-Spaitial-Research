#!/usr/bin/env python3
"""Create summary tables for the wildfire evacuation pilot."""

from __future__ import annotations

import csv
import argparse
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "pipeline_validation"
PAPER = ROOT / "paper"
DEFAULT_PERSONAS_FILE = DATA / "personas.csv"
DEFAULT_SPATIAL_CONTEXT_FILE = DATA / "spatial_context.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def resolve_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_personas(personas_file: Path, spatial_context_file: Path) -> list[dict[str, str]]:
    personas = read_csv(personas_file)
    spatial = {row["persona_id"]: row for row in read_csv(spatial_context_file)} if spatial_context_file.exists() else {}
    merged = []
    for persona in personas:
        row = dict(persona)
        row.update(spatial.get(persona["persona_id"], {}))
        merged.append(row)
    return merged


def mean(rows: list[dict[str, str]], field: str) -> float:
    vals = [float(r[field]) for r in rows]
    return sum(vals) / len(vals) if vals else 0.0


def pct(rows: list[dict[str, str]], predicate) -> float:
    return sum(1 for r in rows if predicate(r)) / len(rows) if rows else 0.0


def write_markdown_table(path: Path, title: str, headers: list[str], rows: list[list[str]]) -> None:
    lines = [f"# {title}", "", "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create summary tables.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--paper-dir", default=str(PAPER))
    parser.add_argument("--personas-file", default=str(DEFAULT_PERSONAS_FILE))
    parser.add_argument("--spatial-context-file", default=str(DEFAULT_SPATIAL_CONTEXT_FILE))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    paper_dir = Path(args.paper_dir)
    paper_dir.mkdir(parents=True, exist_ok=True)
    personas = load_personas(resolve_path(args.personas_file), resolve_path(args.spatial_context_file))
    scores = read_csv(output_dir / "feasibility_scores.csv")

    summary_rows = []
    for condition in ["baseline", "spatial_grounded"]:
        rows = [r for r in scores if r["condition"] == condition]
        summary_rows.append({
            "metric_scope": "condition",
            "group": condition,
            "n_runs": len(rows),
            "evacuation_rate": round(pct(rows, lambda r: r["decision"] == "Evacuate now"), 3),
            "delay_rate": round(pct(rows, lambda r: r["decision"] == "Delay evacuation"), 3),
            "private_vehicle_rate": round(pct(rows, lambda r: r["transportation_mode"] == "Private vehicle"), 3),
            "shelter_dependency_rate": round(pct(rows, lambda r: r["destination_type"] == "Public shelter"), 3),
            "violation_rate": round(mean(rows, "any_violation"), 3),
            "hard_violation_rate": round(mean(rows, "any_hard_violation"), 3),
            "soft_issue_rate": round(mean(rows, "any_soft_issue"), 3),
            "spatial_inconsistency_rate": round(pct(rows, lambda r: int(r["spatial_inconsistency_count"]) > 0), 3),
            "mode_feasibility_rate": round(mean(rows, "mode_feasible"), 3),
            "destination_feasibility_rate": round(mean(rows, "destination_feasible"), 3),
            "mean_feasibility_score": round(mean(rows, "feasibility_score"), 3),
            "mean_spatial_consistency_score": round(mean(rows, "spatial_consistency_score"), 3),
        })

    equity_groups = [
        ("income_low", lambda r: r["is_low_income"] == "1"),
        ("income_middle_high", lambda r: r["is_low_income"] == "0"),
        ("vehicle_yes", lambda r: r["vehicle_access"] == "Yes"),
        ("vehicle_no", lambda r: r["vehicle_access"] == "No"),
        ("children_yes", lambda r: r["has_children"] == "1"),
        ("children_no", lambda r: r["has_children"] == "0"),
        ("medical_yes", lambda r: r["has_medical_need"] == "1"),
        ("medical_no", lambda r: r["has_medical_need"] == "0"),
        ("risk_high", lambda r: r["wildfire_risk_level"] in {"High", "Very high"}),
        ("risk_lower", lambda r: r["wildfire_risk_level"] not in {"High", "Very high"}),
    ]
    for condition in ["baseline", "spatial_grounded"]:
        condition_rows = [r for r in scores if r["condition"] == condition]
        for name, pred in equity_groups:
            rows = [r for r in condition_rows if pred(r)]
            if rows:
                summary_rows.append({
                    "metric_scope": "equity_group",
                    "group": f"{condition}:{name}",
                    "n_runs": len(rows),
                    "evacuation_rate": round(pct(rows, lambda r: r["decision"] == "Evacuate now"), 3),
                    "delay_rate": round(pct(rows, lambda r: r["decision"] == "Delay evacuation"), 3),
                    "private_vehicle_rate": round(pct(rows, lambda r: r["transportation_mode"] == "Private vehicle"), 3),
                    "shelter_dependency_rate": round(pct(rows, lambda r: r["destination_type"] == "Public shelter"), 3),
                    "violation_rate": round(mean(rows, "any_violation"), 3),
                    "hard_violation_rate": round(mean(rows, "any_hard_violation"), 3),
                    "soft_issue_rate": round(mean(rows, "any_soft_issue"), 3),
                    "spatial_inconsistency_rate": round(pct(rows, lambda r: int(r["spatial_inconsistency_count"]) > 0), 3),
                    "mode_feasibility_rate": round(mean(rows, "mode_feasible"), 3),
                    "destination_feasibility_rate": round(mean(rows, "destination_feasible"), 3),
                    "mean_feasibility_score": round(mean(rows, "feasibility_score"), 3),
                    "mean_spatial_consistency_score": round(mean(rows, "spatial_consistency_score"), 3),
                })

    with (output_dir / "summary_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    group_rows = [row for row in summary_rows if row["metric_scope"] == "equity_group"]
    with (output_dir / "group_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(group_rows)

    stability_rows = []
    grouped = defaultdict(list)
    for row in scores:
        grouped[(row["persona_id"], row["condition"])].append(row)
    for (persona_id, condition), rows in sorted(grouped.items()):
        decisions = {r["decision"] for r in rows}
        modes = {r["transportation_mode"] for r in rows}
        destinations = {r["destination_type"] for r in rows}
        stability_rows.append({
            "persona_id": persona_id,
            "condition": condition,
            "n_repeats": len(rows),
            "unique_decisions": len(decisions),
            "unique_transportation_modes": len(modes),
            "unique_destination_types": len(destinations),
            "decision_stable": int(len(decisions) == 1),
            "mode_stable": int(len(modes) == 1),
            "destination_stable": int(len(destinations) == 1),
            "all_outputs_stable": int(len(decisions) == 1 and len(modes) == 1 and len(destinations) == 1),
        })

    with (output_dir / "prompt_stability.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(stability_rows[0].keys()))
        writer.writeheader()
        writer.writerows(stability_rows)

    persona_summary = []
    for label, field in [
        ("Income", "income_level"),
        ("Vehicle access", "vehicle_access"),
        ("Household type", "family_structure"),
        ("Medical/caregiving", "medical_caregiving_responsibilities"),
        ("Risk level", "wildfire_risk_level"),
    ]:
        counts = Counter(p[field] for p in personas)
        for value, count in sorted(counts.items()):
            persona_summary.append([label, value, str(count), f"{count / len(personas):.1%}"])
    write_markdown_table(paper_dir / "table1_persona_summary.md", "Table 1. Persona Variable Summary", ["Variable", "Category", "Count", "Share"], persona_summary)

    condition_table = []
    for r in summary_rows[:2]:
        condition_table.append([
            r["group"],
            str(r["n_runs"]),
            f"{float(r['violation_rate']):.1%}",
            f"{float(r['hard_violation_rate']):.1%}",
            f"{float(r['soft_issue_rate']):.1%}",
            f"{float(r['mode_feasibility_rate']):.1%}",
            f"{float(r['destination_feasibility_rate']):.1%}",
            f"{float(r['mean_feasibility_score']):.3f}",
            f"{float(r['mean_spatial_consistency_score']):.3f}",
        ])
    write_markdown_table(
        paper_dir / "table2_feasibility_by_condition.md",
        "Table 2. Feasibility Metrics by Condition",
        ["Condition", "Runs", "Any violation", "Hard violation", "Soft issue", "Mode feasible", "Destination feasible", "Feasibility score", "Spatial consistency"],
        condition_table,
    )

    print(f"Wrote summary metrics to {output_dir / 'summary_metrics.csv'}")
    print(f"Wrote group summary metrics to {output_dir / 'group_summary.csv'}")
    print(f"Wrote prompt stability metrics to {output_dir / 'prompt_stability.csv'}")


if __name__ == "__main__":
    main()
