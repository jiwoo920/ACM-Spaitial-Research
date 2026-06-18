#!/usr/bin/env python3
"""Fetch a minimal real spatial-risk context from FEMA National Risk Index.

This adds a real county-level wildfire-risk reference for Los Angeles County,
California. It does not replace the synthetic persona fields; it documents and
stores one authoritative spatial layer that can be used to calibrate v1.
"""

from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "real_context"
SOURCE = "FEMA National Risk Index Counties ArcGIS FeatureServer"
URL = "https://services.arcgis.com/XG15cJAlne2vxtgt/ArcGIS/rest/services/National_Risk_Index_Counties/FeatureServer/0/query"


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    params = {
        "f": "json",
        "where": "STATEABBRV='CA' AND COUNTY='Los Angeles'",
        "outFields": "STATE,STATEABBRV,COUNTY,STCOFIPS,POPULATION,RISK_SCORE,RISK_RATNG,SOVI_SCORE,SOVI_RATNG,RESL_SCORE,RESL_RATNG,WFIR_RISKS,WFIR_RISKR,WFIR_AFREQ,WFIR_EALT",
        "returnGeometry": "false",
    }
    url = URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.load(response)
    features = data.get("features", [])
    if not features:
        raise RuntimeError("No FEMA NRI record returned for Los Angeles County.")
    rows = [feature["attributes"] for feature in features]
    out = DATA / "fema_nri_los_angeles_county.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (DATA / "sources.md").write_text(
        "# Real Context Sources\n\n"
        f"- {SOURCE}: county-level National Risk Index record for Los Angeles County, CA.\n"
        f"- Query URL: {url}\n"
        "- Fields used include overall risk rating, social vulnerability rating, community resilience rating, "
        "and wildfire hazard-type risk score/rating.\n"
        "- This is a partial real-data attachment for v1 calibration; the current household personas remain synthetic.\n",
        encoding="utf-8",
    )
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
