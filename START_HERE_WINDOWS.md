# Open the Phase 2 pitching research dashboard on Windows

**Updating your existing GitHub-connected project?** Follow
[the Phase 2 upgrade instructions](docs/PHASE2_UPGRADE_WINDOWS.md). They use the
provided Git bundle to keep your history, GitHub remote, and existing website.

This release includes the prepared motion/teaching videos, traces, and a verified reference-report snapshot. Watching them does not require FFmpeg, motion-capture software, the optional ezc3d dependency, or the large source archives.

1. Stop your current Streamlit server by pressing **Ctrl+C** in its VS Code terminal.
2. Download and extract `pitching-performance-elbow-loading-phase2.zip` into a **new folder**, preserving your existing working copy.
3. In VS Code, choose **File → Open Folder** and select the extracted folder containing `app.py`, `assets`, and this file.
4. Choose **Terminal → New Terminal**. Run each command separately:

```powershell
uv sync --frozen
```

```powershell
uv run --frozen streamlit run streamlit_app.py
```

5. Open the **Local URL** printed by Streamlit. Select **Phase 2 comparisons** for
   the new study, or **Watch pitches** for the motion examples.

## Read the Phase 2 study

- Compare age/body-size, kinematic, and combined predictors against the mean baseline.
- Select pitch speed or elbow moment and inspect the paired conditional intervals.
- Review all ten refitted athlete partitions and the downloadable research report.
- Sidebar filters leave the prespecified full-cohort comparison unchanged.

Start with [the results](docs/PHASE2_RESULTS.md) and
[the frozen analysis plan](docs/PHASE2_ANALYSIS_PLAN.md).

## First exploration

- Leave the sidebar filters empty to see the three prepared examples.
- Choose a recorded study pitch at 69.5, 85.3, or 94.4 mph and play its marker replay.
- Expand **Inspect a paused marker frame** and enable the frame inspector to move through the observed motion.
- Watch the short instructional animation and choose one of the five measurement explanations.
- Inspect the processed trace and move its interval slider. Compare the maximum in the selected window with the source's published peak.
- Use **Open the official OBP-CV camera example** for real camera footage. The optional Google Drive embed depends on its public sharing settings and your connection.

The study replays are animations of actual measured markers, not camera recordings. Only three prepared study pitches are included. The separate 62.7 mph camera demonstration has no verified link to the 411 study pitches, so its footage is never paired with their metrics. A single video does not directly measure elbow joint moment or injury risk.

The precomputed Phase 1 and Phase 2 reports are included. To regenerate both,
run `uv run --frozen pitching phase2`, which fetches the small pinned source
files if absent. This does not download large motion archives. The
`pitching run` command reproduces Phase 1 only. See `README.md` and
`docs/VIDEO_METHODS.md` for science, provenance, and licensing.

## Put it on GitHub and deploy

The existing repository is
[owengarrett20-svg/pitching-performance-elbow-loading-github-ready](https://github.com/owengarrett20-svg/pitching-performance-elbow-loading-github-ready).
Use [the upgrade guide](docs/PHASE2_UPGRADE_WINDOWS.md) to publish this update.
The existing deployment continues to use `main`, `streamlit_app.py`, and Python
3.12. Phase 2 reaches the public app after the updated branch is pushed and the
deployment rebuild finishes.
