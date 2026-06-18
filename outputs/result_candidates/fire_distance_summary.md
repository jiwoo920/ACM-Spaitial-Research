# Fire-Distance Candidate Analysis

Distance-to-fire is computed from TIGERweb tract centroids to a representative point: Representative Griffith Park wildfire point (34.1366, -118.2942).

This is an exploratory variable for result-candidate generation, not a verified wildfire perimeter or operational fire-distance measure.

| Group | Condition | n | Mean distance km | Evacuate now | High urgency | Spatial inconsistency | Public shelter |
|---|---:|---:|---:|---:|---:|---:|---:|
| near | baseline | 70 | 9.15 | 100.0% | 100.0% | 40.0% | 2.9% |
| medium | baseline | 70 | 11.03 | 100.0% | 100.0% | 58.6% | 5.7% |
| far | baseline | 60 | 24.22 | 100.0% | 100.0% | 26.7% | 1.7% |
| near | spatial_grounded | 70 | 9.15 | 100.0% | 98.6% | 42.9% | 100.0% |
| medium | spatial_grounded | 70 | 11.03 | 100.0% | 100.0% | 62.9% | 98.6% |
| far | spatial_grounded | 60 | 24.22 | 96.7% | 96.7% | 25.0% | 100.0% |

## Interpretation Candidate

Distance-to-fire is a promising spatial variable for positioning the study, but this candidate should be described as approximate until linked to verified wildfire perimeters or risk surfaces.
