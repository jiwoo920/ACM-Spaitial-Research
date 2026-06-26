# Statistical Tests Summary

These tests use the existing 400-response GIS-enriched dataset. They provide statistical support for feasibility-audit findings, not ground-truth evacuation prediction accuracy.

## Main Tests

- Vehicle access vs. violation/spatial inconsistency was tested separately for baseline and spatially grounded conditions using Fisher's exact test.
- Original `transit_access` label vs. public transit recommendation was tested separately by condition using chi-square or simulated Fisher exact tests depending on expected cell counts.
- Baseline vs. spatially grounded public-transit recommendation was tested as a paired persona-level comparison using McNemar's test.
- Transit-stop proxy group vs. violation/spatial inconsistency among no-vehicle households was tested using Fisher's exact test.

## Significant Results At p < 0.05
- Vehicle access vs violation/spatial inconsistency (Baseline): Fisher exact, p = <0.001, odds_ratio = 0
- Vehicle access vs violation/spatial inconsistency (Spatially grounded): Fisher exact, p = <0.001, odds_ratio = 0
- Original transit_access label vs public transit recommendation (Baseline): Fisher exact simulated p-value, p = <0.001, Cramers_V = 0.2748
- Original transit_access label vs public transit recommendation (Spatially grounded): Fisher exact simulated p-value, p = <0.001, Cramers_V = 0.382

## Interpretation Boundary

These tests support subgroup differences and prompt/proxy associations within the experiment. They do not validate LLM decisions against real evacuation behavior, and they do not establish route-level transit reachability or verified shelter access.
