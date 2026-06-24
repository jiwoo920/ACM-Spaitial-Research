# Spatial Variable Impact Recommendation

## Ranking of result candidates

1. **Transit access impact**: strongest SRC candidate. It directly answers whether spatially grounded prompting reduces a concrete feasibility mismatch while showing residual risk for no-vehicle households with limited/no transit access.
2. **Paired response change analysis**: useful support. It clarifies whether spatial context changes decisions, mode, destination, urgency, or mostly reasoning language.
3. **Combined spatial constraint analysis**: useful exploratory backup. It identifies high-risk combinations but includes small subgroups, so claims should be cautious.
4. **Hazard distance impact**: useful for spatial positioning, but approximate hazard distances make this exploratory.
5. **Shelter accessibility impact**: relevant but weaker as a main figure because approximate shelter/travel-time fields limit interpretability.

## Recommended SRC figure/table choice

Keep the transit-access grouped bar chart as the main Figure 1 candidate. It is more directly tied to the research question than the older vehicle-access-only figure because it shows both selected improvement and remaining feasibility risk.

A compact paired-change statistic can be added in prose if there is space: spatially grounded prompting changed mode and destination more often than the top-level evacuation decision, suggesting that spatial context may affect operational plan details more than the decision to evacuate.

## Short professor-facing summary

Using the existing 400 GPT-4.1-mini responses, the strongest new candidate result is transit access impact. Spatially grounded prompting reduced public-transit mismatches when transit access was limited, but no-vehicle households with limited/no transit still had high residual violation or spatial-inconsistency risk. Paired response analysis suggests the spatial prompt changes mode, destination, and spatial reasoning more than the top-level evacuation decision. Shelter, hazard-distance, and combined-constraint analyses are useful exploratory checks, but because several spatial attributes are approximate and some subgroup sizes are small, they should be treated as candidate evidence rather than broad generalizable findings.
