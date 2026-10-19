# Study summary: Phases 1 and 2

**Question.** Do completed-pitch rotational summaries add predictive information
beyond age, mass, and height for pitch speed and peak internal elbow varus moment
in held-out athletes from this source cohort?

**Scope.** This exploratory study uses Driveline Baseball Research & Development's
[OpenBiomechanics Project](https://github.com/drivelineresearch/openbiomechanics/tree/44b98dae05cceb016f080ab39d105c85b8639084),
pinned to commit `44b98dae05cceb016f080ab39d105c85b8639084`. The cohort contains
411 fastball pitches from 100 athletes and 100 sessions, primarily collegiate
players. Pitch speed spans 69.5–94.4 mph. It is not an MLB-representative sample.

## Data trust and biomechanical interpretation

The official POI and metadata CSVs use their documented schema. Both have 411
unique `session_pitch` keys and match one-to-one; shared session and observed-speed
fields agree. The audit verifies these properties before analysis. All focal
measures and predictors are observed. Twenty-five other POI columns each contain
eight missing observations, which remain missing.

Age, mass, and height form the anthropometric group. The kinematic group contains
peak shoulder internal rotation velocity, peak hip–shoulder separation, and peak
torso rotation velocity. Peak separation differs from separation at foot plant.
These peaks can occur at different instants and do not reconstruct sequencing or
energy transfer. See [VARIABLES.md](VARIABLES.md).

## Evaluation design

Phase 1 established the audit and combined baseline. The [Phase 2 plan](PHASE2_ANALYSIS_PLAN.md)
was committed before running the new comparisons, after Phase 1 had been viewed.
This is an exploratory follow-on, not preregistration or independent confirmation.

Four models share five athlete-grouped folds, primary seed 42: training-fold mean,
anthropometric ridge, kinematic ridge, and combined ridge. All ridge models use
fixed `alpha=10`. Imputation and standardization fit only within training folds.
Targets, identifiers, and speed-encoding filenames are excluded as predictors;
missing outcomes are never imputed. The mean and combined predictions reproduce
Phase 1 within recorded numerical tolerance.

**Equal-athlete MAE is primary:** average absolute error within each athlete, then
average those means equally. All primary scores use 411 pitches and 100 athletes:

| Model | Speed equal-athlete MAE, mph | Elbow moment equal-athlete MAE, N·m |
| --- | ---: | ---: |
| Training-fold mean | 3.807 | 15.662 |
| Age, mass, height | 3.542 | 12.404 |
| Three rotational measures | 3.530 | 15.557 |
| Combined | 3.153 | 12.104 |

## Primary results and conditional uncertainty

The primary contrast is combined minus anthropometric equal-athlete MAE, with
negative differences favoring the combined model:

| Outcome | Difference | Conditional 95% interval |
| --- | ---: | ---: |
| Speed, mph | -0.389 | [-0.749, -0.029] |
| Elbow moment, N·m | -0.299 | [-1.218, 0.628] |

The speed contrast has a conditional interval below zero. The elbow contrast
includes zero: its small observed improvement leaves the incremental predictive
value of these kinematic summaries uncertain. Kinematics alone also have higher
elbow-moment error than anthropometrics. Unfavorable comparisons are retained.

Intervals use 5,000 paired athlete-cluster percentile resamples, seed 20261019,
preserving all pitches and sampled athlete multiplicities. They condition on
fixed out-of-fold predictions and the observed cohort. There is no refitting
within bootstrap draws; full training-set, model-selection, external-cohort, and
measurement uncertainty are excluded. Overlapping training folds limit sampling
interpretation. No p-values or multiplicity-adjusted confirmation are claimed.

Ten complete evaluations refit training pipelines for seeds 42–51. Primary
contrasts range from -0.430 to -0.213 mph and -0.398 to -0.037 N·m. These partitions
reuse the same athletes; they are sensitivity analyses, not independent
replications or confidence intervals. The [complete report](PHASE2_RESULTS.md)
includes all scores, planned contrasts, figures, and output links.

## What the study supports and what remains

The study demonstrates reproducible, internally validated prediction comparisons
on unseen athletes from the same source. Predictors summarize completed pitches;
this is retrospective prediction, not pre-pitch forecasting or causal evidence
that changing mechanics improves performance. One released session per athlete
prevents future-session evaluation. External validation remains unperformed.

Internal net elbow moment is a joint-loading measure, not UCL force, tissue
damage, injury probability, or a safe threshold. There are no injury labels.
Three marker replays and traces are linked to study pitches; the separate camera
example is not. Marker frames and processed-signal events have not been
independently synchronized. Phase 2 adds no new video, pose estimation, or moment
estimation from footage. See [VIDEO_METHODS.md](VIDEO_METHODS.md).

Reproduce both phases with `uv run --frozen pitching phase2` after environment
installation. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for offline use,
provenance, and snapshot refresh instructions. Version 0.4.0 is implemented in
this checkout; updating the public app requires publishing the code and snapshot.

**Attribution and use.** Source data and definitions: Driveline Baseball Research
& Development and Kyle Boddy, *The OpenBiomechanics Project*. This project adds
audits, figures, models, conditional error summaries, and educational adaptations;
it does not imply Driveline endorsement. Original software is MIT. OBP material
and derivatives retain CC BY-NC-SA 4.0 **plus the upstream professional-sports/
financial-analysis affiliation exclusion**. Such excluded use requires the
licensor's specific written paid license. Read [LICENSING.md](LICENSING.md).
