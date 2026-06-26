# GIS Result Candidate Ranking

This ranking uses only the existing 400-response GPT-4.1-mini dataset enriched with LA County Open Data tract geometries, tract centroids, a representative wildfire point, candidate shelter/service points, and transit-stop proximity proxies. No new LLM calls were made.

## 1. Best Main SRC Figure Candidate

**`project/figures/figure2_prompt_vs_gis_transport_audit_combined.png`**

The combined response-level figure is now the strongest SRC candidate because it separates prompt-label sensitivity from GIS-proxy feasibility audit for no-vehicle households. Panel (a) shows transportation choices under original transit-access labels, while Panel (b) audits the same response set against tract-centroid transit-stop proximity proxies. This directly communicates that plausible prompt-following behavior can still leave spatial feasibility risks.

## 2. Best Single-Panel Main Figure

**`project/figures/no_vehicle_gis_proxy_transport_risk_bar.png`** or **`project/figures/no_vehicle_transit_proxy_risk_simple_v2.png`**

Use a single-panel bar chart if space is too tight for the combined figure. The chart is easy to read in a 2-page SRC abstract and keeps the claim focused on no-vehicle feasibility risk under a transit-stop proximity proxy.

## 3. Best Supporting Spatial Figure

**`project/figures/spatial_auditing_map_with_mismatch_callouts.png`**

The map is useful for advisor discussion and can support the paper if space allows. It is more explanatory than the plain spatial positioning map because it overlays selected response-level mismatch examples. It may be too visually dense for the main 2-page abstract unless the paper needs a stronger GIS-facing figure.

## 4. Best Method/Audit Support

**GIS label audit boxplots**: `project/figures/gis_label_audit_transit_boxplot.png`, `project/figures/gis_label_audit_shelter_boxplot.png`, and `project/figures/gis_label_audit_fire_boxplot.png`.

These are useful methods/advisor-support figures. They compare original prompt labels with GIS-derived proxy distances and should be framed as exploratory GIS-supported audits, not validation of operational accessibility or exposure.

## 5. Advisor Discussion Figures

- `project/figures/no_vehicle_prompt_label_transport_behavior.png`: useful for showing prompt-label sensitivity.
- `project/figures/no_vehicle_gis_proxy_transport_behavior_bubble.png`: useful for showing response-level mode choices under GIS proxy groups.
- `project/figures/shelter_proxy_behavior_audit.png`: useful for discussing shelter language and candidate service proximity.

## 6. Exploratory-Only / Not Recommended As Main Figure

- `project/figures/transit_distance_vs_feasibility_risk_scatter.png`: exploratory spatial association only; do not frame causally.
- `project/figures/fire_distance_reasoning_salience_bar.png`: evacuation decision and urgency are close to ceiling, so it is weaker as a main result.
- `project/figures/nearby_shelter_claim_by_distance_simple.png`: useful support, but weaker than the response-level shelter audit.

## Claims To Avoid

- Do not claim actual route-level reachability.
- Do not claim verified wildfire evacuation shelter access.
- Do not call the representative fire point an active wildfire or verified perimeter.
- Do not claim the LLM used exact GIS distances unless those values were included in the original prompt.
- Do not claim GIS analysis proves operational evacuation feasibility.

## Recommended SRC Framing

Use the combined prompt-label vs GIS-proxy transportation audit if space allows. If the 2-page layout is tight, use the GIS-proxy risk bar as the main analytical figure and keep the response-level bubbles/map for advisor discussion or appendix material.
