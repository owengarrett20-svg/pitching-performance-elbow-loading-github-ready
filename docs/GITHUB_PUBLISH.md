# Publish the project to GitHub and Streamlit Community Cloud

The project now has a
[published repository](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready)
and a [live reference dashboard](https://pitching-performance-elbow-loading-app-ready-bpn9pb4j3udcqxo9k.streamlit.app/).
Phase 2 is already published at commit `a2f339e`. To add the Phase 3 version
0.5.0 experience update to that existing project, use
[PHASE3_UPGRADE_WINDOWS.md](PHASE3_UPGRADE_WINDOWS.md) with
`pitching-phase3-update.bundle`. Keep the same repository, remote, and Streamlit
app. The initial-publication instructions below remain useful for a new copy or
permitted fork; the historical Phase 2 guide remains available separately.

The Streamlit message **“The app's code is not connected to a remote GitHub repository”** means that the folder running on your computer has not been published to GitHub. A downloaded ZIP is a source copy; it does not establish a remote repository.

This release includes a separate hosted entry point and a verified reference-data snapshot so that a clean GitHub checkout can display the complete demonstration without downloading source CSVs or training models.

## Windows: publish from VS Code

1. Download and extract `pitching-performance-elbow-loading-phase3.zip` into a new folder so your existing working copy is preserved. This source ZIP contains no Git history or configured remote. Open the folder containing `app.py`, `streamlit_app.py`, `pyproject.toml`, and `assets` in VS Code.
2. In **Terminal → New Terminal**, run `git --version`. If Git is missing, install Git for Windows with `winget install --id Git.Git --exact --source winget`, then fully restart VS Code.
3. Open **Source Control** with **Ctrl+Shift+G**. Choose **Initialize Repository** if offered. If a Git repository already exists, continue with it.
4. Commit the project files with a descriptive message. The supplied `.gitignore` excludes environments, source archives, local reports, caches, and secrets. The small `assets/demo` snapshot is intentionally included. If Git asks for your identity, use your own name and GitHub-verified email or the private noreply address GitHub supplies in your account email settings.
5. Open the Command Palette with **Ctrl+Shift+P**, search **Publish to GitHub**, and follow the sign-in flow. Use your account and a new repository named `pitching-performance-elbow-loading`. Choose the visibility appropriate for your permitted research portfolio use. Do not enter access tokens into this chat or source files.
6. Open the resulting GitHub repository in your browser. Confirm that `streamlit_app.py`, `uv.lock`, `requirements.txt`, `.github/workflows/tests.yml`, and `assets/demo/reports/analysis.csv` are present. The original large source archives and your `.venv` should not be present.
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

The hosted entry point verifies all `assets/demo` snapshot hashes before opening the dashboard. It displays 411 source pitches, 100 athletes, the unchanged Phase 1/2 findings, and the bundled motion/teaching assets through five focused views. Only the active view renders. It does not need your local `reports/` or `data/` directories and does not fetch data or retrain on a page interaction. The optional external Google Drive recording still depends on its source availability and sharing settings.

The normal `app.py` remains the research entry point for regenerated local reports. This distinction keeps a stable public reference demonstration separate from new analyses you run locally.

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

The repository and dashboard URLs are recorded in the README. Phase 2 has been
pushed; the prepared Phase 3 version 0.5.0 update remains local until pushed to
that repository and rebuilt by the deployment. Check the new GitHub Actions run
and deployment logs after pushing, then inspect all five views, the study
findings, and shared pitch links. A successful local run does not establish that
remote CI or deployment has passed. Once stable, create a GitHub release from
the tested commit; add an archive DOI only if an archival service actually
issues one.

Read [PHASE3_EXPERIENCE.md](PHASE3_EXPERIENCE.md) for interaction and presentation
checks. The [collaboration guide](COLLABORATION.md) describes the future
authorized-data workflow. The public introduction route provides no confidential
player-data upload service; it does not establish a team partnership or extend
OBP data-use permissions.
