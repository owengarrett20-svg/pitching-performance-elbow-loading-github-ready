# Data audit

Source revision: `44b98dae05cceb016f080ab39d105c85b8639084`.

POI: 411 rows; metadata: 411 rows. Join: **one to one**, 411 matched pitches, 100 athletes, 100 sessions. No unmatched or duplicate pitch IDs. Shared sessions and observed pitch speeds agree.

25 POI columns have missing observations. See missingness.csv for every column in each source table and the merged table; missing values remain missing.

One row is a pitch, not an independent athlete. Hip–shoulder separation is a peak angle, not specifically the foot-plant angle. Elbow varus moment is an internal net moment, not tissue-specific ligament loading or an injury endpoint.

Source: Driveline Baseball Research & Development, OpenBiomechanics Project. Data-derived outputs: upstream CC BY-NC-SA 4.0 with its additional professional-organization exclusion; see docs/LICENSING.md. This report joins and summarizes the original source tables.
