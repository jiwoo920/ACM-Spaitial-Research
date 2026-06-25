#!/usr/bin/env python3
"""Post-hoc subgroup interaction result candidates.

Uses existing GPT-4.1-mini 400-response outputs only. No API calls or prompt
changes are performed.
"""

from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs" / "main_experiment_gpt_acs_200"

CONDITION_LABEL = {"baseline": "Baseline", "spatial_grounded": "Spatially grounded"}
MODE_COLUMNS = [
    "Private vehicle",
    "Public transit",
    "Ride with family/friend",
    "Emergency transport",
    "Walk",
    "Mixed/other",
    "No transportation",
]
HAZARD_KEYWORDS = re.compile(r"\b(?:fire|wildfire|hazard|urgent|urgency|smoke|evacuation zone|zone|risk)\b", re.I)


def pct(x: float) -> float:
    return round(float(x) * 100, 1)


def rate(series: pd.Series) -> float:
    return pct(series.mean()) if len(series) else 0.0


def write_md(path: Path, body: str) -> None:
    path.write_text(dedent(body).strip() + "\n", encoding="utf-8")


def tertile_group(series: pd.Series, labels: list[str]) -> pd.Series:
    ranked = series.rank(method="first")
    return pd.qcut(ranked, q=3, labels=labels)


def add_mode_distribution(row: dict, g: pd.DataFrame) -> dict:
    for mode in MODE_COLUMNS:
        mask = g["transportation_mode"].eq(mode)
        row[f"{mode}_count"] = int(mask.sum())
        row[f"{mode}_rate"] = rate(mask)
    return row


def load_data() -> pd.DataFrame:
    personas = pd.read_csv(DATA_DIR / "personas_acs_200.csv", keep_default_na=False)
    scores = pd.read_csv(OUT_DIR / "feasibility_scores.csv", keep_default_na=False)
    parsed = pd.read_csv(
        OUT_DIR / "llm_responses_parsed.csv",
        keep_default_na=False,
        usecols=["run_id", "reasoning", "key_constraints_considered"],
    )
    persona_cols = ["persona_id", "household_size", "daily_mobility_constraints"]
    df = scores.merge(personas[persona_cols], on="persona_id", how="left").merge(parsed, on="run_id", how="left")
    df["condition_label"] = df["condition"].map(CONDITION_LABEL)
    df["reasoning_text"] = df["reasoning"].fillna("") + " " + df["key_constraints_considered"].fillna("")
    df["hazard_keyword_mention"] = df["reasoning_text"].str.contains(HAZARD_KEYWORDS)
    df["high_urgency"] = df["departure_urgency"].str.lower().eq("high")
    df["evacuate_now"] = df["decision"].eq("Evacuate now")
    df["any_violation_or_spatial_inconsistency"] = (df["any_violation"].astype(int) > 0) | (
        df["spatial_inconsistency_count"].astype(int) > 0
    )
    df["vehicle_group"] = df["vehicle_access"].map(lambda x: "No vehicle" if str(x).strip().lower() == "no" else "Vehicle access")
    medcare = df["medical_caregiving_responsibilities"].str.lower()
    mobility = df["daily_mobility_constraints"].str.lower()
    df["medical_or_care_need"] = medcare.ne("none")
    df["mobility_constraint"] = mobility.ne("none") | medcare.str.contains("mobility", regex=True)
    df["care_or_mobility_need"] = df["medical_or_care_need"] | df["mobility_constraint"]
    df["limited_no_transit"] = df["transit_access"].isin(["Limited", "None"])
    df["shelter_time_group"] = tertile_group(df["road_travel_time_to_shelter"].astype(float), ["Short", "Medium", "Long"])
    df["single_large_group"] = ""
    df.loc[df["household_size"].astype(int).eq(1), "single_large_group"] = "Single-person"
    df.loc[df["household_size"].astype(int).ge(4), "single_large_group"] = "Large household (4+)"
    df["good_moderate_transit"] = df["transit_access"].isin(["Good", "Moderate"])
    df["short_medium_shelter_time"] = df["shelter_time_group"].isin(["Short", "Medium"])
    return df


def summarize_group(g: pd.DataFrame, base: dict) -> dict:
    row = {
        **base,
        "n": len(g),
        "violation_spatial_inconsistency_rate": rate(g["any_violation_or_spatial_inconsistency"]),
        "soft_feasibility_issue_rate": rate(g["any_soft_issue"]),
        "mode_feasibility_rate": rate(g["mode_feasible"]),
        "public_transit_rate": rate(g["transportation_mode"].eq("Public transit")),
        "ride_family_friend_rate": rate(g["transportation_mode"].eq("Ride with family/friend")),
        "private_vehicle_rate": rate(g["transportation_mode"].eq("Private vehicle")),
        "public_shelter_rate": rate(g["destination_type"].eq("Public shelter")),
        "exploratory_note": "small subgroup; interpret as exploratory" if len(g) < 30 else "",
    }
    return add_mode_distribution(row, g)


def no_vehicle_household_size(df: pd.DataFrame) -> pd.DataFrame:
    sdf = df[(df["vehicle_group"].eq("No vehicle")) & (df["single_large_group"].ne(""))]
    rows = []
    for (condition, group), g in sdf.groupby(["condition_label", "single_large_group"]):
        rows.append(summarize_group(g, {"condition": condition, "household_size_group": group}))
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "no_vehicle_household_size_analysis.csv", index=False)

    top = out.sort_values("violation_spatial_inconsistency_rate", ascending=False).iloc[0]
    write_md(
        OUT_DIR / "no_vehicle_household_size_summary.md",
        f"""
        # No-Vehicle Household Size Interaction Summary

        Among no-vehicle households, the highest observed risk is **{top['household_size_group']} / {top['condition']}** at {top['violation_spatial_inconsistency_rate']:.1f}% violation/spatial-inconsistency (n = {int(top['n'])}). Single-person no-vehicle households show very high public-transit reliance, while large no-vehicle households have a small but nonzero ride/family-friend share. Because large no-vehicle households have n < 30 per condition, this result is exploratory rather than generalizable.
        """,
    )
    return out


def vulnerable_household_interaction(df: pd.DataFrame) -> pd.DataFrame:
    general = (~df["care_or_mobility_need"]) & df["short_medium_shelter_time"]
    complex_vulnerable = df["care_or_mobility_need"] & df["shelter_time_group"].eq("Long")
    rows = []
    for label, mask in {
        "General household": general,
        "Complex vulnerable household": complex_vulnerable,
    }.items():
        for condition, g in df[mask].groupby("condition_label"):
            rows.append(summarize_group(g, {"condition": condition, "household_group": label}))
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "vulnerable_household_interaction_analysis.csv", index=False)

    complex_rows = out[out["household_group"].eq("Complex vulnerable household")]
    general_rows = out[out["household_group"].eq("General household")]
    write_md(
        OUT_DIR / "vulnerable_household_interaction_summary.md",
        f"""
        # General vs Complex Vulnerable Household Summary

        Complex vulnerable households combine medical/care or mobility needs with long shelter travel time. Their violation/spatial-inconsistency rate is {complex_rows['violation_spatial_inconsistency_rate'].max():.1f}% at the highest condition-specific cell, compared with {general_rows['violation_spatial_inconsistency_rate'].max():.1f}% for the general household control. This is a meaningful interaction candidate because it contrasts a safer control group against a spatially and socially constrained subgroup. Interpret cautiously if any selected cell has n < 30.
        """,
    )
    return out


def combined_constraints_with_control(df: pd.DataFrame) -> pd.DataFrame:
    groups = {
        "Safe control": df["vehicle_group"].eq("Vehicle access") & df["good_moderate_transit"] & df["short_medium_shelter_time"],
        "No vehicle + limited/no transit": df["vehicle_group"].eq("No vehicle") & df["limited_no_transit"],
        "No vehicle + long shelter travel time": df["vehicle_group"].eq("No vehicle") & df["shelter_time_group"].eq("Long"),
        "Care/mobility need + long shelter travel time": df["care_or_mobility_need"] & df["shelter_time_group"].eq("Long"),
        "No vehicle + limited/no transit + large household": df["vehicle_group"].eq("No vehicle")
        & df["limited_no_transit"]
        & df["household_size"].astype(int).ge(4),
    }
    rows = []
    for label, mask in groups.items():
        for condition, g in df[mask].groupby("condition_label"):
            rows.append(summarize_group(g, {"condition": condition, "constraint_group": label}))
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "combined_constraints_with_control.csv", index=False)

    safe = out[out["constraint_group"].eq("Safe control")]
    top = out[out["constraint_group"].ne("Safe control")].sort_values("violation_spatial_inconsistency_rate", ascending=False).iloc[0]
    write_md(
        OUT_DIR / "combined_constraints_with_control_summary.md",
        f"""
        # Combined Constraints With Safe Control Summary

        The safe control group has low risk relative to constrained groups: its maximum violation/spatial-inconsistency rate is {safe['violation_spatial_inconsistency_rate'].max():.1f}%. The highest constrained-group rate is **{top['constraint_group']} / {top['condition']}** at {top['violation_spatial_inconsistency_rate']:.1f}% (n = {int(top['n'])}). This is one of the strongest SRC candidates because it shows a clean contrast between safe-control households and overlapping mobility/spatial constraints. Small cells, especially the optional triple-constraint large-household group, should be labeled exploratory.
        """,
    )
    return out


def wildfire_risk_decision_check(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (condition, risk), g in df.groupby(["condition_label", "wildfire_risk_level"]):
        rows.append(
            {
                "condition": condition,
                "wildfire_risk_level": risk,
                "n": len(g),
                "evacuate_now_rate": rate(g["evacuate_now"]),
                "high_urgency_rate": rate(g["high_urgency"]),
                "hazard_fire_reasoning_keyword_rate": rate(g["hazard_keyword_mention"]),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "wildfire_risk_decision_check.csv", index=False)

    write_md(
        OUT_DIR / "wildfire_risk_decision_check_summary.md",
        f"""
        # Wildfire Risk Decision Check Summary

        Wildfire-risk level is weak as a main decision figure because evacuation and urgency rates are near ceiling. Across risk/condition cells, the minimum evacuate-now rate is {out['evacuate_now_rate'].min():.1f}% and the minimum high-urgency rate is {out['high_urgency_rate'].min():.1f}%. The more defensible interpretation is that wildfire risk appears in reasoning language, but the scenario framing already pushes nearly all responses toward immediate evacuation.
        """,
    )
    return out


def recommendation(no_vehicle: pd.DataFrame, vulnerable: pd.DataFrame, combined: pd.DataFrame, wildfire: pd.DataFrame) -> None:
    combined_top = combined[combined["constraint_group"].ne("Safe control")].sort_values(
        "violation_spatial_inconsistency_rate", ascending=False
    ).iloc[0]
    vulnerable_top = vulnerable.sort_values("violation_spatial_inconsistency_rate", ascending=False).iloc[0]
    no_vehicle_top = no_vehicle.sort_values("violation_spatial_inconsistency_rate", ascending=False).iloc[0]
    wildfire_min_decision = wildfire["evacuate_now_rate"].min()
    rows = [
        {
            "rank": 1,
            "analysis": "Combined constraints with safe control",
            "strongest_contrast": f"{combined_top['constraint_group']} / {combined_top['condition']} vs Safe control",
            "key_result": f"Highest constrained risk {combined_top['violation_spatial_inconsistency_rate']:.1f}% (n = {int(combined_top['n'])}); safe control maximum {combined[combined['constraint_group'].eq('Safe control')]['violation_spatial_inconsistency_rate'].max():.1f}%.",
            "recommended_src_use": "Strongest new figure candidate if replacing/augmenting the transit figure.",
            "caution": "Triple-constraint subgroup is exploratory if selected.",
        },
        {
            "rank": 2,
            "analysis": "General vs complex vulnerable household",
            "strongest_contrast": "General household vs care/mobility need + long shelter travel time",
            "key_result": f"Highest complex/general cell risk {vulnerable_top['violation_spatial_inconsistency_rate']:.1f}% (n = {int(vulnerable_top['n'])}).",
            "recommended_src_use": "Good secondary table/prose candidate.",
            "caution": "Interpret as exploratory if cell n < 30.",
        },
        {
            "rank": 3,
            "analysis": "No-vehicle single vs no-vehicle large household",
            "strongest_contrast": "No-vehicle single-person vs no-vehicle large household",
            "key_result": f"Highest cell risk {no_vehicle_top['violation_spatial_inconsistency_rate']:.1f}% (n = {int(no_vehicle_top['n'])}).",
            "recommended_src_use": "Useful detail, but less broad than combined-constraint figure.",
            "caution": "Large no-vehicle household cells are small.",
        },
        {
            "rank": 4,
            "analysis": "Wildfire risk decision check",
            "strongest_contrast": "High vs moderate wildfire risk",
            "key_result": f"Evacuate-now rate minimum {wildfire_min_decision:.1f}%; decision outcome has little variation.",
            "recommended_src_use": "Discussion only; not a main figure.",
            "caution": "Reasoning salience, not decision effect.",
        },
    ]
    rec = pd.DataFrame(rows)
    rec.to_csv(OUT_DIR / "subgroup_interaction_recommendation.csv", index=False)
    write_md(
        OUT_DIR / "subgroup_interaction_recommendation.md",
        """
        # Subgroup Interaction Result Recommendation

        1. **Combined constraints with safe control** is the strongest new SRC candidate. It provides the cleanest contrast between a low-risk control group and households with overlapping transportation/spatial constraints.
        2. **General vs complex vulnerable household** is a good supporting result because it connects care/mobility needs with shelter travel time, but selected cells should be checked for n.
        3. **No-vehicle single vs no-vehicle large household** is useful as a focused transportation-feasibility detail. It should be treated as exploratory when large-household cells are small.
        4. **Wildfire risk decision check** is weak as a main figure because evacuation decision and urgency are near ceiling. Use it only to say wildfire risk appears more in reasoning language than in decision variation.

        **Recommendation:** do not change prompts or run new LLM calls yet. For SRC figure selection, compare the existing transit-access Figure 1 against the new combined-constraints-with-control figure. The combined-control figure may be stronger if the paper wants an interaction story; the transit figure remains stronger if the paper wants a direct prompting-improvement story.
        """,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data()
    no_vehicle = no_vehicle_household_size(df)
    vulnerable = vulnerable_household_interaction(df)
    combined = combined_constraints_with_control(df)
    wildfire = wildfire_risk_decision_check(df)
    recommendation(no_vehicle, vulnerable, combined, wildfire)


if __name__ == "__main__":
    main()
