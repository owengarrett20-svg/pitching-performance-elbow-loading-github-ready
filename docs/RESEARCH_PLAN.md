# Phase 1 research plan

**Question:** How well do a small set of anthropometric and completed-pitch kinematic summaries predict pitch speed and peak internal elbow varus moment for athletes withheld from model fitting?

This is a reproducible exploratory study, not a causal mechanics intervention, prospective injury model, or professional-team decision system. The source is Driveline Baseball Research & Development's OpenBiomechanics Project at commit [`44b98dae05cceb016f080ab39d105c85b8639084`](https://github.com/drivelineresearch/openbiomechanics/tree/44b98dae05cceb016f080ab39d105c85b8639084). Definitions and sample characteristics follow its [pitching reference](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/baseball_pitching/README.md), [data dictionary](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/baseball_pitching/data/data_dictionary.csv), and [datasheet](https://github.com/drivelineresearch/openbiomechanics/blob/44b98dae05cceb016f080ab39d105c85b8639084/DATASHEET.md). See [VARIABLES.md](VARIABLES.md) and [LICENSING.md](LICENSING.md).

## Smallest runnable milestone: trustworthy analysis table

Start with only the official pitching POI and metadata CSVs, loaded using their documented schema. No large C3D archive, full-signal release, MATLAB installation, or video is necessary.

The first useful output is an audit report that:

1. Records the pinned source, source-file checksums, environment, and row counts.
2. Rejects missing/duplicate `session_pitch` keys, unmatched pitches, and disagreement in shared `session` or `pitch_speed_mph` values; joins with one-to-one validation.
3. Reports athlete and session counts, pitches per athlete, pitch types, and column-level missingness before modeling.
4. Lists the exact target and predictor definitions and units without silently renaming similar variables.

The pinned upstream datasheet describes 411 pitches, 100 athletes, and 100 sessions. Verify those counts from the files; do not manufacture rows to match an expectation. Stop on an unexplained structural mismatch rather than proceeding with a misleading merged dataset. This milestone makes subsequent plots and scores interpretable.

## Exploratory analysis

Produce distributions for pitch speed (mph), peak elbow varus moment (N·m), peak shoulder internal rotation velocity (degrees/s), peak hip–shoulder separation (degrees), and peak torso rotation velocity (degrees/s). Add scatter plots relating the kinematic summaries and loading to pitch speed, with sample sizes and units visible. Retain the distinction between peak separation and separation at foot plant.

Trial-level summaries weight athletes with more pitches more heavily. Include athlete counts and repeated-measures context; do not attach independent-trial inferential claims to those plots. Use descriptive associations to characterize the sample and identify potential data-quality issues. Do not automatically remove unusual observations or replace missing measurements with plausible-looking values.

## Prespecified baseline models

Fit two separate regression tasks:

- Target 1: `pitch_speed_mph`, scored in mph.
- Target 2: `elbow_varus_moment`, scored in N·m.

Use the same small, fixed predictor set for both:

```text
age_yrs
session_mass_kg
session_height_m
max_shoulder_internal_rotational_velo
max_rotation_hip_shoulder_separation
max_torso_rotational_velo
```

Compare a **training-fold mean** predictor (`DummyRegressor`, mean strategy) with **ridge regression using fixed alpha = 10**. A mean baseline establishes how much can be gained over predicting a typical pitch. Ridge supplies a simple regularized linear model for correlated rotational summaries while keeping model complexity modest for 100 athletes. Alpha is fixed in advance; Phase 1 does not tune it against the reported evaluation folds or select predictors using their outcome correlations.

Keep both targets, other kinetic/energetic summaries, `user`, `session`, `session_pitch`, and all filenames out of the feature matrix. Metadata repeats pitch speed, and pitch filenames encode it; accidentally including these fields would invalidate the speed model. Excluding identifiers also prevents learning arbitrary labels for individual athletes or sessions.

## Leakage-safe evaluation

Use five-fold **shuffled `GroupKFold`**, grouped by metadata `user`, with random seed **42**. Every pitch from an athlete belongs to one evaluation fold, and that athlete is absent from the corresponding training set. Record each pitch's athlete, fold, observed outcome, out-of-fold prediction, and residual for reproducible error inspection.

For each target, exclude rows missing that observed outcome and report the exclusion count. Never impute the target. If a predictor is missing, fit its median imputation using the training fold only; fit feature standardization inside that same training pipeline before ridge regression. Apply those learned transformations to the held-out fold. Imputed predictor values are modeling estimates, not new observed measurements, and the raw missingness audit must remain available.

A shuffled row split would mix pitches from the same athlete across training and evaluation, allowing stable athlete characteristics to inflate apparent performance. Athlete grouping asks a more useful portfolio question: performance for another athlete measured in the same source setting. The source has one released session per athlete here, so this design does not measure within-athlete forecasting across future sessions.

Report, for each model and target:

- Pooled out-of-fold trial **MAE**, **RMSE**, and **R²**, with physical units for MAE/RMSE.
- **Macro-athlete MAE**: compute mean absolute error within each athlete, then average those athlete means equally.
- Per-fold scores and sample/athlete counts to expose variation across folds.

Trial MAE weights pitches equally; macro-athlete MAE gives equal weight to athletes despite differing pitch counts. Negative held-out R² is possible and should be reported. Comparisons are descriptive internal validation. Do not treat folds or repeated pitches as independent experiments, claim statistical significance from five scores, or assert an uncertainty interval that has not been computed with an appropriate athlete-level procedure.

## Dashboard and tests

The Streamlit dashboard should expose the audited data, distributions, associations, and out-of-fold observed-versus-predicted values and errors. Show source/units, available sample size, model/target choice, and limitations. Subgroup filters describe that subset; they do not retrain a tuned model or turn its errors into an external validation. The optional visual extension adds labeled marker replays and a separate camera example; it does not change the Phase 1 model specification or imply paired video for each trial.

Tests should cover malformed join keys and cardinality, shared-value conflicts, missingness accounting, source-schema expectations, target/identifier exclusion, athlete separation across folds, and correct out-of-fold scoring. Exercise the dashboard with an automated smoke test. Preserve a documented environment and deterministic commands so another researcher can regenerate the audit, plots, predictions, and dashboard from the pinned files.

## Interpretation boundaries and later work

The biological interpretation concerns performance and an internal net loading summary. Net elbow varus moment does not directly reveal UCL force or injury risk, and these tables contain no injury endpoint. Absolute N·m depends partly on body size; including mass and height does not establish a causal loading mechanism. Same-pitch peak kinematics make the models retrospective, not forecasts from pre-pitch information. Peak summaries cannot recover kinematic sequence or energy transfer.

The sample is small, primarily collegiate, restricted to fastballs, and collected under a particular measurement/modeling pipeline. Held-out-athlete validation does not establish generalization to MLB, youth, other pitch types, injured athletes, or other laboratories. No synchronized video is assumed. No copyrighted MLB footage is acquired.

Later phases may preregister sensitivity analyses for body-size normalization, obtain a genuinely external cohort, inspect time-resolved signals with their sampling rates and event definitions, or evaluate a richer model using nested athlete-grouped validation. Those extensions are outside Phase 1. Professional-sports or commercial reuse must follow the upstream licensing conditions before any such deployment.

This plan adapts source dataset descriptions and definitions and adds this project's analysis design. Documentation adaptations follow CC BY-NC-SA 4.0 with the additional upstream exclusion; see [LICENSING.md](LICENSING.md). No statistical performance result is asserted in this plan.
