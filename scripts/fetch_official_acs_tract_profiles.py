#!/usr/bin/env python3
"""Fetch official ACS 5-year tract variables for Los Angeles County.

Requires a Census API key in CENSUS_API_KEY. The output can replace the
ACS-style synthetic profile file before regenerating personas.
"""

from __future__ import annotations

import csv
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ACS_URL = "https://api.census.gov/data/2023/acs/acs5"
ACS_REFERENCE_URL = "https://www.census.gov/programs-surveys/acs"

VARIABLES = {
    "NAME": "name",
    "B19013_001E": "median_household_income",
    "B25044_001E": "occupied_housing_units",
    "B25044_003E": "owner_no_vehicle",
    "B25044_010E": "renter_no_vehicle",
    "B17001_001E": "poverty_universe",
    "B17001_002E": "poverty_count",
    "B25010_001E": "average_household_size",
    "B01001_001E": "total_population",
    "B01001_003E": "male_under_5",
    "B01001_004E": "male_5_9",
    "B01001_005E": "male_10_14",
    "B01001_006E": "male_15_17",
    "B01001_027E": "female_under_5",
    "B01001_028E": "female_5_9",
    "B01001_029E": "female_10_14",
    "B01001_030E": "female_15_17",
    "B01001_020E": "male_65_66",
    "B01001_021E": "male_67_69",
    "B01001_022E": "male_70_74",
    "B01001_023E": "male_75_79",
    "B01001_024E": "male_80_84",
    "B01001_025E": "male_85_plus",
    "B01001_044E": "female_65_66",
    "B01001_045E": "female_67_69",
    "B01001_046E": "female_70_74",
    "B01001_047E": "female_75_79",
    "B01001_048E": "female_80_84",
    "B01001_049E": "female_85_plus",
    "B08301_001E": "commute_total",
    "B08301_010E": "public_transport_commute",
}

PROFILE_FIELDS = [
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
    "profile_data_source",
    "acs_reference_url",
    "profile_limitations",
]


def num(row: dict[str, str], key: str) -> float:
    try:
        value = float(row.get(key, "0") or 0)
    except ValueError:
        value = 0.0
    return max(value, 0.0)


def category_income(median: float) -> str:
    if median < 55000:
        return "Low"
    if median < 80000:
        return "Lower-middle"
    if median < 110000:
        return "Middle"
    return "High"


def transit_label(public_pct: float) -> str:
    if public_pct >= 15:
        return "Good"
    if public_pct >= 7:
        return "Moderate"
    if public_pct >= 2:
        return "Limited"
    return "None"


def vulnerability(poverty: float, no_vehicle: float, elderly: float) -> str:
    score = poverty * 0.45 + no_vehicle * 0.35 + elderly * 0.20
    if score >= 22:
        return "High"
    if score >= 12:
        return "Moderate"
    return "Low"


def main() -> None:
    api_key = os.environ.get("CENSUS_API_KEY")
    if not api_key:
        raise SystemExit("CENSUS_API_KEY is required to fetch official ACS estimates.")

    params = {
        "get": ",".join(VARIABLES),
        "for": "tract:*",
        "in": "state:06 county:037",
        "key": api_key,
    }
    url = f"{ACS_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    header, records = data[0], data[1:]
    rows = [dict(zip(header, record)) for record in records]
    # Pick tracts with wildfire-relevant social constraints: high no-vehicle,
    # high poverty, high elderly, and high income edge tracts.
    def rank(row: dict[str, str]) -> float:
        occupied = num(row, "B25044_001E") or 1
        no_vehicle = (num(row, "B25044_003E") + num(row, "B25044_010E")) / occupied * 100
        poverty = num(row, "B17001_002E") / (num(row, "B17001_001E") or 1) * 100
        total = num(row, "B01001_001E") or 1
        elderly = sum(num(row, key) for key in [
            "B01001_020E", "B01001_021E", "B01001_022E", "B01001_023E", "B01001_024E", "B01001_025E",
            "B01001_044E", "B01001_045E", "B01001_046E", "B01001_047E", "B01001_048E", "B01001_049E",
        ]) / total * 100
        return no_vehicle * 0.45 + poverty * 0.35 + elderly * 0.20

    selected = sorted(rows, key=rank, reverse=True)[:20]
    output = []
    for i, row in enumerate(selected, start=1):
        occupied = num(row, "B25044_001E") or 1
        no_vehicle = (num(row, "B25044_003E") + num(row, "B25044_010E")) / occupied * 100
        poverty = num(row, "B17001_002E") / (num(row, "B17001_001E") or 1) * 100
        total = num(row, "B01001_001E") or 1
        children = sum(num(row, key) for key in [
            "B01001_003E", "B01001_004E", "B01001_005E", "B01001_006E",
            "B01001_027E", "B01001_028E", "B01001_029E", "B01001_030E",
        ]) / total * 100
        elderly = sum(num(row, key) for key in [
            "B01001_020E", "B01001_021E", "B01001_022E", "B01001_023E", "B01001_024E", "B01001_025E",
            "B01001_044E", "B01001_045E", "B01001_046E", "B01001_047E", "B01001_048E", "B01001_049E",
        ]) / total * 100
        public_pct = num(row, "B08301_010E") / (num(row, "B08301_001E") or 1) * 100
        tract_id = f"06037{row['tract']}"
        output.append({
            "census_tract_id": tract_id,
            "neighborhood_label": f"Los Angeles County tract {row['tract']}",
            "median_household_income": round(num(row, "B19013_001E")),
            "income_category": category_income(num(row, "B19013_001E")),
            "percent_no_vehicle": round(no_vehicle, 1),
            "average_household_size": round(num(row, "B25010_001E"), 2),
            "percent_children": round(children, 1),
            "percent_elderly": round(elderly, 1),
            "poverty_rate": round(poverty, 1),
            "public_transportation_proxy": round(public_pct, 1),
            "wildfire_risk_level": "High" if i <= 12 else "Moderate",
            "distance_to_nearest_shelter": round(1.5 + (i % 6) * 0.8, 1),
            "road_travel_time_to_shelter": 10 + (i % 6) * 5,
            "distance_to_hazard_zone": round(0.7 + (i % 5) * 0.6, 1),
            "transit_access": transit_label(public_pct),
            "neighborhood_vulnerability_level": vulnerability(poverty, no_vehicle, elderly),
            "profile_data_source": "Official ACS 2023 5-year tract estimates via U.S. Census API for Los Angeles County; spatial risk/distance fields are approximate study values.",
            "acs_reference_url": ACS_REFERENCE_URL,
            "profile_limitations": "ACS variables are official tract estimates; wildfire risk, shelter distance, travel time, and hazard distance are approximate placeholders pending GIS integration.",
        })

    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / "acs_tract_profiles_20_official_acs.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PROFILE_FIELDS)
        writer.writeheader()
        writer.writerows(output)
    print(f"Wrote {len(output)} official ACS-derived tract profiles to {path}")


if __name__ == "__main__":
    main()
