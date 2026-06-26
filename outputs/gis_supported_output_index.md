# GIS-Supported Output Index

## Response-Level Behavior Audit Figures

- `project/figures/no_vehicle_prompt_label_transport_behavior.png`: bubble/count plot of no-vehicle transportation choices by original prompt transit labels.
- `project/figures/no_vehicle_gis_proxy_transport_behavior_bubble.png`: bubble/count plot of no-vehicle transportation choices by GIS-derived transit-stop proximity proxy.
- `project/figures/no_vehicle_gis_proxy_transport_risk_bar.png`: no-vehicle violation/spatial-inconsistency risk by GIS transit proxy group.
- `project/figures/figure2_prompt_vs_gis_transport_audit_combined.png`: combined paper-ready figure separating prompt-label sensitivity from GIS-proxy feasibility audit.
- `project/figures/spatial_auditing_map_with_mismatch_callouts.png`: spatial audit map with selected response-level mismatch callouts.
- `project/figures/shelter_proxy_behavior_audit.png`: shelter behavior audit by candidate shelter/service proximity group.

## Response-Level Behavior Audit Tables

- `project/outputs/no_vehicle_prompt_label_transport_behavior.csv`: source counts and percentages for prompt-label transportation behavior.
- `project/outputs/no_vehicle_gis_proxy_transport_behavior.csv`: source counts and percentages for GIS-proxy transportation behavior.
- `project/outputs/shelter_proxy_behavior_audit.csv`: source rates for shelter-related behavior categories.

## Polished Existing Candidate Figures

- `project/figures/no_vehicle_transit_proxy_risk_simple_v2.png`: v2 simplified no-vehicle feasibility risk by transit-stop proximity proxy.
- `project/figures/selected_tracts_fire_shelter_transit_map_polished_v2.png`: v2 polished spatial positioning map.
- `project/figures/gis_label_audit_transit_boxplot.png`: transit label audit boxplot.
- `project/figures/gis_label_audit_shelter_boxplot.png`: shelter-distance label audit boxplot.
- `project/figures/gis_label_audit_fire_boxplot.png`: wildfire-risk label audit boxplot.

## Interpretation Boundary

These outputs distinguish prompt-label sensitivity from GIS-proxy feasibility auditing. They use tract centroid proxies, candidate shelter/service proximity proxies, and transit-stop proximity proxies. They do not prove route-level reachability, verified wildfire shelter access, active wildfire exposure, or operational evacuation feasibility.
