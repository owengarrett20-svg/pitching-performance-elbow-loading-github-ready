# Upgrade your existing project to Phase 4 on Windows

Phase 3 is published in your existing repository at `edf5c05`. Version 0.6.0
adds an interactive measured-marker lab, downloadable athlete research reports,
and local tools for auditing authorized new data and freezing/evaluating models.
The existing Phase 1/2 source data, model comparisons, and scientific findings
remain unchanged. The new workflow does not mean an external study has already
been performed.

Use `pitching-phase4-update.bundle` with your existing GitHub-connected folder.
The separate `pitching-performance-elbow-loading-phase4.zip` is a complete
source copy for a fresh folder; it has no Git history or configured remote.

## 1. Download and verify the bundle first

Download **`pitching-phase4-update.bundle`** into your normal **Downloads** folder.
Check the exact filename: browser downloads can acquire a suffix such as `(1)`.
Do not substitute the source ZIP for the bundle.

In VS Code, open your existing project and its PowerShell terminal. Stop any
running Streamlit server with **Ctrl+C**. Run each command below separately and
continue only when it succeeds.

```powershell
Test-Path "$env:USERPROFILE\Downloads\pitching-phase4-update.bundle"
```

This must print **True**. If it prints False, find the downloaded file in your
browser's download list, move it to Downloads or use its actual path, and check
its filename. The error “does not appear to be a git repository” can refer to a
missing or unreadable local bundle; it does not establish a GitHub login problem.

```powershell
git bundle verify "$env:USERPROFILE\Downloads\pitching-phase4-update.bundle"
```

Continue only when verification says the bundle **“is okay.”** If verification
fails, stop and redownload the bundle. Do not run the merge against an old
`FETCH_HEAD`: a later “Already up to date” can refer to an earlier successful
fetch and does not confirm the Phase 4 update.

## 2. Update the existing project and preview it

```powershell
git status
```

Continue when the working tree is clean. Preserve or commit your own edits
before merging. Do not discard changes or force a merge around unexpected
history. The bundle permits a fast-forward from the published Phase 3 history.

```powershell
git fetch "$env:USERPROFILE\Downloads\pitching-phase4-update.bundle" main
```

If fetch fails, stop here. Only after a successful fetch, run:

```powershell
git merge --ff-only FETCH_HEAD
```

```powershell
uv sync --frozen
```

```powershell
uv run --frozen streamlit run streamlit_app.py
```

Open the **Local URL** printed by Streamlit. The reference demonstration needs
no raw-data download, model fitting, MATLAB license, FFmpeg, or large motion
archive. A source ZIP can preview the same app but does not update your existing
Git history.

## 3. Inspect the additions

- **Start here:** research question, recorded-marker preview, and verified findings.
- **Explore pitches:** recorded-pitch charts, athlete averages, observed A/B
  comparisons, and checked share links.
- **Watch motion:** interactive marker inspection and processed-trace controls,
  with independent clocks and source/measurement explanations. Existing replays
  and the separate camera demonstration remain available.
- **Athlete reports:** summaries of an athlete's available recorded pitches,
  verified saved errors when eligible, and self-contained HTML/CSV downloads.
  Open the HTML in a browser and use **Print → Save as PDF** if a PDF is useful.
- **Study results:** unchanged full-cohort comparisons, uncertainty scope,
  prediction errors, and the detailed audit.
- **New-data lab:** mapping/protocol templates and explicit local CLI steps.
  The public app does not accept athlete files or run external model fitting.
- **Methods & collaboration:** definitions, provenance, limitations, and a
  non-sensitive public introduction route.

Marker and processed-signal clocks have no verified alignment. Do not interpret
independent cursors as synchronized event frames. Athlete reports describe a
few recorded pitches from one released session, not longitudinal progress or
stable consistency. Elbow varus moment remains a net joint-loading measure,
without injury or causal coaching claims.

## 4. Publish to the same repository and website

When the local preview looks right, return to the terminal, press **Ctrl+C**,
and run:

```powershell
git push origin main
```

Keep the current repository and remote:
[owengarrett20-svg/pitching-performance-elbow-loading-github-ready](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready).
The existing deployment uses `main`, `streamlit_app.py`, and Python 3.12.
Check GitHub **Actions** and Streamlit deployment logs after pushing. Phase 4
reaches the public app only after the branch is pushed and the rebuild succeeds.

The address remains:
<https://pitching-performance-elbow-loading-app-ready-bpn9pb4j3udcqxo9k.streamlit.app/>.

## Use the research tools separately

Viewing the public reference app does not require running these tools. For a
new study, begin with [NEW_DATA_GUIDE.md](NEW_DATA_GUIDE.md), then
[EXTERNAL_VALIDATION.md](EXTERNAL_VALIDATION.md). Review rights, identifiers,
units, definitions, signs, and protocol before preparing data. Keep authorized
inputs and outputs in the approved environment under ignored `local_studies/`;
do not publish them with the reference snapshot.

The study requires an actual independently authorized evaluation cohort. No
external performance result is supplied or claimed by this update. OBP's
professional-sports/financial-analysis affiliation restriction still applies,
including to models or reports derived from those data. The original software's
MIT license does not grant restricted data rights.

For development checks and the unchanged OBP analysis, follow
[REPRODUCIBILITY.md](REPRODUCIBILITY.md).
