# Freeze a development model, then evaluate a new cohort

This is an implemented **local research workflow**, not a completed external
study. No independent evaluation cohort has been supplied to the public
demonstration. The existing Phase 2 results remain grouped out-of-fold results
from the released OBP cohort, with their original limitations. They are not
replaced by a fit on all development rows.

The external workflow asks a specific question: how well do fixed models using
**completed-pitch measurements** predict pitch speed and peak internal net elbow
varus moment in independent new athletes? It does not implement future-session
forecasting, a mechanics intervention, tissue-specific forces, or injury risk.

## Before beginning

Use an approved local or private environment and appropriately authorized
development and evaluation data. Agree access, retention, outputs, and publication
with the responsible data owner. The public Streamlit application supplies
planning templates; it does not accept private measurements.

Original software is MIT. Model parameters and reports derive from their input
data and retain applicable rights and restrictions. **OBP-trained model bundles
remain OBP-derived**, including its professional-sports/financial-analysis
affiliation exclusion. The software license does not authorize restricted
organizational use of OBP models or data. A future team study needs appropriate
independent permissions for both development and evaluation inputs. See
[LICENSING.md](LICENSING.md).

Prepare already joined pitch-level CSVs using the
[new-data mapping and audit guide](NEW_DATA_GUIDE.md). Definitions, units, signs,
population, collection protocol, identity namespace, and authorized-use basis
must be reviewed. Unit conversion does not establish equivalence between
different biomechanical definitions or instruments.

## Freeze the study protocol

Copy [the protocol template](../analysis/external_validation_protocol.template.json)
to a private study folder. Complete all fields for the actual study. The blank
template intentionally has empty text and false attestations and cannot freeze
a model unchanged.

The protocol declares:

- A study ID, research question, and intended external population.
- `evaluation_design: independent_new_athletes`.
- `prediction_context: same_pitch_post_motion`.
- The development and external `athlete_id_namespace` values.
- Investigator attestations that external athletes are disjoint, external
  outcomes have not been inspected at freeze time, and measurement compatibility
  has been reviewed.

Only the template's fixed fields are accepted. The models, feature sets, outcomes,
and ridge penalty are fixed in this implementation; protocol fields cannot tune
them. These are investigator declarations, not legal verification, proof of
unseen outcomes, preregistration, or independently authenticated provenance.

An athlete ID namespace identifies the system in which IDs denote people. A
different prefix or namespace is not proof of different athletes. Resolve
cross-system identities with the data owner before analysis. The software rejects
known overlapping athlete/pitch IDs in a shared namespace and complete reuse of
development source or measurement content. Across different namespaces it records
the identity-check limitation and relies on the explicit disjoint-athlete
attestation; it cannot independently reconcile identities.

## Run one stage at a time

From the project root, install the locked environment:

```bash
uv sync --frozen
```

The paths below are placeholders for actual, authorized CSVs and completed JSON
files. `local_studies/` is excluded from Git. That exclusion prevents ordinary
accidental staging; it is not a privacy or security arrangement by itself.

First audit only the development input:

```bash
uv run --frozen pitching new-data audit --csv local_studies/development.csv --mapping local_studies/development_mapping.json --output local_studies/development
```

Then freeze the protocol, preprocessing, and model parameters:

```bash
uv run --frozen pitching external freeze --prepared local_studies/development --protocol local_studies/protocol.json --output local_studies/frozen
```

`freeze` reads the prepared development directory and protocol. It does not open
the external dataset. It requires observed outcomes from at least two development
athletes for each target. Rows missing a target are excluded separately for that
target, with counts retained. Predictors are imputed from that target's eligible
development rows; outcomes are never imputed.

After freezing, audit the external input with its own reviewed mapping:

```bash
uv run --frozen pitching new-data audit --csv local_studies/external.csv --mapping local_studies/external_mapping.json --output local_studies/external
```

Evaluate the frozen models:

```bash
uv run --frozen pitching external evaluate --prepared local_studies/external --bundle local_studies/frozen --output local_studies/evaluation
```

Stop on any failed command. Preparation requires a new output directory. Freeze
and evaluation require new or empty output directories, refuse to overwrite
existing results, and keep outputs separate from input/bundle directories.

## What is frozen

For each outcome, the four models are:

| Model | Predictors |
| --- | --- |
| Training mean | Mean observed outcome in eligible development rows |
| Anthropometric ridge | Age, mass, height |
| Kinematic ridge | Peak shoulder rotational velocity, peak thorax–pelvis separation, peak torso rotational velocity |
| Combined ridge | All six predictors |

Ridge alpha remains 10. The imputer learns medians and the training-only missing
indicator columns, retaining all-missing features using the existing technical
fallback. Scaling and regression parameters are also learned only from the
development rows. Newly missing external predictors use frozen development
statistics; evaluation does not learn a new median or create new indicators.
All-missing training features and their absent observed ranges remain visible in
the recorded predictor profiles.

The bundle contains `models.json`, `protocol.json`,
`development_provenance.json`, `freeze_metadata.json`, and `manifest.json`.
The numerical models retain feature ordering, medians, indicator positions,
scaling parameters, coefficients, and intercepts. Metadata retain development
membership, input hashes, measurement definitions, target-specific training
counts/profiles, source rights, and producing code/package versions.

Loading verifies the fixed file list, checksums, model vector dimensions and
finite values, canonical definitions, and consistency between protocol,
provenance, membership counts, and training summaries. Prediction uses numerical
JSON parameters, with no pickle/joblib object loading, fitting, feature selection,
or tuning. Checksums detect accidental corruption and stale files. They are not
authenticity signatures: a party that replaces every file and its hashes can
construct a different internally coherent bundle. Recorded producing-code
hashes document the fit; loading does not require executing that earlier code.

## Inspect the external outputs

| File | Contents |
| --- | --- |
| `external_predictions.csv` | Every external pitch × outcome × model, including predictions for missing outcomes; residuals and errors remain missing when the outcome is missing |
| `external_metrics.csv` | All eight outcome/model combinations, evaluation counts, pooled pitch MAE/RMSE/R², and equal-athlete MAE |
| `external_athlete_errors.csv` | Each evaluated athlete's MAE and observed-pitch count for each outcome/model |
| `covariate_shift.csv` | External predictor ranges, missingness, and counts outside each target model's eligible development ranges |
| `evaluation_audit.json` | Cohort counts, identity-check limits, input/bundle/code hashes, rights, and explicit no-training/no-target-imputation flags |
| `external_provenance.json` | External prepared-input provenance and owner declarations |
| `external_report.md` | A plain-language local report with every model and the scope limitations |
| `evaluation_manifest.json` | Output checksums and the frozen-bundle binding |

The primary error is the **unweighted mean of per-athlete MAE**. This keeps an
athlete with many recorded pitches from dominating the score. Pooled pitch MAE
and RMSE answer different questions and are reported separately. R² remains
missing for fewer than two observed outcomes or a constant outcome. A target with
no observed external outcomes gets predictions but no invented evaluation score.
Prediction or error arithmetic that overflows fails explicitly.

The shift table is descriptive. Its training range comes from the development
rows actually eligible for each outcome model; its external summary includes all
external prediction rows. Missing training ranges remain missing. A value inside
a training range is not evidence that instruments, signals, populations, or
prediction behavior are equivalent.

These outputs provide no confidence intervals, p-values, multiplicity adjustment,
external independence certification, clinical threshold, causal effect, or
guaranteed performance improvement. Compare every fixed model, investigate
unfavorable findings, review protocol compatibility and missingness, and report
the external cohort's limitations. Do not tune repeatedly on this external
cohort and continue calling it an untouched final evaluation.

## Keep the evidence separate

Private new-data outputs are not automatically copied into the public snapshot.
Review allowed aggregate outputs with the owner before any publication. Preserve
the original OBP cohort, Phase 2 plan, and existing report checksums separately
from a new study. Synthetic fixtures in the automated tests exist solely to
verify software behavior and are never external research results.

The next scientific milestone is a properly authorized, completed independent
study with a frozen protocol and an honest report. This release supplies the
tools to perform it; it does not claim that milestone has already occurred.
