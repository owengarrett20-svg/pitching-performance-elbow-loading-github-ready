# Pitching Performance and Elbow Loading

A reproducible Python research portfolio project using Driveline Baseball Research & Development's [OpenBiomechanics Project (OBP)](https://github.com/drivelineresearch/openbiomechanics). **Phase 1** builds a trustworthy pitch-level table, explores performance and internal elbow joint moment, and evaluates simple models on athletes excluded from model fitting.

**Research question:** How well do a small set of anthropometric and completed-pitch kinematic summaries predict pitch speed and peak internal elbow varus moment for held-out athletes in this dataset?

This is retrospective exploratory research. Net joint moment is not UCL force, injury probability, or evidence that changing a movement will prevent injury. There are no injury labels in this analysis.

**Licensing matters for a professional-sports portfolio.** Original project code is MIT. OBP data, biomechanics documentation, and derived figures/tables have **CC BY-NC-SA 4.0 plus an additional professional-organization exclusion**. Upstream specifically requires a separate written paid license for use by employees, contractors, associates, or significant shareholders of professional sports organizations or financial-analysis firms. Do not present this as an unrestricted open-data product or carry it into team work without checking those terms. Full text and attribution: [docs/LICENSING.md](docs/LICENSING.md).

## Study at a glance

- A verified one-to-one join preserves **411 fastballs from 100 athletes**.
- Athlete-held-out ridge MAE is **3.04 mph** for speed and **12.40 N·m** for elbow moment, compared with mean-baseline errors of 3.83 mph and 15.64 N·m.
- Marker replays and source traces explain measurement concepts while keeping recorded camera footage, processed signals, and schematic lessons distinct.

![Descriptive pitch-level and athlete-mean performance/loading associations](docs/images/performance_loading.png)

*Example output, not a causal or injury-risk analysis. Source: Driveline Baseball Research & Development, OBP; figure adapted by this project under the data terms above.*

Read the [one-page study summary](docs/STUDY_SUMMARY.md), [research roadmap](docs/ROADMAP.md), and [publication/deployment guide](docs/GITHUB_PUBLISH.md). Citation metadata for this software is in [CITATION.cff](CITATION.cff); dataset attribution remains separate.

## Open the reference demonstration

From a clean checkout, the bundled reference snapshot works without source downloads or model fitting:

```bash
uv sync --frozen
uv run --frozen streamlit run streamlit_app.py
```

For Streamlit Community Cloud, publish this repository to GitHub, select your published branch (normally `main`), use **`streamlit_app.py`** as the main file, and choose **Python 3.12**. The snapshot is verified on read. The [deployment guide](docs/GITHUB_PUBLISH.md) explains the Windows publication steps and the “not connected to a remote GitHub repository” message. No public repository/demo URL is claimed until you actually publish it.

## Reproduce the study

Use **Python 3.12** and **uv** (tested with Python 3.12.14 and uv 0.12.23). The exact dependency graph and package hashes are saved in `uv.lock`; `.python-version` selects Python 3.12. Install uv using its [official instructions](https://docs.astral.sh/uv/getting-started/installation/) if it is not already available.

From this repository's root:

```bash
uv sync --frozen --extra dev

# Smallest milestone: fetch immutable files, then validate the join and missingness.
uv run --frozen pitching fetch
uv run --frozen pitching audit

# Complete Phase 1: verify cache, create figures, and evaluate grouped baselines.
uv run --frozen pitching run --offline

# Tests include real-data checks after fetch, with no network calls during tests.
uv run --frozen pytest -q
uv run --frozen ruff check src tests scripts app.py streamlit_app.py

# Explore the data and held-out model errors.
uv run --frozen streamlit run app.py --server.headless true
```

`uv run --frozen pitching run` also fetches absent files and verifies existing files, so it is a single-command workflow after environment installation. No MATLAB, large C3D archive, full-signal data, video, database credentials, or GitHub token is needed. `uv.toml` keeps the package cache local; plotting uses a writable temporary cache when the cloud home folder is read-only.

Commands default to the current directory as project root. To call the CLI elsewhere:

```bash
uv run --project /path/to/project pitching --project-dir /path/to/project run --offline
```

Use the displayed command in a terminal on a machine that has this checkout. A localhost dashboard process runs on that machine; this repository does not create a hosted dashboard or a Codex web preview. See [reproducibility notes](docs/REPRODUCIBILITY.md) for portable setup and artifact validation.

## Data provenance and first milestone

The source is pinned to OBP commit [`44b98dae05cceb016f080ab39d105c85b8639084`](https://github.com/drivelineresearch/openbiomechanics/tree/44b98dae05cceb016f080ab39d105c85b8639084). `source_manifest.json` records paths, sizes, and SHA-256 hashes for the two CSVs and their schema/license references. Downloads use HTTPS with normal TLS verification. Existing cache files must match; analysis stops on unexplained changes rather than changing the expected hashes.

The original `obp.load_poi("pitching")` and `obp.load_metadata("pitching")` use `pandas.read_csv`. This project uses their **documented schema directly**, retaining the official paths:

- `baseball_pitching/data/poi/poi_metrics.csv`
- `baseball_pitching/data/metadata.csv`

`session_pitch` is a pitch identifier; `user` identifies the athlete. The join rejects empty or duplicate pitch keys, unmatched coverage, conflicting shared session IDs or observed pitch speeds, and sessions assigned to multiple athletes. `merge(validate="one_to_one")` prevents accidental row multiplication. The full POI column set is checked against the pinned official data dictionary. Missing targets are never filled from metadata's duplicate speed field.

Verified source composition:

- **411 fastball pitches, 100 athletes, 100 sessions**; 2–5 pitches per athlete.
- Both source tables have 411 unique pitch IDs; all match one-to-one.
- No missing observations in the five focal variables or six model predictors.
- **25 other POI columns each have eight missing observations.** Missingness is reported by column in POI, metadata, and merged tables. These are not invented zeros or repaired observations.
- Mostly collegiate athletes; pitch speed spans **69.5–94.4 mph**. This is not an MLB-representative cohort.

The first milestone's outputs are `reports/audit.json`, `reports/audit.md`, `reports/missingness.csv`, and `reports/analysis.csv`.

## Biomechanical measures and exploratory plots

| Source variable | Interpretation | Units |
| --- | --- | --- |
| `pitch_speed_mph` | Recorded pitch speed | mph |
| `elbow_varus_moment` | Peak internal net elbow varus moment | N·m |
| `max_shoulder_internal_rotational_velo` | Peak shoulder internal rotation angular velocity | deg/s |
| `max_rotation_hip_shoulder_separation` | Peak thorax–pelvis separation angle | deg |
| `max_torso_rotational_velo` | Peak torso axial (Z) angular velocity | deg/s |

Peak hip–shoulder separation differs from the separate foot-plant variable. Peaks can occur at different instants; they cannot reconstruct a kinematic sequence or establish energy transfer. Absolute joint moment is affected partly by body size and biomechanical model assumptions. See [variable definitions](docs/VARIABLES.md) for conventions and source references.

Generated figures:

- `reports/figures/distributions.png`: observed distributions for all five measures, with units and missing counts.
- `reports/figures/velocity_elbow.png`: pitch-level speed/moment association alongside athlete means.
- `reports/figures/kinematics_vs_outcomes.png`: three rotational summaries against both outcomes.
- Two `errors_*.png` figures: athlete-held-out ridge predictions and residuals.

Repeated pitches are clustered within athletes. These are descriptive plots, without independent-pitch significance tests or causal coaching recommendations. All measured values, including unusual observations, are retained.

## Models and statistical reasoning

Two tasks predict **pitch speed** and **peak internal elbow varus moment** separately. Both use the same six prespecified predictors: age, mass, height, peak shoulder internal rotation velocity, peak hip–shoulder separation, and peak torso rotation velocity.

The comparison is a training-fold mean predictor against **ridge regression with alpha fixed at 10**. Ridge is a modest regularized linear baseline for potentially correlated rotational summaries. Alpha and features were fixed before inspecting these model scores; there is no hyperparameter search or selection on validation performance.

Five-fold shuffled `GroupKFold`, grouped by athlete `user` with seed 42, assigns each athlete's pitches to one held-out fold. The same partition is used for both targets. Each fold contains 20 held-out athletes; pitch counts differ. Identifiers and filenames are excluded from predictors: filenames encode pitch speed, and metadata repeats it. Both outcome columns are excluded from both feature matrices.

The ridge pipeline fits median imputation, missingness indicators, and standardization **inside each training fold**. Imputed predictors are computational estimates, not observed measurements; no outcomes are imputed. The pinned focal data need no such filling. No full-data feature selection or normalization is performed before splitting. See [the research plan](docs/RESEARCH_PLAN.md) and `reports/model_spec.json` for exact rules and technical handling of wholly missing training features.

## Baseline results

Pooled out-of-fold results from the pinned data, five athlete-grouped folds, seed 42:

| Outcome | Model | MAE | RMSE | R² | Equal-athlete MAE |
| --- | --- | ---: | ---: | ---: | ---: |
| Speed (mph) | Training mean | 3.828 | 4.735 | -0.010 | 3.807 |
| Speed (mph) | Ridge | 3.037 | 3.876 | 0.323 | 3.153 |
| Elbow moment (N·m) | Training mean | 15.636 | 19.791 | -0.017 | 15.662 |
| Elbow moment (N·m) | Ridge | 12.395 | 15.885 | 0.345 | 12.104 |

All four rows use 411 observed outcomes from 100 athletes. MAE/RMSE retain the outcome's units. Equal-athlete MAE averages each athlete's mean absolute error equally; pooled MAE weights pitches equally. The saved `fold_metrics.csv` exposes fold variation. These scores are internal descriptive validation, not confidence intervals, independent experiments, clinical thresholds, or an external benchmark.

Ridge improves over the mean baseline here, while substantial error remains. Same-pitch kinematic peaks are measured during the delivery: the models do not predict performance from pre-pitch information. Neither outcome is an injury label. No causal mechanism or injury-risk reduction follows from these scores. Results are descriptive of this dataset and need independent validation before broader scientific claims.

## Dashboard

The **Watch pitches** tab now includes three real metadata-linked C3D marker animations at half speed, an optional paused-frame inspector, released angle/velocity/moment traces with event markers, a 15-second instructional video, and five measurement lessons. It also links a separate official OBP-CV camera recording without claiming it belongs to a selected study pitch. Read [video methods and provenance](docs/VIDEO_METHODS.md).

Prepared visual assets are bundled. You do not need to install motion-processing extras or download the large archives to use the dashboard. These examples do not introduce automatic video pose estimation or a video-to-elbow-loading calculation.

The research entry point (`app.py`) reads locally regenerated reports. The hosted entry point (`streamlit_app.py`) reads a verified committed reference snapshot. Neither fetches data or retrains models on a browser interaction. Filter by athlete or playing level; explore distributions and pairwise associations; choose a target and model to inspect out-of-fold observed/predicted values, residuals, and the largest errors.

Subset error summaries are recomputed for the selected pitches and clearly separated from the saved full-CV metrics. A completion marker and hashes protect against mixing an old prediction file with a partially refreshed dataset. The data can be explored after the audit-only milestone, while model errors require a completed pipeline run.

## Tests and reproducibility

Tests use clearly labeled synthetic fixtures to check malformed joins, conflicts, target preservation, missingness counts, checksum failures, train-only preprocessing, forbidden predictor exclusion, disjoint athlete folds, deterministic predictions, and error metrics. Streamlit AppTest exercises filters, errors, missing/invalid artifacts, and stale-result protection. A cached real-data integration check runs the complete offline workflow and verifies reports and plot files. On a checkout without downloaded data, real-data integration tests explicitly skip; run `pitching fetch` first to execute them.

`reports/run_metadata.json` records source revision, project Git revision/dirty status, code/manifest/lock hashes, Python/library versions, split settings, and generated-artifact checksums. `split_audit.json`, `fold_assignments.csv`, and `oof_predictions.csv` make the evaluation inspectable. No serialized model is required to reproduce the reported scores. Raw caches, environments, and working reports are ignored by Git. The intentionally exported `assets/demo` reference snapshot is tracked and retains the upstream data terms. Retain `reports/ATTRIBUTION.md` with any redistributed plots or tables.

## Limitations and next research steps

This sample is small, fastball-only, primarily collegiate, and collected in one source setting. There is one released session per athlete, no prospective temporal holdout, no injury outcome, and no assumed synchronized-video coverage. Marker-based kinematics and inverse-dynamics joint moments depend on preprocessing, segment models, soft-tissue artifact, and measurement conventions. No copyrighted MLB footage is downloaded.

For the next portfolio review, explain the join audit, compare ridge with the mean baseline in physical units, and inspect athlete-level errors without changing the model to chase the displayed folds. Write a short interpretation of the speed/moment association and what the model cannot establish. Keep a separate list of later hypotheses—body-size normalization, time-resolved kinematic sequence, external cohorts, and richer models with nested athlete-grouped tuning. Those belong to later phases, after a prespecified analysis plan and any necessary data permission.

## Repository layout

```text
app.py                   local research reports and Watch pitches tab
streamlit_app.py         read-only hosted reference demo
assets/demo/             checksum-verified reference reports for clean clones
.github/workflows/       automated reproduction/tests on GitHub
assets/                  prepared motion, signal, and instructional examples
src/pitching/video_lab.py verified media viewer and five measurement lessons
src/pitching/data.py     pinned downloads, schema checks, join, missingness
src/pitching/plots.py    exploratory and held-out error figures
src/pitching/models.py   fixed features and athlete-grouped baselines
src/pitching/cli.py      fetch / audit / run commands
source_manifest.json    pinned original files and SHA-256 checksums
pyproject.toml, uv.lock  Python environment and exact dependency resolution
tests/                   synthetic unit/UI tests and real-data integration checks
docs/                    licensing, definitions, research plan, reproducibility
reports/                 generated locally; ignored by Git
data/raw/                immutable-source local cache; ignored by Git
```

## Attribution

Driveline Baseball Research & Development and Kyle Boddy, *The OpenBiomechanics Project*. Dataset citation is retained in [docs/licenses/UPSTREAM-CITATION.cff](docs/licenses/UPSTREAM-CITATION.cff); the analysis source revision is linked above. This project joins source tables and adds summaries, figures, and models; it does not imply Driveline endorsement. This research README adapts source definitions and reports data-derived results; those portions retain the [upstream data/documentation terms](docs/LICENSING.md). Original software is separately MIT-licensed.
