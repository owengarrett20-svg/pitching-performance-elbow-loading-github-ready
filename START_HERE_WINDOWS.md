# Open the updated pitching viewer on Windows

This release includes the prepared motion/teaching videos, traces, and a verified reference-report snapshot. Watching them does not require FFmpeg, motion-capture software, the optional ezc3d dependency, or the large source archives.

1. Stop your current Streamlit server by pressing **Ctrl+C** in its VS Code terminal.
2. Download and extract the new `pitching-performance-elbow-loading-github-ready.zip` into a **new folder**, preserving your existing working copy.
3. In VS Code, choose **File → Open Folder** and select the extracted folder containing `app.py`, `assets`, and this file.
4. Choose **Terminal → New Terminal**. Run each command separately:

```powershell
uv sync --frozen
```

```powershell
uv run --frozen streamlit run streamlit_app.py
```

5. Open the **Local URL** printed by Streamlit. Select the new **Watch pitches** tab.

## First exploration

- Leave the sidebar filters empty to see the three prepared examples.
- Choose a recorded study pitch at 69.5, 85.3, or 94.4 mph and play its marker replay.
- Expand **Inspect a paused marker frame** and enable the frame inspector to move through the observed motion.
- Watch the short instructional animation and choose one of the five measurement explanations.
- Inspect the processed trace and move its interval slider. Compare the maximum in the selected window with the source's published peak.
- Use **Open the official OBP-CV camera example** for real camera footage. The optional Google Drive embed depends on its public sharing settings and your connection.

The study replays are animations of actual measured markers, not camera recordings. Only three prepared study pitches are included. The separate 62.7 mph camera demonstration has no verified link to the 411 study pitches, so its footage is never paired with their metrics. A single video does not directly measure elbow joint moment or injury risk.

The precomputed Phase 1 reports are already included. To regenerate them later, run `uv run --frozen pitching run`, which fetches the small pinned CSV/documentation files if absent. This does not download large motion archives. See `README.md` and `docs/VIDEO_METHODS.md` for science, provenance, and licensing.

## Put it on GitHub and deploy

See [docs/GITHUB_PUBLISH.md](docs/GITHUB_PUBLISH.md) for VS Code publication steps. Streamlit Community Cloud needs a published GitHub repository and branch. Use `main`, entry point `streamlit_app.py`, and Python 3.12. No public repository or deployment has been created by these local files.
