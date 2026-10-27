# Measured-marker replay catalog

Source: Driveline Baseball Research & Development, OpenBiomechanics Project.

https://github.com/drivelineresearch/openbiomechanics/releases/download/dataset-v1/pitching_c3d.zip

Source release archive SHA-256: `2f5277dc63c7f7535fa4b15310d6f38b3f3b761e572896eec529854c8c920d29`.

Changes: exact metadata-linked C3Ds selected; observed skin-marker coordinates converted to meters and retained every sixth source sample; guide links and numerical arrays prepared for an interactive display. Missing points remain missing.

Some source trajectories carry a single Skeleton_<digits>_ subject namespace. That namespace is removed only from known body-marker display labels, with the complete original labels and reversible alias map retained. Coordinates, sampling, and signs are unchanged; different subjects are never merged.

These are motion-capture marker replays, not camera recordings or validated skeletal models. Their clocks have not been aligned to released processed signals or pitch events.

Data and derivatives retain CC BY-NC-SA 4.0 plus the upstream additional professional-sports / financial-analysis affiliation exclusion. Original software licensing does not grant data rights.

Full terms: https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/LICENSE-DATA.md
