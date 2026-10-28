# Install the Phase 2 update in your existing GitHub project

This update adds the predictor-group study, paired athlete-cluster uncertainty,
partition sensitivity, figures, tests, and a new **Phase 2 comparisons** dashboard
tab. It includes your published README and keeps the same repository and
Streamlit entry point.

The delivered update is based on your published commit
`d51421d88daf8dbbf597d7e7c357b06565d65656`. Its Git bundle contains that history
plus the frozen plan, implementation, and computed results. The code and results
are prepared locally; they reach your existing website after you push the update.

## Update the existing Windows checkout

1. Download **`pitching-phase2-update.bundle`** into your normal **Downloads**
   folder. Keep that exact filename.
2. In VS Code, open your existing GitHub-connected
   `pitching-performance-elbow-loading-github-ready` project folder.
3. Stop a running Streamlit process with **Ctrl+C** and open a PowerShell terminal.
4. Run `git status`. Finish or preserve any outstanding edits before updating.
5. Run these commands one at a time:

```powershell
git fetch "$env:USERPROFILE\Downloads\pitching-phase2-update.bundle" main
```

```powershell
git merge --ff-only FETCH_HEAD
```

```powershell
uv sync --frozen
```

```powershell
uv run --frozen streamlit run streamlit_app.py
```

Open the local URL and select **Phase 2 comparisons**. You should see the four
models, both outcome choices, conditional paired intervals, partition
sensitivity, and report downloads. The full-cohort comparisons remain fixed
when sidebar filters change; the athlete-detail table follows the selected
athletes.

The bundle updates files and history through Git. Your existing `origin` and
GitHub login remain configured. If the merge reports that a fast-forward is
impossible, retain the current files and inspect the histories before resolving
the divergence. A force push is not part of this update.

## Update the existing website

After reviewing the local app, press **Ctrl+C** and run:

```powershell
git push origin main
```

Streamlit Community Cloud should rebuild the existing deployment from its
configured branch. The entry point is still **`streamlit_app.py`**, Python is
still **3.12**, and the existing public app URL remains the same.

Check GitHub's **Actions** tab and the Streamlit build logs. After the deployment
finishes, refresh the public app and verify that **Phase 2 comparisons** appears.
The prepared snapshot contains the entire study; the hosted app does not fit
models or bootstrap data for visitors.

## Reproduce the science yourself

These commands are optional for viewing the prepared dashboard and required for
independently regenerating the research outputs:

```powershell
uv sync --frozen --extra dev --extra motion
uv run --frozen pitching fetch
uv run --frozen pitching phase2 --offline
uv run --frozen pytest -q
uv run --frozen python scripts/export_demo_snapshot.py
```

The Phase 2 command regenerates Phase 1 first, then applies the committed
`analysis/phase2_plan.json`. It writes results under `reports/phase2/` and records
the source, code, plan, dependencies, checksums, and Phase 1 reproduction check.
Large motion archives are unnecessary for this study. Archive-dependent motion
tests may skip when those archives are absent.

The Phase-1-only `pitching run` command remains available. Its fresh completion
marker intentionally does not bind an older Phase 2 study. Use `pitching phase2`
when you want a current, complete two-phase snapshot.

## Full source archive

The separate **`pitching-performance-elbow-loading-phase2.zip`** is a complete
source-and-reference-results copy. It can be extracted into a new folder for
inspection and local use with `streamlit_app.py`. It excludes `.git`, environments,
caches, and large raw archives. Use the Git bundle above to update your existing
connected repository while retaining its history.

## Reading the result

Start with [PHASE2_RESULTS.md](../PHASE2_RESULTS.md), then inspect the
[frozen analysis plan](../PHASE2_ANALYSIS_PLAN.md).

The selected kinematic summaries improve observed speed prediction in this
cohort. Their incremental value for elbow moment beyond age, mass, and height
remains uncertain: its conditional interval includes zero. The intervals describe
fixed held-out errors, rather than full model-training uncertainty. No injury,
causal, or external-validation claim follows from this update.

OBP data and derivatives retain the upstream restrictions in
[LICENSING.md](../LICENSING.md).
