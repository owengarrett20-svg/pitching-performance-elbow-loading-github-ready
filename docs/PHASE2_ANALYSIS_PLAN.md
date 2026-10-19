# Phase 2 analysis plan: predictor groups and athlete-level uncertainty

This plan is frozen before running the new Phase 2 comparisons. Phase 1 results and this cohort have already been viewed. This is a transparent **exploratory follow-on**, not a preregistered study or independent confirmatory evidence. The executable specification is [phase2_plan.json](../analysis/phase2_plan.json). Record its SHA-256 digest with each completed analysis so changes to the plan are visible.

## Question and biomechanical rationale

Do completed-pitch rotational kinematics improve held-out-athlete prediction beyond age, mass, and height for **both** pitch speed and peak internal elbow varus moment?

Body size can relate to absolute joint moments, while rotational measures describe aspects of the completed delivery. Comparing these predictor groups separates their predictive contributions within this modeling setup. It is not causal adjustment, an estimate of the effect of changing mechanics, or a test of tissue tolerance. The anthropometric group includes age as well as body-size measures. The outcomes and their units remain `pitch_speed_mph` (mph) and `elbow_varus_moment` (N·m). Neither outcome has priority.

Elbow varus moment is an internal net joint moment, not UCL force or injury probability. No injury outcomes are available. Peak separation and peak angular velocities may occur at different instants; their association with an outcome does not establish segmental sequencing or energy transfer. Absolute N·m is retained; no new body-size normalization is introduced.

## Data and inclusion

Use the same pinned OpenBiomechanics Project source commit, `44b98dae05cceb016f080ab39d105c85b8639084`, and checksum-verified one-to-one POI/metadata join as Phase 1. Include all verified pitches; the expected source contains 411 pitches from 100 athletes. Stop on an unexplained source or join mismatch. Do not remove outliers or select a favorable subgroup.

For each target separately, omit rows with missing or nonfinite observed outcomes and report the excluded count. Never impute an outcome or fill pitch speed from metadata's duplicate speed field. Report predictor missingness without altering the source table. Fit any predictor imputation and standardization using training rows only. The pinned Phase 1 sample has no missing values in the focal predictors or targets; this is not a reason to disable missing-data checks.

No new dataset, footage, synchronized video, event-frame alignment, or motion-model validation is claimed. Existing visual examples remain educational and do not supply extra observations. Source and derived-material licensing conditions continue to apply; see [LICENSING.md](LICENSING.md).

## Fixed predictor groups and models

| Model ID | Predictor group |
| --- | --- |
| `dummy_mean` | Training-fold mean outcome; no predictor dependence |
| `ridge_anthropometric` | `age_yrs`, `session_mass_kg`, `session_height_m` |
| `ridge_kinematic` | `max_shoulder_internal_rotational_velo`, `max_rotation_hip_shoulder_separation`, `max_torso_rotational_velo` |
| `ridge_combined` | All six listed predictors |

All ridge models use fixed `alpha=10`, with training-fold median imputation, missingness indicators, and training-fold standardization. Preserve the existing all-missing-training-feature fallback as a computational convention rather than a measured value. Training and scoring use only rows with observed finite outcomes for the target. There is no feature search, correlation-based selection, hyperparameter tuning, or nonlinear model comparison in Phase 2.

Exclude both targets, IDs, session labels, filenames, other kinetic/energetic variables, and any duplicate outcome fields from every predictor set. Source filenames encode speed. The combined model deliberately reproduces the Phase 1 feature specification rather than adding information learned from the test folds.

## Shared athlete-grouped evaluation

Generate five-fold shuffled `GroupKFold` assignments using athlete `user` and **seed 42**. Construct the assignments before target-specific filtering and reuse them across targets and all four models. All pitches from each athlete stay together; no held-out athlete occurs in the corresponding training set. This matches the Phase 1 primary partition.

Save per-pitch observed values, predictions, residuals, absolute errors, athlete IDs, and fold labels, together with the exact predictor list and train/test athlete audit. Preserve identifiers for auditing and display, never as predictors.

This estimates performance for held-out athletes in the same source setting. The cohort has one released session per athlete; the analysis does not test future-session forecasting, new laboratories, MLB players, or causal interventions. Training-fold overlap also means fold scores and prediction errors cannot be treated as independent experiments.

## Estimands and paired comparisons

The **primary metric is equal-athlete MAE** (`athlete_mae`): calculate mean absolute error within each athlete and then average those athlete means equally. This prevents athletes with more recorded pitches from receiving more weight in the primary summary.

The **primary contrast**, reported for each target, is:

```text
equal-athlete MAE(ridge_combined) − equal-athlete MAE(ridge_anthropometric)
```

Negative differences favor the combined model. A lower error is a predictive result in this cohort, not a demonstrated benefit of changing the athlete's mechanics.

Secondary summaries are pooled pitch MAE, RMSE, and R². Pooled MAE weights pitches equally; RMSE emphasizes large errors. R² can be negative and is undefined for a constant observed outcome. Retain those behaviors rather than clipping scores.

Prespecified secondary contrasts are combined minus kinematic, kinematic minus anthropometric, and each of the three ridge models minus the training-mean baseline. Report every planned contrast for both outcomes, including unfavorable findings. Do not select the most favorable target, partition, or model after looking at the results.

## Conditional paired athlete-cluster bootstrap

For the seed-42 out-of-fold predictions, use **5,000 bootstrap resamples**, RNG seed **20261019**, and **95% percentile intervals** at quantiles 0.025 and 0.975. Bootstrap equal-athlete MAE and pooled MAE for the paired model differences. These are conditional descriptive uncertainty intervals.

Within each target, draw the number of eligible athletes with replacement from its observed eligible athlete IDs. Each sampled athlete contributes all their observed pitches. Use the same draw and athlete multiplicities for the two models in each contrast. An athlete drawn three times contributes three times; converting the draw to a set is incorrect.

- For equal-athlete MAE, average athlete-level MAEs using bootstrap draw multiplicities.
- For pooled MAE, sum each athlete's absolute errors with those multiplicities and divide by the correspondingly weighted pitch count.
- Compute the paired difference within each resample, then take its empirical percentile limits. Do not subtract endpoints of separately calculated model intervals.

These intervals condition on already fitted models and their fixed out-of-fold predictions. They do **not** include full model-refitting, training-set, tuning, external-cohort, or measurement uncertainty. Resampling by athlete respects within-athlete pitch clustering, but it does not remove dependencies induced by overlapping cross-validation training sets or turn these intervals into exact frequentist coverage guarantees for an external population.

There are two outcomes and several related contrasts. No p-values, formal significance threshold, confirmatory multiplicity claim, or declaration that an interval excluding zero establishes a biomechanical effect is planned. Present magnitude, direction, units, and the conditional interpretation together.

## Partition sensitivity with full refitting

Repeat the complete grouped evaluation for ten prespecified seeds, **42 through 51 inclusive**, with five folds each. Refit imputation, scaling, mean predictors, and ridge models inside every training fold for every seed. Reuse that seed's assignments across targets and models. Seed 42 remains the primary analysis and is included in the ten-run summary.

Save per-seed metrics and paired contrasts. Describe the range and direction of results across partitions and show the individual values. These ten results reuse the same cohort, have overlapping training sets, and are not independent replications. Their range, standard deviation, or fold spread must not be labeled a confidence interval. Do not choose the best seed as the reported result.

## Outputs, checks, and interpretation

The implementation should produce auditable model metrics, paired contrast intervals, sensitivity results, fold/feature manifests, provenance, figures, and a short report. It should test disjoint athlete partitions, shared folds across models/targets, training-only preprocessing, deterministic resampling, duplicate-athlete weighting, paired interval arithmetic, forbidden-feature rejection, and reproduction of the Phase 1 combined baseline.

Report exceptions and missingness explicitly. Pipeline completion requires a consistent set of output hashes; a dashboard must reject a partial or stale report set. Future changes to this plan require a new plan digest and an explanation, rather than silently replacing the original specification.

Discussion should answer whether the additional kinematic predictors improve the selected prediction metric in this sample, how sensitive that answer is to athlete partitions, and how uncertain the conditional error contrast is. It should also state what remains unresolved: external validity, prospective prediction, measurement error, tissue-specific loading, injury outcomes, and causal effects. No new normalized-moment claim or synchronized video claim follows from this phase.

Source definitions and documentation adaptations retain the upstream data terms; original software remains separately licensed. See [LICENSING.md](LICENSING.md).
