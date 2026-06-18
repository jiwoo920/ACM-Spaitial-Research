# Transit Access Candidate Analysis

This candidate keeps the existing transit result but separates the overall limited-transit pattern from the no-vehicle + limited/no transit subgroup.

## Key Checks

- Public transit selected when transit access is limited: baseline 26.7%, spatially grounded 6.7%.
- No-vehicle + limited/no transit, baseline: n=8, violation/spatial-inconsistency 100.0%, public transit 100.0%, ride 0.0%, public shelter 0.0%.
- No-vehicle + limited/no transit, spatial_grounded: n=8, violation/spatial-inconsistency 87.5%, public transit 25.0%, ride 50.0%, public shelter 100.0%.

## Interpretation Candidate

Transit access helps explain why no-vehicle households remain difficult for LLM-generated evacuation planning. Spatially grounded prompting appears to reduce public-transit recommendations when transit is limited, but mobility feasibility risks remain in the no-vehicle + limited/no transit subgroup.
