# GIS Label Audit Boxplot Interpretation

These boxplots compare original approximate prompt labels with GIS-derived tract-centroid proxy distances. They are an exploratory GIS-supported audit, not operational validation.

- Transit prompt labels show 20% potential mismatch under the major transit-stop proximity proxy. This suggests partial alignment but also supports treating GIS enrichment as a spatial context extension.
- Shelter prompt labels have a mean absolute difference of 5.52 km against nearest candidate shelter/service proximity. This should not be interpreted as verified shelter reachability.
- Wildfire risk labels are only weakly comparable to the representative fire-point distance; the mean absolute hazard/fire distance difference is 11.27 km. This should not be interpreted as active wildfire exposure.

Safe claim: the GIS audit makes approximate spatial assumptions visible and partially checkable. Avoid claiming route-level reachability, verified wildfire evacuation shelters, active wildfire perimeters, or operational evacuation feasibility.
