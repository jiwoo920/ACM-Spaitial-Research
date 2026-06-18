#!/usr/bin/env python3
"""Generate ACS-calibrated synthetic household personas for the v1 study.

The tract profiles below are lightweight study profiles for Los Angeles County.
They are calibrated to plausible ACS-style tract-level variables rather than
real individual records.
"""

from __future__ import annotations

import csv
import argparse
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


PERSONA_FIELDS = [
    "persona_id",
    "census_tract_id",
    "neighborhood_label",
    "age_household_head",
    "household_size",
    "family_structure",
    "income_level",
    "vehicle_access",
    "employment_school_status",
    "medical_caregiving_responsibilities",
    "daily_mobility_constraints",
    "children_present",
    "elderly_present",
    "income_category",
    "tract_median_income",
    "tract_percent_no_vehicle",
    "tract_poverty_rate",
    "tract_percent_children",
    "tract_percent_elderly",
]

SPATIAL_FIELDS = [
    "persona_id",
    "census_tract_id",
    "census_tract_or_area",
    "neighborhood_label",
    "wildfire_risk_level",
    "distance_to_nearest_shelter",
    "road_travel_time_to_shelter",
    "distance_to_hazard_zone",
    "transit_access",
    "neighborhood_vulnerability_level",
]

BASE_PROFILE_FIELDS = [
    "census_tract_id",
    "neighborhood_label",
    "median_household_income",
    "income_category",
    "percent_no_vehicle",
    "average_household_size",
    "percent_children",
    "percent_elderly",
    "poverty_rate",
    "public_transportation_proxy",
    "wildfire_risk_level",
    "distance_to_nearest_shelter",
    "road_travel_time_to_shelter",
    "distance_to_hazard_zone",
    "transit_access",
    "neighborhood_vulnerability_level",
]

PROFILE_FIELDS = BASE_PROFILE_FIELDS + [
    "profile_data_source",
    "acs_reference_url",
    "profile_limitations",
]


TRACT_PROFILES = [
    ("06037101110", "Tujunga foothill tract", 76000, "Middle", 5, 2.8, 22, 15, 10, 8, "Very high", 3.6, 18, 0.9, "Limited", "Moderate"),
    ("06037101220", "Sunland hillside tract", 84000, "Middle", 4, 2.7, 20, 18, 8, 7, "Very high", 4.2, 22, 1.1, "Limited", "Moderate"),
    ("06037103100", "La Crescenta interface tract", 103000, "High", 3, 2.9, 23, 14, 6, 5, "High", 3.1, 17, 1.6, "Limited", "Low"),
    ("06037103200", "Altadena canyon tract", 92000, "Middle", 6, 2.6, 19, 19, 9, 9, "High", 2.8, 16, 1.3, "Moderate", "Moderate"),
    ("06037104110", "Pasadena north tract", 88000, "Middle", 7, 2.4, 17, 20, 10, 11, "High", 2.4, 14, 2.0, "Moderate", "Moderate"),
    ("06037106020", "Eagle Rock hillside tract", 97000, "High", 8, 2.5, 18, 16, 8, 12, "Moderate", 2.0, 13, 2.8, "Moderate", "Low"),
    ("06037108010", "Northeast LA transit tract", 69000, "Lower-middle", 14, 3.1, 25, 13, 17, 19, "Moderate", 1.7, 12, 3.4, "Good", "High"),
    ("06037111100", "San Fernando low-income tract", 61000, "Lower-middle", 13, 3.4, 28, 11, 19, 16, "High", 3.8, 24, 1.9, "Moderate", "High"),
    ("06037112100", "Sylmar interface tract", 74000, "Middle", 9, 3.2, 27, 12, 13, 10, "Very high", 4.7, 28, 0.8, "Limited", "High"),
    ("06037113100", "Granada Hills tract", 99000, "High", 4, 2.8, 21, 17, 7, 6, "High", 3.5, 19, 1.7, "Limited", "Low"),
    ("06037115100", "Chatsworth edge tract", 91000, "Middle", 5, 2.7, 20, 18, 8, 7, "Very high", 5.4, 33, 0.7, "Limited", "Moderate"),
    ("06037117100", "Woodland Hills south tract", 118000, "High", 3, 2.5, 17, 21, 5, 4, "Very high", 4.9, 29, 0.6, "Limited", "Low"),
    ("06037118100", "Canoga Park tract", 64000, "Lower-middle", 12, 3.0, 24, 14, 18, 15, "High", 2.6, 18, 2.2, "Moderate", "High"),
    ("06037119100", "Reseda mixed tract", 71000, "Lower-middle", 10, 2.9, 22, 16, 15, 14, "Moderate", 2.3, 15, 3.0, "Moderate", "Moderate"),
    ("06037121100", "Topanga-adjacent tract", 126000, "High", 2, 2.4, 15, 23, 4, 3, "Very high", 6.1, 38, 0.5, "None", "Low"),
    ("06037124100", "Malibu canyon tract", 132000, "High", 2, 2.3, 14, 24, 4, 2, "Very high", 7.4, 42, 0.4, "None", "Low"),
    ("06037262100", "East LA dense tract", 52000, "Low", 18, 3.5, 30, 10, 24, 24, "Moderate", 1.4, 11, 4.0, "Good", "High"),
    ("06037271100", "South LA transit tract", 48000, "Low", 20, 3.2, 29, 11, 27, 28, "Moderate", 1.2, 10, 4.5, "Good", "High"),
    ("06037402100", "Whittier hills tract", 83000, "Middle", 6, 3.0, 24, 14, 10, 9, "High", 3.0, 18, 1.8, "Moderate", "Moderate"),
    ("06037543100", "Santa Clarita interface tract", 108000, "High", 3, 3.1, 25, 12, 6, 5, "Very high", 5.0, 30, 0.8, "Limited", "Low"),
]


def income_level(profile: dict[str, object], rng: random.Random) -> str:
    poverty = float(profile["poverty_rate"])
    median = int(profile["median_household_income"])
    low_weight = max(0.1, poverty / 35)
    high_weight = max(0.1, (median - 65000) / 90000)
    return rng.choices(
        ["Low", "Lower-middle", "Middle", "Upper-middle"],
        weights=[low_weight, low_weight + 0.25, 0.45, high_weight],
        k=1,
    )[0]


def make_profile(row: tuple[object, ...]) -> dict[str, object]:
    profile = dict(zip(BASE_PROFILE_FIELDS, row))
    profile["profile_data_source"] = "ACS-style synthetic tract profile; not an official ACS estimate"
    profile["acs_reference_url"] = "https://www.census.gov/programs-surveys/acs"
    profile["profile_limitations"] = "Income, vehicle, poverty, household size, children, elderly, and transit fields are ACS-style calibration inputs; shelter and hazard distances are approximate study values."
    return profile


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_profiles(path: str | None) -> tuple[list[dict[str, object]], bool]:
    if not path:
        return [make_profile(row) for row in TRACT_PROFILES], True
    source_path = Path(path)
    if not source_path.is_absolute():
        source_path = ROOT.parent / source_path
    rows = read_csv(source_path)
    missing = [field for field in BASE_PROFILE_FIELDS if field not in rows[0]]
    if missing:
        raise SystemExit(f"Profile file is missing required columns: {', '.join(missing)}")
    return [dict(row) for row in rows], False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ACS-style or official ACS-derived synthetic personas.")
    parser.add_argument("--profiles-file", default="", help="Optional tract profile CSV. Use official ACS-derived profile file here after fetching.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(20260601)
    profiles, write_profiles = load_profiles(args.profiles_file)
    personas: list[dict[str, object]] = []
    spatial_rows: list[dict[str, object]] = []

    for tract_index, profile in enumerate(profiles, start=1):
        for local_index in range(1, 11):
            persona_num = (tract_index - 1) * 10 + local_index
            persona_id = f"ACS-{persona_num:03d}"
            no_vehicle = rng.random() < float(profile["percent_no_vehicle"]) / 100
            children_present = rng.random() < float(profile["percent_children"]) / 100
            elderly_present = rng.random() < float(profile["percent_elderly"]) / 100
            household_size = max(1, round(rng.gauss(float(profile["average_household_size"]), 0.9)))
            if children_present:
                household_size = max(household_size, rng.choice([3, 4, 5]))
            if elderly_present:
                age = rng.randint(67, 88)
            else:
                age = rng.randint(24, 66)

            if children_present and elderly_present:
                family_structure = "Multigenerational household with children"
            elif children_present:
                family_structure = "Household with children"
            elif household_size == 1:
                family_structure = "Single adult household"
            else:
                family_structure = rng.choice(["Two-adult household", "Shared adult household"])

            medical = "None"
            if elderly_present and rng.random() < 0.45:
                medical = "Older adult mobility or medication needs"
            elif children_present and rng.random() < 0.25:
                medical = "Child caregiving responsibilities"

            mobility = "None"
            if no_vehicle:
                mobility = "No private vehicle; depends on transit or rides"
            elif elderly_present and rng.random() < 0.30:
                mobility = "Reduced mobility for household head"

            personas.append({
                "persona_id": persona_id,
                "census_tract_id": profile["census_tract_id"],
                "neighborhood_label": profile["neighborhood_label"],
                "age_household_head": age,
                "household_size": household_size,
                "family_structure": family_structure,
                "income_level": income_level(profile, rng),
                "vehicle_access": "No" if no_vehicle else "Yes",
                "employment_school_status": rng.choice(["Employed full-time", "Employed part-time", "Remote worker", "Retired", "Student/caregiver at home"]),
                "medical_caregiving_responsibilities": medical,
                "daily_mobility_constraints": mobility,
                "children_present": int(children_present),
                "elderly_present": int(elderly_present),
                "income_category": profile["income_category"],
                "tract_median_income": profile["median_household_income"],
                "tract_percent_no_vehicle": profile["percent_no_vehicle"],
                "tract_poverty_rate": profile["poverty_rate"],
                "tract_percent_children": profile["percent_children"],
                "tract_percent_elderly": profile["percent_elderly"],
            })

            spatial_rows.append({
                "persona_id": persona_id,
                "census_tract_id": profile["census_tract_id"],
                "census_tract_or_area": f"{profile['neighborhood_label']} ({profile['census_tract_id']})",
                "neighborhood_label": profile["neighborhood_label"],
                "wildfire_risk_level": profile["wildfire_risk_level"],
                "distance_to_nearest_shelter": profile["distance_to_nearest_shelter"],
                "road_travel_time_to_shelter": profile["road_travel_time_to_shelter"],
                "distance_to_hazard_zone": profile["distance_to_hazard_zone"],
                "transit_access": profile["transit_access"],
                "neighborhood_vulnerability_level": profile["neighborhood_vulnerability_level"],
            })

    DATA.mkdir(parents=True, exist_ok=True)
    if write_profiles:
        with (DATA / "acs_tract_profiles_20.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=PROFILE_FIELDS)
            writer.writeheader()
            writer.writerows(profiles)
    with (DATA / "personas_acs_200.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PERSONA_FIELDS)
        writer.writeheader()
        writer.writerows(personas)
    with (DATA / "spatial_context_acs_200.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SPATIAL_FIELDS)
        writer.writeheader()
        writer.writerows(spatial_rows)
    print("Wrote 20 tract profiles, 200 personas, and 200 spatial context rows.")


if __name__ == "__main__":
    main()
