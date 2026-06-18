# Cross-Model Comparison Candidate

This comparison uses the existing gpt-4o-mini 50-persona validation subset and the matching GPT-4.1-mini main-experiment personas. Gemini and Claude are not included because no Gemini/Anthropic run has been executed in the current package.

| Model | Condition | Metric | Value |
|---|---|---:|---:|
| gpt-4.1-mini_main_subset | baseline | mode_feasibility_rate | 100.0% |
| gpt-4.1-mini_main_subset | baseline | soft_feasibility_issue_rate | 0.0% |
| gpt-4.1-mini_main_subset | baseline | spatial_inconsistency_rate | 58.0% |
| gpt-4.1-mini_main_subset | baseline | no_vehicle_violation_or_spatial_inconsistency_rate | 85.3% |
| gpt-4.1-mini_main_subset | baseline | limited_transit_public_transit_rate | 0.0% |
| gpt-4.1-mini_main_subset | baseline | lower_income_public_shelter_rate | 7.3% |
| gpt-4.1-mini_main_subset | baseline | lower_income_hotel_motel_rate | 0.0% |
| gpt-4.1-mini_main_subset | spatial_grounded | mode_feasibility_rate | 100.0% |
| gpt-4.1-mini_main_subset | spatial_grounded | soft_feasibility_issue_rate | 0.0% |
| gpt-4.1-mini_main_subset | spatial_grounded | spatial_inconsistency_rate | 68.0% |
| gpt-4.1-mini_main_subset | spatial_grounded | no_vehicle_violation_or_spatial_inconsistency_rate | 100.0% |
| gpt-4.1-mini_main_subset | spatial_grounded | limited_transit_public_transit_rate | 0.0% |
| gpt-4.1-mini_main_subset | spatial_grounded | lower_income_public_shelter_rate | 97.6% |
| gpt-4.1-mini_main_subset | spatial_grounded | lower_income_hotel_motel_rate | 0.0% |
| gpt-4o-mini_validation_50 | baseline | mode_feasibility_rate | 100.0% |
| gpt-4o-mini_validation_50 | baseline | soft_feasibility_issue_rate | 0.0% |
| gpt-4o-mini_validation_50 | baseline | spatial_inconsistency_rate | 4.0% |
| gpt-4o-mini_validation_50 | baseline | no_vehicle_violation_or_spatial_inconsistency_rate | 2.9% |
| gpt-4o-mini_validation_50 | baseline | limited_transit_public_transit_rate | 0.0% |
| gpt-4o-mini_validation_50 | baseline | lower_income_public_shelter_rate | 68.3% |
| gpt-4o-mini_validation_50 | baseline | lower_income_hotel_motel_rate | 0.0% |
| gpt-4o-mini_validation_50 | spatial_grounded | mode_feasibility_rate | 100.0% |
| gpt-4o-mini_validation_50 | spatial_grounded | soft_feasibility_issue_rate | 0.0% |
| gpt-4o-mini_validation_50 | spatial_grounded | spatial_inconsistency_rate | 20.0% |
| gpt-4o-mini_validation_50 | spatial_grounded | no_vehicle_violation_or_spatial_inconsistency_rate | 26.5% |
| gpt-4o-mini_validation_50 | spatial_grounded | limited_transit_public_transit_rate | 0.0% |
| gpt-4o-mini_validation_50 | spatial_grounded | lower_income_public_shelter_rate | 100.0% |
| gpt-4o-mini_validation_50 | spatial_grounded | lower_income_hotel_motel_rate | 0.0% |

## Interpretation Candidate

The cross-model candidate should be framed as model sensitivity, not model-invariant robustness. If Gemini or Claude results are added later, this table can become a stronger multi-model comparison.
