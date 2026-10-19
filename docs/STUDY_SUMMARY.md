# Study summary

**Question.** How well do a small set of anthropometric and completed-pitch
kinematic summaries predict pitch speed and peak internal elbow varus moment for
athletes withheld from model fitting?

**Scope.** This exploratory study uses Driveline Baseball Research & Development's
[OpenBiomechanics Project](https://github.com/drivelineresearch/openbiomechanics/tree/44b98dae05cceb016f080ab39d105c85b8639084),
pinned to commit `44b98dae05cceb016f080ab39d105c85b8639084`. The cohort contains
411 fastball pitches from 100 athletes and 100 sessions, primarily collegiate
players. Pitch speed spans 69.5–94.4 mph. It is not an MLB-representative sample.

## Data trust comes first

The official pitching POI and metadata CSVs are loaded using their documented
schema. Both have 411 unique `session_pitch` keys and match one-to-one; shared
session and observed-speed fields agree. The audit checks these properties before
analysis and records column-level missingness. All five focal measures and six
model predictors are observed in the pinned data. Twenty-five other POI columns
each contain eight missing observations; these remain missing.

The five focal measures are pitch speed (mph), peak internal elbow varus moment
(N·m), peak shoulder internal rotation velocity (deg/s), peak hip–shoulder
separation (deg), and peak torso rotation velocity (deg/s). Peak separation is
distinct from separation at foot plant. Peaks can occur at different instants;
they do not reconstruct segment sequencing. See [VARIABLES.md](VARIABLES.md).

## Evaluation and results

Both outcomes use six prespecified predictors: age, mass, height, peak shoulder
internal rotation velocity, peak hip–shoulder separation, and peak torso rotation
velocity. A training-fold mean is compared with ridge regression at fixed
`alpha=10`. Five shuffled athlete-grouped folds use seed 42; each athlete appears
in exactly one held-out fold. Training-fold imputation and standardization prevent
information leakage. Neither targets, identifiers, nor speed-encoding filenames
are predictors, and missing outcomes are never imputed.

Pooled out-of-fold results for all 411 observed outcomes:

| Outcome | Mean baseline MAE | Ridge MAE | Ridge RMSE | Ridge R² |
| --- | ---: | ---: | ---: | ---: |
| Pitch speed | 3.828 mph | 3.037 mph | 3.876 mph | 0.323 |
| Elbow moment | 15.636 N·m | 12.395 N·m | 15.885 N·m | 0.345 |

Ridge improves on predicting the training mean in this cohort, with substantial
remaining error. Equal-athlete ridge MAE is 3.153 mph and 12.104 N·m, respectively;
this weights every athlete equally rather than every pitch equally. Fold-level
variation is saved, but these results do not include inferential confidence
intervals. Full specifications and predictions are reproducible from the locked
environment; see [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

## What the study supports

The work demonstrates a transparent analysis workflow and internal validation on
unseen athletes from the same source. Predictors are measured during the completed
pitch, so this is retrospective prediction. It does not establish pre-pitch
forecasting, causal mechanics changes, or transfer to a different laboratory or
professional team. One session per athlete prevents a future-session evaluation.

Internal net elbow moment is a joint-loading summary, not UCL force, tissue
damage, or injury probability. There are no injury labels. Three illustrative
marker replays and their traces are linked to study pitches; the separate camera
example is not. Marker animation frames have not been synchronized independently
to processed-signal event times. See [VIDEO_METHODS.md](VIDEO_METHODS.md).

**Attribution and use.** Source data and definitions: Driveline Baseball Research
& Development and Kyle Boddy, *The OpenBiomechanics Project*. This project adds
joins, audits, figures, models, and educational adaptations; it does not imply
Driveline endorsement. Original software is MIT. OBP material and derivatives
retain CC BY-NC-SA 4.0 **plus the upstream professional-sports/financial-analysis
affiliation exclusion**. Such excluded use requires the licensor's specific
written paid license. Read [LICENSING.md](LICENSING.md) before reuse.
