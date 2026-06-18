# Income Subgroup Analysis

This candidate uses the existing GPT-4.1-mini 400-response main experiment. Lower-income households are defined by the existing `is_low_income` feasibility-rule flag.

## Summary

| Group | Condition | n | Violation/spatial inconsistency | Soft issue | Public shelter | Hotel/motel |
|---|---:|---:|---:|---:|---:|---:|
| lower_income | baseline | 166 | 43.4% | 4.8% | 4.2% | 0.0% |
| higher_income | baseline | 34 | 38.2% | 0.0% | 0.0% | 0.0% |
| lower_income | spatial_grounded | 166 | 45.8% | 1.2% | 99.4% | 0.0% |
| higher_income | spatial_grounded | 34 | 38.2% | 0.0% | 100.0% | 0.0% |

## Interpretation Candidate

Income-related patterns are useful as a secondary equity result, especially for destination feasibility. However, this analysis should not replace the main mobility-feasibility finding unless destination-type differences are clearer than the vehicle/transit results.
