# Transit-Stop Proximity Threshold Definition

This memo documents the threshold used to group tract-centroid distance to transit-stop proxy points. The current transit layer uses major transit-stop proxy points rather than full GTFS `stops.txt`, so all results should be described as an exploratory transit-stop proximity proxy, not full transit accessibility or route-level reachability.

## Working Definition

- Near: `nearest_transit_stop_distance_km <= 0.5 km`.
- Moderate: `0.5 < nearest_transit_stop_distance_km <= 1.5 km`.
- Far: `nearest_transit_stop_distance_km > 1.5 km`.
- No nearby stop: no transit proxy within 2 km.
- Simplified figure grouping: Near + Moderate are combined as `Near/Moderate Proximity`; Far + No nearby stop are combined as `Transit-Desert Proxy`.

## Why the Main Figure Uses 1.5 km

The 1.5 km cutoff is a conservative walking-proximity threshold for a lightweight tract-centroid audit. It is wide enough to avoid treating every tract-centroid offset as inaccessible, but still separates tracts with clearly distant major transit proxy points. Because these are major transit-stop proxy points rather than full GTFS stops, the cutoff should not be interpreted as a formal transit-accessibility standard.

## Sensitivity Check

The sensitivity output recalculates no-vehicle household groups at 1.0 km, 1.5 km, and 2.0 km cutoffs. For each cutoff, the audit reports n per group, violation/spatial-inconsistency rate, public-transit recommendation rate, and mode proxy issue rate by condition.

- At the main 1.5 km cutoff, the beyond-threshold group has n = 9/9 responses across baseline/spatially grounded cells, with violation/spatial-inconsistency rates of 100.0% and 100.0%.
- At the stricter 1.0 km cutoff, the beyond-threshold group remains high risk, with violation/spatial-inconsistency rates of 100.0% and 100.0%.
- At the looser 2.0 km cutoff, only the clearest distant-proxy cases remain beyond-threshold, with violation/spatial-inconsistency rates of 100.0% and 100.0%.

## Interpretation

The conclusion does not depend on treating 1.5 km as an exact accessibility boundary: no-vehicle households remain a high-risk group under all tested thresholds. What changes is the size of the beyond-threshold subgroup. Therefore, the main claim should be framed as threshold-sensitive exploratory screening: transit-stop proximity proxies help audit feasibility risks, but they do not prove actual route-level reachability.

## Claims To Avoid

- Do not claim route-level reachability.
- Do not claim full transit accessibility.
- Do not claim the LLM used exact GIS distances unless those distances were in the prompt.
- Do not claim operational evacuation feasibility.
