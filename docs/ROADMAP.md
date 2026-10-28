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

## 4. Publish and archive the research release — partially complete

Phase 2 version 0.4.0 (`a2f339e`), Phase 3 version 0.5.0 (`edf5c05`), and
Phase 4 version 0.6.0 (`ad4cd71`) have been pushed to the existing public
repository. Their source and prepared snapshot
are available through the connected branch. Check the published Actions run and the rebuilt app when reviewing a
release; a Git push alone does not independently verify those services.

A tagged software release and archival DOI remain separate steps. Publish an
actual tag only from a checked revision, and add a DOI only if an archival
service issues one. Preserve attribution and the data-use restrictions.

## 5. Phase 3: readable, interactive research experience — published code

**Question:** Can a first-time visitor understand the study and inspect its
observations without first reading research tables or application code?

Version 0.5.0 separates **Start here**, **Explore pitches**, **Watch motion**,
**Study results**, and **Methods & collaboration**. Only the active view is
rendered. The opening pairs a verified marker example with the research question
and saved findings. Interactive charts, keyboard-accessible recorded-pitch
selection, observed A/B comparisons, and checked share links make the existing
cohort easier to inspect.

Study scores and conditional intervals remain full-cohort results regardless of
explorer filters. Athlete means remain a different observation unit from pitches.
The interface introduces no new data, injury score, mechanics intervention,
video synchronization, or external validation. Its scientific definitions and
models remain those of Phases 1 and 2.

The [experience notes](archive/PHASE3_EXPERIENCE.md) describe the scope and release checks.
The code was published at `edf5c05`. Historical upgrade instructions remain in
[PHASE3_UPGRADE_WINDOWS.md](archive/PHASE3_UPGRADE_WINDOWS.md). A source commit alone does
not independently verify a particular deployment or remote CI run.

The [collaboration guide](COLLABORATION.md) offers a proposed path from a
non-sensitive research introduction to independently authorized data and an
approved analysis environment. The public site does not accept confidential
athlete data. OBP professional-affiliation restrictions remain explicit.

**Done when:** desktop and phone-width visitors can navigate, inspect real
observations, read the uncertain elbow finding, locate methods, and understand
the contact/data-use boundaries. This presentation milestone does not complete
the next scientific validation milestone.

## 6. Phase 4: motion, athlete reports, and a new-data workflow — published code

**Question:** Can a visitor inspect measured movement and source-derived
measurements, take away a readable report, and understand how an authorized new
dataset would be evaluated?

Version 0.6.0 adds:

- An [interactive motion lab](MOTION_LAB.md) using the three prepared marker
  examples and released traces, with independent controls and explicit clock
  limitations.
- [Athlete research reports](ATHLETE_REPORTS.md) as self-contained printable
  HTML and source-attributed downloads. Reports describe available recorded
  pitches; they do not establish longitudinal progress or stable consistency.
- A [local new-data adapter and audit](NEW_DATA_GUIDE.md) with explicit column
  mapping, units, definitions, signs, grouping, provenance, and permission review.
- A [two-stage external-evaluation workflow](EXTERNAL_VALIDATION.md): freeze
  fixed development models and preprocessing, then evaluate a new-athlete cohort
  without fitting or tuning against it. Numerical JSON artifacts avoid executable
  model deserialization.
- **Athlete reports** and **New-data lab** views alongside the existing guided
  site. The public app accepts no confidential athlete-file uploads.

The Phase 1/2 cohort, comparisons, and uncertainty scope remain unchanged.
External-evaluation tools are an implemented capability, not evidence that a new
cohort has been evaluated or that the models generalize. No independent external
result, future-session validation, injury prediction, or professional-team
partnership is included.

**Release checks:** source/error identity matching, preserved missingness,
printable/escaped reports, valid unit conversions, strict prepared-data and model
hashes, athlete-overlap rejection, frozen prediction equivalence, no
external-evaluation fitting, and desktop/phone usability. The source-clock audit
must retain unverified alignment rather than invent synchronized event frames.

The code is published at `ad4cd71`; historical instructions remain in
[PHASE4_UPGRADE_WINDOWS.md](archive/PHASE4_UPGRADE_WINDOWS.md). A source push does not
independently verify remote CI or deployment. A tagged release or DOI remains a
separate publication step.

## 7. Phase 5: source-linked exploration and an auditable portfolio — published

**Question:** Can a reviewer select an observed pitch, inspect its actual source
motion and markers, compare another delivery, and assess the project's research
claims and contribution record?

Version 0.7.0 adds a [searchable pitch workspace](PITCH_WORKSPACE.md) with a
selectable source table, A/B replays, marker-set inspection, associated values,
and checked paired links. The [verified catalog](PITCH_CATALOG.md) provides
measured-marker arrays for all 411 study pitches from the official C3D archive.
Original label aliases and missing observations remain explicit; this expands
inspectable motion, not camera coverage or scientific validation. The existing
three MP4/processed-trace examples remain a separate subset. Starting two trials
from their own first samples does not establish event alignment.

The [research brief](RESEARCH_BRIEF.md) derives cohort counts, model results,
contrasts, and evidence limits from verified artifacts. The
[measurement audit](MEASUREMENT_VERIFICATION.md) checks twelve selected released
scalar summaries against three released traces. Source-scalar agreement is not
an independent reconstruction of inverse dynamics or validation of all quantities
in all pitches. Existing Phase 1/2 findings and their uncertainty scope remain
unchanged.

The PhD application guide (kept with private application materials) and
[contribution record](CONTRIBUTIONS_AND_AI.md) describe an independent AI-assisted
research software project. Personal framing, interface review, AI implementation,
agent-executed checks, and personally completed method review stay distinct.
Private CV/application drafts are outside the public repository. The project is
not presented as a publication, independent biomechanical validation, or a
completed external study.

**Release checks:** correct source IDs after table sorting/searching, repeated
A/B selections and URL changes, unavailable/corrupt evidence without substitution,
marker-label and missingness preservation, safe offline exports, truthful brief
failure states, desktop/phone interaction, and a clean historical bundle upgrade.
Phase 5 was published at `102ec49`; version 0.7.1 (`443f6cf`) added chart-point
selection, A/B swap, within-athlete stepping, and cohort percentiles to the workspace.

## 7a. Pitcher-versus-pitch variation — implemented in 0.8.0

**Question:** How much speed and elbow-moment variation lies between rather than
within pitchers, and does the speed–moment slope differ within a session and
across pitchers?

The [variation analysis](ATHLETE_VARIATION.md) scales elbow moment by body weight
× height, reports ICC(1) variance shares, and contrasts pooled within-athlete with
between-athlete-mean slopes using a seeded athlete-cluster bootstrap. It is
exploratory, specified after the data had been explored, and reported with a
college-only sensitivity subset. It does not identify causal effects of throwing
harder, and the narrow within-session speed range limits extrapolation.

**Natural next step:** test whether the within-pitcher relationship holds over
larger, deliberate velocity changes in an independently authorized cohort with
repeated sessions, ideally alongside wearable or markerless measurement.

## 8. Phase 6: complete an external-validation study — proposed scientific milestone

**Question:** Do the fixed measurement definitions and models generalize to a
genuinely new athlete cohort?

Obtain an appropriately licensed independent dataset. Document instrumentation,
units, population, processing, signal conventions, and the athlete identity
crosswalk before evaluation. Record the operator's permission and measurement
review; software cannot independently certify legal authority or equivalence.
Freeze the model/protocol using development data before inspecting external
outcomes. Keep the evaluation cohort out of fitting, tuning, and model selection.

The Phase 4 workflow implements descriptive new-athlete evaluation. Report all
fixed models, target-specific eligible counts, pooled and equal-athlete errors,
missingness, and covariate differences, including unfavorable findings. Source
identity overlap and dataset reuse checks help, but differently namespaced IDs
still require an independently reviewed identity crosswalk.

**Done when:** actual authorized inputs, frozen provenance, eligibility,
measurement compatibility, cohort shift, predictions, and external errors are
reported. That study has not occurred in this release. Future-session or temporal
validation asks a different question and needs its own protocol; the current
one-session-per-athlete OBP sample cannot supply it.

## 9. Establish marker/signal alignment and time-resolved mechanics — proposed

**Question:** What temporal relationships can the released signals support beyond
individual peaks and separate inspection controls?

The marker catalog expands inspectable motion and the three detailed trace
examples remain available. Neither establishes a shared clock. Specify anatomical frames, event definitions, signs,
filtering, sampling, and analysis windows. Resolve the documented shoulder signal
convention and establish a source-supported marker/signal time mapping before
adding synchronized cursors, overlays, or event-frame labels. Matching sample
counts, rates, or published peaks is insufficient and does not independently
replicate inverse dynamics.

Add camera analysis only when recording rights, calibration, pitch identity, and
synchronization are established. No camera coverage is assumed for all study
pitches, and no MLB footage acquisition is planned. Video landmarks alone cannot
be relabeled as internal joint moments or injury scores.

**Done when:** the quantities and time mapping are validated with their
uncertainty and provenance. Interactive rendering alone does not complete that
scientific validation.

## 10. Consider broader model development — proposed

Change model complexity only for a stated scientific question and a defensible
evaluation design. Tuning or model selection requires nested athlete-grouped
validation or an untouched evaluation cohort. These already displayed folds
cannot remain an unbiased final test after repeated model selection.

Report all planned candidates and failures. Do not frame lower prediction error
as a validated intervention, tissue-specific loading measure, or injury model.
