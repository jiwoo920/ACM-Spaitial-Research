# Figure and Table Candidate Recommendations

These are candidates for a 2-page SRC abstract. Do not include all of them; use the strongest and clearest subset.

## Strongest Current Candidates

1. **Vehicle access figure** (`figures/main_experiment_gpt_acs_200/violation_by_vehicle_access.png`): strongest main finding; directly supports the claim that no-vehicle households are the clearest feasibility-risk group.
2. **Transit secondary table** (`outputs/result_candidates/no_vehicle_transit_access_analysis.csv`): useful compact explanation of why no-vehicle households remain difficult, especially when transit access is limited.
3. **Cross-model comparison table/heatmap** (`outputs/result_candidates/cross_model_comparison_summary.csv`): useful only as a model-sensitivity result, not as a robustness claim.

## Promising but Secondary

- **Income analysis**: useful equity candidate, but may broaden the SRC abstract away from mobility/spatial feasibility unless destination-type differences are central.
- **Fire-distance analysis and map**: promising for SIGSPATIAL positioning, but currently based on an exploratory representative point rather than verified wildfire perimeter data.

## Suggested 2-page SRC Combination

- Keep Table 1: baseline vs. spatially grounded feasibility metrics.
- Keep Figure 1: vehicle access gap.
- Add either a small transit secondary table or one sentence from the fire-distance/map candidate, depending on available space.
- Mention cross-model comparison in 1 sentence as model sensitivity if space allows.

## Interpretation Guardrails

- Say: spatially grounded prompting improves selected metrics.
- Say: feasibility risks remain.
- Say: variable-based analysis reveals which household/spatial constraints matter.
- Say: model comparison reveals model sensitivity.
- Do not say: spatial grounding solves the problem.
- Do not say: the effect is model-invariant.
- Do not say: LLM decisions are reliable.
