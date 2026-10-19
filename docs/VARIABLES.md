# Variable definitions and interpretation

Definitions below are adapted from Driveline Baseball Research & Development's [pitching reference](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/baseball_pitching/README.md), [CSV data dictionary](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/baseball_pitching/data/data_dictionary.csv), and [datasheet](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/DATASHEET.md), pinned to commit `44b98dae05cceb016f080ab39d105c85b8639084`. This document adds project-specific interpretation and modeling cautions. See [LICENSING.md](LICENSING.md) for attribution and the upstream data/documentation terms.

## Unit of observation and joins

One POI row summarizes one pitching trial. The pinned release describes 411 fastball trials from 100 athletes and 100 sessions. These are repeated measurements, not 411 independent athletes.

| Field | Table | Meaning and project use |
| --- | --- | --- |
| `session_pitch` | POI and metadata | Unique pitch ID; validated one-to-one join key. |
| `session` | POI and metadata | Session ID; redundant copies must agree after joining. Excluded from model features. |
| `user` | Metadata | Anonymized athlete ID; cross-validation grouping variable, never a predictor. |
| `filename_new`, `modelname_new` | Metadata | C3D/static-model filenames; excluded from model features. Pitch filenames encode pitch speed and identifiers. |
| `pitch_type`, `p_throws` | POI | Pitch type and pitcher handedness. The pinned pitching release contains fastballs (`FF`). |

An inner join alone can silently lose unmatched pitches. The audit checks missing and duplicate keys, validates join cardinality, checks membership on both sides, and verifies shared values before building the analysis table.

## Five exploratory measures

| Source variable | Definition | Unit | Interpretation |
| --- | --- | --- | --- |
| `pitch_speed_mph` | Pitch speed | mph | Performance target. Present in both tables; retain one agreed copy. |
| `elbow_varus_moment` | Peak elbow varus moment | N·m | Internal net elbow moment; the source's varus convention is positive. Loading target, not an injury outcome. |
| `max_shoulder_internal_rotational_velo` | Peak shoulder internal rotation velocity | degrees/s | Joint rotational velocity, not ball speed. |
| `max_rotation_hip_shoulder_separation` | Peak separation between thorax and pelvis | degrees | Largest separation summary; distinct from separation at a specified event. |
| `max_torso_rotational_velo` | Peak torso axial (Z) rotation velocity | degrees/s | Segment axial rotation summary; does not identify when the torso peaked relative to other segments. |

`rotation_hip_shoulder_separation_fp` is a different variable: hip–shoulder separation **at foot plant**, in degrees. It must not be relabeled as the peak measure. Foot plant is defined by the source as the 100%-body-weight event; foot contact is a separate 10%-body-weight event. The Phase 1 baseline uses the peak separation variable listed above.

A high shoulder rotation velocity and a high torso rotation velocity need not occur at the same time. Peak values cannot establish proximal-to-distal sequencing, segment timing, or energy flow. Those questions require the appropriate time-resolved signals and event definitions in a later analysis.

## Anthropometric baseline predictors

| Field | Definition | Unit |
| --- | --- | --- |
| `age_yrs` | Athlete age at collection | years |
| `session_mass_kg` | Body mass at the assessment | kg |
| `session_height_m` | Body height at the assessment | m |

The two targets are modeled in their original units. Larger athletes may generate larger absolute joint moments; body mass and height therefore belong in the interpretation and in these simple baseline predictors. Including anthropometrics in a predictive model does not establish causal adjustment, remove every confounder, or normalize N·m to body size. A body-size-normalized loading analysis would be a separately specified sensitivity analysis with its own rationale.

## Measurement and loading limitations

The source reports marker-based motion capture and derived joint mechanics. Forces and moments are internal net quantities. By default they are expressed in the proximal segment frame; the source provides special dual-frame quantities at shoulders and hips. The elbow moment convention is varus positive/valgus negative. Marker-derived signals were low-pass filtered using a fourth-order Butterworth filter at 20 Hz; ground-reaction forces used 40 Hz. These processing choices and soft-tissue/modeling artifacts affect the measurements.

An internal net elbow varus moment is not a direct measurement of UCL force, tissue stress, damage, or injury probability. The released tables do not supply an injury outcome for this project. Predicting the released moment estimates an observable loading summary; it does not predict who will be injured or prescribe a safe moment threshold.

The peak kinematic predictors are measured during the same completed pitch as each outcome. These models estimate retrospective relationships and generalization to held-out athletes with those measurements available. They are not forecasts made before a pitch or before a season. Associations cannot establish that changing one mechanic will cause increased speed or reduced loading.

## Population and media scope

The source reports ages approximately 17.7–27.6 years, a predominantly collegiate sample, and only fastballs in this pitching release. Findings do not automatically transfer to MLB pitchers, youth populations, women, other pitch types, injured athletes, other laboratories, or future sessions. A held-out athlete fold is internal validation within this source, not external validation in a professional team.

POI and metadata are sufficient for Phase 1. This project neither assumes synchronized video for every pitch nor treats C3D filenames as video availability. It does not download MLB footage. Pitching metadata's `user` identifiers also do not establish a public crosswalk to the separate High Performance module's `athlete_uid`.
