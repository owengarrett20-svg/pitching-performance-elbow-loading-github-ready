# Reproducing the study, motion/reporting lab, and local new-data tools

The reproducible unit is the code revision, `uv.lock`, `source_manifest.json`,
analysis plans, and saved evaluation specifications. A screenshot or running
server is not sufficient provenance.

## Environment

Use Python 3.12 and uv 0.12.23 or a compatible uv that understands this lockfile.
The tested interpreter is 3.12.14. From the checkout root:

```bash
uv sync --frozen --extra dev
```

`--frozen` prevents dependency re-resolution. `.python-version` selects Python;
`uv.lock` records the exact dependency graph and package artifact hashes.
`uv.toml` keeps the package cache under ignored `.cache/uv`, subject to explicit
user cache settings. Floating package bounds describe compatibility; the lockfile
defines this analysis environment. Re-resolving dependencies warrants validation.

Completed reports record Python and library versions. Numerical calculations
are deterministic for the pinned environment and seeds, with possible small
floating-point differences across platforms or BLAS implementations. Scientific
reproduction concerns source inputs, folds, predictions, and metrics; PNG bytes
may vary with fonts or rendering libraries.

Altair is a direct runtime dependency for the Phase 3 interactive charts. Its
version is pinned in the same lockfile; the presentation update does not change
the fixed Phase 1/2 model definitions or introduce another dataset.

The committed `.gitattributes` preserves all asset bytes and consistent source
line endings. Keep these rules on Windows: newline conversion must not invalidate
snapshot, CSV, trace, or compressed-output checksums.

## Source data and one-command reproduction

```bash
# Download and verify nine small source/schema/license files, under 0.4 MB total.
uv run --frozen pitching fetch

# Validate the documented schema, shared fields, join, and missingness offline.
uv run --frozen pitching audit

# Rebuild Phase 1 and all planned Phase 2 comparisons from the verified cache.
uv run --frozen pitching phase2 --offline

# Explore locally regenerated results.
uv run --frozen streamlit run app.py
```

Alternatively, `uv run --frozen pitching phase2` fetches absent source files and
verifies existing files before running both phases. No large C3D archive, footage,
MATLAB license, or video-processing dependency is required for either analysis.

Each downloaded file must match its recorded byte count and SHA-256 digest in
`source_manifest.json`. The cache pins OBP commit
`44b98dae05cceb016f080ab39d105c85b8639084`. The audit requires nonempty unique
pitch keys, complete one-to-one coverage, overlapping-field agreement, valid
athlete/session relationships, and the exact POI schema. It stops on a mismatch.
Do not edit manifest checksums to accept unexplained source changes.

Working source files in `data/raw/` and generated `reports/` are ignored by Git.
They retain the upstream terms, not the original software's MIT license. The
committed `assets/demo/reports/` snapshot is a deliberate derived publication.
All derived tables and figures retain the attribution/noncommercial/share-alike
terms and affiliation restriction documented in [LICENSING.md](LICENSING.md).

## Command boundaries and stale-result behavior

- `pitching run [--offline]` reproduces **Phase 1 only**: audit, exploratory
  figures, training-mean/combined baseline predictions, and metrics.
- `pitching phase2 [--offline]` first rebuilds Phase 1, then evaluates the recorded
  Phase 2 plan and binds the complete outputs together.
- A Phase 1-only refresh removes the completed parent's binding to older Phase 2
  outputs. Those older files may remain on disk but cannot be shown as current
  Phase 2 results. Run `pitching phase2` to regenerate them.

This deliberate full refresh avoids comparisons with a different input table or
an incomplete earlier run. An audit-only result does not establish completed
model evaluation.

## Evaluation settings

Both phases predict speed (mph) and peak internal net elbow varus moment (N·m).
Five shuffled `GroupKFold` folds use athlete `user`; primary seed is 42.
Assignments are created before target-specific filtering and shared across
outcomes and models. No athlete is present in a training fold and its held-out
fold. Missing/nonfinite outcomes are omitted separately by target, never imputed.
All pinned outcomes and focal predictors are observed.

Training-fold median imputation, missingness indicators, and standardization
precede ridge alpha 10. The computational fallback for a completely missing
training feature is not treated as a measured observation. Both targets,
identifiers, filenames, and other kinetic/energetic measures are excluded from
the predictor groups. Filenames encode speed and therefore cannot be predictors.

Phase 1 compares the training-fold mean with the six-feature combined ridge.
Phase 2 retains those specifications and adds:

| Model | Predictors |
| --- | --- |
| Anthropometric ridge | Age, mass, height |
| Kinematic ridge | Peak shoulder internal rotation velocity, peak hip–shoulder separation, peak torso rotation velocity |
| Combined ridge | All six predictors above |

The [Phase 2 plan](PHASE2_ANALYSIS_PLAN.md) and
[machine-readable specification](../analysis/phase2_plan.json) were committed
before the new comparisons, after Phase 1 results had been viewed. The study is
an exploratory follow-on. There is no new feature search or alpha tuning.

The primary metric is equal-athlete MAE: average absolute error within athlete,
then across athletes equally. Pooled MAE weights pitches equally; RMSE and R²
are descriptive secondary measures. The primary contrast is combined minus
anthropometric equal-athlete MAE for each outcome; negative values favor the
combined model. All six planned model pairs are reported for both outcomes and
both MAE weightings.

There is no canonical OBP benchmark split. These completed-pitch predictors
support retrospective evaluation on held-out athletes from this source setting,
not future sessions or external MLB players. Tuning against the displayed folds
would require a new nested grouped design or untouched evaluation data.

## Conditional resampling and partition sensitivity

The primary-partition intervals use 5,000 paired athlete-cluster percentile
resamples, RNG seed 20261019, at quantiles 0.025 and 0.975. Each draw samples
eligible athlete IDs with replacement and retains all their eligible pitches
and draw multiplicities. Paired models use identical draws. Pooled-MAE contrasts
retain weighted athlete pitch counts; equal-athlete contrasts average within
athlete before weighting sampled athletes.

**Predictions stay fixed within bootstrap draws.** Intervals describe saved
errors conditional on the fitted folds and observed source cohort. They exclude
full training-set/model-refitting, model-selection, external-cohort, and
measurement uncertainty. Clustering does not remove dependence from overlapping
cross-validation training sets or guarantee external-population coverage. No
p-values, formal significance threshold, or multiplicity-adjusted confirmation
are reported.

Ten full evaluations refit imputation, scaling, means, and ridge models for seeds
42–51. Seed 42 remains primary and is included in the ten-run summary. Saved
per-seed scores and contrasts describe sensitivity; the same athletes recur, so
these are not independent experiments and their spread is not a confidence
interval. No favorable seed is substituted for the planned primary result.

## Saved outputs and provenance

Phase 1 outputs at `reports/` include `analysis.csv`, `fold_assignments.csv`,
`split_audit.json`, `oof_predictions.csv`, `model_metrics.csv`, `fold_metrics.csv`,
`model_spec.json`, figures, and the completed `run_metadata.json` marker.
Residuals are observed minus predicted.

Phase 2 outputs at `reports/phase2/` include:

| Output | Contents |
| --- | --- |
| `phase2_model_metrics.csv` | All primary-partition model scores |
| `phase2_oof_predictions.csv` | Per-pitch predictions, observed values, errors, athlete IDs, and folds |
| `phase2_athlete_errors.csv` / `phase2_athlete_differences.csv` | Per-athlete model errors and paired contrasts |
| `phase2_comparisons.csv` | All planned contrasts and conditional intervals |
| `phase2_bootstrap_samples.csv.gz` | Reproducible saved bootstrap contrasts |
| `phase2_sensitivity_*.csv` / `*.csv.gz` | Refit partition assignments, predictions, scores, and contrasts |
| `phase2_split_audit.json` / `phase2_sensitivity_split_audit.json` | Train/test athlete checks |
| `phase2_plan.json` / `phase2_model_spec.json` | Actual plan and evaluation specification |
| `phase2_report.md` / `figures/` | Generated narrative report and research figures |
| `run_metadata.json` / `ATTRIBUTION.md` | Input, plan, code, and output hashes; environment; source terms |

The mean and combined primary predictions must reproduce Phase 1 within the
recorded tolerance before Phase 2 is accepted. Metadata records the original
plan's Git commit and digest, producing project revision and dirty status, code
hashes, source/lock hashes, library versions, eligibility counts, seeds, and
artifact hashes. The report displays rounded numbers; CSVs preserve precision.
See [PHASE2_RESULTS.md](PHASE2_RESULTS.md) for the complete results.

## Checks and atomic completion

```bash
uv run --frozen pytest -q
uv run --frozen ruff check src tests scripts app.py streamlit_app.py
uv run --frozen ruff format --check src tests scripts app.py streamlit_app.py
uv run --frozen python scripts/export_requirements.py --check
```

Run tests after `pitching fetch` to include real-data integration checks. Tests
without required cached inputs skip explicitly. Synthetic fixtures are labeled
and never enter research results. Optional archive-dependent motion checks need
the motion extra and raw archives; their absence does not prevent either
analysis phase or viewing prepared assets. No private API or copyrighted footage
is required.

The workflow removes the relevant success marker before refresh. Phase 2's child
marker is written only after its outputs; the parent marker then binds that
marker and all child artifact hashes. The dashboard requires a completed,
consistent parent/child set. Partial or stale Phase 2 output is rejected, while a
valid Phase 1-only run remains usable.

To check every artifact bound by the parent marker in a Bash-compatible terminal:

```bash
uv run --frozen python - <<'PY'
import hashlib, json
from pathlib import Path
root = Path('reports')
metadata = json.loads((root / 'run_metadata.json').read_text())
assert metadata['status'] == 'completed'
for name, expected in metadata['artifacts_sha256'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
print('All completed-run artifacts verified.')
PY
```

## Dashboards and the hosted reference snapshot

`uv run --frozen streamlit run app.py` reads local reports beside the app. Set
nonsecret `PITCHING_REPORT_DIR` to select another report folder. The hosted entry
point, `streamlit_app.py`, reads the committed `assets/demo` snapshot and verifies
its files before display. Neither dashboard downloads data or fits models during
browser interactions. The new-data audit/freeze/evaluate commands are separate,
explicit local workflows; the public site does not accept athlete-file uploads. Phase 2 cohort scores, intervals, and partition sensitivity
do not change with sidebar filters; the athlete-detail table follows the selected
athletes without recomputing their full-eligible-pitch errors.

To refresh the reference snapshot deliberately:

```bash
uv run --frozen pitching phase2
uv run --frozen python scripts/export_demo_snapshot.py
uv run --frozen streamlit run streamlit_app.py
```

The exporter verifies producing code, source manifest, lockfile, Phase 2 plan,
and output hashes before export. Commit the snapshot and manifest together.
The hosted reader does not modify the snapshot. Phase 2 version 0.4.0 has been
pushed to the connected branch, followed by Phase 3 version 0.5.0 at `edf5c05`.
The prepared Phase 4 version 0.6.0 update remains local until pushed and rebuilt;
creating local files does not update the public app. See
[PHASE4_UPGRADE_WINDOWS.md](PHASE4_UPGRADE_WINDOWS.md) and
[GITHUB_PUBLISH.md](GITHUB_PUBLISH.md) for upgrade and deployment guidance.

## Guided views and interactive release checks

Phase 4 retains **Start here**, **Explore pitches**, **Watch motion**,
**Study results**, and **Methods & collaboration**, and adds **Athlete reports**
and **New-data lab**. Only the active route is
rendered. The default study view uses average absolute prediction error per
athlete; the detailed mode retains all planned contrasts and the saved audit.

Explorer charts use observed measurements. In athlete-average mode, each point
averages complete selected-axis pitch pairs for one athlete; it is not an
individual pitch or a time-averaged movement trace. The A/B table calculates
B-minus-A differences from two actual recorded rows and retains missing values.
Filters change the displayed observations and athlete-detail tables, not the
full-cohort study comparisons or conditional intervals.

A link such as `?page=explore&pitch=1623_3` names a view and a recorded pitch.
The router allowlists view names and checks identifiers against the analysis
rows. Motion links identify the example actually displayed; unavailable replays
are explained instead of being silently paired with another pitch's metrics.

Application checks should cover an opening visit, both study outcomes, chart and
dropdown selection, consecutive selection changes, athlete-average mode, filters,
recorded-pitch links, and stale-result handling. Check desktop and phone-width
layouts for clipped text, chart rendering, keyboard/touch selection, and page
overflow. Browser layout review complements the automated unit and Streamlit
checks; it is not an external scientific validation.

The [experience notes](PHASE3_EXPERIENCE.md) and
[collaboration guide](COLLABORATION.md) state the presentation and data-use
boundaries. The public introduction link accepts a non-sensitive description
only; it does not create an authorized channel for player files or supply a
confidential upload service. New data require permission, compatible definitions,
a reviewed mapping, and a separately frozen external evaluation plan. The
implemented local tools assist those checks; they do not establish external
validity or authorize confidential transfer through the public site.

## Motion inspection and downloadable reports

The [motion lab](MOTION_LAB.md) reads the prepared marker and trace assets offline.
Its frame and processed-signal controls are independent: no source-supported
clock relationship has been verified. Check pitch and athlete identity, file
hashes, source units, selected indices, missing markers, and the actual displayed
sample before interpreting a view. Matching source grids or extrema is not
synchronization or an independent inverse-dynamics replication.

[Athlete reports](ATHLETE_REPORTS.md) use the selected athlete's available
recorded rows. HTML is self-contained and printable through the browser's
**Print → Save as PDF**. Preserve the embedded source/terms and metadata with
redistributed material. Target/focal missing values stay missing. A report may
include saved primary combined-model errors only when the verified source
identities and observations match. It does not refit a model or recompute a
confidence interval for one athlete. The source's few pitches from one released
session cannot establish long-term consistency or development.

## Local new-data audit and frozen external evaluation

The local workflow is deliberately separate from the public OBP reference
snapshot. Templates contain definitions and placeholders, not invented athlete
measurements. Before entering actual data, review rights, population, collection
protocol, identifier namespace, source units, signed coordinate conventions, and
whether each measurement actually matches the canonical definition. An explicit
operator declaration records that review; it is not independent legal or
instrument validation.

See [NEW_DATA_GUIDE.md](NEW_DATA_GUIDE.md) for the complete mapping format and
[EXTERNAL_VALIDATION.md](EXTERNAL_VALIDATION.md) for the freeze/evaluate protocol.
The command sequence is:

```bash
# Use actual independently authorized files after reviewing both guides.
uv run --frozen pitching new-data audit --csv local_studies/development.csv --mapping local_studies/development_mapping.json --output local_studies/development_prepared
uv run --frozen pitching external freeze --prepared local_studies/development_prepared --protocol local_studies/external_protocol.json --output local_studies/frozen_models

# Prepare and evaluate the independent new-athlete cohort after freezing.
uv run --frozen pitching new-data audit --csv local_studies/evaluation.csv --mapping local_studies/evaluation_mapping.json --output local_studies/evaluation_prepared
uv run --frozen pitching external evaluate --prepared local_studies/evaluation_prepared --bundle local_studies/frozen_models --output local_studies/external_results
```

These paths are examples of local filenames, not bundled example data. Review and
complete the mapping/protocol templates first. Source columns must be mapped
explicitly; supported unit conversions do not authorize automatic sign reversal,
renaming an event-specific value as a peak, or substituting an external moment
for an internal moment. Missing targets remain unobserved and are excluded
separately by outcome. Invalid numeric values and grouping conflicts stop the
audit rather than being silently repaired.

Prepared artifacts bind canonical data, mapping, provenance, and audit outputs
with checksums. The freeze stage learns imputation/scaling and fixed mean/ridge
models only from development observations. Its numerical JSON bundle records
parameters and provenance without executable deserialization. External evaluation
reads that frozen state and does not fit, tune, or select models using evaluation
outcomes. Known athlete/pitch overlap and reused inputs are rejected; cross-dataset
identity equivalence still needs an independently reviewed crosswalk. Namespace
changes cannot certify independence.

Metrics are descriptive errors for the supplied evaluation cohort. Undefined R²
remains undefined, target-specific missingness changes eligibility, and pooled
pitch metrics differ from equal-athlete metrics. Covariate summaries describe
observed differences rather than proving or correcting transferability. No
external confidence interval, prospective performance, causal intervention, or
injury probability is implied.

Keep inputs, identity mappings, frozen model bundles, and outputs in the approved
environment under ignored `local_studies/`. A source path or filename can itself
be confidential. Do not copy these artifacts into `assets/demo`, attach them to
public issues, or publish them merely because they passed software checks.
OBP-derived model bundles and outputs retain the original data-use restrictions;
independently authorized new data require their own permissions and agreed terms.
The workflow is implemented, but this release contains no actual external study.

No new cloud environment, MATLAB/Octave project, or additional Git worktree is
needed to reproduce the existing Python study.
