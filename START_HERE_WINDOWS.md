# Open the Phase 4 pitching research dashboard on Windows

**Updating your existing GitHub-connected project?** Follow
[the Phase 4 upgrade instructions](docs/PHASE4_UPGRADE_WINDOWS.md). They verify
`pitching-phase4-update.bundle` before fetching it, then preserve your Git
history, GitHub remote, and existing website. Phase 3 is published at `edf5c05`;
this version 0.6.0 update adds motion/reporting and new-data tools while retaining
the Phase 1/2 data and scientific findings.

The release includes the prepared motion/teaching assets and a verified
reference-report snapshot. Viewing it requires no FFmpeg, MATLAB installation,
optional ezc3d dependency, or large motion archive.

## Open a fresh source copy

1. Stop your current Streamlit server with **Ctrl+C** in its VS Code terminal.
2. Download and extract `pitching-performance-elbow-loading-phase4.zip` into a **new folder**, preserving your existing working copy.
3. In VS Code, choose **File → Open Folder** and select the extracted folder containing `app.py`, `assets`, and this file.
4. Choose **Terminal → New Terminal**. Run each command separately, stopping if one fails:

```powershell
uv sync --frozen
```

```powershell
uv run --frozen streamlit run streamlit_app.py
```

5. Open the **Local URL** printed by Streamlit. Begin with **Start here**.

The ZIP is a source copy without Git history or a configured remote. Use the
bundle guide above to update an existing connected project. Before fetching,
`Test-Path` must find the bundle and `git bundle verify` must say it is okay.

## Explore the seven views

- **Start here:** research question, measured-marker replay, and main findings.
- **Explore pitches:** hover/select recorded pitches, change axes, inspect athlete averages, compare observations, and share checked pitch links.
- **Watch motion:** inspect measured markers in 3D and move the independent frame and processed-signal controls. Open the existing replays and measurement lessons when useful.
- **Athlete reports:** select an athlete and download an illustrated, printable research report or source-attributed tables/metadata. Open the HTML in a browser and use **Print → Save as PDF** for a PDF copy.
- **Study results:** compare saved errors for speed or elbow moment, then inspect the detailed audit and conditional intervals.
- **New-data lab:** review templates and local preparation/freezing/evaluation steps for an independently authorized study. The public app accepts no athlete-data uploads.
- **Methods & collaboration:** definitions, data-quality reports, limitations, and guidance for a non-sensitive research introduction.

Only the active view renders. Explorer filters change displayed observations;
they do not recompute the full-cohort study comparisons or intervals. Athlete
reports describe the available sample, rather than an athlete's complete career,
longitudinal development, or reliable consistency.

## Understand the motion evidence

The three prepared study pitches have observed speeds of 69.5, 85.3, and
94.4 mph. Their visualizations use measured skin markers, not camera footage or
a validated anatomical joint-center model. The marker and processed-signal clocks
have no verified alignment, so the controls remain independent. Matching grids
or published peaks does not validate synchronization or inverse dynamics.

The separate official 62.7 mph OBP-CV camera example has no verified identity link
to the 411 study pitches. Its playback depends on source sharing settings and
availability. No camera coverage is assumed for all pitches. A single video
does not directly measure elbow joint moment or injury risk.

See [MOTION_LAB.md](docs/MOTION_LAB.md),
[ATHLETE_REPORTS.md](docs/ATHLETE_REPORTS.md), and
[VIDEO_METHODS.md](docs/VIDEO_METHODS.md) for definitions and provenance.

## Reproduce the existing research or prepare a new study

Start with [the study summary](docs/STUDY_SUMMARY.md),
[the Phase 2 results](docs/PHASE2_RESULTS.md), and
[the frozen analysis plan](docs/PHASE2_ANALYSIS_PLAN.md).
The supplied reports are derived from the existing 411-pitch cohort. Run
`uv run --frozen pitching phase2` to regenerate both phases from the small
pinned source files; `pitching run` remains Phase 1 only. Follow
[REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) for checks and output provenance.

For a new cohort, follow [NEW_DATA_GUIDE.md](docs/NEW_DATA_GUIDE.md) and
[EXTERNAL_VALIDATION.md](docs/EXTERNAL_VALIDATION.md). Keep approved data and
outputs local or in the agreed organizational environment; `local_studies/` is
ignored by Git. The freeze/evaluate workflow is implemented, but this release
contains no actual external-validation study or result.

## Update the same website

Keep the existing repository
[owengarrett20-svg/pitching-performance-elbow-loading-github-ready](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready)
and deployment configuration: `main`, `streamlit_app.py`, Python 3.12. Use
[the Phase 4 guide](docs/PHASE4_UPGRADE_WINDOWS.md) to publish this update; check
Actions and deployment logs after the push.

A public collaboration introduction must contain no confidential athlete data.
OBP's additional professional-sports/financial-analysis affiliation restriction
continues to govern its data and derivatives; the original software's MIT
license does not grant those data rights. See
[LICENSING.md](docs/LICENSING.md) and [COLLABORATION.md](docs/COLLABORATION.md).
