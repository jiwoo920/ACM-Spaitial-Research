#!/usr/bin/env python3
"""Generate exploratory result candidates for SRC figure/table selection."""

from __future__ import annotations

import csv
import json
import math
import statistics
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_OUTPUT = ROOT / "outputs" / "main_experiment_gpt_acs_200"
DATA = ROOT / "data"
CANDIDATE_OUTPUT = ROOT / "outputs" / "result_candidates"
CANDIDATE_FIGURES = ROOT / "figures" / "result_candidates"

REPRESENTATIVE_FIRE = {
    "name": "Representative Griffith Park wildfire point",
    "latitude": 34.1366,
    "longitude": -118.2942,
    "note": "Exploratory representative point for distance-to-fire candidate analysis; not a real incident perimeter.",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and not fieldnames:
        raise ValueError(f"Cannot write empty CSV without fieldnames: {path}")
    fieldnames = fieldnames or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def pct(rows: list[dict[str, str]], predicate) -> float:
    return 100.0 * sum(1 for row in rows if predicate(row)) / len(rows) if rows else 0.0


def mean(rows: list[dict[str, str]], field: str) -> float:
    vals = [float(row[field]) for row in rows if row.get(field) not in {"", None}]
    return sum(vals) / len(vals) if vals else 0.0


def summarize_group(rows: list[dict[str, str]], group: str, condition: str) -> dict[str, object]:
    return {
        "group": group,
        "condition": condition,
        "n": len(rows),
        "violation_or_spatial_inconsistency_rate": round(pct(rows, lambda r: r["any_violation"] == "1"), 1),
        "spatial_inconsistency_rate": round(pct(rows, lambda r: int(r["spatial_inconsistency_count"]) > 0), 1),
        "soft_feasibility_issue_rate": round(pct(rows, lambda r: r["any_soft_issue"] == "1"), 1),
        "public_shelter_destination_rate": round(pct(rows, lambda r: r["destination_type"] == "Public shelter"), 1),
        "hotel_motel_destination_rate": round(pct(rows, lambda r: r["destination_type"] == "Hotel/motel"), 1),
        "mean_feasibility_score": round(mean(rows, "feasibility_score"), 3),
        "mean_spatial_consistency_score": round(mean(rows, "spatial_consistency_score"), 3),
    }


def income_group(row: dict[str, str]) -> str:
    return "lower_income" if row.get("is_low_income") == "1" else "higher_income"


def write_income_outputs(scores: list[dict[str, str]]) -> None:
    rows = []
    for condition in ["baseline", "spatial_grounded"]:
        condition_rows = [r for r in scores if r["condition"] == condition]
        for group in ["lower_income", "higher_income"]:
            subset = [r for r in condition_rows if income_group(r) == group]
            rows.append(summarize_group(subset, group, condition))
    write_csv(CANDIDATE_OUTPUT / "income_group_analysis.csv", rows)

    dest_rows = []
    for condition in ["baseline", "spatial_grounded"]:
        for group in ["lower_income", "higher_income"]:
            subset = [r for r in scores if r["condition"] == condition and income_group(r) == group]
            counts = Counter(r["destination_type"] for r in subset)
            total = len(subset) or 1
            for destination, count in sorted(counts.items()):
                dest_rows.append({
                    "condition": condition,
                    "income_group": group,
                    "destination_type": destination,
                    "n": count,
                    "share_percent": round(100.0 * count / total, 1),
                })
    write_csv(CANDIDATE_OUTPUT / "income_destination_analysis.csv", dest_rows)

    lines = [
        "# Income Subgroup Analysis",
        "",
        "This candidate uses the existing GPT-4.1-mini 400-response main experiment. Lower-income households are defined by the existing `is_low_income` feasibility-rule flag.",
        "",
        "## Summary",
        "",
        "| Group | Condition | n | Violation/spatial inconsistency | Soft issue | Public shelter | Hotel/motel |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['group']} | {row['condition']} | {row['n']} | "
            f"{row['violation_or_spatial_inconsistency_rate']}% | {row['soft_feasibility_issue_rate']}% | "
            f"{row['public_shelter_destination_rate']}% | {row['hotel_motel_destination_rate']}% |"
        )
    lines += [
        "",
        "## Interpretation Candidate",
        "",
        "Income-related patterns are useful as a secondary equity result, especially for destination feasibility. However, this analysis should not replace the main mobility-feasibility finding unless destination-type differences are clearer than the vehicle/transit results.",
    ]
    (CANDIDATE_OUTPUT / "income_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_transit_outputs(scores: list[dict[str, str]]) -> None:
    mode_rows = []
    for condition in ["baseline", "spatial_grounded"]:
        condition_rows = [r for r in scores if r["condition"] == condition]
        for transit in ["Good", "Moderate", "Limited", "None"]:
            subset = [r for r in condition_rows if r["transit_access"] == transit]
            total = len(subset) or 1
            counts = Counter(r["transportation_mode"] for r in subset)
            for mode, count in sorted(counts.items()):
                mode_rows.append({
                    "condition": condition,
                    "transit_access": transit,
                    "transportation_mode": mode,
                    "n": count,
                    "share_percent": round(100.0 * count / total, 1),
                })
            mode_rows.append({
                "condition": condition,
                "transit_access": transit,
                "transportation_mode": "__public_transit_total__",
                "n": counts["Public transit"],
                "share_percent": round(100.0 * counts["Public transit"] / total, 1),
            })
    write_csv(CANDIDATE_OUTPUT / "transit_access_mode_analysis.csv", mode_rows)

    subgroup_rows = []
    for condition in ["baseline", "spatial_grounded"]:
        subset = [
            r for r in scores
            if r["condition"] == condition
            and r["vehicle_access"] == "No"
            and r["transit_access"] in {"Limited", "None"}
        ]
        subgroup_rows.append({
            "condition": condition,
            "n": len(subset),
            "violation_or_spatial_inconsistency_rate": round(pct(subset, lambda r: r["any_violation"] == "1"), 1),
            "spatial_inconsistency_rate": round(pct(subset, lambda r: int(r["spatial_inconsistency_count"]) > 0), 1),
            "public_transit_mode_rate": round(pct(subset, lambda r: r["transportation_mode"] == "Public transit"), 1),
            "ride_with_family_friend_rate": round(pct(subset, lambda r: r["transportation_mode"] == "Ride with family/friend"), 1),
            "emergency_transport_rate": round(pct(subset, lambda r: r["transportation_mode"] == "Emergency transport"), 1),
            "public_shelter_destination_rate": round(pct(subset, lambda r: r["destination_type"] == "Public shelter"), 1),
        })
    write_csv(CANDIDATE_OUTPUT / "no_vehicle_transit_access_analysis.csv", subgroup_rows)

    limited = {
        condition: [
            r for r in scores
            if r["condition"] == condition and r["transit_access"] == "Limited"
        ]
        for condition in ["baseline", "spatial_grounded"]
    }
    lines = [
        "# Transit Access Candidate Analysis",
        "",
        "This candidate keeps the existing transit result but separates the overall limited-transit pattern from the no-vehicle + limited/no transit subgroup.",
        "",
        "## Key Checks",
        "",
        f"- Public transit selected when transit access is limited: baseline {pct(limited['baseline'], lambda r: r['transportation_mode'] == 'Public transit'):.1f}%, spatially grounded {pct(limited['spatial_grounded'], lambda r: r['transportation_mode'] == 'Public transit'):.1f}%.",
    ]
    for row in subgroup_rows:
        lines.append(
            f"- No-vehicle + limited/no transit, {row['condition']}: n={row['n']}, "
            f"violation/spatial-inconsistency {row['violation_or_spatial_inconsistency_rate']}%, "
            f"public transit {row['public_transit_mode_rate']}%, ride {row['ride_with_family_friend_rate']}%, "
            f"public shelter {row['public_shelter_destination_rate']}%."
        )
    lines += [
        "",
        "## Interpretation Candidate",
        "",
        "Transit access helps explain why no-vehicle households remain difficult for LLM-generated evacuation planning. Spatially grounded prompting appears to reduce public-transit recommendations when transit is limited, but mobility feasibility risks remain in the no-vehicle + limited/no transit subgroup.",
    ]
    (CANDIDATE_OUTPUT / "transit_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def fetch_selected_tracts_geojson(tract_ids: list[str]) -> dict:
    where = "GEOID IN (" + ",".join(f"'{tract_id}'" for tract_id in tract_ids) + ")"
    params = {
        "where": where,
        "outFields": "GEOID,BASENAME,STATE,COUNTY,TRACT,CENTLAT,CENTLON",
        "f": "geojson",
        "returnGeometry": "true",
        "outSR": "4326",
    }
    url = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer/0/query?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.load(response)
    if not data.get("features"):
        raise RuntimeError("TIGERweb returned no tract features")
    return data


def distance_group(distance: float, q1: float, q2: float) -> str:
    if distance <= q1:
        return "near"
    if distance <= q2:
        return "medium"
    return "far"


def write_fire_distance_outputs(scores: list[dict[str, str]]) -> None:
    profiles = read_csv(DATA / "acs_tract_profiles_20_official_acs.csv")
    tract_ids = [row["census_tract_id"] for row in profiles]
    geojson = fetch_selected_tracts_geojson(tract_ids)
    by_tract = {feature["properties"]["GEOID"]: feature for feature in geojson["features"]}

    tract_rows = []
    for profile in profiles:
        tract_id = profile["census_tract_id"]
        feature = by_tract[tract_id]
        props = feature["properties"]
        lat = float(props["CENTLAT"])
        lon = float(props["CENTLON"])
        distance = haversine_km(lat, lon, REPRESENTATIVE_FIRE["latitude"], REPRESENTATIVE_FIRE["longitude"])
        feature["properties"].update({
            "distance_to_nearest_fire_km": round(distance, 2),
            "representative_fire_name": REPRESENTATIVE_FIRE["name"],
        })
        tract_rows.append({
            "census_tract_id": tract_id,
            "neighborhood_label": profile["neighborhood_label"],
            "centroid_lat": lat,
            "centroid_lon": lon,
            "distance_to_nearest_fire_km": round(distance, 2),
        })
    distances = sorted(row["distance_to_nearest_fire_km"] for row in tract_rows)
    q1 = statistics.quantiles(distances, n=3)[0]
    q2 = statistics.quantiles(distances, n=3)[1]
    tract_group = {}
    for row in tract_rows:
        group = distance_group(row["distance_to_nearest_fire_km"], q1, q2)
        row["fire_distance_group"] = group
        tract_group[row["census_tract_id"]] = row

    write_csv(DATA / "selected_tracts_fire_distance.csv", tract_rows)

    fire_feature = {
        "type": "Feature",
        "properties": REPRESENTATIVE_FIRE,
        "geometry": {
            "type": "Point",
            "coordinates": [REPRESENTATIVE_FIRE["longitude"], REPRESENTATIVE_FIRE["latitude"]],
        },
    }
    map_geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "source": "U.S. Census TIGERweb Census Tracts layer; representative wildfire point is exploratory.",
        },
        "features": geojson["features"] + [fire_feature],
    }
    (CANDIDATE_OUTPUT / "selected_tracts_fire_map.geojson").write_text(json.dumps(map_geojson, indent=2), encoding="utf-8")

    enriched_scores = []
    for row in scores:
        new_row = dict(row)
        tract = tract_group.get(row.get("census_tract_id", ""))
        if not tract:
            # feasibility_scores do not carry tract id, so join through persona file below.
            pass
        enriched_scores.append(new_row)

    personas = {row["persona_id"]: row for row in read_csv(DATA / "personas_acs_200.csv")}
    for row in enriched_scores:
        tract = tract_group[personas[row["persona_id"]]["census_tract_id"]]
        row["census_tract_id"] = personas[row["persona_id"]]["census_tract_id"]
        row["distance_to_nearest_fire_km"] = str(tract["distance_to_nearest_fire_km"])
        row["fire_distance_group"] = tract["fire_distance_group"]

    analysis_rows = []
    for condition in ["baseline", "spatial_grounded"]:
        for group in ["near", "medium", "far"]:
            subset = [r for r in enriched_scores if r["condition"] == condition and r["fire_distance_group"] == group]
            decisions = Counter(r["decision"] for r in subset)
            urgency = Counter(r["departure_urgency"] for r in subset)
            destinations = Counter(r["destination_type"] for r in subset)
            total = len(subset) or 1
            analysis_rows.append({
                "condition": condition,
                "fire_distance_group": group,
                "n": len(subset),
                "mean_distance_to_fire_km": round(sum(float(r["distance_to_nearest_fire_km"]) for r in subset) / total, 2),
                "evacuate_now_rate": round(100.0 * decisions["Evacuate now"] / total, 1),
                "delay_rate": round(100.0 * decisions["Delay evacuation"] / total, 1),
                "stay_rate": round(100.0 * decisions["Stay"] / total, 1),
                "high_urgency_rate": round(100.0 * urgency["High"] / total, 1),
                "spatial_inconsistency_rate": round(pct(subset, lambda r: int(r["spatial_inconsistency_count"]) > 0), 1),
                "public_shelter_destination_rate": round(100.0 * destinations["Public shelter"] / total, 1),
                "hotel_motel_destination_rate": round(100.0 * destinations["Hotel/motel"] / total, 1),
                "friend_relative_destination_rate": round(100.0 * destinations["Friend/relative home"] / total, 1),
            })
    write_csv(CANDIDATE_OUTPUT / "fire_distance_analysis.csv", analysis_rows)

    lines = [
        "# Fire-Distance Candidate Analysis",
        "",
        f"Distance-to-fire is computed from TIGERweb tract centroids to a representative point: {REPRESENTATIVE_FIRE['name']} ({REPRESENTATIVE_FIRE['latitude']}, {REPRESENTATIVE_FIRE['longitude']}).",
        "",
        "This is an exploratory variable for result-candidate generation, not a verified wildfire perimeter or operational fire-distance measure.",
        "",
        "| Group | Condition | n | Mean distance km | Evacuate now | High urgency | Spatial inconsistency | Public shelter |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in analysis_rows:
        lines.append(
            f"| {row['fire_distance_group']} | {row['condition']} | {row['n']} | {row['mean_distance_to_fire_km']} | "
            f"{row['evacuate_now_rate']}% | {row['high_urgency_rate']}% | {row['spatial_inconsistency_rate']}% | "
            f"{row['public_shelter_destination_rate']}% |"
        )
    lines += [
        "",
        "## Interpretation Candidate",
        "",
        "Distance-to-fire is a promising spatial variable for positioning the study, but this candidate should be described as approximate until linked to verified wildfire perimeters or risk surfaces.",
    ]
    (CANDIDATE_OUTPUT / "fire_distance_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_cross_model_outputs(main_scores: list[dict[str, str]]) -> None:
    cross_path = ROOT.parent / "project" / "outputs" / "cross_model_validation_openai_50" / "feasibility_scores.csv"
    cross_rows = read_csv(cross_path) if cross_path.exists() else []
    if not cross_rows:
        lines = [
            "# Cross-Model Comparison Candidate",
            "",
            "No second-model feasibility score file was found. Gemini/Claude comparison requires new provider credentials and new model runs.",
        ]
        (CANDIDATE_OUTPUT / "cross_model_comparison_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        write_csv(CANDIDATE_OUTPUT / "cross_model_comparison_summary.csv", [], fieldnames=["model", "condition", "metric", "value"])
        return

    subset_personas = sorted({row["persona_id"] for row in cross_rows})
    model_rows = []
    datasets = {
        "gpt-4.1-mini_main_subset": [r for r in main_scores if r["persona_id"] in subset_personas],
        "gpt-4o-mini_validation_50": cross_rows,
    }
    for model, rows in datasets.items():
        for condition in ["baseline", "spatial_grounded"]:
            subset = [r for r in rows if r["condition"] == condition]
            no_vehicle = [r for r in subset if r["vehicle_access"] == "No"]
            limited = [r for r in subset if r["transit_access"] == "Limited"]
            lower_income = [r for r in subset if income_group(r) == "lower_income"]
            metrics = {
                "mode_feasibility_rate": pct(subset, lambda r: r["mode_feasible"] == "1"),
                "soft_feasibility_issue_rate": pct(subset, lambda r: r["any_soft_issue"] == "1"),
                "spatial_inconsistency_rate": pct(subset, lambda r: int(r["spatial_inconsistency_count"]) > 0),
                "no_vehicle_violation_or_spatial_inconsistency_rate": pct(no_vehicle, lambda r: r["any_violation"] == "1"),
                "limited_transit_public_transit_rate": pct(limited, lambda r: r["transportation_mode"] == "Public transit"),
                "lower_income_public_shelter_rate": pct(lower_income, lambda r: r["destination_type"] == "Public shelter"),
                "lower_income_hotel_motel_rate": pct(lower_income, lambda r: r["destination_type"] == "Hotel/motel"),
            }
            for metric, value in metrics.items():
                model_rows.append({
                    "model": model,
                    "condition": condition,
                    "n": len(subset),
                    "metric": metric,
                    "value_percent": round(value, 1),
                })
    write_csv(CANDIDATE_OUTPUT / "cross_model_comparison_summary.csv", model_rows)

    lines = [
        "# Cross-Model Comparison Candidate",
        "",
        "This comparison uses the existing gpt-4o-mini 50-persona validation subset and the matching GPT-4.1-mini main-experiment personas. Gemini and Claude are not included because no Gemini/Anthropic run has been executed in the current package.",
        "",
        "| Model | Condition | Metric | Value |",
        "|---|---|---:|---:|",
    ]
    for row in model_rows:
        lines.append(f"| {row['model']} | {row['condition']} | {row['metric']} | {row['value_percent']}% |")
    lines += [
        "",
        "## Interpretation Candidate",
        "",
        "The cross-model candidate should be framed as model sensitivity, not model-invariant robustness. If Gemini or Claude results are added later, this table can become a stronger multi-model comparison.",
    ]
    (CANDIDATE_OUTPUT / "cross_model_comparison_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_candidate_recommendations() -> None:
    lines = [
        "# Figure and Table Candidate Recommendations",
        "",
        "These are candidates for a 2-page SRC abstract. Do not include all of them; use the strongest and clearest subset.",
        "",
        "## Strongest Current Candidates",
        "",
        "1. **Vehicle access figure** (`figures/main_experiment_gpt_acs_200/violation_by_vehicle_access.png`): strongest main finding; directly supports the claim that no-vehicle households are the clearest feasibility-risk group.",
        "2. **Transit secondary table** (`outputs/result_candidates/no_vehicle_transit_access_analysis.csv`): useful compact explanation of why no-vehicle households remain difficult, especially when transit access is limited.",
        "3. **Cross-model comparison table/heatmap** (`outputs/result_candidates/cross_model_comparison_summary.csv`): useful only as a model-sensitivity result, not as a robustness claim.",
        "",
        "## Promising but Secondary",
        "",
        "- **Income analysis**: useful equity candidate, but may broaden the SRC abstract away from mobility/spatial feasibility unless destination-type differences are central.",
        "- **Fire-distance analysis and map**: promising for SIGSPATIAL positioning, but currently based on an exploratory representative point rather than verified wildfire perimeter data.",
        "",
        "## Suggested 2-page SRC Combination",
        "",
        "- Keep Table 1: baseline vs. spatially grounded feasibility metrics.",
        "- Keep Figure 1: vehicle access gap.",
        "- Add either a small transit secondary table or one sentence from the fire-distance/map candidate, depending on available space.",
        "- Mention cross-model comparison in 1 sentence as model sensitivity if space allows.",
        "",
        "## Interpretation Guardrails",
        "",
        "- Say: spatially grounded prompting improves selected metrics.",
        "- Say: feasibility risks remain.",
        "- Say: variable-based analysis reveals which household/spatial constraints matter.",
        "- Say: model comparison reveals model sensitivity.",
        "- Do not say: spatial grounding solves the problem.",
        "- Do not say: the effect is model-invariant.",
        "- Do not say: LLM decisions are reliable.",
    ]
    (CANDIDATE_OUTPUT / "candidate_recommendations.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    CANDIDATE_OUTPUT.mkdir(parents=True, exist_ok=True)
    CANDIDATE_FIGURES.mkdir(parents=True, exist_ok=True)
    scores = read_csv(MAIN_OUTPUT / "feasibility_scores.csv")
    write_income_outputs(scores)
    write_transit_outputs(scores)
    write_fire_distance_outputs(scores)
    write_cross_model_outputs(scores)
    write_candidate_recommendations()
    print(f"Wrote candidate outputs to {CANDIDATE_OUTPUT}")


if __name__ == "__main__":
    main()
