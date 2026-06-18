#!/usr/bin/env python3
"""Generate a synthetic pilot household persona dataset for wildfire evacuation."""

from __future__ import annotations

import csv
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


AREAS = [
    ("North Ridge", "High", 1.2, 6.8, "limited"),
    ("Canyon Creek", "Very high", 0.6, 8.2, "none"),
    ("Pine Flats", "Moderate", 3.4, 4.9, "moderate"),
    ("West Valley", "High", 1.9, 7.1, "limited"),
    ("Riverbend", "Low", 6.4, 2.2, "good"),
    ("Oak Terrace", "Moderate", 4.0, 3.6, "moderate"),
    ("Mesa South", "High", 2.7, 6.4, "limited"),
    ("Downtown Edge", "Low", 8.5, 1.4, "good"),
]

STRUCTURES = [
    "Single adult",
    "Two adults",
    "Single parent with children",
    "Two parents with children",
    "Multigenerational household",
    "Older adult living alone",
    "Older couple",
]

INCOMES = ["Low", "Lower-middle", "Middle", "Upper-middle", "High"]


def choose_vehicle(income: str, structure: str) -> str:
    p = {
        "Low": 0.35,
        "Lower-middle": 0.55,
        "Middle": 0.78,
        "Upper-middle": 0.9,
        "High": 0.96,
    }[income]
    if "Older" in structure:
        p -= 0.12
    if "children" in structure:
        p += 0.08
    return "Yes" if random.random() < max(0.08, min(0.98, p)) else "No"


def household_size_for(structure: str) -> int:
    if structure == "Single adult":
        return 1
    if structure == "Two adults":
        return 2
    if structure == "Single parent with children":
        return random.choice([2, 3, 4])
    if structure == "Two parents with children":
        return random.choice([3, 4, 5, 6])
    if structure == "Multigenerational household":
        return random.choice([4, 5, 6, 7])
    if structure == "Older adult living alone":
        return 1
    return 2


def age_for(structure: str) -> int:
    if "Older" in structure:
        return random.randint(67, 88)
    if structure == "Multigenerational household":
        return random.randint(42, 70)
    if "children" in structure:
        return random.randint(26, 54)
    return random.randint(22, 66)


def employment_for(age: int, structure: str) -> str:
    if age >= 67:
        return random.choice(["Retired", "Retired; occasional medical appointments"])
    if "children" in structure:
        return random.choice([
            "Parent works daytime; children attend school",
            "Parent works evening shifts; children attend school",
            "One adult works hourly shifts; children attend school",
        ])
    return random.choice([
        "Full-time worker",
        "Part-time worker",
        "Remote worker",
        "Unemployed / job-seeking",
        "Student and part-time worker",
    ])


def medical_for(age: int, structure: str) -> str:
    options = ["None", "None", "None"]
    if age >= 67:
        options += ["Mobility limitation", "Needs regular medication", "Caregiving for spouse"]
    if "children" in structure:
        options += ["One child has asthma", "Childcare pickup responsibility"]
    if structure == "Multigenerational household":
        options += ["Caregiving for older relative", "One member uses mobility aid"]
    return random.choice(options)


def mobility_constraints(vehicle: str, transit: str, medical: str, structure: str, income: str) -> str:
    constraints = []
    if vehicle == "No":
        constraints.append("No private vehicle")
    if transit in {"none", "limited"}:
        constraints.append(f"{transit.capitalize()} transit access")
    if medical != "None":
        constraints.append(medical)
    if "children" in structure:
        constraints.append("Must coordinate children")
    if income in {"Low", "Lower-middle"}:
        constraints.append("Limited emergency lodging budget")
    return "; ".join(constraints) if constraints else "Few routine mobility constraints"


def main() -> None:
    random.seed(20260530)
    DATA.mkdir(parents=True, exist_ok=True)

    personas = []
    for i in range(1, 73):
        area, risk, hazard_base, shelter_base, transit = random.choice(AREAS)
        structure = random.choice(STRUCTURES)
        income = random.choices(INCOMES, weights=[24, 22, 30, 16, 8], k=1)[0]
        size = household_size_for(structure)
        age = age_for(structure)
        vehicle = choose_vehicle(income, structure)
        employment = employment_for(age, structure)
        medical = medical_for(age, structure)
        shelter_distance = max(0.4, round(random.gauss(shelter_base, 1.0), 1))
        hazard_distance = max(0.1, round(random.gauss(hazard_base, 0.8), 1))
        car_time = int(max(5, shelter_distance * random.uniform(3.0, 5.6)))
        road_time = car_time if vehicle == "Yes" else int(car_time * random.uniform(1.2, 1.8))
        personas.append({
            "persona_id": f"HH-{i:03d}",
            "age_household_head": age,
            "household_size": size,
            "family_structure": structure,
            "income_level": income,
            "vehicle_access": vehicle,
            "employment_school_status": employment,
            "medical_caregiving_responsibilities": medical,
            "daily_mobility_constraints": mobility_constraints(vehicle, transit, medical, structure, income),
            "census_tract_or_area": area,
            "distance_to_nearest_shelter": shelter_distance,
            "road_travel_time_to_shelter": road_time,
            "distance_to_hazard_zone": hazard_distance,
            "transit_access": transit.capitalize(),
            "wildfire_risk_level": risk,
        })

    fieldnames = list(personas[0].keys())
    with (DATA / "personas.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(personas)

    spatial_fields = [
        "persona_id",
        "census_tract_or_area",
        "distance_to_nearest_shelter",
        "road_travel_time_to_shelter",
        "distance_to_hazard_zone",
        "transit_access",
        "wildfire_risk_level",
    ]
    with (DATA / "spatial_context.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=spatial_fields)
        writer.writeheader()
        writer.writerows({k: p[k] for k in spatial_fields} for p in personas)

    print(f"Wrote {len(personas)} personas to {DATA / 'personas.csv'}")


if __name__ == "__main__":
    main()
