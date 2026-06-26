# Statistical And Scatter Interpretation

This analysis adds statistical support and optional tract-level scatter figures to the feasibility-audit framing. No new LLM responses were generated.

## Statistical Support

The strongest statistical support remains the relationship between vehicle access and violation/spatial inconsistency. This aligns with the paper's core finding that no-vehicle households are the clearest feasibility-risk group. Tests involving `transit_access` should be interpreted as prompt-label sensitivity tests because the original label is ACS-informed and approximate, not GTFS-derived.

McNemar's test evaluates paired changes between baseline and spatially grounded responses for the same personas. It is useful for checking whether prompt condition changed public-transit recommendation behavior, but it should not be interpreted as external predictive validity.

The transit-stop proxy group tests among no-vehicle households are GIS-proxy feasibility audits. They use tract-centroid distance to major transit-stop proxy points and do not represent route-level reachability.

## Exploratory Scatter Figures

- `project/figures/transit_proxy_distance_vs_risk_scatter.png` shows an exploratory tract-level association between nearest transit-stop proxy distance and feasibility risk.
- `project/figures/shelter_distance_vs_nearby_claim_scatter.png` shows whether candidate shelter/service distance aligns with nearby-shelter language.
- `project/figures/no_vehicle_share_vs_risk_scatter.png` shows whether tracts with more no-vehicle personas also show higher feasibility risk.

The correlation coefficients in these scatter plots are exploratory tract-level associations. They are not model prediction accuracy, do not use real evacuation ground truth, and should not be framed as validating LLM behavior.

## Why Feasibility Rates, Not Prediction-Correlation Metrics

This study evaluates whether LLM-generated evacuation decisions contain obvious feasibility risks under household constraints and spatial proxy checks. Because there is no real evacuation ground truth in the dataset, prediction-correlation metrics would overstate what the experiment can support. Feasibility rates are more appropriate because they audit internal consistency and constraint violations rather than claiming behavioral prediction accuracy.

## Recommended Wording

Use the statistical tests as support for feasibility-audit contrasts, especially vehicle access and no-vehicle transit-proxy risk. Use tract-level scatter plots as exploratory visual diagnostics only. Avoid claiming predictive accuracy, real evacuation validity, operational feasibility, route-level reachability, or verified shelter accessibility.
