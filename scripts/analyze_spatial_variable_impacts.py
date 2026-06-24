#!/usr/bin/env python3
"""Generate exploratory spatial-variable impact result candidates.

This script uses the existing GPT-4.1-mini main experiment outputs only. It
does not call any LLM API.
"""

from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs" / "main_experiment_gpt_acs_200"
FIG_DIR = ROOT / "figures" / "main_experiment_gpt_acs_200"

CONDITION_ORDER = ["baseline", "spatial_grounded"]
CONDITION_LABEL = {"baseline": "Baseline", "spatial_grounded": "Spatially grounded"}
MODE_ORDER = [
    "Private vehicle",
    "Public transit",
    "Ride with family/friend",
    "Emergency transport",
    "Walk",
    "Mixed/other",
    "No transportation",
]
KEYWORDS_SPATIAL = re.compile(
    r"\b(?:spatial|shelter|transit|distance|nearby|near|close|travel time|road|hazard|fire|wildfire|zone|risk)\b",
    re.I,
)
KEYWORDS_HAZARD = re.compile(r"\b(?:fire|wildfire|hazard|close|nearby|distance|urgent|evacuation zone|zone)\b", re.I)
KEYWORDS_NEARBY_SHELTER = re.compile(r"\b(?:nearby shelter|nearest shelter|close shelter|proximity to shelter|reasonable travel time|accessible shelter)\b", re.I)


def pct(x: float) -> float:
    return round(float(x) * 100, 1)


def rate(series: pd.Series) -> float:
    return pct(series.mean()) if len(series) else 0.0


def classify_income(value: str) -> str:
    v = str(value).strip().lower()
    if v in {"low", "lower", "lower-middle"} or "low" in v:
        return "Lower income"
    return "Higher income"


def tertile_group(series: pd.Series, labels: list[str]) -> pd.Series:
    ranked = series.rank(method="first")
    return pd.qcut(ranked, q=3, labels=labels)


def condition_display(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["condition_label"] = out["condition"].map(CONDITION_LABEL).fillna(out["condition"])
    return out


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["condition_label"] = out["condition"].map(CONDITION_LABEL)
    out["vehicle_group"] = out["vehicle_access"].map(lambda x: "No vehicle" if str(x).strip().lower() == "no" else "Vehicle access")
    out["income_group"] = out["income_level"].map(classify_income)
    out["limited_no_transit"] = out["transit_access"].isin(["Limited", "None"])
    out["mobility_constrained_broad"] = (out["vehicle_group"] == "No vehicle") | out["limited_no_transit"]
    out["mobility_constrained_strict"] = (out["vehicle_group"] == "No vehicle") & out["limited_no_transit"]
    out["any_violation_or_spatial_inconsistency"] = (out["any_violation"].astype(int) > 0) | (
        out["spatial_inconsistency_count"].astype(int) > 0
    )
    out["public_transit_selected"] = out["transportation_mode"].eq("Public transit")
    out["public_shelter_selected"] = out["destination_type"].eq("Public shelter")
    out["evacuate_now"] = out["decision"].eq("Evacuate now")
    out["high_urgency"] = out["departure_urgency"].str.lower().eq("high")
    out["reasoning_text"] = (
        out.get("reasoning", pd.Series("", index=out.index)).fillna("")
        + " "
        + out.get("key_constraints_considered", pd.Series("", index=out.index)).fillna("")
    )
    out["spatial_keyword_mentioned"] = out["reasoning_text"].str.contains(KEYWORDS_SPATIAL)
    out["hazard_keyword_mentioned"] = out["reasoning_text"].str.contains(KEYWORDS_HAZARD)
    out["nearby_shelter_claim"] = out["reasoning_text"].str.contains(KEYWORDS_NEARBY_SHELTER)
    out["shelter_distance_group"] = tertile_group(out["distance_to_nearest_shelter"].astype(float), ["Near", "Medium", "Far"])
    out["road_travel_time_group"] = tertile_group(out["road_travel_time_to_shelter"].astype(float), ["Short", "Medium", "Long"])
    out["hazard_distance_group"] = tertile_group(out["distance_to_hazard_zone"].astype(float), ["Near", "Medium", "Far"])
    out["nearby_shelter_inconsistency"] = out["nearby_shelter_claim"] & (
        out["shelter_distance_group"].eq("Far") | out["road_travel_time_group"].eq("Long")
    )
    return out


def grouped_rates(df: pd.DataFrame, group_cols: list[str], metrics: dict[str, str]) -> pd.DataFrame:
    rows = []
    for keys, g in df.groupby(group_cols, dropna=False, observed=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(group_cols, keys))
        row["n"] = len(g)
        for out_name, col in metrics.items():
            row[out_name] = rate(g[col])
        rows.append(row)
    return pd.DataFrame(rows)


def write_md(path: Path, text: str) -> None:
    path.write_text(dedent(text).strip() + "\n", encoding="utf-8")


def paired_prompt_change(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = [
        "persona_id",
        "repeat",
        "condition",
        "decision",
        "transportation_mode",
        "destination_type",
        "departure_urgency",
        "spatial_keyword_mentioned",
        "vehicle_group",
        "limited_no_transit",
        "income_group",
    ]
    wide = df[cols].pivot(index=["persona_id", "repeat"], columns="condition")
    rows = []
    subgroup_defs = {
        "All personas": pd.Series(True, index=df[["persona_id", "repeat"]].drop_duplicates().set_index(["persona_id", "repeat"]).index),
    }
    base_meta = df[df["condition"] == "baseline"].set_index(["persona_id", "repeat"])
    subgroup_defs = {
        "All personas": pd.Series(True, index=base_meta.index),
        "No-vehicle households": base_meta["vehicle_group"].eq("No vehicle"),
        "Vehicle-access households": base_meta["vehicle_group"].eq("Vehicle access"),
        "Limited/no transit households": base_meta["limited_no_transit"],
        "Lower-income households": base_meta["income_group"].eq("Lower income"),
        "Higher-income households": base_meta["income_group"].eq("Higher income"),
    }
    changes = pd.DataFrame(index=base_meta.index)
    changes["decision changed"] = wide[("decision", "baseline")] != wide[("decision", "spatial_grounded")]
    changes["mode changed"] = wide[("transportation_mode", "baseline")] != wide[("transportation_mode", "spatial_grounded")]
    changes["destination changed"] = wide[("destination_type", "baseline")] != wide[("destination_type", "spatial_grounded")]
    changes["urgency changed"] = wide[("departure_urgency", "baseline")] != wide[("departure_urgency", "spatial_grounded")]
    changes["reasoning spatial keyword mention changed"] = (
        wide[("spatial_keyword_mentioned", "baseline")] != wide[("spatial_keyword_mentioned", "spatial_grounded")]
    )
    for subgroup, mask in subgroup_defs.items():
        g = changes.loc[mask[mask].index]
        row = {"subgroup": subgroup, "n_pairs": len(g)}
        for col in changes.columns:
            row[col] = rate(g[col])
        rows.append(row)
    summary = pd.DataFrame(rows)
    plot = summary[summary["subgroup"].eq("All personas")].melt(
        id_vars=["subgroup", "n_pairs"], var_name="change_metric", value_name="rate"
    )
    order = [
        "decision changed",
        "mode changed",
        "destination changed",
        "urgency changed",
        "reasoning spatial keyword mention changed",
    ]
    plot["change_metric"] = pd.Categorical(plot["change_metric"], order, ordered=True)
    return summary, plot


def transit_access_impact(df: pd.DataFrame) -> pd.DataFrame:
    metrics = {
        "public_transit_selected_rate": "public_transit_selected",
        "violation_or_spatial_inconsistency_rate": "any_violation_or_spatial_inconsistency",
    }
    rates = grouped_rates(df, ["condition_label", "transit_access"], metrics)
    mode_dist = (
        df.groupby(["condition_label", "transit_access", "transportation_mode"])
        .size()
        .rename("count")
        .reset_index()
    )
    totals = mode_dist.groupby(["condition_label", "transit_access"])["count"].transform("sum")
    mode_dist["percentage"] = (mode_dist["count"] / totals * 100).round(1)
    out = mode_dist.merge(rates, on=["condition_label", "transit_access"], how="left")
    return out


def shelter_accessibility_impact(df: pd.DataFrame) -> pd.DataFrame:
    metrics = {
        "public_shelter_selected_rate": "public_shelter_selected",
        "spatial_inconsistency_rate": "any_violation_or_spatial_inconsistency",
        "nearby_shelter_inconsistency_rate": "nearby_shelter_inconsistency",
    }
    by_distance = grouped_rates(df, ["condition_label", "shelter_distance_group"], metrics)
    by_distance["attribute"] = "Shelter distance"
    by_distance = by_distance.rename(columns={"shelter_distance_group": "group"})
    by_time = grouped_rates(df, ["condition_label", "road_travel_time_group"], metrics)
    by_time["attribute"] = "Road travel time"
    by_time = by_time.rename(columns={"road_travel_time_group": "group"})
    out = pd.concat([by_distance, by_time], ignore_index=True)
    return out


def hazard_distance_impact(df: pd.DataFrame, paired_summary: pd.DataFrame | None = None) -> pd.DataFrame:
    metrics = {
        "evacuate_now_rate": "evacuate_now",
        "high_urgency_rate": "high_urgency",
        "hazard_keyword_mention_rate": "hazard_keyword_mentioned",
    }
    by_risk = grouped_rates(df, ["condition_label", "wildfire_risk_level"], metrics)
    by_risk["attribute"] = "Wildfire risk level"
    by_risk = by_risk.rename(columns={"wildfire_risk_level": "group"})
    by_dist = grouped_rates(df, ["condition_label", "hazard_distance_group"], metrics)
    by_dist["attribute"] = "Hazard distance"
    by_dist = by_dist.rename(columns={"hazard_distance_group": "group"})

    base = df[df["condition"] == "baseline"].set_index(["persona_id", "repeat"])
    spatial = df[df["condition"] == "spatial_grounded"].set_index(["persona_id", "repeat"])
    pair = base[["hazard_distance_group", "decision", "destination_type"]].join(
        spatial[["decision", "destination_type"]], lsuffix="_baseline", rsuffix="_spatial"
    )
    changes = []
    for group, g in pair.groupby("hazard_distance_group", observed=False):
        changes.append(
            {
                "condition_label": "Paired change",
                "attribute": "Hazard distance",
                "group": group,
                "n": len(g),
                "decision_changed_rate": rate(g["decision_baseline"] != g["decision_spatial"]),
                "destination_changed_rate": rate(g["destination_type_baseline"] != g["destination_type_spatial"]),
            }
        )
    out = pd.concat([by_risk, by_dist, pd.DataFrame(changes)], ignore_index=True)
    return out


def combined_spatial_constraint_analysis(df: pd.DataFrame) -> pd.DataFrame:
    subgroup_masks = {
        "No vehicle + limited/no transit": (df["vehicle_group"] == "No vehicle") & df["limited_no_transit"],
        "No vehicle + long shelter travel time": (df["vehicle_group"] == "No vehicle") & df["road_travel_time_group"].eq("Long"),
        "High wildfire risk + limited/no transit": df["wildfire_risk_level"].eq("High") & df["limited_no_transit"],
        "Near hazard + mobility constrained": df["hazard_distance_group"].eq("Near") & df["mobility_constrained_broad"],
        "Long shelter travel time + limited/no transit": df["road_travel_time_group"].eq("Long") & df["limited_no_transit"],
    }
    rows = []
    for subgroup, mask in subgroup_masks.items():
        for condition, g in df[mask].groupby("condition_label"):
            rows.append(
                {
                    "subgroup": subgroup,
                    "condition_label": condition,
                    "n": len(g),
                    "violation_spatial_inconsistency_rate": rate(g["any_violation_or_spatial_inconsistency"]),
                    "soft_feasibility_issue_rate": rate(g["any_soft_issue"]),
                    "mode_feasibility_rate": rate(g["mode_feasible"]),
                    "public_transit_selected_rate": rate(g["public_transit_selected"]),
                    "public_shelter_selected_rate": rate(g["public_shelter_selected"]),
                    "mean_feasibility_score": round(g["feasibility_score"].mean(), 3) if len(g) else 0,
                }
            )
    out = pd.DataFrame(rows)
    return out


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    personas = pd.read_csv(DATA_DIR / "personas_acs_200.csv", keep_default_na=False)
    parsed = pd.read_csv(OUT_DIR / "llm_responses_parsed.csv", keep_default_na=False)
    scores = pd.read_csv(OUT_DIR / "feasibility_scores.csv", keep_default_na=False)

    parsed_small = parsed[["run_id", "reasoning", "key_constraints_considered", "raw_response"]]
    df = scores.merge(parsed_small, on="run_id", how="left")
    persona_income = personas[["persona_id", "income_category", "tract_median_income", "tract_percent_no_vehicle", "tract_poverty_rate"]]
    df = df.merge(persona_income, on="persona_id", how="left")
    df = add_derived_columns(df)

    paired, _ = paired_prompt_change(df)
    paired.to_csv(OUT_DIR / "paired_prompt_change_analysis.csv", index=False)
    paired[paired["subgroup"].eq("All personas")].melt(
        id_vars=["subgroup", "n_pairs"], var_name="change_metric", value_name="rate"
    ).to_csv(OUT_DIR / "paired_prompt_change_plot_data.csv", index=False)

    transit = transit_access_impact(df)
    transit.to_csv(OUT_DIR / "transit_access_impact.csv", index=False)
    transit[
        ["condition_label", "transit_access", "public_transit_selected_rate", "violation_or_spatial_inconsistency_rate"]
    ].drop_duplicates().to_csv(OUT_DIR / "transit_access_impact_plot_data.csv", index=False)

    shelter = shelter_accessibility_impact(df)
    shelter.to_csv(OUT_DIR / "shelter_accessibility_impact.csv", index=False)
    shelter[shelter["attribute"].eq("Road travel time")].to_csv(
        OUT_DIR / "shelter_accessibility_plot_data.csv", index=False
    )

    hazard = hazard_distance_impact(df)
    hazard.to_csv(OUT_DIR / "hazard_distance_impact.csv", index=False)
    hazard[hazard["attribute"].eq("Hazard distance")].to_csv(OUT_DIR / "hazard_distance_plot_data.csv", index=False)

    combined = combined_spatial_constraint_analysis(df)
    combined.to_csv(OUT_DIR / "combined_spatial_constraint_analysis.csv", index=False)
    combined.to_csv(OUT_DIR / "combined_spatial_constraint_plot_data.csv", index=False)

    # Summary markdown files.
    all_pair = paired[paired["subgroup"].eq("All personas")].iloc[0]
    write_md(
        OUT_DIR / "paired_prompt_change_summary.md",
        f"""
        # Paired Prompt Change Analysis

        Spatially grounded prompting changed transportation mode in {all_pair['mode changed']:.1f}% of paired persona responses and destination type in {all_pair['destination changed']:.1f}%, compared with decision changes in {all_pair['decision changed']:.1f}% and urgency changes in {all_pair['urgency changed']:.1f}%. Reasoning spatial-keyword mention changed in {all_pair['reasoning spatial keyword mention changed']:.1f}% of pairs. This suggests the spatial prompt affected mode/destination choices and spatial language more than the top-level evacuation decision.
        """,
    )

    limited = transit[transit["transit_access"].isin(["Limited", "None"])]
    limited_rates = limited.groupby("condition_label")["public_transit_selected_rate"].mean().to_dict()
    nvlt = combined[combined["subgroup"].eq("No vehicle + limited/no transit")]
    write_md(
        OUT_DIR / "transit_access_impact_summary.md",
        f"""
        # Transit Access Impact Summary

        Public-transit selection under limited/no transit access averaged {limited_rates.get('Baseline', 0):.1f}% in baseline and {limited_rates.get('Spatially grounded', 0):.1f}% in the spatially grounded condition. The no-vehicle + limited/no transit subgroup remained high risk: {nvlt[nvlt['condition_label'].eq('Baseline')]['violation_spatial_inconsistency_rate'].iloc[0]:.1f}% in baseline and {nvlt[nvlt['condition_label'].eq('Spatially grounded')]['violation_spatial_inconsistency_rate'].iloc[0]:.1f}% spatially grounded. This is one of the strongest result candidates because it shows both improvement and residual feasibility risk.
        """,
    )

    long_time = shelter[(shelter["attribute"].eq("Road travel time")) & (shelter["group"].eq("Long"))]
    write_md(
        OUT_DIR / "shelter_accessibility_summary.md",
        f"""
        # Shelter Accessibility Impact Summary

        Public shelter recommendations persisted even for the long travel-time group: {long_time[long_time['condition_label'].eq('Baseline')]['public_shelter_selected_rate'].iloc[0]:.1f}% in baseline and {long_time[long_time['condition_label'].eq('Spatially grounded')]['public_shelter_selected_rate'].iloc[0]:.1f}% spatially grounded. Nearby-shelter inconsistency remains an exploratory diagnostic rather than a main figure candidate, because the available shelter distance and travel-time attributes are approximate. This result is useful for discussion but weaker than the transit-access analysis.
        """,
    )

    hazard_near = hazard[(hazard["attribute"].eq("Hazard distance")) & (hazard["group"].eq("Near"))]
    write_md(
        OUT_DIR / "hazard_distance_summary.md",
        f"""
        # Wildfire Risk / Hazard Distance Impact Summary

        For the near hazard-distance group, high-urgency responses were {hazard_near[hazard_near['condition_label'].eq('Baseline')]['high_urgency_rate'].iloc[0]:.1f}% in baseline and {hazard_near[hazard_near['condition_label'].eq('Spatially grounded')]['high_urgency_rate'].iloc[0]:.1f}% spatially grounded. Hazard keyword mentions were {hazard_near[hazard_near['condition_label'].eq('Baseline')]['hazard_keyword_mention_rate'].iloc[0]:.1f}% in baseline and {hazard_near[hazard_near['condition_label'].eq('Spatially grounded')]['hazard_keyword_mention_rate'].iloc[0]:.1f}% spatially grounded. Because hazard distances are approximate, this should be framed as exploratory: spatial context may change reasoning salience more clearly than top-level decisions.
        """,
    )

    top_combined = combined.sort_values("violation_spatial_inconsistency_rate", ascending=False).head(4)
    write_md(
        OUT_DIR / "combined_spatial_constraint_summary.md",
        "# Combined Spatial Constraint Summary\n\n"
        + "The highest-risk exploratory combinations are:\n\n"
        + "\n".join(
            f"- {r.subgroup} / {r.condition_label}: {r.violation_spatial_inconsistency_rate:.1f}% risk, n = {int(r.n)}"
            for r in top_combined.itertuples()
        )
        + "\n\nThese patterns suggest mobility constraints remain the strongest feasibility signal. Small subgroup sizes should be interpreted as exploratory rather than generalizable.",
    )

    # Recommendation summary table.
    summary_rows = [
        {
            "Analysis": "Paired response change",
            "Main question": "How much does the spatial prompt change the same persona's response?",
            "Strongest metric": "Mode and destination changed rates",
            "Key result": f"Mode changed {all_pair['mode changed']:.1f}%; destination changed {all_pair['destination changed']:.1f}%; decision changed {all_pair['decision changed']:.1f}%.",
            "Interpretation": "Spatial context appears to affect operational choices more than the top-level decision.",
            "Recommended use": "Use as supporting result or methods validation.",
            "Include in SRC?": "maybe",
        },
        {
            "Analysis": "Transit access impact",
            "Main question": "Does transit access change transportation mode choice?",
            "Strongest metric": "Public transit selected under limited/no transit",
            "Key result": f"Limited/no transit public-transit selection averaged {limited_rates.get('Baseline', 0):.1f}% baseline vs {limited_rates.get('Spatially grounded', 0):.1f}% spatially grounded; no-vehicle + limited/no transit risk remained high.",
            "Interpretation": "Strongest candidate: shows selected improvement plus residual mobility risk.",
            "Recommended use": "Main SRC figure candidate.",
            "Include in SRC?": "yes",
        },
        {
            "Analysis": "Shelter accessibility impact",
            "Main question": "Do shelter distance and travel time affect destination choice?",
            "Strongest metric": "Public shelter selected in long travel-time group",
            "Key result": f"Long travel-time public shelter selection: {long_time[long_time['condition_label'].eq('Baseline')]['public_shelter_selected_rate'].iloc[0]:.1f}% baseline vs {long_time[long_time['condition_label'].eq('Spatially grounded')]['public_shelter_selected_rate'].iloc[0]:.1f}% spatially grounded.",
            "Interpretation": "Useful exploratory evidence; approximate shelter travel-time fields limit claim strength.",
            "Recommended use": "Appendix or professor discussion candidate.",
            "Include in SRC?": "no",
        },
        {
            "Analysis": "Hazard distance impact",
            "Main question": "Does hazard distance affect urgency and reasoning?",
            "Strongest metric": "Hazard keyword mention rate by distance",
            "Key result": f"Near-distance hazard keyword mentions: {hazard_near[hazard_near['condition_label'].eq('Baseline')]['hazard_keyword_mention_rate'].iloc[0]:.1f}% baseline vs {hazard_near[hazard_near['condition_label'].eq('Spatially grounded')]['hazard_keyword_mention_rate'].iloc[0]:.1f}% spatially grounded.",
            "Interpretation": "Exploratory; may show reasoning salience more than actual decision change.",
            "Recommended use": "Mention only if positioning needs spatial-variable breadth.",
            "Include in SRC?": "maybe",
        },
        {
            "Analysis": "Combined spatial constraints",
            "Main question": "Do combined spatial and household constraints identify high-risk groups?",
            "Strongest metric": "Violation/spatial-inconsistency rate by combined subgroup",
            "Key result": f"Highest observed subgroup risk: {top_combined.iloc[0]['subgroup']} / {top_combined.iloc[0]['condition_label']} at {top_combined.iloc[0]['violation_spatial_inconsistency_rate']:.1f}% (n = {int(top_combined.iloc[0]['n'])}).",
            "Interpretation": "Mobility constraints dominate; combined subgroups are informative but often small.",
            "Recommended use": "Secondary result candidate; avoid broad claims.",
            "Include in SRC?": "maybe",
        },
    ]
    summary_table = pd.DataFrame(summary_rows)
    summary_table.to_csv(OUT_DIR / "spatial_variable_impact_summary_table.csv", index=False)
    write_md(
        OUT_DIR / "spatial_variable_impact_recommendation.md",
        """
        # Spatial Variable Impact Recommendation

        ## Ranking of result candidates

        1. **Transit access impact**: strongest SRC candidate. It directly answers whether spatially grounded prompting reduces a concrete feasibility mismatch while showing residual risk for no-vehicle households with limited/no transit access.
        2. **Paired response change analysis**: useful support. It clarifies whether spatial context changes decisions, mode, destination, urgency, or mostly reasoning language.
        3. **Combined spatial constraint analysis**: useful exploratory backup. It identifies high-risk combinations but includes small subgroups, so claims should be cautious.
        4. **Hazard distance impact**: useful for spatial positioning, but approximate hazard distances make this exploratory.
        5. **Shelter accessibility impact**: relevant but weaker as a main figure because approximate shelter/travel-time fields limit interpretability.

        ## Recommended SRC figure/table choice

        Keep the transit-access grouped bar chart as the main Figure 1 candidate. It is more directly tied to the research question than the older vehicle-access-only figure because it shows both selected improvement and remaining feasibility risk.

        A compact paired-change statistic can be added in prose if there is space: spatially grounded prompting changed mode and destination more often than the top-level evacuation decision, suggesting that spatial context may affect operational plan details more than the decision to evacuate.

        ## Short professor-facing summary

        Using the existing 400 GPT-4.1-mini responses, the strongest new candidate result is transit access impact. Spatially grounded prompting reduced public-transit mismatches when transit access was limited, but no-vehicle households with limited/no transit still had high residual violation or spatial-inconsistency risk. Paired response analysis suggests the spatial prompt changes mode, destination, and spatial reasoning more than the top-level evacuation decision. Shelter, hazard-distance, and combined-constraint analyses are useful exploratory checks, but because several spatial attributes are approximate and some subgroup sizes are small, they should be treated as candidate evidence rather than broad generalizable findings.
        """,
    )


if __name__ == "__main__":
    main()
