# Open the Phase 3 pitching research dashboard on Windows

**Updating your existing GitHub-connected project?** Follow
[the Phase 3 upgrade instructions](docs/PHASE3_UPGRADE_WINDOWS.md). They use
`pitching-phase3-update.bundle` to preserve your history, GitHub remote, and
existing website. Phase 2 is already published; this version 0.5.0 update changes
the research experience while preserving its models, data, and findings.

This release includes the prepared motion/teaching videos, traces, and a verified
reference-report snapshot. Viewing the demonstration does not require FFmpeg,
motion-capture software, the optional ezc3d dependency, or the large source archives.

## Open a fresh source copy

1. Stop your current Streamlit server by pressing **Ctrl+C** in its VS Code terminal.
2. Download and extract `pitching-performance-elbow-loading-phase3.zip` into a **new folder**, preserving your existing working copy.
3. In VS Code, choose **File → Open Folder** and select the extracted folder containing `app.py`, `assets`, and this file.
4. Choose **Terminal → New Terminal**. Run each command separately:

```powershell
uv sync --frozen
```

```powershell
uv run --frozen streamlit run streamlit_app.py
```

5. Open the **Local URL** printed by Streamlit. Begin with **Start here**.

The ZIP is a source copy without Git history or a configured remote. For an
existing connected project, use the bundle upgrade guide above instead.

## Explore the five views

- **Start here:** read the research question, watch a measured-marker replay, and inspect the main findings.
- **Explore pitches:** hover or select recorded pitches, change axes, switch to athlete averages, compare two observations, and share a checked pitch link.
- **Watch motion:** inspect the three prepared marker replays, paused frames, processed traces, and expandable measurement explanations.
- **Study results:** select pitch speed or elbow moment, compare average prediction errors, and open the detailed audit and conditional intervals.
- **Methods & collaboration:** read the definitions, data-quality reports, limitations, and guidance for a non-sensitive research introduction.

Only the active view renders. Sidebar filters change displayed observations;
they leave the planned full-cohort study comparisons and intervals unchanged.
An athlete average summarizes released pitch measurements, not a single delivery
or a time-averaged movement trace. Differences between observed pitches do not
predict the effect of changing mechanics.

## Inspect the motion evidence

- In **Watch motion**, choose a recorded example at 69.5, 85.3, or 94.4 mph.
- Expand **Inspect a paused marker frame** and enable the frame inspector to move through the observed motion.
- Open the instructional animation or one of the five measurement explanations.
- Inspect the processed trace and its selected interval alongside the published peak, without assuming alignment with the marker replay.
- Use **Open the official OBP-CV camera example** for the separate camera demonstration. The optional Google Drive embed depends on source availability, public sharing settings, and your connection.

The study replays animate measured skin markers. Only three prepared study
pitches are included. The separate 62.7 mph camera demonstration has no verified
link to the 411 study pitches; its footage is never paired with their metrics.
Marker and processed-trace clocks have no verified alignment. A single video
does not directly measure elbow joint moment or injury risk.

## Read or reproduce the research

Start with [the study summary](docs/STUDY_SUMMARY.md),
[the Phase 2 results](docs/PHASE2_RESULTS.md), and
[the frozen analysis plan](docs/PHASE2_ANALYSIS_PLAN.md).

The precomputed Phase 1 and Phase 2 reports are included. To regenerate both,
run `uv run --frozen pitching phase2`, which fetches the small pinned source
files if absent. This does not download large motion archives. The
`pitching run` command reproduces Phase 1 only. Follow
[the reproducibility guide](docs/REPRODUCIBILITY.md) for complete checks.

## Update the same GitHub repository and website

The existing repository is
[owengarrett20-svg/pitching-performance-elbow-loading-github-ready](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready).
Use [the Phase 3 upgrade guide](docs/PHASE3_UPGRADE_WINDOWS.md) to publish this
update. Keep the existing deployment configured for `main`, `streamlit_app.py`,
and Python 3.12. The public app updates after the branch is pushed and the
Streamlit rebuild finishes; check Actions and deployment logs.

The [Phase 3 experience notes](docs/PHASE3_EXPERIENCE.md) explain the presentation
scope. The [collaboration guide](docs/COLLABORATION.md) describes future work on
independently authorized data. A public introduction must contain no confidential
athlete data. OBP's additional professional-sports affiliation restriction still
applies; the software's MIT license does not grant restricted data rights.
