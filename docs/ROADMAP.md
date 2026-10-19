# Research and portfolio roadmap

The goal is a reproducible project with claims matched to its evidence. Stages
below distinguish implemented analyses from publication work and future research.
Publication here means a labeled software/research release, not peer review.

## 1. Phase 1: data trust and a runnable research portfolio — implemented

The source/schema/license audit, one-to-one join checks, missingness summaries,
exploratory figures, combined ridge and training-mean baselines, athlete-grouped
validation, tests, documentation, and read-only hosted snapshot are implemented.
The portfolio repository and public dashboard already exist. See the
[study summary](STUDY_SUMMARY.md) and [reproducibility guide](REPRODUCIBILITY.md).

Marker animations, processed traces, and instructional schematics remain clearly
distinguished. Existing camera material is a separate official demonstration,
without a verified identity link to study pitches or assumed synchronization.

## 2. Phase 2: fixed predictor-group comparisons — implemented

**Question:** How much predictive information do three released rotational
summaries add beyond age, mass, and height?

The [analysis plan](PHASE2_ANALYSIS_PLAN.md) and machine-readable specification were
committed before the Phase 2 comparisons. Phase 1 results had already been viewed;
this remains an exploratory follow-on, not preregistration or confirmation.

Training-mean, anthropometric-only, kinematic-only, and combined models share the
same five athlete-grouped folds. Ridge alpha remains fixed at 10; all learned
preprocessing stays within training folds. Both outcomes, all planned contrasts,
and unfavorable results are reported in [PHASE2_RESULTS.md](PHASE2_RESULTS.md).

**Completed evidence:** the combined-minus-anthropometric equal-athlete MAE is
-0.389 mph for speed and -0.299 N·m for elbow moment in the primary partition.
The latter's conditional interval includes zero. The findings do not establish
causal effects of mechanics changes or the superiority of a model externally.

## 3. Phase 2: conditional athlete-level uncertainty — implemented

**Question:** How sensitive are saved error contrasts to sampled athletes and
partition choices?

The implementation uses 5,000 paired athlete-cluster percentile resamples of
fixed out-of-fold errors, seed 20261019. Athlete multiplicity and within-athlete
pitch clustering are retained. Conditional 95% intervals for the primary contrast
are [-0.749, -0.029] mph and [-1.218, 0.628] N·m.

Ten complete grouped evaluations refit preprocessing and models for seeds 42–51.
Their results are shown individually and as descriptive ranges. These overlapping
partitions are neither independent experiments nor confidence intervals.

**Scope boundary:** bootstrap intervals exclude model-refitting and full
training-set uncertainty. They do not supply external validation, exact coverage
guarantees, or multiplicity-adjusted confirmation. A broader uncertainty target
would require a separately justified design and explicit full-pipeline refitting.

## 4. Publish and archive the Phase 2 release — pending

Version 0.4.0 and its verified reference snapshot are implemented locally. Update
the existing repository and hosted app, run automated checks on the published
revision, and verify the Phase 2 dashboard against the saved report. Preserve
the current live URL, source attribution, and data restrictions.

Then create a tagged software release with the actual version and repository
URLs. Add a DOI only if an archival service issues one. A local commit or release
package does not establish that these publication steps have happened.

**Done when:** a fresh checkout reproduces both phases, public CI passes on the
release revision, the hosted app shows matching results, and another researcher
can identify the units, sample, evaluation unit, and licensing limits from the
README and study summary.

## 5. Establish external or temporal validation — proposed

**Question:** Do the fixed definitions and model generalize to a genuinely new
cohort or later assessment sessions?

Obtain an appropriately licensed dataset and document instrumentation, units,
population, and signal-convention compatibility before analysis. Freeze the
model specification before viewing evaluation outcomes. Keep athlete identities
separated across development and evaluation; distinguish new sessions from new
athletes. Revisit permissions before professional-team or commercial use.

**Done when:** provenance, permission, cohort shift, missingness, and external
errors are reported, including declines. The current one-session-per-athlete
sample cannot supply future-session validation. No external cohort is claimed.

## 6. Study time-resolved mechanics with verified alignment — proposed

**Question:** What temporal relationships can released marker and processed
signals support beyond isolated peaks?

Begin with the three verified examples. Specify anatomical frames, events,
signal signs, filtering, sampling, and analysis windows. Resolve the documented
shoulder-velocity convention and establish a marker/signal clock mapping before
adding synchronized overlays or event-frame labels. Matching published peak
values does not independently replicate inverse dynamics.

Only add camera analysis when recording rights, calibration, pitch identity, and
synchronization are established. No video coverage is assumed for all study
pitches, and no MLB footage acquisition is planned. Video landmarks alone cannot
be relabeled as internal joint moments or injury scores.

**Done when:** quantities and alignment have been validated and uncertainty is
reported. The Phase 2 statistical extension does not complete these checks.

## 7. Consider broader model development — proposed

Change model complexity only for a stated scientific question and a defensible
evaluation design. Tuning or model selection requires nested athlete-grouped
validation or an untouched evaluation cohort. These already displayed folds
cannot remain an unbiased final test after repeated model selection.

Report all planned candidates and failures. Do not frame lower prediction error
as a validated intervention, tissue-specific loading measure, or injury model.
