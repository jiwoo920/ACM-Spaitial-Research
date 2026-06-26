#!/usr/bin/env python3
"""Extract a lightweight LA County tract boundary background for figures.

This uses the manually downloaded LA County Open Data 2020 Census Tracts
GeoJSON. It creates a downsampled polygon-boundary CSV for context only; it is
not used for analysis.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/Users/hanna/Downloads/2020_Census_Tracts.geojson")
OUT = ROOT / "data" / "la_county_tract_background_outline.csv"


def iter_outer_rings(geometry: dict):
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if geom_type == "Polygon":
        yield coords[0]
    elif geom_type == "MultiPolygon":
        for polygon in coords:
            yield polygon[0]


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing LA County tract GeoJSON: {SOURCE}")
    geo = json.loads(SOURCE.read_text())
    rows = []
    for feature_i, feature in enumerate(geo.get("features", [])):
        props = feature.get("properties", {})
        tract_id = props.get("CT20") or props.get("GEOID") or props.get("GEOID20") or feature_i
        for ring_i, ring in enumerate(iter_outer_rings(feature.get("geometry", {}))):
            if not ring:
                continue
            step = max(1, len(ring) // 40)
            sampled = ring[::step]
            if sampled[-1] != ring[-1]:
                sampled.append(ring[-1])
            for order, point in enumerate(sampled):
                rows.append(
                    {
                        "background_id": f"{tract_id}_{ring_i}",
                        "order": order,
                        "lon": point[0],
                        "lat": point[1],
                    }
                )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["background_id", "order", "lon", "lat"])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
