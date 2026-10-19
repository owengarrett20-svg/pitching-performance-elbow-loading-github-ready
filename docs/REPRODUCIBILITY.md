# Reproducing Phase 1

The reproducible unit is the code revision, `uv.lock`, `source_manifest.json`, and the model specification—not a screenshot or a running server.

## Environment

Use Python 3.12 and uv 0.12.23 or a compatible uv that understands this lockfile. The tested interpreter is 3.12.14. Run `uv sync --frozen --extra dev` from the checkout root. `--frozen` prevents an unnoticed dependency re-resolution. Python version selection lives in `.python-version`; dependencies and their artifact hashes live in `uv.lock`. `uv.toml` keeps the package cache in ignored `.cache/uv`. Existing user cache settings take precedence where explicitly configured.

The core tested library versions are recorded automatically in `reports/run_metadata.json`. Floating dependency bounds in `pyproject.toml` describe compatibility; use the committed lockfile for this analysis. Re-resolving dependencies is a new environment and warrants rerunning validation. Numerical output is deterministic for the pinned environment/seed; small floating-point differences across operating systems or BLAS implementations are possible. PNG rendering may differ by platform/fonts, so scientific reproduction concerns inputs, folds, predictions, and metrics rather than identical picture bytes.

The committed `.gitattributes` keeps source/configuration line endings consistent and preserves all bytes under `assets/`. Keep those rules when publishing: Git for Windows line-ending conversion would otherwise invalidate the bundled report and trace checksums.

## Data

1. `uv run --frozen pitching fetch` downloads nine manifest-listed small files from the pinned commit using HTTPS. Only two are measurement CSVs. Other files are schema, loader reference, datasheet, attribution, and license evidence; their total size is under 0.4 MB.
2. Every file's bytes and SHA-256 must match `source_manifest.json`. Repeated fetches verify existing cache files without requiring a download.
3. `uv run --frozen pitching audit` works offline. It requires unique, nonempty pitch IDs, full one-to-one coverage, shared-field agreement, valid athlete/session relationships, numeric focal measurements, and the exact pinned POI schema.
4. `uv run --frozen pitching run --offline` generates all figures, out-of-fold predictions and metrics using only those local files.

Raw and derived data are ignored by Git, not licensed by the code's MIT file. Preserve the upstream attribution/noncommercial/share-alike and professional-organization restriction when sharing derived figures/tables. Source license texts are under `docs/licenses/`. Do not edit checksums simply to accept changed or corrupted data. Preserve any deliberate local edits, remove the affected cached file, and re-fetch its original bytes if corruption is diagnosed.

## Evaluation

Features: age, mass, height, peak shoulder internal rotation velocity, peak hip–shoulder separation, peak torso axial rotation velocity. Outcomes: speed (mph) and peak internal elbow varus moment (N·m). Algorithms: training-fold mean and ridge alpha 10. Five shuffled GroupKFold partitions, seed 42, group `user`; the partition is shared across outcomes. Imputation/scaling fit within training folds. Outcomes are never imputed.

`fold_assignments.csv` records each pitch's evaluation fold; `split_audit.json` records train/test athlete IDs and verifies zero overlap. `oof_predictions.csv` contains one prediction per eligible pitch, target, and model; residual is observed minus predicted. `model_metrics.csv` contains pooled MAE/RMSE/R² and equal-athlete MAE. `fold_metrics.csv` shows variation across folds; it is not a confidence interval. `model_spec.json` records exact features, settings, missing/nonfinite policies, and target exclusions.

There is no canonical OBP benchmark split. This split estimates transfer to held-out athletes in the source cohort, not to future sessions or an external MLB population. Features are same-pitch measurements, so this is retrospective prediction. Repeatedly changing features/alpha based on these displayed results would turn the folds into model-selection data; a later tuning study needs nested athlete-grouped validation or a separate untouched evaluation set.

## Checks and completion

Run `uv run --frozen pytest -q` after fetch to include cached real-data integration tests. Without the source cache those tests explicitly skip rather than fabricate data. Unit/UI fixtures are marked synthetic in test code and never enter reported scientific results. No test needs copyrighted footage or a private API.

The complete workflow writes `run_metadata.json` last, recording artifact hashes, project Git revision and dirty status, source-code hashes, and installed library versions. Code hashes remain useful even before the first commit or with uncommitted edits. The success marker is removed before a refresh. The dashboard requires a completed run and matching hashes for analysis, predictions and metrics before displaying model errors, preventing stale files from masquerading as current output. Existing generated files may remain after a failure; they are not a completed result without the marker. Audit-only runs are useful for data exploration but do not establish completed modeling.

To validate all recorded artifact hashes:

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

## Dashboard processes and reuse

Run `uv run --frozen streamlit run app.py --server.headless true` from the project root. The app reads reports beside `app.py`; set nonsecret `PITCHING_REPORT_DIR` to use another report folder. Changing filters does not fit or tune a model. Stop the process with Ctrl+C. A new cloud machine must start its own process; live servers do not persist through environment publication. The localhost service is for local validation/use, not a hosted public portfolio deployment.

Each Codex cloud task is already isolated. Use its existing checkout; do not create an additional worktree unless explicitly requested. The new project is a separate local Git repository. To work in another machine, transfer this checkout or push it to a repository you control, then select that repository in your Codex environment. A local commit does not create a GitHub repository or publish a website. The older MATLAB/Octave project is a separate repository and is not needed for these commands.

## Hosted reference snapshot

The optional `streamlit_app.py` entry point reads the committed `assets/demo` reference reports. `scripts/export_demo_snapshot.py` is an explicit maintainer operation after a verified pipeline run; it checks the producing code, source-manifest, lockfile and output hashes before export. The hosted reader rechecks file hashes and never downloads data, retrains models, or writes into the source snapshot. See [GITHUB_PUBLISH.md](GITHUB_PUBLISH.md). This snapshot is a data-derived publication under the upstream terms, separate from ignored working `reports/`.
