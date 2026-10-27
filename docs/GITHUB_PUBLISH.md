# Publish the project to GitHub and Streamlit Community Cloud

The project now has a
[published repository](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready)
and a [live reference dashboard](https://pitching-performance-elbow-loading-app-ready-bpn9pb4j3udcqxo9k.streamlit.app/).
Phase 4 is published at commit `ad4cd71`. To add Phase 5 version 0.7.0 to
that project, use [PHASE5_UPGRADE_WINDOWS.md](PHASE5_UPGRADE_WINDOWS.md) with
`pitching-phase5-update.bundle`. Confirm the file exists and passes
`git bundle verify` before fetching; stop on a failed fetch rather than merging
an older `FETCH_HEAD`. Keep the repository, remote, and Streamlit address.
The initial-publication instructions below remain useful for a new copy or
permitted fork; earlier upgrade guides remain as historical records.

The Streamlit message **“The app's code is not connected to a remote GitHub repository”** means that the folder running on your computer has not been published to GitHub. A downloaded ZIP is a source copy; it does not establish a remote repository.

This release includes a separate hosted entry point and a verified reference-data snapshot so that a clean GitHub checkout can display the complete demonstration without downloading source CSVs or training models.

## Windows: publish from VS Code

1. Download and extract `pitching-performance-elbow-loading-phase5.zip` into a new folder so your existing working copy is preserved. This source ZIP contains no Git history or configured remote. Open the folder containing `app.py`, `streamlit_app.py`, `pyproject.toml`, and `assets` in VS Code.
2. In **Terminal → New Terminal**, run `git --version`. If Git is missing, install Git for Windows with `winget install --id Git.Git --exact --source winget`, then fully restart VS Code.
3. Open **Source Control** with **Ctrl+Shift+G**. Choose **Initialize Repository** if offered. If a Git repository already exists, continue with it.
4. Commit the project files with a descriptive message. The supplied `.gitignore` excludes environments, source archives, local reports, caches, secrets, `local_studies/` inputs/bundles/results, and `local_applications/` drafts. Review files before publishing; an ignore rule is not a review of data permissions. The `assets/demo` snapshot and prepared `assets/pitch_catalog` arrays are intentionally included. Keep original archives, private CVs, and tailored application drafts out of the public repository. If Git asks for your identity, use your own name and GitHub-verified email or the private noreply address GitHub supplies in your account email settings.
5. Open the Command Palette with **Ctrl+Shift+P**, search **Publish to GitHub**, and follow the sign-in flow. Use your account and a new repository named `pitching-performance-elbow-loading`. Choose the visibility appropriate for your permitted research portfolio use. Do not enter access tokens into this chat or source files.
6. Open the resulting GitHub repository in your browser. Confirm that `streamlit_app.py`, `uv.lock`, `requirements.txt`, `.github/workflows/tests.yml`, and `assets/demo/reports/analysis.csv` are present. The original large source archives, your `.venv`, and new-data studies or private model bundles should not be present.
7. Check the **Actions** tab after the first push. The included workflow will run the locked installation, small source fetch, tests, and lint. Those remote checks have not run until the workflow actually executes in your GitHub repository.

If the VS Code publication command is unavailable, create an empty repository on GitHub and use the remote URL GitHub provides. Do not initialize another README/license there when this folder already has them. From an existing committed local repository:

```powershell
# Replace the URL with the actual empty repository you created.
git remote add origin https://github.com/YOUR_ACCOUNT/pitching-performance-elbow-loading.git
git push -u origin main
```

If `origin` already exists, inspect it with `git remote -v` rather than replacing it blindly. Use normal GitHub browser authentication/Git Credential Manager. Do not force-push to resolve an unexpected remote history; inspect the history first.

## Deploy the read-only reference demonstration

In Streamlit Community Cloud, create an app from the GitHub repository:

| Setting | Value |
| --- | --- |
| Repository | The repository you just published |
| Branch | `main`, or the actual branch you published |
| Main file path | **`streamlit_app.py`** |
| Python version | **3.12** in Advanced settings |
| Secrets | None required |

Select **Deploy**. Keep `uv.lock`, `pyproject.toml`, and the generated `requirements.txt` in the repository root. The lockfile specifies the analysis environment; the requirements export provides pinned runtime dependencies plus the local package for pip-based installation. The entry point also makes the source directory explicit.

The hosted entry point verifies all `assets/demo` snapshot hashes before opening the dashboard. It displays 411 source pitches, 100 athletes, the unchanged Phase 1/2 findings, and the bundled motion/teaching assets through eight focused views, including the Research brief and searchable paired-pitch workspace. Only the active view renders. It does not need your local `reports/` or `data/` directories and does not fetch data or retrain on a page interaction. The comparison workspace reads the verified 411-pitch marker catalog and links selected rows to their exact replays, markers, and values. The original three MP4/processed-trace examples remain a separate subset. Independent controls or simultaneous starts do not establish event alignment or camera coverage. Downloaded reports describe the public reference cohort. The New-data lab page contains instructions/templates rather than an athlete-file uploader or remotely executed model fitting. The optional external Google Drive recording still depends on its source availability and sharing settings.

The normal `app.py` remains the research entry point for regenerated OBP reports. New-data audit and external freeze/evaluate commands are explicit local workflows under an approved environment. Keep their inputs and outputs separate from `assets/demo`; the reference exporter does not authorize or automatically publish a private study.

## Preview the exact hosted path locally

```powershell
uv sync --frozen
uv run --frozen streamlit run streamlit_app.py
```

No source download is needed for that demonstration. For code contributions and complete reproducibility checks:

```powershell
uv sync --frozen --extra dev
uv run --frozen pitching fetch
uv run --frozen pytest -q
```

## Refresh the reference snapshot deliberately

After a code, model, source, or dependency change, reproduce the analysis and explicitly export a new snapshot:

```powershell
uv run --frozen pitching phase2
uv run --frozen python scripts/export_demo_snapshot.py
uv run --frozen python scripts/export_requirements.py
```

Commit the snapshot manifest and all listed files together. The exporter verifies output hashes and the producing code/source/lock hashes. It refuses stale or corrupted reports rather than publishing them under a new label. The hosted reader is read-only and checks the snapshot again.

## Licensing and publication status

Original software is MIT. The published reference tables, figures, marker clips, and teaching/documentation adaptations retain OBP's data terms: CC BY-NC-SA 4.0 plus its additional professional-sports/financial-analysis affiliation exclusion. Preserve attribution and the full upstream terms. This is an independent research portfolio; the code license does not authorize restricted organizational or commercial reuse. See [LICENSING.md](LICENSING.md).

The repository and dashboard URLs are recorded in the README. Phase 4 has been
pushed; the prepared Phase 5 version 0.7.0 update remains local until pushed and
rebuilt. Check the new Actions run and deployment logs, then inspect all eight
views, table search/selection, both comparison identities, marker controls,
report/brief downloads, and shared links. A successful local run does not
establish that remote CI or deployment passed. A tagged release and archival DOI
remain separate steps; add a DOI only if an archival service actually issues one.

Read [PHASE3_EXPERIENCE.md](PHASE3_EXPERIENCE.md) for the earlier interaction
milestone, [MOTION_LAB.md](MOTION_LAB.md) for measurement inspection, and
[ATHLETE_REPORTS.md](ATHLETE_REPORTS.md) for report scope. The
[new-data guide](NEW_DATA_GUIDE.md) and
[external-evaluation guide](EXTERNAL_VALIDATION.md) describe the implemented
local tools for a future authorized study. No independent external evaluation
has been completed in this release. The [collaboration guide](COLLABORATION.md)
describes permission and communication requirements. The public introduction route provides no confidential
player-data upload service; it does not establish a team partnership or extend
OBP data-use permissions.


## Publish the research portfolio with accurate evidence

The [research brief](RESEARCH_BRIEF.md),
[contribution/AI-assistance record](CONTRIBUTIONS_AND_AI.md), and
[PhD application guide](PHD_APPLICATION_GUIDE.md) distinguish a software portfolio
from a publication or completed independent validation. The generated public
brief can be committed under `docs/research_brief/`; preserve its provenance,
source terms, and evidence scope. Check that it matches the published reference
snapshot before sharing it in an application.

Public project documentation contains no uploaded CV or institution-specific
private application drafts. Those materials stay outside the public repository.
An ignore rule does not authorize publication of private content. Follow the
program's current submission and authorship rules rather than uploading an
unsolicited supplement.
